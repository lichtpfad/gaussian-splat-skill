"""
Gaussian Splatting Environment Setup (Windows)
===============================================
Проверяет и устанавливает все зависимости для nerfstudio gaussian splatting pipeline.

Запуск:
  python setup.py
  python setup.py --install-dir C:\work\nerf
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# ─── Версии ──────────────────────────────────────────────────────────────────
COLMAP_VERSION = "3.9.1"
COLMAP_URL = f"https://github.com/colmap/colmap/releases/download/{COLMAP_VERSION}/COLMAP-{COLMAP_VERSION}-windows-cuda.zip"
TORCH_INDEX = "https://download.pytorch.org/whl/cu124"
NERFSTUDIO_VERSION = "nerfstudio==1.1.5"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}!{RESET} {msg}")
def fail(msg):  print(f"  {RED}✗{RESET} {msg}")
def info(msg):  print(f"  {BOLD}→{RESET} {msg}")


# ─── Проверки ─────────────────────────────────────────────────────────────────

def check_python311():
    """Проверяет наличие Python 3.11."""
    result = subprocess.run(["py", "-3.11", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"Python 3.11: {result.stdout.strip()}")
        return True
    fail("Python 3.11 не найден (нужен py launcher)")
    warn("Скачать: https://www.python.org/downloads/release/python-3119/")
    return False


def check_cuda():
    """Проверяет CUDA через nvidia-smi."""
    result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"CUDA GPU: {result.stdout.strip()}")
        return True
    fail("nvidia-smi не найден — CUDA недоступна")
    warn("Установить CUDA Toolkit 12.4: https://developer.nvidia.com/cuda-12-4-0-download-archive")
    return False


def check_vs_build_tools():
    """Проверяет VS Build Tools (нужны для компиляции gsplat)."""
    msvc_base = Path("C:/Program Files (x86)/Microsoft Visual Studio")
    if msvc_base.exists():
        ok("VS Build Tools: найдены")
        return True
    fail("VS Build Tools не найдены")
    warn("Установить: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    warn("Нужны компоненты: MSVC v143, Windows SDK 10")
    return False


def check_ffmpeg():
    """Проверяет ffmpeg в PATH."""
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode == 0:
        version = result.stdout.split("\n")[0]
        ok(f"ffmpeg: {version}")
        return True
    warn("ffmpeg не найден")
    return False


def check_venv(install_dir: Path):
    """Проверяет наличие venv."""
    python = install_dir / "venv" / "Scripts" / "python.exe"
    if python.exists():
        result = subprocess.run([str(python), "--version"], capture_output=True, text=True)
        ok(f"venv: {result.stdout.strip()} в {install_dir / 'venv'}")
        return True
    warn(f"venv не найден в {install_dir / 'venv'}")
    return False


def check_nerfstudio(install_dir: Path):
    """Проверяет установку nerfstudio в venv."""
    python = install_dir / "venv" / "Scripts" / "python.exe"
    if not python.exists():
        return False
    result = subprocess.run([str(python), "-c", "import nerfstudio; print(nerfstudio.__version__)"],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"nerfstudio: {result.stdout.strip()}")
        return True
    warn("nerfstudio не установлен в venv")
    return False


def check_plyfile(install_dir: Path):
    """Проверяет установку plyfile в venv."""
    python = install_dir / "venv" / "Scripts" / "python.exe"
    if not python.exists():
        return False
    result = subprocess.run([str(python), "-c", "import plyfile; print(plyfile.__version__)"],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"plyfile: {result.stdout.strip()}")
        return True
    warn("plyfile не установлен")
    return False


def check_colmap(install_dir: Path):
    """Проверяет наличие COLMAP."""
    colmap = install_dir / "colmap" / "bin" / "colmap.exe"
    if colmap.exists():
        ok(f"COLMAP {COLMAP_VERSION}: {colmap}")
        return True
    warn(f"COLMAP не найден в {install_dir / 'colmap'}")
    return False


def check_torch_patch(install_dir: Path):
    """Проверяет патч torch.load в eval_utils.py."""
    eval_utils = install_dir / "venv" / "Lib" / "site-packages" / "nerfstudio" / "utils" / "eval_utils.py"
    if not eval_utils.exists():
        return False
    content = eval_utils.read_text(encoding="utf-8")
    if "weights_only=False" in content:
        ok("torch.load патч: применён")
        return True
    warn("torch.load патч: не применён (нужен для PyTorch 2.6+)")
    return False


# ─── Установка ────────────────────────────────────────────────────────────────

def install_ffmpeg():
    """Устанавливает ffmpeg через winget."""
    info("Устанавливаю ffmpeg через winget...")
    result = subprocess.run(["winget", "install", "Gyan.FFmpeg", "--silent"], check=False)
    if result.returncode == 0:
        ok("ffmpeg установлен. Перезапустите терминал для обновления PATH")
    else:
        fail("Не удалось установить ffmpeg автоматически")
        warn("Скачать вручную: https://ffmpeg.org/download.html")


def create_venv(install_dir: Path):
    """Создаёт Python 3.11 venv."""
    venv_dir = install_dir / "venv"
    info(f"Создаю venv в {venv_dir}...")
    subprocess.run(["py", "-3.11", "-m", "venv", str(venv_dir)], check=True)
    ok("venv создан")


def install_pytorch(install_dir: Path):
    """Устанавливает PyTorch с поддержкой CUDA 12.4."""
    pip = install_dir / "venv" / "Scripts" / "pip.exe"
    info("Устанавливаю PyTorch 2.6 + CUDA 12.4 (может занять несколько минут)...")
    subprocess.run([
        str(pip), "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", TORCH_INDEX
    ], check=True)
    ok("PyTorch установлен")


def install_nerfstudio(install_dir: Path):
    """Устанавливает nerfstudio."""
    pip = install_dir / "venv" / "Scripts" / "pip.exe"
    info(f"Устанавливаю {NERFSTUDIO_VERSION}...")
    subprocess.run([str(pip), "install", NERFSTUDIO_VERSION], check=True)
    ok("nerfstudio установлен")


def install_plyfile(install_dir: Path):
    """Устанавливает plyfile."""
    pip = install_dir / "venv" / "Scripts" / "pip.exe"
    subprocess.run([str(pip), "install", "plyfile"], check=True)
    ok("plyfile установлен")


def install_colmap(install_dir: Path):
    """Скачивает и распаковывает COLMAP 3.9.1."""
    colmap_dir = install_dir / "colmap"
    zip_path = install_dir / f"colmap-{COLMAP_VERSION}.zip"

    info(f"Скачиваю COLMAP {COLMAP_VERSION}...")
    info(f"URL: {COLMAP_URL}")

    def progress(count, block_size, total_size):
        pct = min(int(count * block_size * 100 / total_size), 100)
        print(f"\r  Загрузка: {pct}%", end="", flush=True)

    urllib.request.urlretrieve(COLMAP_URL, zip_path, reporthook=progress)
    print()

    info("Распаковываю...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(colmap_dir)
    zip_path.unlink()

    # COLMAP zip распаковывается в подпапку — найти и поднять на уровень выше
    subdirs = [d for d in colmap_dir.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and (subdirs[0] / "bin").exists():
        for item in subdirs[0].iterdir():
            shutil.move(str(item), str(colmap_dir / item.name))
        subdirs[0].rmdir()

    ok(f"COLMAP установлен в {colmap_dir}")


def create_colmap_wrapper(install_dir: Path):
    """Создаёт colmap_wrapper.bat."""
    wrapper = install_dir / "colmap_wrapper.bat"
    content = f"""@echo off
