# Gaussian Splatting — Полный справочник команд

Детальный разбор всех шагов, параметров и ошибок. Использовать как справочник при работе с пайплайном.

---

## Окружение и пути

```
Python:          C:\work\nerf\venv\Scripts\python.exe
pip:             C:\work\nerf\venv\Scripts\pip.exe
ns-train:        C:\work\nerf\venv\Scripts\ns-train.exe
ns-export:       C:\work\nerf\venv\Scripts\ns-export.exe
ns-process-data: C:\work\nerf\venv\Scripts\ns-process-data.exe
COLMAP:          C:\work\nerf\colmap\bin\colmap.exe (через C:\work\nerf\colmap_wrapper.bat)
```

ВАЖНО: COLMAP 3.9.1, не 3.13+ (нарушена совместимость CLI с nerfstudio 1.1.5).

---

## Шаг 1: Подготовка видеоматериала

### Требования к видео
- Источник: DJI дрон, 4K (3840x2160), 50fps, формат HEVC/MOV
- Минимум 70-80% перекрытие между кадрами
- Несколько облётов сцены с разных ракурсов (6 видео = отличное покрытие)
- Избегать резких поворотов и смаза движения

### Определение цветового профиля

Открыть `.SRT` файл рядом с видео:
```
[color_md : normal]     -> Rec.709, LUT не нужен
[color_md : d_cinelike] -> D-Cinelike
[color_md : d_log_m]    -> D-Log M, нужна LUT конвертация в Rec.709
```

Визуальный признак D-Log M: нет настоящих чёрных, всё молочно-серое.

Если D-Log M:
```bash
ffmpeg -i input.mp4 -vf "lut3d=DLogM_to_Rec709.cube" -c:v libx264 output_rec709.mp4
```
LUT скачать с официальной страницы DJI Mavic 3 downloads.

НЕ применять D-Log M LUT к Rec.709 footage — сделает белёсым.
УРОК: content/14 оказался Rec.709/D-Cinelike — всегда проверять SRT первым.

### Извлечение кадров через ns-process-data

```bash
export PYTHONIOENCODING=utf-8
export PATH="/c/work/nerf/venv/Scripts:/c/Users/stani/AppData/Local/Microsoft/WinGet/Links:/c/work/nerf/colmap/bin:$PATH"

/c/work/nerf/venv/Scripts/ns-process-data.exe videos \
  --data "/c/work/nerf/content/14/Drone L/002" \
  --output-dir /c/work/nerf/data/mountain14 \
  --num-frames-target 300 \
  --colmap-cmd "C:/work/nerf/colmap_wrapper.bat" \
  --camera-type perspective \
  --matching-method vocab_tree \
  2>&1
```

Параметры:
- `--num-frames-target 300` — 250-350 оптимально. При 499 кадрах качество не улучшается
- `--camera-type perspective` — для DJI дронов
- `--matching-method vocab_tree` — для нескольких видео

### Скрипт extract_frames.py

```bash
# Ровно 300 кадров суммарно
python C:/work/nerf/extract_frames.py --input "content/14/Drone L/002" --output data/mountain14/images --count 300

# По fps
python C:/work/nerf/extract_frames.py --input "content/14/Drone L/002" --output data/mountain14/images --fps 2
```

После ручного извлечения запустить COLMAP через `ns-process-data images`.

---

## Шаг 2: COLMAP

### Запуск отдельно (если кадры уже извлечены)

```bash
/c/work/nerf/venv/Scripts/ns-process-data.exe images \
  --data /c/work/nerf/data/mountain14/images_raw \
  --output-dir /c/work/nerf/data/mountain14 \
  --colmap-cmd "C:/work/nerf/colmap_wrapper.bat" \
  --matching-method vocab_tree \
  --skip-image-processing \
  2>&1
```

### Выбор метода сопоставления

| Метод | Когда использовать | Скорость | Точность |
|-------|--------------------|----------|----------|
| `vocab_tree` | Несколько видео (2+) | Быстро | Хорошая |
| `sequential` | Одно непрерывное видео | Быстро | Только для видео |
| `exhaustive` | <300 кадров, максимум точности | O(N²) | Лучшая |

