# XW Launcher v0.9.1-alpha

*Лаунчер использует официальное API Mojang. Рекомендуется наличие лицензионного аккаунта Minecraft.*

## Возможности
- Загрузка официальных версий Minecraft
- Установка и запуск игры
- Управление оффлайн-профилями
- Просмотр установленных модов
- Новости версий Minecraft

## Запуск для разработки
```bash
python -m venv .venv
.venv\Scripts\activate
pip install minecraft-launcher-lib
python run.py
```

## Сборка в .exe
```bash
pip install pyinstaller
python build.py
```
Результат: `dist/XWLauncher.exe`

## Структура
```
xw-launcher/
├── src/                 # исходный код
├── assets/              # иконка
├── run.py               # запуск для разработки
├── build.py             # сборка в .exe
└── version_info.txt     # версия для .exe
```
