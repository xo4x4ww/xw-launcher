import subprocess
import sys
import os

VERSION = "0.9.1-alpha"
NAME = "XWLauncher"
ICON = os.path.join("assets", "icon.ico")
VERSION_FILE = "version_info.txt"
MAIN_SCRIPT = os.path.join("src", "main.py")

def build():
    print(f"Сборка {NAME} v{VERSION} в .exe...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", NAME,
        "--distpath", "dist",
        "--workpath", "build_temp",
        "--specpath", "build_temp",
        "--add-data", f"src{os.pathsep}src",
        MAIN_SCRIPT,
    ]

    if os.path.exists(ICON):
        cmd.extend(["--icon", ICON])
        print(f"  Иконка: {ICON}")
    else:
        print("  Иконка не найдена, используется стандартная")

    if os.path.exists(VERSION_FILE):
        cmd.extend(["--version-file", VERSION_FILE])
        print(f"  Версия из файла: {VERSION_FILE}")
    else:
        print("  Файл версии не найден")

    print("  Сборка начата, подождите...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = os.path.join("dist", f"{NAME}.exe")
        print(f"  Готово! Файл создан: {exe_path}")
    else:
        print("  Ошибка при сборке:")
        print(result.stderr)

if __name__ == "__main__":
    build()