### Почему colmap_wrapper.bat обязателен

COLMAP.exe напрямую не находит DLL. Wrapper добавляет `C:\work\nerf\colmap\lib` в PATH:
```bat
@echo off
set SCRIPT_PATH=C:\work\nerf\colmap
set PATH=%SCRIPT_PATH%\lib;%PATH%
"%SCRIPT_PATH%\bin\colmap.exe" %*
```

### Ожидаемые результаты
- Дрон с хорошим перекрытием: ~100% matched frames
- Если < 80% — добавить больше кадров

---

## Шаг 3: Прореживание кадров

499 кадров избыточны. 246 дали лучший результат чем 499 в v4.

```python
import json, shutil

with open('/c/work/nerf/data/mountain14/transforms.json') as f:
    data = json.load(f)

frames = data['frames']
filtered = frames[::2]  # Каждый второй
data['frames'] = filtered

shutil.copy('.../transforms.json', '.../transforms_full.json.bak')

with open('.../transforms.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Было: {len(frames)}, стало: {len(filtered)}")
```

---

## Шаг 4: Обучение splatfacto-big (лучшая конфигурация v4)

### Полная команда

```bash
export PYTHONIOENCODING=utf-8
export PATH="/c/work/nerf/venv/Scripts:/c/Users/stani/AppData/Local/Microsoft/WinGet/Links:/c/work/nerf/colmap/bin:/c/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.1/bin:/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64:$PATH"
export CUDA_HOME="/c/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.1"
export CUDA_PATH="C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v13.1"
WIN_SDK_INC="/c/Program Files (x86)/Windows Kits/10/Include/10.0.22621.0"
WIN_SDK_LIB="/c/Program Files (x86)/Windows Kits/10/Lib/10.0.22621.0"
MSVC="/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207"
export INCLUDE="$MSVC/include;$WIN_SDK_INC/ucrt;$WIN_SDK_INC/shared;$WIN_SDK_INC/um"
export LIB="$MSVC/lib/x64;$WIN_SDK_LIB/ucrt/x64;$WIN_SDK_LIB/um/x64"

/c/work/nerf/venv/Scripts/ns-train.exe splatfacto-big \
  --data /c/work/nerf/data/ДАТАСЕТ \
  --output-dir /c/work/nerf/outputs \
  --experiment-name ИМЯ \
  --max-num-iterations 35000 \
  --pipeline.model.use-bilateral-grid True \
  --pipeline.model.rasterize-mode antialiased \
  --pipeline.model.use-scale-regularization True \
  --pipeline.model.stop-split-at 20000 \
  nerfstudio-data \
  --downscale-factor 2 \
  2>&1
```

### Объяснение параметров

**`splatfacto-big`** — включает: `cull_alpha_thresh=0.005`, `densify_grad_thresh=0.0005`, `sh_degree=3`

**`--max-num-iterations 35000`** — правило: минимум 15K итераций ПОСЛЕ stop_split_at

**`--pipeline.model.use-bilateral-grid True`** — per-frame коррекция освещения. Критично для теней при дроне. ВНИМАНИЕ: НЕ экспортируется в PLY

**`--pipeline.model.rasterize-mode antialiased`** — Mip-Splatting, устраняет мерцание при zoom-out

**`--pipeline.model.use-scale-regularization True`** — убирает "сигарообразные" гауссианы, шипы и floaters

**`--pipeline.model.stop-split-at 20000`** (default 15000) — больше времени на densification

**`nerfstudio-data --downscale-factor 2`** — 1080p вместо 4K. Без этого выбирается factor=4 (мыльно). Субкоманда идёт ПОСЛЕ параметров модели

### Ожидаемые показатели
- RTX 4080: ~15-16 ms/iter
- 35K итераций ≈ 9-10 минут
- Результат: ~500-600K гауссианов, ~120-130 MB PLY

### Патч torch.load

