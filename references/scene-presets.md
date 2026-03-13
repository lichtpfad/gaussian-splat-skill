# Scene Presets — Параметры по типу сцены

Справочник для подбора параметров splatfacto-big на основе визуального анализа кадров.

---

## Визуальная диагностика

При анализе sample frames проверить каждый пункт и отметить наблюдения:

### Тип сцены
- [ ] Горный/скальный пейзаж (аэро)
- [ ] Городская среда (аэро)
- [ ] Природа/лес/растительность
- [ ] Побережье/вода
- [ ] Снег/пустыня (мало текстуры)
- [ ] Съёмка с земли (здания, улицы)
- [ ] Интерьер

### Освещение
- [ ] Равномерное (пасмурно, тень) → `bilateral_grid` менее критичен
- [ ] Жёсткие тени (солнце) → `bilateral_grid=True` обязательно
- [ ] Разная экспозиция между кадрами (дрон меняет высоту/угол) → `bilateral_grid=True`
- [ ] HDR сцена (тёмные тени + яркое небо) → флаги экспозиции + bilateral

### Геометрия и детализация
- [ ] Крупные плоские поверхности (стены, скалы) → `stop_split_at` можно оставить 20000
- [ ] Много мелких деталей (ветки, трава, камни) → `stop_split_at=25000+`
- [ ] Вытянутые объекты (деревья, антенны) → `scale_regularization=True` обязательно
- [ ] Симметричная/регулярная геометрия → `sh_degree=1` достаточно

### Покрытие камерой
- [ ] Равномерное со всех сторон → `num_frames_target=250`
- [ ] Преимущественно сверху (дрон) → `num_frames_target=300`, vocab_tree
- [ ] Плотные + редкие зоны → `num_frames_target=350+`, проредить равномерно
- [ ] Одно непрерывное видео → `sequential` matching

### Качество кадров
- [ ] Чёткие кадры без смаза → норма
- [ ] Смаз движения на части кадров → отфильтровать при прореживании
- [ ] Шум/зернистость (ISO высокий) → `bilateral_grid` помогает
- [ ] Lens flare, засветки → исключить проблемные кадры

---

## Пресеты по типу сцены

### 🏔️ Горный/скальный пейзаж (аэро) — ПРОТЕСТИРОВАНО ✓

*Наш случай: mountain14, 6 DJI видео 4K 50fps*

```
use_bilateral_grid=True       # Жёсткие тени, разная экспозиция с высоты
rasterize_mode=antialiased    # Широкий baseline дрона → мерцание
use_scale_regularization=True # Вытянутые скальные структуры
stop_split_at=20000
max_num_iterations=35000
sh_degree=3                   # Скалы дают view-dependent блики
downscale_factor=2
num_frames_target=250-300
matching_method=vocab_tree
```

**Ожидаемый результат:** 400-600K gaussians, 100-130MB PLY

**TouchDesigner:** обязательно DC-only PLY (`create_dc_only.py`) — SH mismatch критичен для аэро

---

### 🌳 Природа / лес / растительность

```
use_bilateral_grid=True       # Листва создаёт динамические тени
rasterize_mode=antialiased
use_scale_regularization=True # Стволы/ветки — вытянутые структуры
stop_split_at=25000           # Много мелких деталей (листья)
max_num_iterations=40000      # Больше итераций для плотной геометрии
sh_degree=3                   # Блики на листве важны
downscale_factor=2
num_frames_target=350         # Растительность требует плотного покрытия
matching_method=vocab_tree
```

**Предупреждение:** Движущиеся листья от ветра = размытые gaussians. Снимать в безветренную погоду или увеличить shutter speed.

**Ожидаемый результат:** 800K-1.5M gaussians, 200-350MB PLY

---

### 🏙️ Городская среда (аэро)

```
use_bilateral_grid=True       # Тени от зданий, разная экспозиция
rasterize_mode=antialiased
use_scale_regularization=True # Вертикальные фасады → длинные gaussians
stop_split_at=20000
max_num_iterations=35000
sh_degree=3                   # Стёкла, металл — сильно view-dependent
downscale_factor=2
num_frames_target=300
matching_method=vocab_tree
```

