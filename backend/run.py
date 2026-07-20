import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import main

if __name__ == "__main__":
    print("Запуск XW Launcher v0.9.1-alpha в режиме разработки...")
    main()