PyTorch 2.6 изменил default `weights_only=True`. При ошибке при экспорте:
```
C:\work\nerf\venv\Lib\site-packages\nerfstudio\utils\eval_utils.py
строка ~62: добавить weights_only=False в torch.load(...)
```

---

## Шаг 5: Экспорт PLY

```bash
# (те же env vars что при обучении)

/c/work/nerf/venv/Scripts/ns-export.exe gaussian-splat \
  --load-config /c/work/nerf/outputs/ИМЯ/splatfacto/ДАТА/config.yml \
  --output-dir /c/work/nerf/exports/ИМЯ \
  2>&1
```

Результат: `splat.ply` с полями `f_dc_0/1/2`, `f_rest_0..44`, `opacity`, `scale_0/1/2`, `rot_0/1/2/3`

---

## Шаг 6: TouchDesigner

### Компоненты
- Tim Gerritsen: https://derivative.ca/community-post/asset/gaussian-splatting/69107
- yeataro: https://github.com/yeataro/TD-Gaussian-Splatting
- POPs GaussianSplat (TD 2025.30600+) — цветокоррекция встроена

### Проблема overexposure
PLY → sRGB, TD рендерит в linear → гамма применяется дважды.
Решение: **Level TOP Gamma = 0.4545** (= 1/2.2) после Render TOP.

### ИЗВЕСТНАЯ ПРОБЛЕМА: SH coordinate system mismatch

Симптом: синяя/зелёная бахрома в тенях (SH degree 1-3).

Причина: nerfstudio применяет `orientation_method='up'` — ротирует сцену ~90°. Матрица из `dataparser_transforms.json` показывает new Y ≈ +old Z, new Z ≈ -old Y. Эта матрица НЕ передаётся в шейдер `calculatecolors` компонента Tim Gerritsen. Axis flip `vec3(x,-y,-z)` не помогает — ротация произвольная.

Решения:
1. **DC-only PLY** (рекомендуется) — `create_dc_only.py`
2. Закомментировать SH degree 1-3 в шейдере `calculatecolors`
3. Переобучить с `--pipeline.model.sh-degree 0`

### create_dc_only.py

```bash
# Пути по умолчанию (v4 -> v4_dc)
python C:/work/nerf/create_dc_only.py

# Явные пути
python C:/work/nerf/create_dc_only.py exports/splat.ply exports/splat_dc/splat.ply
```

---

## Лог версий mountain14

| Версия | Кадры | Downscale | Параметры | Gaussians | Качество |
|--------|-------|-----------|-----------|-----------|----------|
| v1 | 499 | 4 (auto) | default | 572K | Мыльно |
| v2 | 499 | 2 | splatfacto-big | 745K | Лучше, артефакты теней |
| v3 | 499 | 1 (4K) | splatfacto-big | — | Остановлено (7.5с/iter) |
| **v4** | **246** | **2** | **bilateral+antialiased+scale_reg+stop_split_at=20000** | **515K** | **ЛУЧШЕЕ** |

v4 config: `outputs/mountain14/splatfacto/2026-02-23_125055/config.yml`

---

## Типичные ошибки

| Ошибка | Решение |
|--------|---------|
| `UnicodeEncodeError` | `export PYTHONIOENCODING=utf-8` |
| COLMAP `Failed to parse options` | Используется 3.13+, нужен 3.9.1 |
| `Could not find COLMAP` | `--colmap-cmd "C:/work/nerf/colmap_wrapper.bat"` |
| gsplat: No CUDA toolkit | Не заданы CUDA_HOME, INCLUDE, LIB, PATH |
| `Ninja is required` | Добавить `/c/work/nerf/venv/Scripts` в PATH |
| Viewer мыльный | JPEG 75% — норма. Оценивать через ns-render или SuperSplat |
| downscale-factor не применяется | Субкоманда `nerfstudio-data --downscale-factor 2` идёт ПОСЛЕ параметров модели |
| `torch.load` ошибка | `weights_only=False` в `eval_utils.py` строка ~62 |
| Синяя бахрома в TD | `create_dc_only.py` → `_dc` PLY |