**Особенность:** Стёклянные поверхности плохо реконструируются — это норма для 3DGS.

---

### 🏖️ Побережье / вода

```
use_bilateral_grid=True       # Отражение неба меняется
rasterize_mode=antialiased
use_scale_regularization=True
stop_split_at=20000
max_num_iterations=35000
sh_degree=3                   # Блики на воде критичны
downscale_factor=2
num_frames_target=250         # Вода — плоская, не требует плотного покрытия
matching_method=vocab_tree
```

**Предупреждение:** Вода с волнами = плохая реконструкция (нет постоянных feature points). Ожидать размытие на водной поверхности.

---

### ❄️ Снег / пустыня / мало текстуры

```
use_bilateral_grid=True
rasterize_mode=antialiased
use_scale_regularization=True
stop_split_at=15000           # Мало деталей → меньше densification нужно
max_num_iterations=25000      # Сцена проще → быстрее сходится
sh_degree=1                   # View-dependent эффекты минимальны
downscale_factor=2
num_frames_target=200         # Меньше кадров достаточно
matching_method=vocab_tree
```

**Предупреждение:** COLMAP может плохо матчить снежные/песчаные поверхности (<70%). Добавить кадры с контрастными объектами на переднем плане.

---

### 🏠 Съёмка с земли (здания, улицы)

```
use_bilateral_grid=True
rasterize_mode=antialiased
use_scale_regularization=True
stop_split_at=20000
max_num_iterations=35000
sh_degree=3
downscale_factor=2
num_frames_target=300
matching_method=exhaustive    # Фото с камеры → exhaustive для точности
                              # (если >300 кадров → vocab_tree)
```

**Особенность:** Съёмка камерой (не дрон) → больше шансов неравномерного покрытия. Рекомендуется круговой обход объекта на нескольких уровнях высоты.

---

### 🏢 Интерьер

```
use_bilateral_grid=True       # Разное освещение в разных комнатах
rasterize_mode=antialiased
use_scale_regularization=False # Интерьер — компактная геометрия
stop_split_at=20000
max_num_iterations=30000
sh_degree=2                   # Умеренные view-dependent эффекты
downscale_factor=2
num_frames_target=300
matching_method=exhaustive    # Интерьер = мало parallax → exhaustive
camera_type=perspective
```

**Предупреждение:** Зеркала и стеклянные поверхности реконструируются плохо. Тёмные углы требуют дополнительных кадров с экспозицией.

---

## Быстрая таблица параметров

| Параметр | Горы аэро | Лес | Город аэро | Вода | Снег | Улица | Интерьер |
|----------|-----------|-----|------------|------|------|-------|----------|
| bilateral_grid | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| scale_reg | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| stop_split_at | 20K | 25K | 20K | 20K | 15K | 20K | 20K |
| max_iterations | 35K | 40K | 35K | 35K | 25K | 35K | 30K |
| sh_degree | 3 | 3 | 3 | 3 | 1 | 3 | 2 |
| downscale | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| num_frames | 300 | 350 | 300 | 250 | 200 | 300 | 300 |
| matching | vocab_tree | vocab_tree | vocab_tree | vocab_tree | vocab_tree | exhaustive | exhaustive |

---

## Флаги для особых случаев

**Если COLMAP matched < 70%:**
- Добавить больше кадров в проблемных зонах
- Попробовать `exhaustive` вместо `vocab_tree`
- Проверить что кадры чёткие (нет смаза)

**Если обучение > 20ms/iter (слишком медленно):**
- Убедиться что `downscale_factor=2`
- Уменьшить `num_frames_target`
- Уменьшить `max_num_iterations` до 25000

**Если много floaters и шипов:**
- Увеличить `cull_alpha_thresh` (добавить `--pipeline.model.cull-alpha-thresh 0.01`)
- Убедиться что `scale_regularization=True`
- Уменьшить `stop_split_at`

**Если не хватает деталей:**
- Увеличить `stop_split_at` до 25000
- Увеличить `max_num_iterations` до 40000
- Добавить больше кадров в детализированных зонах
