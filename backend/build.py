import subprocess
import sys
import os

VERSION = "0.9.1-alpha"
NAME = "XWLauncher"

# Полные пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(BASE_DIR, "assets", "icon.ico")
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")
MAIN_SCRIPT = os.path.join(BASE_DIR, "src", "main.py")

def build():
    print(f"Сборка {NAME} v{VERSION} в .exe...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", NAME,
        "--distpath", os.path.join(BASE_DIR, "dist"),
        "--workpath", os.path.join(BASE_DIR, "build_temp"),
        "--specpath", os.path.join(BASE_DIR, "build_temp"),
        "--paths", os.path.join(BASE_DIR, "src"),
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
        print(f"  Файл версии не найден: {VERSION_FILE}")

    cmd.append(MAIN_SCRIPT)

    print("  Сборка начата, подождите...")
    
    # Запускаем без capture_output чтобы видеть прогресс
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join(BASE_DIR, "dist", f"{NAME}.exe")
        print(f"\n  Готово! Файл создан: {exe_path}")
    else:
        print("\n  Ошибка при сборке!")
        print(f"  Код ошибки: {result.returncode}")

if __name__ == "__main__":
    build()