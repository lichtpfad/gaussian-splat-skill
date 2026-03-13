# Gaussian Splat Skill for Claude Code

A Claude Code skill for creating Gaussian Splats from drone video using [nerfstudio](https://nerf.studio), and exporting to TouchDesigner.

## What it does

- **Guided pipeline** — step-by-step from raw video to PLY file
- **Scene analysis** — Claude reads sample frames and recommends optimal training parameters based on scene type (aerial mountain, forest, urban, coastal, etc.)
- **Auto setup** — checks and installs the full environment on first run (Python venv, PyTorch/CUDA, nerfstudio, COLMAP, ffmpeg)
- **TouchDesigner export** — creates DC-only PLY to fix SH coordinate mismatch artifacts

## Requirements

- Windows 11
- NVIDIA GPU with CUDA 12.4+
- Python 3.11 (via py launcher)
- VS Build Tools 2022 (for gsplat CUDA compilation)

## Installation

Copy the skill into your Claude Code project:

```
your-project/
└── .claude/
    └── skills/
        └── create-gaussian-splat/   ← contents of this repo
```

Or clone directly:

```bash
git clone https://github.com/lichtpfad/gaussian-splat-skill .claude/skills/create-gaussian-splat
```

Then start Claude Code and say:
> "Create a gaussian splat from my drone video"

Claude will ask for your install directory and set up everything automatically.

## Skill structure

```
SKILL.md                       # Core pipeline (Steps -1 to 6)
scripts/
  setup.py                     # Full environment setup script
references/
  scene-presets.md             # Visual diagnostic checklist + 7 scene presets
  pipeline-guide.md            # Full command reference with all parameters
```

## Pipeline overview

| Step | Description |
|------|-------------|
| -1 | Environment check — asks for install dir, runs setup.py if needed |
| 0  | Scene analysis — reads sample frames, recommends parameters |
| 1  | Color profile check (SRT file: Rec.709 / D-Log M) |
| 2  | Frame extraction (`extract_frames.py` or `ns-process-data`) |
| 3  | COLMAP Structure-from-Motion |
| 4  | Train `splatfacto-big` with optimized parameters |
| 5  | Export PLY via `ns-export gaussian-splat` |
| 6  | Prepare for TouchDesigner (DC-only PLY + Level TOP gamma) |

## Scene presets

The skill includes tested parameter presets for:
- 🏔️ Aerial mountain/rock (tested ✓)
- 🌳 Forest/vegetation
- 🏙️ Aerial urban
- 🏖️ Coastal/water
- ❄️ Snow/low-texture
- 🏠 Ground-level exterior
- 🏢 Interior

## Key lessons (from real project)

- `COLMAP 3.9.1` required — 3.13+ breaks nerfstudio 1.1.5 CLI compatibility
- `--downscale-factor 2` must be passed as a subcommand after model params
- nerfstudio viewer streams JPEG 75% — use `ns-render` or SuperSplat for quality assessment
- SH degree 1-3 causes blue/green fringing in TouchDesigner — use DC-only PLY
- `bilateral_grid=True` is critical for drone footage (varying exposure per frame)

## Tested environment

- nerfstudio 1.1.5, PyTorch 2.6.0+cu124, CUDA 13.1
- COLMAP 3.9.1
- RTX 4080 16GB (~16ms/iter, 35K iterations ≈ 9 min)
