import json
import os
import subprocess
import threading
import tkinter as tk
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk, font as tkfont

import minecraft_launcher_lib


class MinecraftLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("1200x720")
        self.root.minsize(1000, 600)
        
        # Центрирование окна
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (720 // 2)
        self.root.geometry(f"1200x720+{x}+{y}")

        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._progress_max = 100
        self._install_in_progress = False
        self._last_progress_change_at = 0.0
        self._last_progress_value = 0
        self._is_fullscreen = False
        self._theme_name = str(self.config.get("theme", "dark")).lower()
        if self._theme_name not in {"dark", "light"}:
            self._theme_name = "dark"
        self._colors: dict[str, str] = {}
        self._current_page = "home"
        self._progress_target = 0.0
        self._progress_display = 0.0
        self._news_items = []
        self._selected_instance = None

        self._setup_window()
        self._apply_theme()
        self._build_ui()
        self._bind_shortcuts()
        self._animate_progress()
        self._load_versions_async()
        self._load_news()

    def _load_config(self) -> dict:
        default = {
            "last_username": "Player",
            "last_version": "",
            "username_history": ["Player"],
            "version_history": [],
            "theme": "dark",
            "ram_allocation": 2048,
            "java_args": "",
            "instances": [],
        }
        if not self.config_path.exists():
            return default
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                saved = json.load(f)
        except:
            return default
        default.update(saved)
        return default

    def _save_config(self) -> None:
        try:
            with self.config_path.open("w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _setup_window(self) -> None:
        # Убираем стандартную рамку для кастомного дизайна
        self.root.overrideredirect(False)
        
        # Устанавливаем иконку
        try:
            icon = tk.PhotoImage(width=32, height=32)
            # Рисуем простую иконку - куб
            for i in range(8, 24):
                for j in range(8, 24):
                    if 8 <= i <= 23 and 8 <= j <= 23:
                        icon.put("#3b82f6", (i, j))
            self.root.iconphoto(True, icon)
        except:
            pass

    def _apply_theme(self) -> None:
        if self._theme_name == "dark":
            self._colors = {
                "bg": "#0a0a0f",
                "surface": "#13141a",
                "surface_light": "#1a1c26",
                "primary": "#3b82f6",
                "primary_dark": "#2563eb",
                "primary_light": "#60a5fa",
                "accent": "#8b5cf6",
                "success": "#10b981",
                "warning": "#f59e0b",
                "error": "#ef4444",
                "text": "#ffffff",
                "text_secondary": "#9ca3af",
                "text_muted": "#6b7280",
                "border": "#2d3748",
                "card": "#181a24",
                "input": "#1e202a",
                "hover": "#222533",
            }
        else:
            self._colors = {
                "bg": "#f8fafc",
                "surface": "#ffffff",
                "surface_light": "#f1f5f9",
                "primary": "#3b82f6",
                "primary_dark": "#2563eb",
                "primary_light": "#60a5fa",
                "accent": "#8b5cf6",
                "success": "#10b981",
                "warning": "#f59e0b",
                "error": "#ef4444",
                "text": "#0f172a",
                "text_secondary": "#475569",
                "text_muted": "#94a3b8",
                "border": "#e2e8f0",
                "card": "#ffffff",
                "input": "#f8fafc",
                "hover": "#f1f5f9",
            }
        
        self.root.configure(bg=self._colors["bg"])
        
        # Настройка стилей ttk
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self._colors["bg"], foreground=self._colors["text"])
        style.configure("TFrame", background=self._colors["bg"])
        style.configure("TLabel", background=self._colors["bg"], foreground=self._colors["text"])
        style.configure("TButton", background=self._colors["primary"], foreground="white", borderwidth=0, focuscolor="none")
        style.map("TButton", background=[("active", self._colors["primary_dark"])])
        style.configure("TCombobox", fieldbackground=self._colors["input"], background=self._colors["input"], foreground=self._colors["text"])
        style.configure("TProgressbar", background=self._colors["primary"], troughcolor=self._colors["surface_light"], borderwidth=0)

    def _build_ui(self) -> None:
        # Очищаем окно
        for w in self.root.winfo_children():
            w.destroy()
        
        # Главный контейнер
        self.main_container = tk.Frame(self.root, bg=self._colors["bg"])
        self.main_container.pack(fill="both", expand=True)
        
        # Заголовок окна (кастомный)
        self._build_titlebar()
        
        # Основной контент
        content = tk.Frame(self.main_container, bg=self._colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Левая панель навигации
        self._build_sidebar(content)
        
        # Правая область контента
        self.content_frame = tk.Frame(content, bg=self._colors["bg"])
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(20, 0))
        
        # Отображаем домашнюю страницу
        self._show_home_page()

    def _build_titlebar(self) -> None:
        titlebar = tk.Frame(self.main_container, bg=self._colors["surface"], height=48)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        
        # Логотип и название
        logo_frame = tk.Frame(titlebar, bg=self._colors["surface"])
        logo_frame.pack(side="left", padx=15, pady=8)
        
        logo = tk.Canvas(logo_frame, width=32, height=32, bg=self._colors["surface"], highlightthickness=0)
        logo.pack(side="left")
        # Рисуем логотип - стилизованный куб
        logo.create_polygon(16, 4, 28, 10, 28, 22, 16, 28, 4, 22, 4, 10, fill=self._colors["primary"], outline="")
        logo.create_polygon(16, 4, 28, 10, 16, 16, 4, 10, fill=self._colors["primary_light"], outline="")
        logo.create_polygon(16, 16, 28, 10, 28, 22, 16, 28, fill=self._colors["primary_dark"], outline="")
        
        tk.Label(logo_frame, text="XW Launcher", font=("Segoe UI", 14, "bold"), 
                bg=self._colors["surface"], fg=self._colors["text"]).pack(side="left", padx=8)
        
        # Кнопки управления окном
        controls = tk.Frame(titlebar, bg=self._colors["surface"])
        controls.pack(side="right", padx=10)
        
        for text, cmd in [("—", lambda: self.root.iconify()), ("□", self._toggle_maximize), ("×", self.root.quit)]:
            btn = tk.Label(controls, text=text, font=("Segoe UI", 14), 
                          bg=self._colors["surface"], fg=self._colors["text_secondary"],
                          padx=10, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=self._colors["text"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=self._colors["text_secondary"]))
            btn.bind("<Button-1>", lambda e, c=cmd: c())

    def _toggle_maximize(self) -> None:
        if self.root.state() == "normal":
            self.root.state("zoomed")
        else:
            self.root.state("normal")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg=self._colors["surface"], width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Аватар/профиль
        profile = tk.Frame(sidebar, bg=self._colors["surface_light"], height=80)
        profile.pack(fill="x", padx=12, pady=(20, 15))
        profile.pack_propagate(False)
        
        avatar = tk.Canvas(profile, width=48, height=48, bg=self._colors["surface_light"], highlightthickness=0)
        avatar.place(x=16, y=16)
        avatar.create_oval(8, 8, 40, 40, fill=self._colors["primary"], outline="")
        avatar.create_text(24, 28, text="👤", font=("Segoe UI", 20), fill="white")
        
        username = self.config.get("last_username", "Player")
        tk.Label(profile, text=username, font=("Segoe UI", 12, "bold"),
                bg=self._colors["surface_light"], fg=self._colors["text"]).place(x=76, y=20)
        tk.Label(profile, text="Offline", font=("Segoe UI", 9),
                bg=self._colors["surface_light"], fg=self._colors["text_muted"]).place(x=76, y=42)
        
        # Навигация
        nav_items = [
            ("home", "🏠", "Главная", self._show_home_page),
            ("instances", "📦", "Инстансы", self._show_instances_page),
            ("mods", "🔧", "Моды", self._show_mods_page),
            ("settings", "⚙️", "Настройки", self._show_settings_page),
        ]
        
        nav_frame = tk.Frame(sidebar, bg=self._colors["surface"])
        nav_frame.pack(fill="x", padx=8, pady=5)
        
        self.nav_buttons = {}
        for key, icon, label, cmd in nav_items:
            btn = tk.Frame(nav_frame, bg=self._colors["surface"], height=44, cursor="hand2")
            btn.pack(fill="x", pady=2)
            btn.pack_propagate(False)
            
            active = self._current_page == key
            bg = self._colors["primary"] if active else self._colors["surface"]
            fg = "white" if active else self._colors["text_secondary"]
            
            btn.configure(bg=bg)
            
            tk.Label(btn, text=icon, font=("Segoe UI", 16), bg=bg, fg=fg).place(x=16, y=10)
            tk.Label(btn, text=label, font=("Segoe UI", 11), bg=bg, fg=fg).place(x=52, y=12)
            
            btn.bind("<Enter>", lambda e, b=btn, k=key: self._nav_hover(b, k, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._nav_hover(b, k, False))
            btn.bind("<Button-1>", lambda e, c=cmd, k=key: self._nav_click(k, c))
            
            for child in btn.winfo_children():
                child.bind("<Enter>", lambda e, b=btn, k=key: self._nav_hover(b, k, True))
                child.bind("<Leave>", lambda e, b=btn, k=key: self._nav_hover(b, k, False))
                child.bind("<Button-1>", lambda e, c=cmd, k=key: self._nav_click(k, c))
            
            self.nav_buttons[key] = btn
        
        # Нижняя часть сайдбара
        bottom = tk.Frame(sidebar, bg=self._colors["surface"])
        bottom.pack(side="bottom", fill="x", padx=8, pady=20)
        
        # Переключатель темы
        theme_frame = tk.Frame(bottom, bg=self._colors["surface_light"], height=40)
        theme_frame.pack(fill="x", pady=5)
        theme_frame.pack_propagate(False)
        
        tk.Label(theme_frame, text="🌙" if self._theme_name == "dark" else "☀️", 
                font=("Segoe UI", 14), bg=self._colors["surface_light"]).place(x=12, y=8)
        tk.Label(theme_frame, text="Тёмная тема", font=("Segoe UI", 10),
                bg=self._colors["surface_light"], fg=self._colors["text"]).place(x=44, y=10)
        
        self.theme_var = tk.BooleanVar(value=self._theme_name == "dark")
        toggle = ttk.Checkbutton(theme_frame, variable=self.theme_var, command=self._toggle_theme)
        toggle.place(x=170, y=10)
        
        # Информация о версии
        tk.Label(bottom, text="XW Launcher v2.0", font=("Segoe UI", 8),
                bg=self._colors["surface"], fg=self._colors["text_muted"]).pack(pady=10)

    def _nav_hover(self, btn: tk.Frame, key: str, hover: bool) -> None:
        if self._current_page == key:
            return
        bg = self._colors["hover"] if hover else self._colors["surface"]
        fg = self._colors["text"] if hover else self._colors["text_secondary"]
        btn.configure(bg=bg)
        for child in btn.winfo_children():
            child.configure(bg=bg, fg=fg)

    def _nav_click(self, key: str, cmd) -> None:
        self._current_page = key
        for k, btn in self.nav_buttons.items():
            active = k == key
            bg = self._colors["primary"] if active else self._colors["surface"]
            fg = "white" if active else self._colors["text_secondary"]
            btn.configure(bg=bg)
            for child in btn.winfo_children():
                child.configure(bg=bg, fg=fg)
        cmd()

    def _toggle_theme(self) -> None:
        self._theme_name = "dark" if self.theme_var.get() else "light"
        self.config["theme"] = self._theme_name
        self._save_config()
        self._apply_theme()
        self._build_ui()
        self._show_home_page()

    def _clear_content(self) -> None:
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_home_page(self) -> None:
        self._clear_content()
        
        # Заголовок страницы
        header = tk.Frame(self.content_frame, bg=self._colors["bg"])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Главная", font=("Segoe UI", 24, "bold"),
                bg=self._colors["bg"], fg=self._colors["text"]).pack(side="left")
        
        # Кнопка запуска (быстрый доступ)
        play_btn = tk.Frame(header, bg=self._colors["primary"], cursor="hand2", padx=24, pady=10)
        play_btn.pack(side="right")
        play_btn.bind("<Button-1>", lambda e: self._quick_launch())
        
        tk.Label(play_btn, text="▶", font=("Segoe UI", 14), bg=self._colors["primary"], fg="white").pack(side="left", padx=(0, 8))
        tk.Label(play_btn, text="ИГРАТЬ", font=("Segoe UI", 12, "bold"), bg=self._colors["primary"], fg="white").pack(side="left")
        
        # Основной контент - две колонки
        main_row = tk.Frame(self.content_frame, bg=self._colors["bg"])
        main_row.pack(fill="both", expand=True)
        
        # Левая колонка (2/3)
        left_col = tk.Frame(main_row, bg=self._colors["bg"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Приветственная карточка
        welcome = tk.Frame(left_col, bg=self._colors["card"])
        welcome.pack(fill="x", pady=(0, 15))
        
        welcome_inner = tk.Frame(welcome, bg=self._colors["card"])
        welcome_inner.pack(fill="both", padx=24, pady=24)
        
        # Определяем время суток для приветствия
        hour = time.localtime().tm_hour
        greeting = "Доброе утро" if hour < 12 else "Добрый день" if hour < 18 else "Добрый вечер"
        
        tk.Label(welcome_inner, text=f"{greeting}, {self.config.get('last_username', 'Player')}!",
                font=("Segoe UI", 20, "bold"), bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w")
        
        last_version = self.config.get("last_version", "не выбрана")
        tk.Label(welcome_inner, text=f"Последняя версия: {last_version}",
                font=("Segoe UI", 11), bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w", pady=(5, 0))
        
        # Быстрые настройки
        quick_settings = tk.Frame(left_col, bg=self._colors["card"])
        quick_settings.pack(fill="x", pady=(0, 15))
        
        qs_inner = tk.Frame(quick_settings, bg=self._colors["card"])
        qs_inner.pack(fill="both", padx=24, pady=20)
        
        tk.Label(qs_inner, text="Быстрый запуск", font=("Segoe UI", 14, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w", pady=(0, 15))
        
        # Выбор версии
        ver_frame = tk.Frame(qs_inner, bg=self._colors["card"])
        ver_frame.pack(fill="x", pady=5)
        
        tk.Label(ver_frame, text="Версия", font=("Segoe UI", 10),
                bg=self._colors["card"], fg=self._colors["text_secondary"], width=10, anchor="w").pack(side="left")
        
        self.home_version_combo = ttk.Combobox(ver_frame, state="readonly", font=("Segoe UI", 10), width=30)
        self.home_version_combo["values"] = self.versions if self.versions else ["Загрузка..."]
        self.home_version_combo.pack(side="left", padx=10)
        if self.versions:
            last = self.config.get("last_version")
            if last in self.versions:
                self.home_version_combo.set(last)
            else:
                self.home_version_combo.current(0)
        
        # Выбор ника
        nick_frame = tk.Frame(qs_inner, bg=self._colors["card"])
        nick_frame.pack(fill="x", pady=5)
        
        tk.Label(nick_frame, text="Никнейм", font=("Segoe UI", 10),
                bg=self._colors["card"], fg=self._colors["text_secondary"], width=10, anchor="w").pack(side="left")
        
        self.home_nick_combo = ttk.Combobox(nick_frame, font=("Segoe UI", 10), width=30)
        self.home_nick_combo["values"] = self.config.get("username_history", ["Player"])
        self.home_nick_combo.set(self.config.get("last_username", "Player"))
        self.home_nick_combo.pack(side="left", padx=10)
        
        # Новости
        news = tk.Frame(left_col, bg=self._colors["card"])
        news.pack(fill="both", expand=True)
        
        news_inner = tk.Frame(news, bg=self._colors["card"])
        news_inner.pack(fill="both", padx=24, pady=20)
        
        tk.Label(news_inner, text="📰 Новости Minecraft", font=("Segoe UI", 14, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w", pady=(0, 15))
        
        # Список новостей
        for title, desc, date in self._news_items:
            item = tk.Frame(news_inner, bg=self._colors["surface_light"], cursor="hand2")
            item.pack(fill="x", pady=4)
            item_inner = tk.Frame(item, bg=self._colors["surface_light"])
            item_inner.pack(fill="x", padx=15, pady=12)
            
            tk.Label(item_inner, text=title, font=("Segoe UI", 11, "bold"),
                    bg=self._colors["surface_light"], fg=self._colors["text"]).pack(anchor="w")
            tk.Label(item_inner, text=desc, font=("Segoe UI", 9),
                    bg=self._colors["surface_light"], fg=self._colors["text_secondary"]).pack(anchor="w")
            tk.Label(item_inner, text=date, font=("Segoe UI", 8),
                    bg=self._colors["surface_light"], fg=self._colors["text_muted"]).pack(anchor="e")
            
            item.bind("<Enter>", lambda e, i=item: i.configure(bg=self._colors["hover"]))
            item.bind("<Leave>", lambda e, i=item: i.configure(bg=self._colors["surface_light"]))
        
        # Правая колонка (1/3)
        right_col = tk.Frame(main_row, bg=self._colors["bg"], width=320)
        right_col.pack(side="right", fill="y", padx=(10, 0))
        right_col.pack_propagate(False)
        
        # Статус загрузки
        status_card = tk.Frame(right_col, bg=self._colors["card"])
        status_card.pack(fill="x", pady=(0, 15))
        
        status_inner = tk.Frame(status_card, bg=self._colors["card"])
        status_inner.pack(fill="x", padx=20, pady=20)
        
        tk.Label(status_inner, text="📊 Статус", font=("Segoe UI", 12, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w", pady=(0, 10))
        
        self.progress = ttk.Progressbar(status_inner, mode="determinate", maximum=100, length=280)
        self.progress.pack(fill="x", pady=(0, 8))
        
        self.status_text = tk.StringVar(value="Готов к запуску")
        tk.Label(status_inner, textvariable=self.status_text, font=("Segoe UI", 9),
                bg=self._colors["card"], fg=self._colors["primary"]).pack(anchor="w")
        
        # Информация о системе
        sys_card = tk.Frame(right_col, bg=self._colors["card"])
        sys_card.pack(fill="both", expand=True)
        
        sys_inner = tk.Frame(sys_card, bg=self._colors["card"])
        sys_inner.pack(fill="both", padx=20, pady=20)
        
        tk.Label(sys_inner, text="💻 Система", font=("Segoe UI", 12, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w", pady=(0, 15))
        
        # Информация о Java
        java_ver = self._get_java_version()
        tk.Label(sys_inner, text="Java:", font=("Segoe UI", 10, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w")
        tk.Label(sys_inner, text=java_ver, font=("Segoe UI", 9),
                bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w", pady=(2, 10))
        
        # Папка игры
        tk.Label(sys_inner, text="Папка игры:", font=("Segoe UI", 10, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w")
        
        path_text = tk.Text(sys_inner, height=2, bg=self._colors["input"], fg=self._colors["text_secondary"],
                           font=("Segoe UI", 8), borderwidth=0, wrap="word")
        path_text.pack(fill="x", pady=(2, 0))
        path_text.insert("1.0", self.minecraft_dir)
        path_text.config(state="disabled")
        
        # Кнопка открыть папку
        open_folder = tk.Label(sys_inner, text="📂 Открыть папку", font=("Segoe UI", 9),
                              bg=self._colors["card"], fg=self._colors["primary"], cursor="hand2")
        open_folder.pack(anchor="w", pady=(5, 0))
        open_folder.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))

    def _show_instances_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg=self._colors["bg"])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Инстансы", font=("Segoe UI", 24, "bold"),
                bg=self._colors["bg"], fg=self._colors["text"]).pack(side="left")
        
        # Кнопка создания инстанса
        add_btn = tk.Frame(header, bg=self._colors["primary"], cursor="hand2", padx=20, pady=8)
        add_btn.pack(side="right")
        add_btn.bind("<Button-1>", lambda e: self._create_instance())
        
        tk.Label(add_btn, text="+", font=("Segoe UI", 14), bg=self._colors["primary"], fg="white").pack(side="left", padx=(0, 5))
        tk.Label(add_btn, text="Новый инстанс", font=("Segoe UI", 11), bg=self._colors["primary"], fg="white").pack(side="left")
        
        # Список инстансов
        instances = self.config.get("instances", [])
        
        if not instances:
            empty = tk.Frame(self.content_frame, bg=self._colors["card"])
            empty.pack(fill="both", expand=True)
            
            empty_inner = tk.Frame(empty, bg=self._colors["card"])
            empty_inner.pack(expand=True)
            
            tk.Label(empty_inner, text="📦", font=("Segoe UI", 48),
                    bg=self._colors["card"], fg=self._colors["text_muted"]).pack()
            tk.Label(empty_inner, text="Нет инстансов", font=("Segoe UI", 16, "bold"),
                    bg=self._colors["card"], fg=self._colors["text"]).pack(pady=(10, 5))
            tk.Label(empty_inner, text="Создайте первый инстанс для начала работы",
                    bg=self._colors["card"], fg=self._colors["text_secondary"]).pack()
            
            create_btn = tk.Label(empty_inner, text="+ Создать инстанс", font=("Segoe UI", 11),
                                 bg=self._colors["primary"], fg="white", padx=20, pady=8, cursor="hand2")
            create_btn.pack(pady=20)
            create_btn.bind("<Button-1>", lambda e: self._create_instance())
        else:
            grid = tk.Frame(self.content_frame, bg=self._colors["bg"])
            grid.pack(fill="both", expand=True)
            
            for i, inst in enumerate(instances):
                card = tk.Frame(grid, bg=self._colors["card"])
                card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
                
                grid.columnconfigure(i%2, weight=1)
                
                inner = tk.Frame(card, bg=self._colors["card"])
                inner.pack(fill="both", padx=20, pady=20)
                
                tk.Label(inner, text=inst.get("name", "Инстанс"), font=("Segoe UI", 14, "bold"),
                        bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w")
                tk.Label(inner, text=f"Версия: {inst.get('version', 'не выбрана')}", font=("Segoe UI", 10),
                        bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w", pady=(2, 0))
                tk.Label(inner, text=f"Модов: {len(inst.get('mods', []))}", font=("Segoe UI", 9),
                        bg=self._colors["card"], fg=self._colors["text_muted"]).pack(anchor="w")
                
                # Кнопки действий
                actions = tk.Frame(inner, bg=self._colors["card"])
                actions.pack(fill="x", pady=(15, 0))
                
                play = tk.Label(actions, text="▶ Играть", font=("Segoe UI", 10),
                               bg=self._colors["primary"], fg="white", padx=15, pady=5, cursor="hand2")
                play.pack(side="left")
                
                settings = tk.Label(actions, text="⚙️", font=("Segoe UI", 12),
                                   bg=self._colors["surface_light"], fg=self._colors["text_secondary"], 
                                   padx=10, pady=5, cursor="hand2")
                settings.pack(side="right")

    def _show_mods_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg=self._colors["bg"])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Моды", font=("Segoe UI", 24, "bold"),
                bg=self._colors["bg"], fg=self._colors["text"]).pack(side="left")
        
        # Вкладки
        tabs = tk.Frame(self.content_frame, bg=self._colors["surface_light"], height=40)
        tabs.pack(fill="x", pady=(0, 15))
        tabs.pack_propagate(False)
        
        for tab in ["Установленные", "Магазин модов", "Обновления"]:
            btn = tk.Label(tabs, text=tab, font=("Segoe UI", 11),
                          bg=self._colors["surface_light"], fg=self._colors["text_secondary"],
                          padx=20, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=self._colors["text"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=self._colors["text_secondary"]))
        
        # Список модов
        mods_frame = tk.Frame(self.content_frame, bg=self._colors["bg"])
        mods_frame.pack(fill="both", expand=True)
        
        mods = [
            ("Fabric API", "0.92.0", "FabricMC", True),
            ("Sodium", "0.5.8", "jellysquid3", True),
            ("Lithium", "0.12.1", "jellysquid3", True),
            ("Iris Shaders", "1.7.0", "coderbot", True),
            ("Mod Menu", "9.0.0", "Prospector", True),
            ("REI", "12.0.0", "shedaniel", False),
            ("Zoomify", "2.11.0", "XanderID", True),
            ("Entity Culling", "1.6.2", "tr7zw", True),
        ]
        
        canvas = tk.Canvas(mods_frame, bg=self._colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(mods_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self._colors["bg"])
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for name, version, author, enabled in mods:
            card = tk.Frame(scrollable, bg=self._colors["card"])
            card.pack(fill="x", pady=3)
            
            inner = tk.Frame(card, bg=self._colors["card"])
            inner.pack(fill="x", padx=20, pady=15)
            
            # Иконка мода
            icon = tk.Canvas(inner, width=40, height=40, bg=self._colors["card"], highlightthickness=0)
            icon.pack(side="left", padx=(0, 15))
            icon.create_rectangle(5, 5, 35, 35, fill=self._colors["primary"], outline="")
            icon.create_text(20, 20, text="📦", font=("Segoe UI", 16))
            
            # Информация
            info = tk.Frame(inner, bg=self._colors["card"])
            info.pack(side="left", fill="x", expand=True)
            
            tk.Label(info, text=name, font=("Segoe UI", 12, "bold"),
                    bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w")
            tk.Label(info, text=f"{author} • v{version}", font=("Segoe UI", 9),
                    bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w")
            
            # Переключатель
            var = tk.BooleanVar(value=enabled)
            toggle = ttk.Checkbutton(inner, variable=var)
            toggle.pack(side="right", padx=10)
            
            # Кнопка удалить
            delete = tk.Label(inner, text="🗑️", font=("Segoe UI", 12),
                             bg=self._colors["card"], fg=self._colors["text_muted"], cursor="hand2")
            delete.pack(side="right", padx=5)

    def _show_settings_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg=self._colors["bg"])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Настройки", font=("Segoe UI", 24, "bold"),
                bg=self._colors["bg"], fg=self._colors["text"]).pack(side="left")
        
        # Контейнер с прокруткой
        canvas = tk.Canvas(self.content_frame, bg=self._colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self._colors["bg"])
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Секции настроек
        sections = [
            ("🎮", "Игра", [
                ("Выделение памяти (MB)", "ram", "spinbox", (512, 16384)),
                ("Аргументы Java", "java_args", "entry", None),
                ("Скрывать лаунчер при запуске", "hide_launcher", "check", None),
                ("Показывать консоль", "show_console", "check", None),
            ]),
            ("🖥️", "Интерфейс", [
                ("Тёмная тема", "theme", "theme_toggle", None),
                ("Язык", "language", "combo", ["Русский", "English"]),
                ("Показывать новости", "show_news", "check", None),
            ]),
            ("📁", "Файлы", [
                ("Папка игры", "game_dir", "path", None),
                ("Папка лаунчера", "launcher_dir", "path", None),
            ]),
        ]
        
        for icon, title, settings in sections:
            card = tk.Frame(scrollable, bg=self._colors["card"])
            card.pack(fill="x", pady=5)
            
            inner = tk.Frame(card, bg=self._colors["card"])
            inner.pack(fill="both", padx=24, pady=20)
            
            # Заголовок секции
            header_frame = tk.Frame(inner, bg=self._colors["card"])
            header_frame.pack(fill="x", pady=(0, 15))
            
            tk.Label(header_frame, text=icon, font=("Segoe UI", 18),
                    bg=self._colors["card"]).pack(side="left", padx=(0, 8))
            tk.Label(header_frame, text=title, font=("Segoe UI", 14, "bold"),
                    bg=self._colors["card"], fg=self._colors["text"]).pack(side="left")
            
            # Настройки
            for label, key, widget_type, options in settings:
                row = tk.Frame(inner, bg=self._colors["card"])
                row.pack(fill="x", pady=8)
                
                tk.Label(row, text=label, font=("Segoe UI", 10),
                        bg=self._colors["card"], fg=self._colors["text_secondary"], width=25, anchor="w").pack(side="left")
                
                if widget_type == "spinbox":
                    var = tk.IntVar(value=self.config.get(key, 2048))
                    spin = tk.Spinbox(row, from_=options[0], to=options[1], textvariable=var,
                                     bg=self._colors["input"], fg=self._colors["text"], width=10)
                    spin.pack(side="left")
                    
                elif widget_type == "entry":
                    entry = tk.Entry(row, bg=self._colors["input"], fg=self._colors["text"],
                                    font=("Segoe UI", 10), width=40)
                    entry.insert(0, self.config.get(key, ""))
                    entry.pack(side="left", fill="x", expand=True)
                    
                elif widget_type == "check":
                    var = tk.BooleanVar(value=self.config.get(key, False))
                    ttk.Checkbutton(row, variable=var).pack(side="left")
                    
                elif widget_type == "theme_toggle":
                    ttk.Checkbutton(row, variable=self.theme_var, command=self._toggle_theme).pack(side="left")
                    
                elif widget_type == "combo":
                    combo = ttk.Combobox(row, values=options, state="readonly", width=15)
                    combo.set(options[0])
                    combo.pack(side="left")
                    
                elif widget_type == "path":
                    path_frame = tk.Frame(row, bg=self._colors["card"])
                    path_frame.pack(side="left", fill="x", expand=True)
                    
                    path_var = tk.StringVar(value=self.minecraft_dir if key == "game_dir" else str(Path.home()))
                    entry = tk.Entry(path_frame, textvariable=path_var, bg=self._colors["input"],
                                    fg=self._colors["text"], font=("Segoe UI", 9))
                    entry.pack(side="left", fill="x", expand=True)
                    
                    browse = tk.Label(path_frame, text="📂", font=("Segoe UI", 12),
                                     bg=self._colors["surface_light"], fg=self._colors["text"], padx=8, cursor="hand2")
                    browse.pack(side="right", padx=(5, 0))
        
        # Кнопки сохранения
        buttons = tk.Frame(scrollable, bg=self._colors["bg"])
        buttons.pack(fill="x", pady=20)
        
        save_btn = tk.Frame(buttons, bg=self._colors["primary"], cursor="hand2", padx=30, pady=10)
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: self._save_settings())
        
        tk.Label(save_btn, text="💾 Сохранить настройки", font=("Segoe UI", 11, "bold"),
                bg=self._colors["primary"], fg="white").pack()
        
        reset_btn = tk.Label(buttons, text="Сбросить", font=("Segoe UI", 10),
                            bg=self._colors["bg"], fg=self._colors["text_secondary"], cursor="hand2")
        reset_btn.pack(side="right", padx=20)

    def _get_java_version(self) -> str:
        try:
            import subprocess
            result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            return result.stderr.split("\n")[0] if result.stderr else "Не найдена"
        except:
            return "Не найдена"

    def _load_news(self) -> None:
        self._news_items = [
            ("Minecraft 1.21 вышел!", "Новое обновление с новыми мобами и блоками", "Вчера"),
            ("XW Launcher v2.0", "Полностью обновлённый интерфейс", "3 дня назад"),
            ("Совет дня", "Используйте инстансы для разных сборок", "Сегодня"),
        ]

    def _quick_launch(self) -> None:
        username = self.home_nick_combo.get().strip()
        version = self.home_version_combo.get().strip()
        
        if not username:
            messagebox.showwarning("Внимание", "Введите никнейм")
            return
        if not version or version == "Загрузка...":
            messagebox.showwarning("Внимание", "Выберите версию")
            return
        
        self._remember_profile(username, version)
        self._launch_game(username, version)

    def _launch_game(self, username: str, version: str) -> None:
        self.status_text.set("Подготовка к запуску...")
        self._reset_progress()
        self._install_in_progress = True
        self._last_progress_change_at = time.time()
        self._watch_install_progress()
        
        thread = threading.Thread(target=self._install_and_launch, args=(username, version), daemon=True)
        thread.start()

    def _install_and_launch(self, username: str, version: str) -> None:
        callback = {
            "setStatus": lambda s: self.root.after(0, lambda: self._update_status(s)),
            "setProgress": lambda v: self.root.after(0, lambda: self._update_progress(v)),
            "setMax": lambda v: self.root.after(0, lambda: self._update_max(v)),
        }
        try:
            minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir, callback=callback)
            
            options = {"username": username}
            command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
            subprocess.Popen(command, cwd=self.minecraft_dir)
            
            self.root.after(0, lambda: self._launch_success(version))
        except Exception as e:
            self.root.after(0, lambda: self._launch_error(e))

    def _update_status(self, status: str) -> None:
        clean = status.replace("_", " ").capitalize()
        self.status_text.set(f"📦 {clean}")
        self._last_progress_change_at = time.time()

    def _update_progress(self, value: int) -> None:
        safe = max(0, min(value, self._progress_max))
        self._progress_target = float(safe)
        self._last_progress_change_at = time.time()
        self._last_progress_value = safe

    def _update_max(self, value: int) -> None:
        self._progress_max = max(1, value)
        self.progress.configure(maximum=self._progress_max)

    def _launch_success(self, version: str) -> None:
        self._install_in_progress = False
        self.status_text.set(f"✓ Minecraft {version} запущен")
        self._progress_target = float(self._progress_max)

    def _launch_error(self, error: Exception) -> None:
        self._install_in_progress = False
        self.status_text.set("❌ Ошибка запуска")
        messagebox.showerror("Ошибка", f"Не удалось запустить игру:\n{error}")

    def _reset_progress(self) -> None:
        self.progress.stop()
        self._progress_max = 100
        self.progress.configure(mode="determinate", maximum=100)
        self._progress_target = 0.0
        self._progress_display = 0.0
        self.progress["value"] = 0

    def _watch_install_progress(self) -> None:
        if not self._install_in_progress:
            return
        
        idle = int(time.time() - self._last_progress_change_at)
        if idle >= 20:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
            if idle >= 60:
                self.status_text.set("⚠️ Проверьте соединение")
        
        self.root.after(1000, self._watch_install_progress)

    def _animate_progress(self) -> None:
        if hasattr(self, 'progress'):
            try:
                if str(self.progress.cget("mode")) == "determinate":
                    if self._progress_display < self._progress_target:
                        delta = max(1.0, (self._progress_target - self._progress_display) * 0.15)
                        self._progress_display = min(self._progress_target, self._progress_display + delta)
                    self.progress["value"] = self._progress_display
            except:
                pass
        self.root.after(33, self._animate_progress)

    def _load_versions_async(self) -> None:
        thread = threading.Thread(target=self._load_versions, daemon=True)
        thread.start()

    def _load_versions(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            versions = [v["id"] for v in manifest if v.get("type") == "release"][:30]
            self.root.after(0, lambda: self._versions_loaded(versions))
        except Exception as e:
            self.root.after(0, lambda: self._versions_error(e))

    def _versions_loaded(self, versions: list) -> None:
        self.versions = versions
        if hasattr(self, 'home_version_combo'):
            self.home_version_combo["values"] = versions
            last = self.config.get("last_version")
            if last in versions:
                self.home_version_combo.set(last)
            elif versions:
                self.home_version_combo.current(0)
        self.status_text.set(f"✓ Загружено {len(versions)} версий")

    def _versions_error(self, error: Exception) -> None:
        self.status_text.set("❌ Ошибка загрузки версий")

    def _remember_profile(self, username: str, version: str) -> None:
        history = self.config.get("username_history", [])
        if username in history:
            history.remove(username)
        history.insert(0, username)
        self.config["username_history"] = history[:8]
        self.config["last_username"] = username
        self.config["last_version"] = version
        self._save_config()

    def _create_instance(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Новый инстанс")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.configure(bg=self._colors["card"])
        
        inner = tk.Frame(dialog, bg=self._colors["card"])
        inner.pack(fill="both", padx=30, pady=30)
        
        tk.Label(inner, text="Создание инстанса", font=("Segoe UI", 16, "bold"),
                bg=self._colors["card"], fg=self._colors["text"]).pack(anchor="w", pady=(0, 20))
        
        tk.Label(inner, text="Название", font=("Segoe UI", 10),
                bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w")
        name_entry = tk.Entry(inner, bg=self._colors["input"], fg=self._colors["text"], font=("Segoe UI", 11))
        name_entry.pack(fill="x", pady=(5, 15))
        name_entry.insert(0, f"Инстанс {len(self.config.get('instances', [])) + 1}")
        
        tk.Label(inner, text="Версия Minecraft", font=("Segoe UI", 10),
                bg=self._colors["card"], fg=self._colors["text_secondary"]).pack(anchor="w")
        version_combo = ttk.Combobox(inner, values=self.versions, state="readonly", font=("Segoe UI", 11))
        version_combo.pack(fill="x", pady=(5, 15))
        if self.versions:
            version_combo.current(0)
        
        buttons = tk.Frame(inner, bg=self._colors["card"])
        buttons.pack(fill="x", pady=(10, 0))
        
        cancel = tk.Label(buttons, text="Отмена", font=("Segoe UI", 10),
                         bg=self._colors["card"], fg=self._colors["text_secondary"], cursor="hand2")
        cancel.pack(side="right", padx=(10, 0))
        cancel.bind("<Button-1>", lambda e: dialog.destroy())
        
        create = tk.Label(buttons, text="Создать", font=("Segoe UI", 10, "bold"),
                         bg=self._colors["primary"], fg="white", padx=20, pady=8, cursor="hand2")
        create.pack(side="right")
        create.bind("<Button-1>", lambda e: self._do_create_instance(name_entry.get(), version_combo.get(), dialog))

    def _do_create_instance(self, name: str, version: str, dialog: tk.Toplevel) -> None:
        if not name.strip():
            messagebox.showwarning("Внимание", "Введите название")
            return
        
        instances = self.config.get("instances", [])
        instances.append({"name": name, "version": version, "mods": []})
        self.config["instances"] = instances
        self._save_config()
        
        dialog.destroy()
        self._show_instances_page()

    def _save_settings(self) -> None:
        self._save_config()
        messagebox.showinfo("Настройки", "Настройки сохранены")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F11>", lambda e: self._toggle_maximize())
        self.root.bind("<Escape>", lambda e: self.root.state("normal") if self.root.state() == "zoomed" else None)
        self.root.bind("<F5>", lambda e: self._load_versions_async())


def main():
    root = tk.Tk()
    app = MinecraftLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()