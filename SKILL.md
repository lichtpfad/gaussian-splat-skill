---
name: create-gaussian-splat
description: This skill should be used when the user asks to "create a gaussian splat", "train a splat", "process drone video for nerf", "export PLY", "run splatfacto", "extract frames from video", "run COLMAP", "prepare dataset for nerfstudio", or wants to use the gaussian splatting pipeline. Also triggers when user mentions TouchDesigner + PLY, DC-only splat, or SH color artifacts.
version: 1.0.0
---

# Gaussian Splatting Pipeline

Pipeline for creating Gaussian Splats from drone video using nerfstudio on this workstation (RTX 4080, Windows 11, CUDA 13.1).

For detailed commands and parameters, consult `references/pipeline-guide.md`.

---

## Environment

```
Python:   <INSTALL_DIR>\venv\Scripts\python.exe  (always use this)
COLMAP:   <INSTALL_DIR>\colmap_wrapper.bat        (not colmap.exe directly — DLL fix)
```

`<INSTALL_DIR>` — директория установки, уточняется на Шаге -1 у пользователя.

Always set before any nerfstudio command:
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
```

---

## Pipeline Overview (8 шагов)

### -1. Проверка окружения (ПЕРВЫЙ ЗАПУСК)

Спросить пользователя:
> "Где находится твоя рабочая директория с nerfstudio? Укажи путь (например `C:\work\nerf`) или напиши 'нет' если нужно установить с нуля."

**Путь указан** → использовать `<путь>\venv\Scripts\python.exe` во всех командах. Сохранить как `INSTALL_DIR`.

**"Нет" / нет установки** → спросить куда установить:
> "Куда установить? Укажи директорию (например `C:\work\nerf`)"

Затем запустить setup-скрипт:
```bash
python ".claude/skills/create-gaussian-splat/scripts/setup.py" --install-dir "<INSTALL_DIR>"
```
Скрипт проверит все компоненты, покажет статус, спросит подтверждение и установит недостающее.

**После успешной установки** → продолжить с Шага 0.

---

### 0. Анализ сцены и подбор параметров (НАЧИНАТЬ ЗДЕСЬ)

Перед запуском пайплайна провести визуальный анализ — это позволяет выбрать оптимальные параметры обучения без экспериментов.

**Запросить у пользователя:**
> "Укажи путь к папке с уже извлечёнными кадрами, или к исходным видео — я посмотрю несколько кадров и предложу настройки."

**Если кадры уже есть** (папка `data/*/images/`):
- Прочитать 4-6 кадров через `Read` tool (равномерно из начала, середины, конца)
- Проанализировать визуально по чеклисту из `references/scene-presets.md`

**Если только видео** — попросить извлечь несколько тестовых кадров:
```bash
python C:/work/nerf/extract_frames.py --input "путь/к/видео" --output /tmp/preview --count 6
```

**По результатам анализа:**
1. Определить тип сцены → взять базовый пресет из `references/scene-presets.md`
2. Скорректировать по наблюдениям (освещение, детализация, покрытие)
3. Сообщить пользователю выбранные параметры с обоснованием

**Пример вывода:**
```
Тип сцены: горный пейзаж (аэро)
Жёсткие тени: да → bilateral_grid=True
Вытянутые скалы: да → scale_regularization=True
Покрытие равномерное → num_frames=280

Рекомендуемые параметры: [пресет горы + корректировки]
```

Полные пресеты и диагностический чеклист: `references/scene-presets.md`

---

### 1. Определить цветовой профиль

Открыть `.SRT` файл рядом с видео:
```
[color_md : normal]     → Rec.709, LUT не нужен
[color_md : d_cinelike] → D-Cinelike
[color_md : d_log_m]    → D-Log M, нужна LUT конвертация
```
Применять LUT только если footage в D-Log M. Ошибочное применение к Rec.709 делает картинку белёсой.

### 2. Извлечь кадры

**Вариант A — автоматически (рекомендуется):**
```bash
/c/work/nerf/venv/Scripts/ns-process-data.exe videos \
  --data "/c/work/nerf/content/ИМЯ/Drone L/НОМ" \
  --output-dir /c/work/nerf/data/ДАТАСЕТ \
  --num-frames-target 300 \
  --colmap-cmd "C:/work/nerf/colmap_wrapper.bat" \
  --camera-type perspective \
  --matching-method vocab_tree
```

**Вариант B — скрипт `C:\work\nerf\extract_frames.py`:**
```bash
# Ровно 300 кадров суммарно
python C:/work/nerf/extract_frames.py --input "content/..." --output data/ДАТАСЕТ/images --count 300

# Или по fps
python C:/work/nerf/extract_frames.py --input "content/..." --output data/ДАТАСЕТ/images --fps 2
```

Matching method: `vocab_tree` для нескольких видео, `sequential` для одного, `exhaustive` для <300 кадров.

### 3. (Опционально) Проредить кадры

499 кадров избыточны — 250-300 оптимально. Проредить через `transforms.json` (оставить каждый второй `frames[::2]`).

### 4. Обучить splatfacto-big (лучшая конфигурация)

```bash
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
  --downscale-factor 2
```

Ключевые параметры:
- `bilateral-grid` — коррекция экспозиции per-frame (важно для дрона)
- `antialiased` — Mip-Splatting, устраняет мерцание
- `scale-regularization` — убирает шипы и floaters
- `stop-split-at 20000` — больше деталей (default 15000)
- `downscale-factor 2` — 1080p обучение. БЕЗ этого nerfstudio выберет factor=4 (мыльно). Субкоманда идёт ПОСЛЕ всех параметров модели

Ожидаемые показатели RTX 4080: ~16ms/iter, 35K итераций ≈ 9-10 минут.

### 5. Экспортировать PLY

```bash
/c/work/nerf/venv/Scripts/ns-export.exe gaussian-splat \
  --load-config /c/work/nerf/outputs/ИМЯ/splatfacto/ДАТА/config.yml \
  --output-dir /c/work/nerf/exports/ИМЯ
```

Если ошибка `torch.load`: добавить `weights_only=False` в `venv/Lib/site-packages/nerfstudio/utils/eval_utils.py` строка ~62.

### 6. Подготовить для TouchDesigner

**Проблема:** синяя/зелёная бахрома в тенях — SH coordinate system mismatch между nerfstudio и компонентом Tim Gerritsen.

**Решение — создать DC-only PLY:**
```bash
python C:/work/nerf/create_dc_only.py \
  exports/ИМЯ/splat.ply \
  exports/ИМЯ_dc/splat.ply
```

В TouchDesigner использовать `_dc` версию + **Level TOP Gamma = 0.4545** после Render TOP.

---

## Структура папок

```
C:\work\nerf\
  content\          # Исходные видео (не в git)
  data\             # COLMAP output (не в git)
  outputs\          # Обученные модели (не в git)
  exports\          # PLY файлы для использования
  extract_frames.py # ffmpeg обёртка
  create_dc_only.py # DC-only PLY для TouchDesigner
  colmap_wrapper.bat
```

---

## Быстрый чеклист

- [ ] Проверить `.SRT` → цветовой профиль
- [ ] `ns-process-data videos` или `extract_frames.py --count 300`
- [ ] COLMAP matched >80% кадров?
- [ ] `ns-train splatfacto-big` с v4 параметрами + `downscale-factor 2`
- [ ] `ns-export gaussian-splat`
- [ ] `create_dc_only.py` → `_dc` версия для TouchDesigner
- [ ] Level TOP Gamma=0.4545 в TouchDesigner

---

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| `UnicodeEncodeError` | `export PYTHONIOENCODING=utf-8` |
| `Failed to parse options` COLMAP | Используется COLMAP 3.13+, нужен 3.9.1 |
| `Could not find COLMAP` | `--colmap-cmd "C:/work/nerf/colmap_wrapper.bat"` |
| gsplat: No CUDA toolkit | Не заданы CUDA_HOME, env vars — см. блок выше |
| Viewer мыльный | Нормально (JPEG 75%), оценивать через `ns-render` или SuperSplat |
| `downscale-factor` не применяется | Субкоманда `nerfstudio-data --downscale-factor 2` идёт ПОСЛЕ параметров модели |
| `torch.load` ошибка при экспорте | Патч `eval_utils.py` строка ~62: `weights_only=False` |
| Синяя бахрома в TD | Использовать `create_dc_only.py` → `_dc` PLY |

---

## Дополнительные ресурсы

### Reference Files
- **`references/scene-presets.md`** — визуальный диагностический чеклист + пресеты параметров по типу сцены (горы, лес, город, вода, интерьер и др.)
- **`references/pipeline-guide.md`** — полные команды со всеми параметрами, история версий mountain14, подробный разбор ошибок

### Скрипты на диске
- `C:\work\nerf\extract_frames.py` — извлечение кадров (`--fps` или `--count`)
- `C:\work\nerf\create_dc_only.py` — DC-only PLY для TouchDesigner

### Ссылки
- SuperSplat viewer: https://playcanvas.com/supersplat/editor
- Tim Gerritsen TD component: https://derivative.ca/community-post/asset/gaussian-splatting/69107
