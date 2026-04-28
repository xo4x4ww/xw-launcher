import json
import os
import subprocess
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import messagebox, ttk

import minecraft_launcher_lib


class MinecraftLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XW Minecraft Launcher")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.resizable(True, True)

        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._progress_max = 100
        self._install_in_progress = False
        self._last_progress_change_at = 0.0
        self._last_progress_value = 0
        self._last_watchdog_message = ""
        self._is_fullscreen = False
        self._theme_name = str(self.config.get("theme", "dark")).lower()
        if self._theme_name not in {"dark", "light"}:
            self._theme_name = "dark"
        self._theme_colors: dict[str, str] = {}
        self._nav_items: list[tk.Frame] = []
        self._active_nav_index = 0
        self._page_frames: dict[int, tk.Frame] = {}
        self._progress_target = 0.0
        self._progress_display = 0.0

        self._apply_window_icon()
        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._animate_progress()
        self._load_versions_async()

    def _load_config(self) -> dict:
        default_config = {
            "last_username": "Player",
            "last_version": "",
            "username_history": ["Player"],
            "version_history": [],
            "theme": "dark",
        }
        if not self.config_path.exists():
            return default_config

        try:
            with self.config_path.open("r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            return default_config

        merged = default_config.copy()
        merged.update(saved)
        merged["username_history"] = [str(item) for item in merged.get("username_history", []) if str(item).strip()]
        merged["version_history"] = [str(item) for item in merged.get("version_history", []) if str(item).strip()]
        return merged

    def _save_config(self) -> None:
        try:
            with self.config_path.open("w", encoding="utf-8") as config_file:
                json.dump(self.config, config_file, ensure_ascii=False, indent=2)
        except OSError:
            self.status_var.set("Не удалось сохранить настройки")

    def _apply_window_icon(self) -> None:
        # Создаем собственную иконку - кубик травы Minecraft
        icon_bitmap = """
#define launcher_width 16
#define launcher_height 16
static unsigned char launcher_bits[] = {
   0x00, 0x00, 0x80, 0x01, 0xc0, 0x03, 0xe0, 0x07,
   0xf0, 0x0f, 0xf8, 0x1f, 0xfc, 0x3f, 0xfe, 0x7f,
   0xfe, 0x7f, 0xfc, 0x3f, 0xf8, 0x1f, 0xf0, 0x0f,
   0xe0, 0x07, 0xc0, 0x03, 0x80, 0x01, 0x00, 0x00
};
"""
        try:
            bitmap_image = tk.BitmapImage(data=icon_bitmap, foreground="#3b82f6", background="#0f172a")
            self.root.iconphoto(True, bitmap_image)
            self._bitmap_image_ref = bitmap_image
        except tk.TclError:
            pass

    def _get_theme_palette(self) -> dict[str, str]:
        if self._theme_name == "light":
            return {
                "bg_primary": "#f8fafc",
                "bg_secondary": "#f1f5f9",
                "bg_tertiary": "#e2e8f0",
                "bg_card": "#ffffff",
                "sidebar_bg": "#ffffff",
                "text_primary": "#0f172a",
                "text_secondary": "#475569",
                "text_muted": "#94a3b8",
                "accent": "#3b82f6",
                "accent_hover": "#2563eb",
                "accent_light": "#dbeafe",
                "success": "#10b981",
                "warning": "#f59e0b",
                "error": "#ef4444",
                "border": "#e2e8f0",
                "input_bg": "#ffffff",
                "progress_bg": "#e2e8f0",
            }
        return {
            "bg_primary": "#0a0e17",
            "bg_secondary": "#111827",
            "bg_tertiary": "#1f2937",
            "bg_card": "#1a2332",
            "sidebar_bg": "#0d1421",
            "text_primary": "#f1f5f9",
            "text_secondary": "#9ca3af",
            "text_muted": "#6b7280",
            "accent": "#3b82f6",
            "accent_hover": "#60a5fa",
            "accent_light": "#1e3a5f",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "border": "#2d3748",
            "input_bg": "#1e293b",
            "progress_bg": "#2d3748",
        }

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        
        self._theme_colors = self._get_theme_palette()
        c = self._theme_colors
        
        self.root.configure(bg=c["bg_primary"])
        
        # Настройка стилей ttk
        style.configure("TFrame", background=c["bg_primary"])
        style.configure("Card.TFrame", background=c["bg_card"], relief="flat")
        style.configure("Sidebar.TFrame", background=c["sidebar_bg"])
        
        style.configure("TLabel", background=c["bg_primary"], foreground=c["text_primary"])
        style.configure("CardTitle.TLabel", background=c["bg_card"], foreground=c["text_primary"], font=("Segoe UI", 16, "bold"))
        style.configure("CardSubtitle.TLabel", background=c["bg_card"], foreground=c["text_secondary"], font=("Segoe UI", 10))
        style.configure("FieldLabel.TLabel", background=c["bg_card"], foreground=c["text_secondary"], font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=c["bg_card"], foreground=c["accent"], font=("Segoe UI", 9))
        style.configure("Path.TLabel", background=c["bg_card"], foreground=c["text_muted"], font=("Segoe UI", 8))
        
        style.configure("Accent.TButton", 
                       background=c["accent"], 
                       foreground="white",
                       borderwidth=0,
                       focuscolor="none",
                       font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                 background=[("active", c["accent_hover"]), ("pressed", c["accent"])])
        
        style.configure("Secondary.TButton",
                       background=c["bg_tertiary"],
                       foreground=c["text_primary"],
                       borderwidth=0,
                       font=("Segoe UI", 10))
        style.map("Secondary.TButton",
                 background=[("active", c["border"]), ("pressed", c["bg_tertiary"])])

        style.configure("TCombobox",
                       fieldbackground=c["input_bg"],
                       background=c["input_bg"],
                       foreground=c["text_primary"],
                       arrowcolor=c["text_primary"])
        style.map("TCombobox",
                 fieldbackground=[("readonly", c["input_bg"])],
                 selectbackground=[("readonly", c["accent"])],
                 selectforeground=[("readonly", "white")])

        style.configure("TProgressbar",
                       background=c["accent"],
                       troughcolor=c["progress_bg"],
                       borderwidth=0,
                       lightcolor=c["accent"],
                       darkcolor=c["accent"])

        style.configure("TCheckbutton",
                       background=c["bg_card"],
                       foreground=c["text_primary"])
        style.map("TCheckbutton",
                 background=[("active", c["bg_card"])])

    def _create_icon(self, canvas: tk.Canvas, icon_type: str, x: int, y: int, size: int, color: str) -> None:
        """Рисует векторные иконки на canvas"""
        canvas.delete("all")
        
        if icon_type == "home":
            # Домик
            points = [
                x + size//2, y + 2,  # вершина крыши
                x + size - 2, y + size//2,  # правый угол
                x + size - 4, y + size//2,
                x + size - 4, y + size - 2,
                x + 4, y + size - 2,
                x + 4, y + size//2,
                x + 2, y + size//2,
            ]
            canvas.create_polygon(points, fill=color, outline="", smooth=True)
            # Дверь
            canvas.create_rectangle(x + size//3, y + size*2//3, x + size*2//3, y + size - 2, 
                                   fill=self._theme_colors["bg_primary"], outline="", width=0)
            
        elif icon_type == "mods":
            # Пазл (моды)
            piece_size = size // 3
            # Верхний левый
            canvas.create_rectangle(x + 2, y + 2, x + piece_size, y + piece_size, fill=color, outline="", width=0)
            # Верхний правый
            canvas.create_rectangle(x + piece_size*2, y + 2, x + size - 2, y + piece_size, fill=color, outline="", width=0)
            # Нижний левый
            canvas.create_rectangle(x + 2, y + piece_size*2, x + piece_size, y + size - 2, fill=color, outline="", width=0)
            # Нижний правый
            canvas.create_rectangle(x + piece_size*2, y + piece_size*2, x + size - 2, y + size - 2, fill=color, outline="", width=0)
            # Выступы
            canvas.create_rectangle(x + piece_size, y + 2, x + piece_size*2, y + 4, fill=color, outline="", width=0)
            canvas.create_rectangle(x + piece_size, y + size - 4, x + piece_size*2, y + size - 2, fill=color, outline="", width=0)
            canvas.create_rectangle(x + 2, y + piece_size, x + 4, y + piece_size*2, fill=color, outline="", width=0)
            canvas.create_rectangle(x + size - 4, y + piece_size, x + size - 2, y + piece_size*2, fill=color, outline="", width=0)
            
        elif icon_type == "settings":
            # Шестеренка
            center_x, center_y = x + size//2, y + size//2
            outer_r = size//2 - 2
            inner_r = size//4
            canvas.create_oval(center_x - inner_r, center_y - inner_r, 
                              center_x + inner_r, center_y + inner_r, 
                              fill="", outline=color, width=2)
            # Зубцы
            import math
            for i in range(8):
                angle = i * math.pi / 4
                x1 = center_x + (inner_r + 2) * math.cos(angle)
                y1 = center_y + (inner_r + 2) * math.sin(angle)
                x2 = center_x + outer_r * math.cos(angle)
                y2 = center_y + outer_r * math.sin(angle)
                canvas.create_line(x1, y1, x2, y2, fill=color, width=3, capstyle="round")
                
        elif icon_type == "screenshots":
            # Фотоаппарат
            # Корпус
            canvas.create_rectangle(x + 2, y + size//3, x + size - 2, y + size - 2, 
                                   fill=color, outline="", width=0)
            # Объектив
            canvas.create_oval(x + size//3, y + size//2, x + size*2//3, y + size*2//3, 
                              fill=self._theme_colors["bg_primary"], outline=color, width=2)
            canvas.create_oval(x + size*2//5, y + size*3//5, x + size*3//5, y + size*7//10, 
                              fill=color, outline="", width=0)
            # Вспышка
            canvas.create_rectangle(x + size*2//3, y + 2, x + size - 4, y + size//3, 
                                   fill=color, outline="", width=0)
            
        elif icon_type == "help":
            # Вопросительный знак в круге
            canvas.create_oval(x + 2, y + 2, x + size - 2, y + size - 2, 
                              fill="", outline=color, width=2)
            # ?
            canvas.create_text(x + size//2, y + size//2, text="?", 
                              fill=color, font=("Segoe UI", size//2, "bold"))
            
        elif icon_type == "play":
            # Треугольник (плей)
            points = [
                x + 4, y + 2,
                x + size - 2, y + size//2,
                x + 4, y + size - 2,
            ]
            canvas.create_polygon(points, fill=color, outline="", smooth=True)
            
        elif icon_type == "refresh":
            # Круговая стрелка
            import math
            center_x, center_y = x + size//2, y + size//2
            r = size//2 - 2
            # Дуга
            canvas.create_arc(x + 2, y + 2, x + size - 2, y + size - 2, 
                             start=30, extent=300, style="arc", outline=color, width=2)
            # Стрелка
            arrow_x = center_x + r * 0.7
            arrow_y = center_y - r * 0.7
            canvas.create_line(arrow_x, arrow_y, arrow_x + 4, arrow_y - 4, fill=color, width=2)
            canvas.create_line(arrow_x, arrow_y, arrow_x - 2, arrow_y - 5, fill=color, width=2)

    def _build_ui(self) -> None:
        # Главный контейнер
        main_container = tk.Frame(self.root, bg=self._theme_colors["bg_primary"])
        main_container.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Боковая панель
        self.sidebar = tk.Frame(main_container, bg=self._theme_colors["sidebar_bg"], width=80)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Логотип
        logo_frame = tk.Frame(self.sidebar, bg=self._theme_colors["sidebar_bg"], height=80)
        logo_frame.pack(fill="x", pady=(20, 30))
        logo_frame.pack_propagate(False)
        
        logo_canvas = tk.Canvas(logo_frame, width=40, height=40, 
                               bg=self._theme_colors["sidebar_bg"], highlightthickness=0)
        logo_canvas.pack(expand=True)
        self._create_icon(logo_canvas, "home", 0, 0, 40, self._theme_colors["accent"])
        
        # Навигационные кнопки
        nav_items = [
            ("home", "Главная"),
            ("mods", "Моды"),
            ("settings", "Настройки"),
            ("screenshots", "Скриншоты"),
            ("help", "Справка"),
        ]
        
        for i, (icon_type, tooltip) in enumerate(nav_items):
            nav_frame = tk.Frame(self.sidebar, bg=self._theme_colors["sidebar_bg"], height=60)
            nav_frame.pack(fill="x", pady=5)
            nav_frame.pack_propagate(False)
            
            canvas = tk.Canvas(nav_frame, width=32, height=32, 
                              bg=self._theme_colors["sidebar_bg"], highlightthickness=0)
            canvas.pack(expand=True)
            
            color = self._theme_colors["accent"] if i == self._active_nav_index else self._theme_colors["text_muted"]
            self._create_icon(canvas, icon_type, 0, 0, 32, color)
            
            # Сохраняем данные для обновления
            nav_frame.canvas = canvas
            nav_frame.icon_type = icon_type
            nav_frame.index = i
            
            # Привязываем события
            nav_frame.bind("<Button-1>", lambda e, idx=i: self._on_nav_click(idx))
            nav_frame.bind("<Enter>", lambda e, f=nav_frame: self._on_nav_hover(f, True))
            nav_frame.bind("<Leave>", lambda e, f=nav_frame: self._on_nav_hover(f, False))
            canvas.bind("<Button-1>", lambda e, idx=i: self._on_nav_click(idx))
            canvas.bind("<Enter>", lambda e, f=nav_frame: self._on_nav_hover(f, True))
            canvas.bind("<Leave>", lambda e, f=nav_frame: self._on_nav_hover(f, False))
            
            self._nav_items.append(nav_frame)
        
        # Основная область контента
        self.content_area = tk.Frame(main_container, bg=self._theme_colors["bg_primary"])
        self.content_area.pack(side="right", fill="both", expand=True)
        
        # Верхняя панель
        topbar = tk.Frame(self.content_area, bg=self._theme_colors["bg_primary"], height=50)
        topbar.pack(fill="x", padx=20, pady=(15, 5))
        topbar.pack_propagate(False)
        
        # Заголовок страницы
        self.page_title = tk.Label(topbar, text="Главная", 
                                  font=("Segoe UI", 20, "bold"),
                                  bg=self._theme_colors["bg_primary"],
                                  fg=self._theme_colors["text_primary"])
        self.page_title.pack(side="left")
        
        # Кнопка темы
        theme_frame = tk.Frame(topbar, bg=self._theme_colors["bg_primary"])
        theme_frame.pack(side="right")
        
        self.theme_var = tk.BooleanVar(value=self._theme_name == "dark")
        theme_btn = ttk.Checkbutton(theme_frame, text="Темная тема", 
                                   variable=self.theme_var, 
                                   command=self._on_theme_toggle,
                                   style="TCheckbutton")
        theme_btn.pack(side="right")
        
        # Контейнер для страниц
        self.page_container = tk.Frame(self.content_area, bg=self._theme_colors["bg_primary"])
        self.page_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Создаем страницы
        self._build_pages()
        self._show_page(0)

    def _build_pages(self) -> None:
        self._page_frames[0] = self._build_home_page()
        self._page_frames[1] = self._build_mods_page()
        self._page_frames[2] = self._build_settings_page()
        self._page_frames[3] = self._build_screenshots_page()
        self._page_frames[4] = self._build_help_page()

    def _build_home_page(self) -> tk.Frame:
        page = tk.Frame(self.page_container, bg=self._theme_colors["bg_primary"])
        
        # Заголовок с приветствием
        welcome_frame = tk.Frame(page, bg=self._theme_colors["bg_card"])
        welcome_frame.pack(fill="x", pady=(0, 15))
        
        welcome_inner = tk.Frame(welcome_frame, bg=self._theme_colors["bg_card"])
        welcome_inner.pack(fill="both", padx=20, pady=20)
        
        tk.Label(welcome_inner, text="Добро пожаловать в XW Launcher!", 
                font=("Segoe UI", 18, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w")
        
        tk.Label(welcome_inner, text="Запустите Minecraft с выбранными настройками",
                font=("Segoe UI", 11),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_secondary"]).pack(anchor="w", pady=(5, 0))
        
        # Основной контент - две колонки
        content = tk.Frame(page, bg=self._theme_colors["bg_primary"])
        content.pack(fill="both", expand=True)
        
        # Левая колонка
        left_col = tk.Frame(content, bg=self._theme_colors["bg_primary"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Форма настроек
        form_card = tk.Frame(left_col, bg=self._theme_colors["bg_card"])
        form_card.pack(fill="both", expand=True)
        
        form_inner = tk.Frame(form_card, bg=self._theme_colors["bg_card"])
        form_inner.pack(fill="both", padx=20, pady=20)
        
        tk.Label(form_inner, text="Настройки запуска", 
                font=("Segoe UI", 14, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 15))
        
        # Никнейм
        tk.Label(form_inner, text="Никнейм", 
                font=("Segoe UI", 10),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_secondary"]).pack(anchor="w", pady=(0, 5))
        
        self.username_combo = ttk.Combobox(form_inner, state="normal", font=("Segoe UI", 11))
        self.username_combo["values"] = self.config.get("username_history", ["Player"])
        self.username_combo.set(self.config.get("last_username", "Player"))
        self.username_combo.pack(fill="x", pady=(0, 15))
        
        # Версия
        tk.Label(form_inner, text="Версия Minecraft", 
                font=("Segoe UI", 10),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_secondary"]).pack(anchor="w", pady=(0, 5))
        
        self.version_combo = ttk.Combobox(form_inner, state="readonly", font=("Segoe UI", 11))
        self.version_combo["values"] = ["Загрузка..."]
        self.version_combo.current(0)
        self.version_combo.pack(fill="x")
        
        # Кнопки действий
        button_frame = tk.Frame(form_inner, bg=self._theme_colors["bg_card"])
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Кнопка Play с иконкой
        play_frame = tk.Frame(button_frame, bg=self._theme_colors["accent"], cursor="hand2")
        play_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        play_canvas = tk.Canvas(play_frame, width=20, height=20, 
                               bg=self._theme_colors["accent"], highlightthickness=0)
        play_canvas.pack(side="left", padx=(15, 5), pady=10)
        self._create_icon(play_canvas, "play", 0, 0, 20, "white")
        
        play_label = tk.Label(play_frame, text="ИГРАТЬ", 
                             font=("Segoe UI", 11, "bold"),
                             bg=self._theme_colors["accent"],
                             fg="white",
                             cursor="hand2")
        play_label.pack(side="left", padx=(0, 15), pady=10)
        
        play_frame.bind("<Button-1>", lambda e: self._on_launch())
        play_canvas.bind("<Button-1>", lambda e: self._on_launch())
        play_label.bind("<Button-1>", lambda e: self._on_launch())
        
        # Кнопка Refresh с иконкой
        refresh_frame = tk.Frame(button_frame, bg=self._theme_colors["bg_tertiary"], cursor="hand2")
        refresh_frame.pack(side="left", padx=(5, 0))
        
        refresh_canvas = tk.Canvas(refresh_frame, width=20, height=20, 
                                  bg=self._theme_colors["bg_tertiary"], highlightthickness=0)
        refresh_canvas.pack(side="left", padx=(15, 5), pady=10)
        self._create_icon(refresh_canvas, "refresh", 0, 0, 20, self._theme_colors["text_primary"])
        
        refresh_label = tk.Label(refresh_frame, text="ОБНОВИТЬ", 
                                font=("Segoe UI", 11),
                                bg=self._theme_colors["bg_tertiary"],
                                fg=self._theme_colors["text_primary"],
                                cursor="hand2")
        refresh_label.pack(side="left", padx=(0, 15), pady=10)
        
        refresh_frame.bind("<Button-1>", lambda e: self._load_versions_async())
        refresh_canvas.bind("<Button-1>", lambda e: self._load_versions_async())
        refresh_label.bind("<Button-1>", lambda e: self._load_versions_async())
        
        self.launch_button = play_frame  # Для совместимости с _set_busy
        
        # Правая колонка
        right_col = tk.Frame(content, bg=self._theme_colors["bg_primary"], width=350)
        right_col.pack(side="right", fill="y", padx=(10, 0))
        right_col.pack_propagate(False)
        
        # Карточка прогресса
        progress_card = tk.Frame(right_col, bg=self._theme_colors["bg_card"])
        progress_card.pack(fill="x", pady=(0, 15))
        
        progress_inner = tk.Frame(progress_card, bg=self._theme_colors["bg_card"])
        progress_inner.pack(fill="x", padx=20, pady=20)
        
        tk.Label(progress_inner, text="Прогресс загрузки", 
                font=("Segoe UI", 12, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_inner, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 5))
        
        self.progress_text_var = tk.StringVar(value="Готов к запуску")
        tk.Label(progress_inner, textvariable=self.progress_text_var,
                font=("Segoe UI", 9),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["accent"]).pack(anchor="w")
        
        # Карточка статуса
        status_card = tk.Frame(right_col, bg=self._theme_colors["bg_card"])
        status_card.pack(fill="both", expand=True)
        
        status_inner = tk.Frame(status_card, bg=self._theme_colors["bg_card"])
        status_inner.pack(fill="both", padx=20, pady=20)
        
        tk.Label(status_inner, text="Информация", 
                font=("Segoe UI", 12, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Загрузка списка версий...")
        tk.Label(status_inner, textvariable=self.status_var,
                font=("Segoe UI", 10),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_secondary"],
                wraplength=280,
                justify="left").pack(anchor="w")
        
        # Путь к Minecraft
        tk.Label(status_inner, text=f"Папка игры:\n{self.minecraft_dir}",
                font=("Segoe UI", 8),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_muted"],
                wraplength=280,
                justify="left").pack(anchor="w", pady=(20, 0))
        
        # Кнопка полноэкранного режима
        self.fullscreen_button = tk.Button(status_inner, text="◉ Полный экран (F11)",
                                          font=("Segoe UI", 9),
                                          bg=self._theme_colors["bg_tertiary"],
                                          fg=self._theme_colors["text_primary"],
                                          bd=0,
                                          cursor="hand2",
                                          command=self._toggle_fullscreen)
        self.fullscreen_button.pack(fill="x", pady=(20, 0))
        
        return page

    def _build_mods_page(self) -> tk.Frame:
        page = tk.Frame(self.page_container, bg=self._theme_colors["bg_primary"])
        
        # Заголовок
        header = tk.Frame(page, bg=self._theme_colors["bg_card"])
        header.pack(fill="x", pady=(0, 15))
        
        header_inner = tk.Frame(header, bg=self._theme_colors["bg_card"])
        header_inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(header_inner, text="Управление модами", 
                font=("Segoe UI", 14, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(side="left")
        
        tk.Button(header_inner, text="+ Добавить мод",
                 font=("Segoe UI", 10),
                 bg=self._theme_colors["accent"],
                 fg="white",
                 bd=0,
                 padx=15,
                 pady=8,
                 cursor="hand2").pack(side="right")
        
        # Список модов
        mods_card = tk.Frame(page, bg=self._theme_colors["bg_card"])
        mods_card.pack(fill="both", expand=True)
        
        mods_inner = tk.Frame(mods_card, bg=self._theme_colors["bg_card"])
        mods_inner.pack(fill="both", padx=20, pady=20)
        
        mods = [
            ("Fabric API", "0.92.0", True),
            ("Sodium", "0.5.8", True),
            ("Lithium", "0.12.1", True),
            ("Iris Shaders", "1.7.0", True),
            ("Mod Menu", "9.0.0", True),
            ("REI", "12.0.0", False),
        ]
        
        for mod_name, version, enabled in mods:
            mod_frame = tk.Frame(mods_inner, bg=self._theme_colors["bg_secondary"])
            mod_frame.pack(fill="x", pady=3)
            
            mod_inner = tk.Frame(mod_frame, bg=self._theme_colors["bg_secondary"])
            mod_inner.pack(fill="x", padx=15, pady=10)
            
            tk.Label(mod_inner, text=mod_name,
                    font=("Segoe UI", 11, "bold"),
                    bg=self._theme_colors["bg_secondary"],
                    fg=self._theme_colors["text_primary"]).pack(side="left")
            
            tk.Label(mod_inner, text=f"v{version}",
                    font=("Segoe UI", 9),
                    bg=self._theme_colors["bg_secondary"],
                    fg=self._theme_colors["text_muted"]).pack(side="left", padx=(10, 0))
            
            status_color = self._theme_colors["success"] if enabled else self._theme_colors["error"]
            status_text = "● Активен" if enabled else "○ Отключен"
            tk.Label(mod_inner, text=status_text,
                    font=("Segoe UI", 9),
                    bg=self._theme_colors["bg_secondary"],
                    fg=status_color).pack(side="right")
        
        return page

    def _build_settings_page(self) -> tk.Frame:
        page = tk.Frame(self.page_container, bg=self._theme_colors["bg_primary"])
        
        card = tk.Frame(page, bg=self._theme_colors["bg_card"])
        card.pack(fill="both", expand=True)
        
        inner = tk.Frame(card, bg=self._theme_colors["bg_card"])
        inner.pack(fill="both", padx=30, pady=30)
        
        tk.Label(inner, text="Настройки лаунчера", 
                font=("Segoe UI", 16, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 20))
        
        settings = [
            ("Показывать консоль при запуске", False),
            ("Скрывать лаунчер при старте игры", True),
            ("Уведомлять об обновлениях", True),
            ("Автоматически проверять Java", True),
            ("Запоминать последний мир", False),
        ]
        
        self.setting_vars = []
        for text, default in settings:
            var = tk.BooleanVar(value=default)
            self.setting_vars.append(var)
            
            cb = ttk.Checkbutton(inner, text=text, variable=var)
            cb.pack(anchor="w", pady=8)
        
        # Кнопка сохранения
        tk.Button(inner, text="Сохранить настройки",
                 font=("Segoe UI", 10, "bold"),
                 bg=self._theme_colors["accent"],
                 fg="white",
                 bd=0,
                 padx=20,
                 pady=10,
                 cursor="hand2").pack(anchor="w", pady=(20, 0))
        
        return page

    def _build_screenshots_page(self) -> tk.Frame:
        page = tk.Frame(self.page_container, bg=self._theme_colors["bg_primary"])
        
        card = tk.Frame(page, bg=self._theme_colors["bg_card"])
        card.pack(fill="both", expand=True)
        
        inner = tk.Frame(card, bg=self._theme_colors["bg_card"])
        inner.pack(fill="both", padx=30, pady=30)
        
        tk.Label(inner, text="Галерея скриншотов", 
                font=("Segoe UI", 16, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 10))
        
        tk.Label(inner, text="Скриншоты сохраняются в папке .minecraft/screenshots", 
                font=("Segoe UI", 10),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_secondary"]).pack(anchor="w", pady=(0, 20))
        
        # Сетка превью
        grid = tk.Frame(inner, bg=self._theme_colors["bg_card"])
        grid.pack(fill="both", expand=True)
        
        for i in range(4):
            grid.columnconfigure(i, weight=1)
        
        for i in range(4):
            preview = tk.Frame(grid, bg=self._theme_colors["bg_secondary"], 
                              width=150, height=120)
            preview.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            preview.pack_propagate(False)
            
            tk.Label(preview, text="🖼️",
                    font=("Segoe UI", 24),
                    bg=self._theme_colors["bg_secondary"],
                    fg=self._theme_colors["text_muted"]).pack(expand=True)
            
            tk.Label(preview, text=f"Скриншот {i+1}",
                    font=("Segoe UI", 8),
                    bg=self._theme_colors["bg_secondary"],
                    fg=self._theme_colors["text_secondary"]).pack()
        
        return page

    def _build_help_page(self) -> tk.Frame:
        page = tk.Frame(self.page_container, bg=self._theme_colors["bg_primary"])
        
        card = tk.Frame(page, bg=self._theme_colors["bg_card"])
        card.pack(fill="both", expand=True)
        
        inner = tk.Frame(card, bg=self._theme_colors["bg_card"])
        inner.pack(fill="both", padx=30, pady=30)
        
        tk.Label(inner, text="Справка и поддержка", 
                font=("Segoe UI", 16, "bold"),
                bg=self._theme_colors["bg_card"],
                fg=self._theme_colors["text_primary"]).pack(anchor="w", pady=(0, 20))
        
        faq_items = [
            ("Как запустить игру?", "Выберите никнейм и версию, затем нажмите 'Играть'"),
            ("Где находятся файлы игры?", f"В папке: {self.minecraft_dir}"),
            ("Как обновить список версий?", "Нажмите кнопку 'Обновить' на главной странице"),
            ("Как переключить тему?", "Используйте переключатель в правом верхнем углу"),
            ("Полноэкранный режим", "Нажмите F11 или кнопку 'Полный экран'"),
            ("Проблемы с запуском?", "Проверьте наличие Java и интернет-соединение"),
        ]
        
        for question, answer in faq_items:
            q_frame = tk.Frame(inner, bg=self._theme_colors["bg_card"])
            q_frame.pack(fill="x", pady=5)
            
            tk.Label(q_frame, text=f"▶ {question}",
                    font=("Segoe UI", 11, "bold"),
                    bg=self._theme_colors["bg_card"],
                    fg=self._theme_colors["accent"]).pack(anchor="w")
            
            tk.Label(q_frame, text=f"   {answer}",
                    font=("Segoe UI", 10),
                    bg=self._theme_colors["bg_card"],
                    fg=self._theme_colors["text_secondary"],
                    wraplength=500,
                    justify="left").pack(anchor="w", pady=(2, 0))
        
        return page

    def _show_page(self, index: int) -> None:
        for page_index, frame in self._page_frames.items():
            if page_index == index:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        
        # Обновляем активную иконку
        titles = ["Главная", "Моды", "Настройки", "Скриншоты", "Справка"]
        self.page_title.config(text=titles[index])
        
        for i, nav_frame in enumerate(self._nav_items):
            color = self._theme_colors["accent"] if i == index else self._theme_colors["text_muted"]
            self._create_icon(nav_frame.canvas, nav_frame.icon_type, 0, 0, 32, color)
        
        self._active_nav_index = index

    def _on_nav_click(self, index: int) -> None:
        self._show_page(index)

    def _on_nav_hover(self, nav_frame: tk.Frame, hover: bool) -> None:
        if nav_frame.index == self._active_nav_index:
            return
        color = self._theme_colors["accent"] if hover else self._theme_colors["text_muted"]
        self._create_icon(nav_frame.canvas, nav_frame.icon_type, 0, 0, 32, color)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F11>", self._toggle_fullscreen_event)
        self.root.bind("<Escape>", self._exit_fullscreen_event)

    def _toggle_fullscreen_event(self, _event: tk.Event) -> str:
        self._toggle_fullscreen()
        return "break"

    def _exit_fullscreen_event(self, _event: tk.Event) -> str:
        if self._is_fullscreen:
            self._toggle_fullscreen()
        return "break"

    def _toggle_fullscreen(self) -> None:
        self._is_fullscreen = not self._is_fullscreen
        self.root.attributes("-fullscreen", self._is_fullscreen)
        button_text = "◉ Оконный режим (F11)" if self._is_fullscreen else "◉ Полный экран (F11)"
        self.fullscreen_button.config(text=button_text)

    def _on_theme_toggle(self) -> None:
        self._theme_name = "dark" if self.theme_var.get() else "light"
        self.config["theme"] = self._theme_name
        self._save_config()
        self._configure_styles()
        
        # Пересоздаем интерфейс
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_ui()
        self._show_page(self._active_nav_index)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        if hasattr(self, 'launch_button'):
            for child in self.launch_button.winfo_children():
                child.configure(state=state)

    def _load_versions_async(self) -> None:
        self._set_busy(True)
        self._start_indeterminate_progress("Загрузка списка версий...")
        self.status_var.set("Получение версий от Mojang...")
        thread = threading.Thread(target=self._load_versions_worker, daemon=True)
        thread.start()

    def _load_versions_worker(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            release_versions = [item["id"] for item in manifest if item.get("type") == "release"]
            versions = release_versions[:30]
            if not versions:
                raise RuntimeError("Не удалось получить релизные версии.")
        except Exception as exc:
            self.root.after(0, lambda: self._on_versions_error(exc))
            return

        self.root.after(0, lambda: self._on_versions_loaded(versions))

    def _on_versions_loaded(self, versions: list[str]) -> None:
        saved_versions = [item for item in self.config.get("version_history", []) if item in versions]
        ordered_versions = saved_versions + [item for item in versions if item not in saved_versions]
        self.versions = ordered_versions
        self.version_combo["values"] = ordered_versions
        last_version = self.config.get("last_version")
        if last_version in ordered_versions:
            self.version_combo.set(last_version)
        else:
            self.version_combo.current(0)
        self._stop_progress()
        self.status_var.set(f"✓ Загружено {len(versions)} версий")
        self.progress_text_var.set("Готов к запуску")
        self._set_busy(False)

    def _on_versions_error(self, exc: Exception) -> None:
        self._stop_progress()
        self.status_var.set("❌ Ошибка загрузки версий")
        self.version_combo["values"] = ["latest"]
        self.version_combo.current(0)
        self._set_busy(False)
        messagebox.showerror("Ошибка", f"Не удалось получить версии:\n{exc}")

    def _on_launch(self) -> None:
        username = self.username_combo.get().strip()
        version = self.version_combo.get().strip()

        if not username:
            messagebox.showwarning("Проверка", "Введите никнейм.")
            return
        if not version or version == "Загрузка...":
            messagebox.showwarning("Проверка", "Выберите версию.")
            return

        self._remember_profile(username, version)
        self._set_busy(True)
        self._reset_progress()
        self.status_var.set(f"⏳ Установка версии {version}...")
        self.progress_text_var.set("Подготовка...")
        self._install_in_progress = True
        self._last_progress_change_at = time.time()
        self._last_progress_value = 0
        self._last_watchdog_message = ""
        self._watch_install_progress()

        thread = threading.Thread(
            target=self._install_and_launch_worker,
            args=(username, version),
            daemon=True,
        )
        thread.start()

    def _install_and_launch_worker(self, username: str, version: str) -> None:
        callback = {
            "setStatus": self._install_status_callback,
            "setProgress": self._install_progress_callback,
            "setMax": self._install_max_callback,
        }
        try:
            minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir, callback=callback)

            options = {"username": username}
            command = minecraft_launcher_lib.command.get_minecraft_command(
                version,
                self.minecraft_dir,
                options,
            )
            subprocess.Popen(command, cwd=self.minecraft_dir)
        except Exception as exc:
            self.root.after(0, lambda: self._on_launch_error(exc))
            return

        self.root.after(0, lambda: self._on_launch_success(version))

    def _on_launch_success(self, version: str) -> None:
        self._install_in_progress = False
        self.status_var.set(f"✓ Minecraft {version} запущен")
        self._progress_target = float(self._progress_max)
        self.progress_text_var.set("Игра запущена!")
        self._set_busy(False)

    def _on_launch_error(self, exc: Exception) -> None:
        self._install_in_progress = False
        self.status_var.set("❌ Ошибка запуска")
        self.progress_text_var.set("Произошла ошибка")
        self._set_busy(False)
        messagebox.showerror("Ошибка запуска", f"Не удалось запустить игру:\n{exc}")

    def _remember_profile(self, username: str, version: str) -> None:
        username_history = self.config.get("username_history", [])
        version_history = self.config.get("version_history", [])

        if username in username_history:
            username_history.remove(username)
        if version in version_history:
            version_history.remove(version)

        username_history.insert(0, username)
        version_history.insert(0, version)

        self.config["last_username"] = username
        self.config["last_version"] = version
        self.config["username_history"] = username_history[:8]
        self.config["version_history"] = version_history[:15]

        self.username_combo["values"] = self.config["username_history"]
        self._save_config()

    def _start_indeterminate_progress(self, text: str) -> None:
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.progress_text_var.set(text)

    def _stop_progress(self) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", maximum=100)
        self._progress_target = 0.0
        self._progress_display = 0.0
        self.progress["value"] = 0
        self.progress_text_var.set("Готов к запуску")

    def _reset_progress(self) -> None:
        self.progress.stop()
        self._progress_max = 100
        self.progress.configure(mode="determinate", maximum=self._progress_max)
        self._progress_target = 0.0
        self._progress_display = 0.0
        self.progress["value"] = 0

    def _install_status_callback(self, status: str) -> None:
        self.root.after(0, lambda: self._update_progress_status(status))

    def _install_progress_callback(self, value: int) -> None:
        self.root.after(0, lambda: self._update_progress_value(value))

    def _install_max_callback(self, value: int) -> None:
        self.root.after(0, lambda: self._update_progress_max(value))

    def _update_progress_status(self, status: str) -> None:
        clean_status = status.replace("_", " ").strip().capitalize()
        self.progress_text_var.set(f"📦 {clean_status}")
        self._last_progress_change_at = time.time()
        self._last_watchdog_message = ""

    def _update_progress_value(self, value: int) -> None:
        safe_value = max(0, min(value, self._progress_max))
        self._progress_target = float(safe_value)
        if safe_value != self._last_progress_value:
            self._last_progress_change_at = time.time()
            self._last_progress_value = safe_value
            self._last_watchdog_message = ""
        percent = int((safe_value / max(1, self._progress_max)) * 100)
        self.status_var.set(f"⬇️ Загрузка... {percent}%")

    def _update_progress_max(self, value: int) -> None:
        self._progress_max = max(1, int(value))
        self.progress.configure(mode="determinate", maximum=self._progress_max)
        self._progress_target = 0.0
        self._progress_display = 0.0
        self.progress["value"] = 0

    def _watch_install_progress(self) -> None:
        if not self._install_in_progress:
            return

        idle_seconds = int(time.time() - self._last_progress_change_at)
        if idle_seconds >= 20:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
            hint = "⏳ Медленное соединение..."
            if idle_seconds >= 60:
                hint = "⚠️ Проверьте интернет-соединение"
            if hint != self._last_watchdog_message:
                self.progress_text_var.set(hint)
                self._last_watchdog_message = hint
        else:
            if str(self.progress.cget("mode")) != "determinate":
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=self._progress_max)
                self.progress["value"] = self._progress_display

        self.root.after(1000, self._watch_install_progress)

    def _animate_progress(self) -> None:
        if str(self.progress.cget("mode")) == "determinate":
            if self._progress_display < self._progress_target:
                delta = max(1.0, (self._progress_target - self._progress_display) * 0.15)
                self._progress_display = min(self._progress_target, self._progress_display + delta)
            elif self._progress_display > self._progress_target:
                self._progress_display = self._progress_target

            self.progress["value"] = self._progress_display

        self.root.after(33, self._animate_progress)


def main() -> None:
    root = tk.Tk()
    MinecraftLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()