set SCRIPT_PATH={install_dir}\\colmap
set PATH=%SCRIPT_PATH%\\lib;%PATH%
"%SCRIPT_PATH%\\bin\\colmap.exe" %*
"""
    wrapper.write_text(content, encoding="utf-8")
    ok(f"colmap_wrapper.bat создан: {wrapper}")


def apply_torch_patch(install_dir: Path):
    """Патчит eval_utils.py для PyTorch 2.6+."""
    eval_utils = install_dir / "venv" / "Lib" / "site-packages" / "nerfstudio" / "utils" / "eval_utils.py"
    if not eval_utils.exists():
        warn(f"eval_utils.py не найден: {eval_utils}")
        return
    content = eval_utils.read_text(encoding="utf-8")
    if "weights_only=False" in content:
        ok("torch.load патч уже применён")
        return
    patched = content.replace("torch.load(", "torch.load(weights_only=False, ")
    eval_utils.write_text(patched, encoding="utf-8")
    ok("torch.load патч применён")


def create_folder_structure(install_dir: Path):
    """Создаёт структуру папок проекта."""
    folders = ["data", "exports", "outputs", "renders", "content"]
    for folder in folders:
        (install_dir / folder).mkdir(exist_ok=True)
    ok(f"Папки созданы: {', '.join(folders)}")


def copy_scripts(install_dir: Path, skill_dir: Path):
    """Копирует pipeline скрипты в install_dir."""
    scripts = ["extract_frames.py", "create_dc_only.py"]
    for script_name in scripts:
        src = skill_dir / "scripts" / script_name
        dst = install_dir / script_name
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
            ok(f"Скопирован: {script_name}")
        elif dst.exists():
            ok(f"Уже существует: {script_name}")
        else:
            warn(f"Не найден в скилле: {script_name}")


# ─── Главная функция ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gaussian Splatting Environment Setup")
    parser.add_argument("--install-dir", type=Path, default=Path("C:/work/nerf"),
                        help="Директория установки (default: C:\\work\\nerf)")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Не спрашивать подтверждения, установить всё недостающее")
    args = parser.parse_args()

    install_dir: Path = args.install_dir.resolve()
    skill_dir = Path(__file__).parent.parent  # .claude/skills/create-gaussian-splat/

    print(f"\n{BOLD}=== Gaussian Splatting Environment Setup ==={RESET}")
    print(f"Директория установки: {install_dir}\n")

    install_dir.mkdir(parents=True, exist_ok=True)

    # ─── Проверка ────────────────────────────────────────────────────────────
    print(f"{BOLD}Проверка компонентов:{RESET}")
    status = {
        "python311":    check_python311(),
        "cuda":         check_cuda(),
        "vs_tools":     check_vs_build_tools(),
        "ffmpeg":       check_ffmpeg(),
        "venv":         check_venv(install_dir),
        "nerfstudio":   check_nerfstudio(install_dir),
        "plyfile":      check_plyfile(install_dir),
        "colmap":       check_colmap(install_dir),
        "torch_patch":  check_torch_patch(install_dir),
    }

    missing = [k for k, v in status.items() if not v]

    if not missing:
        print(f"\n{GREEN}{BOLD}Всё установлено! Окружение готово к работе.{RESET}")
        return

    # ─── Предупреждения о блокирующих зависимостях ───────────────────────────
    print(f"\n{YELLOW}Не найдено: {', '.join(missing)}{RESET}")

    blocking = [k for k in ["python311", "cuda", "vs_tools"] if k in missing]
    if blocking:
        print(f"\n{RED}Блокирующие зависимости требуют ручной установки:{RESET}")
        for b in blocking:
            if b == "python311":
                warn("Python 3.11: https://www.python.org/downloads/release/python-3119/")
            elif b == "cuda":
                warn("CUDA Toolkit 12.4: https://developer.nvidia.com/cuda-12-4-0-download-archive")
            elif b == "vs_tools":
                warn("VS Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("\nПосле установки запустите setup.py снова.")
        if blocking == missing:
            return

    # ─── Подтверждение ───────────────────────────────────────────────────────
    auto_installable = [k for k in missing if k not in blocking]
    if auto_installable and not args.yes:
        print(f"\nАвтоматически установить: {', '.join(auto_installable)}")
        answer = input("Продолжить? [y/N]: ").strip().lower()
        if answer not in ("y", "yes", "д", "да"):
            print("Отмена.")
            return

    # ─── Установка ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}Установка:{RESET}")

    if "ffmpeg" in missing:
        install_ffmpeg()

    if "venv" in missing and "python311" not in blocking:
        create_venv(install_dir)

    if "nerfstudio" in missing and "venv" not in missing or \
       ("venv" in missing and "python311" not in blocking):
        install_pytorch(install_dir)
        install_nerfstudio(install_dir)

    if "plyfile" in missing:
        install_plyfile(install_dir)

    if "colmap" in missing:
        install_colmap(install_dir)

    # colmap_wrapper.bat всегда создаём если COLMAP есть
    if not (install_dir / "colmap_wrapper.bat").exists():
        create_colmap_wrapper(install_dir)

    if "torch_patch" in missing:
        apply_torch_patch(install_dir)

    create_folder_structure(install_dir)
    copy_scripts(install_dir, skill_dir)

    # ─── Итог ────────────────────────────────────────────────────────────────
    print(f"\n{GREEN}{BOLD}✓ Установка завершена!{RESET}")
    print(f"  Путь: {install_dir}")
    print(f"  Python: {install_dir / 'venv' / 'Scripts' / 'python.exe'}")
    print(f"  COLMAP: {install_dir / 'colmap_wrapper.bat'}")
    print(f"\nТеперь можно создавать Gaussian Splats!")


if __name__ == "__main__":
    main()
