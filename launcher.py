import json
import os
import subprocess
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import messagebox, ttk, font as tkfont

import minecraft_launcher_lib


class JustLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("1000x650")
        self.root.minsize(900, 550)
        self.root.configure(bg="#0D0D0D")
        
        # Центрирование
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.root.winfo_screenheight() // 2) - (650 // 2)
        self.root.geometry(f"1000x650+{x}+{y}")

        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._progress_max = 100
        self._install_in_progress = False
        self._last_progress_change_at = 0.0
        self._current_page = "home"
        self._progress_target = 0.0
        self._progress_display = 0.0
        self._news_items = []
        self._servers = [
            {"name": "SURVIVAL", "desc": "Ванильное выживание. Ноль модов, ноль плагинов.", 
             "online": "21/100", "ip": "PLAY.SURVIVAL.NET", "version": "1.20.1"},
            {"name": "ANARCHY", "desc": "У нас разрешено всё, присоединяйся!", 
             "online": "84/200", "ip": "PLAY.ANARCHY.NET", "version": "1.8 - 1.20.1"},
        ]
        self._installations = [
            {"name": "Последняя версия", "version": "1.20.1", "type": "Релиз", "time": "10ч", "loader": None},
            {"name": "Test", "version": "1.20-pre1", "type": "Снапшот", "time": "2ч", "loader": None},
            {"name": "Create", "version": "1.19.2", "type": "Сборка", "loader": "Fabric", "time": "20ч"},
            {"name": "Старая версия", "version": "1.19", "type": "Релиз", "time": "20ч", "loader": None},
        ]

        self._setup_styles()
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
            "ram_allocation": 2048,
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

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", background="#4A90D9", troughcolor="#1E1E1E", borderwidth=0, thickness=4)

    def _build_ui(self) -> None:
        # Главный контейнер
        self.main_container = tk.Frame(self.root, bg="#0D0D0D")
        self.main_container.pack(fill="both", expand=True)
        
        # Верхняя панель (заголовок и ник)
        self._build_topbar()
        
        # Основной контент с боковой панелью
        content = tk.Frame(self.main_container, bg="#0D0D0D")
        content.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Левая панель навигации
        self._build_sidebar(content)
        
        # Правая область контента
        self.content_frame = tk.Frame(content, bg="#0D0D0D")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        # Нижняя панель с иконками
        self._build_bottombar()
        
        # Показываем главную страницу
        self._show_home_page()

    def _build_topbar(self) -> None:
        topbar = tk.Frame(self.main_container, bg="#0D0D0D", height=55)
        topbar.pack(fill="x", padx=15, pady=(10, 5))
        topbar.pack_propagate(False)
        
        # Логотип
        logo_frame = tk.Frame(topbar, bg="#0D0D0D")
        logo_frame.pack(side="left")
        
        logo = tk.Canvas(logo_frame, width=36, height=36, bg="#0D0D0D", highlightthickness=0)
        logo.pack(side="left")
        # Рисуем логотип - стилизованный куб
        logo.create_polygon(18, 4, 30, 10, 30, 22, 18, 28, 6, 22, 6, 10, fill="#4A90D9", outline="")
        logo.create_polygon(18, 4, 30, 10, 18, 16, 6, 10, fill="#6BAED6", outline="")
        logo.create_polygon(18, 16, 30, 10, 30, 22, 18, 28, fill="#2171B5", outline="")
        
        tk.Label(logo_frame, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(side="left", padx=8)
        
        # Правая часть - ник и иконки
        right_frame = tk.Frame(topbar, bg="#0D0D0D")
        right_frame.pack(side="right")
        
        # Иконки (уведомления, настройки)
        icons_frame = tk.Frame(right_frame, bg="#0D0D0D")
        icons_frame.pack(side="right", padx=(0, 15))
        
        for icon in ["🔔", "⚙️"]:
            btn = tk.Label(icons_frame, text=icon, font=("Segoe UI", 14),
                          bg="#0D0D0D", fg="#888888", cursor="hand2")
            btn.pack(side="left", padx=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#FFFFFF"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg="#888888"))
        
        # Профиль игрока
        profile_frame = tk.Frame(right_frame, bg="#1E1E1E")
        profile_frame.pack(side="right")
        
        profile_inner = tk.Frame(profile_frame, bg="#1E1E1E")
        profile_inner.pack(padx=12, pady=6)
        
        username = self.config.get("last_username", "Player")
        tk.Label(profile_inner, text=f"👤 {username}", font=("Segoe UI", 11, "bold"),
                bg="#1E1E1E", fg="#FFFFFF").pack(side="left")
        
        # Выпадающее меню
        tk.Label(profile_inner, text=" ▼", font=("Segoe UI", 9),
                bg="#1E1E1E", fg="#888888").pack(side="left", padx=(5, 0))

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg="#121212", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Навигационные кнопки
        nav_items = [
            ("🎮", "Играть", "home"),
            ("📦", "Установки", "installations"),
            ("🌐", "Сервера", "servers"),
            ("📚", "Сборки", "modpacks"),
            ("📰", "Новости", "news"),
        ]
        
        nav_frame = tk.Frame(sidebar, bg="#121212")
        nav_frame.pack(fill="x", padx=10, pady=15)
        
        self.nav_buttons = {}
        for icon, label, key in nav_items:
            btn = tk.Frame(nav_frame, bg="#121212", height=42, cursor="hand2")
            btn.pack(fill="x", pady=2)
            btn.pack_propagate(False)
            
            active = self._current_page == key
            bg = "#2A2A2A" if active else "#121212"
            fg = "#FFFFFF" if active else "#AAAAAA"
            
            btn.configure(bg=bg)
            
            tk.Label(btn, text=icon, font=("Segoe UI", 14), bg=bg, fg=fg).place(x=12, y=10)
            tk.Label(btn, text=label, font=("Segoe UI", 11), bg=bg, fg=fg).place(x=42, y=11)
            
            btn.bind("<Enter>", lambda e, b=btn, k=key: self._nav_hover(b, k, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._nav_hover(b, k, False))
            btn.bind("<Button-1>", lambda e, k=key: self._nav_click(k))
            
            for child in btn.winfo_children():
                child.bind("<Enter>", lambda e, b=btn, k=key: self._nav_hover(b, k, True))
                child.bind("<Leave>", lambda e, b=btn, k=key: self._nav_hover(b, k, False))
                child.bind("<Button-1>", lambda e, k=key: self._nav_click(k))
            
            self.nav_buttons[key] = btn

    def _build_bottombar(self) -> None:
        bottombar = tk.Frame(self.main_container, bg="#121212", height=45)
        bottombar.pack(fill="x", side="bottom")
        bottombar.pack_propagate(False)
        
        items = [
            ("👤", "Аккаунты"),
            ("⚙️", "Настройки"),
            ("📁", "Папка игры"),
        ]
        
        for icon, label in items:
            btn = tk.Frame(bottombar, bg="#121212", cursor="hand2")
            btn.pack(side="left", padx=20, pady=8)
            
            tk.Label(btn, text=icon, font=("Segoe UI", 12), bg="#121212", fg="#AAAAAA").pack(side="left")
            tk.Label(btn, text=label, font=("Segoe UI", 10), bg="#121212", fg="#AAAAAA").pack(side="left", padx=5)
            
            btn.bind("<Enter>", lambda e, b=btn: self._bottom_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self._bottom_hover(b, False))
            for child in btn.winfo_children():
                child.bind("<Enter>", lambda e, b=btn: self._bottom_hover(b, True))
                child.bind("<Leave>", lambda e, b=btn: self._bottom_hover(b, False))
            
            if label == "Папка игры":
                btn.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))
                for child in btn.winfo_children():
                    child.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))

    def _bottom_hover(self, btn: tk.Frame, hover: bool) -> None:
        fg = "#FFFFFF" if hover else "#AAAAAA"
        btn.configure(bg="#1E1E1E" if hover else "#121212")
        for child in btn.winfo_children():
            child.configure(bg="#1E1E1E" if hover else "#121212", fg=fg)

    def _nav_hover(self, btn: tk.Frame, key: str, hover: bool) -> None:
        if self._current_page == key:
            return
        bg = "#1E1E1E" if hover else "#121212"
        fg = "#FFFFFF" if hover else "#AAAAAA"
        btn.configure(bg=bg)
        for child in btn.winfo_children():
            child.configure(bg=bg, fg=fg)

    def _nav_click(self, key: str) -> None:
        self._current_page = key
        for k, btn in self.nav_buttons.items():
            active = k == key
            bg = "#2A2A2A" if active else "#121212"
            fg = "#FFFFFF" if active else "#AAAAAA"
            btn.configure(bg=bg)
            for child in btn.winfo_children():
                child.configure(bg=bg, fg=fg)
        
        pages = {
            "home": self._show_home_page,
            "installations": self._show_installations_page,
            "servers": self._show_servers_page,
            "modpacks": self._show_modpacks_page,
            "news": self._show_news_page,
        }
        pages.get(key, self._show_home_page)()

    def _clear_content(self) -> None:
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_home_page(self) -> None:
        self._clear_content()
        
        # Верхняя строка с приветствием и кнопкой Играть
        top_row = tk.Frame(self.content_frame, bg="#0D0D0D")
        top_row.pack(fill="x", pady=(0, 15))
        
        # Приветствие
        welcome = tk.Frame(top_row, bg="#0D0D0D")
        welcome.pack(side="left")
        
        tk.Label(welcome, text="Добро пожаловать,", font=("Segoe UI", 12),
                bg="#0D0D0D", fg="#AAAAAA").pack(anchor="w")
        
        username = self.config.get("last_username", "Player")
        tk.Label(welcome, text=username, font=("Segoe UI", 20, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(anchor="w")
        
        # Кнопка Играть
        play_btn = tk.Frame(top_row, bg="#4A90D9", cursor="hand2")
        play_btn.pack(side="right")
        play_btn.bind("<Button-1>", lambda e: self._quick_launch())
        
        play_inner = tk.Frame(play_btn, bg="#4A90D9")
        play_inner.pack(padx=30, pady=10)
        tk.Label(play_inner, text="▶ Играть", font=("Segoe UI", 13, "bold"),
                bg="#4A90D9", fg="#FFFFFF").pack()
        
        # Основной контент - две колонки
        main_content = tk.Frame(self.content_frame, bg="#0D0D0D")
        main_content.pack(fill="both", expand=True)
        
        # Левая колонка
        left_col = tk.Frame(main_content, bg="#0D0D0D")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Карточка "Рекомендованные сервера"
        servers_card = tk.Frame(left_col, bg="#1A1A1A")
        servers_card.pack(fill="x", pady=(0, 10))
        
        servers_inner = tk.Frame(servers_card, bg="#1A1A1A")
        servers_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(servers_inner, text="🌐 Рекомендованные сервера", font=("Segoe UI", 11, "bold"),
                bg="#1A1A1A", fg="#FFFFFF").pack(anchor="w", pady=(0, 8))
        
        for server in self._servers[:2]:
            s_frame = tk.Frame(servers_inner, bg="#1A1A1A")
            s_frame.pack(fill="x", pady=3)
            
            tk.Label(s_frame, text=f"• {server['name']}", font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#AAAAAA").pack(side="left")
            tk.Label(s_frame, text=server['online'], font=("Segoe UI", 9),
                    bg="#1A1A1A", fg="#4A90D9").pack(side="right")
        
        # Карточка "Новости"
        news_card = tk.Frame(left_col, bg="#1A1A1A")
        news_card.pack(fill="both", expand=True)
        
        news_inner = tk.Frame(news_card, bg="#1A1A1A")
        news_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(news_inner, text="📰 Новости", font=("Segoe UI", 11, "bold"),
                bg="#1A1A1A", fg="#FFFFFF").pack(anchor="w", pady=(0, 8))
        
        for title, desc in self._news_items:
            item = tk.Frame(news_inner, bg="#1A1A1A", cursor="hand2")
            item.pack(fill="x", pady=5)
            
            tk.Label(item, text=title, font=("Segoe UI", 10, "bold"),
                    bg="#1A1A1A", fg="#4A90D9").pack(anchor="w")
            tk.Label(item, text=desc, font=("Segoe UI", 9),
                    bg="#1A1A1A", fg="#888888").pack(anchor="w")
            
            item.bind("<Enter>", lambda e, i=item: self._card_hover(i, True))
            item.bind("<Leave>", lambda e, i=item: self._card_hover(i, False))
        
        # Правая колонка
        right_col = tk.Frame(main_content, bg="#0D0D0D", width=280)
        right_col.pack(side="right", fill="y", padx=(10, 0))
        right_col.pack_propagate(False)
        
        # Карточка "ПОДБОРКА ЛУЧШИХ МОДОВ"
        mods_card = tk.Frame(right_col, bg="#1A1A1A")
        mods_card.pack(fill="x", pady=(0, 10))
        
        mods_inner = tk.Frame(mods_card, bg="#1A1A1A")
        mods_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(mods_inner, text="🔥 ПОДБОРКА ЛУЧШИХ МОДОВ", font=("Segoe UI", 10, "bold"),
                bg="#1A1A1A", fg="#FF6B6B").pack(anchor="w", pady=(0, 5))
        tk.Label(mods_inner, text="СООБЩЕСТВО", font=("Segoe UI", 8),
                bg="#1A1A1A", fg="#888888").pack(anchor="w")
        
        # Карточка "НОВЫЙ СНАПШОТ"
        snapshot_card = tk.Frame(right_col, bg="#1A1A1A")
        snapshot_card.pack(fill="x", pady=(0, 10))
        
        snap_inner = tk.Frame(snapshot_card, bg="#1A1A1A")
        snap_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(snap_inner, text="🆕 НОВЫЙ СНАПШОТ", font=("Segoe UI", 10, "bold"),
                bg="#1A1A1A", fg="#4A90D9").pack(anchor="w", pady=(0, 5))
        tk.Label(snap_inner, text="ПОСЛЕДНЯЯ ВЕРСИЯ: 1.20.2", font=("Segoe UI", 9),
                bg="#1A1A1A", fg="#888888").pack(anchor="w")
        
        # Карточка "ОБНОВЛЕНИЕ ЛАУНЧЕРА"
        update_card = tk.Frame(right_col, bg="#1A1A1A")
        update_card.pack(fill="x", pady=(0, 10))
        
        update_inner = tk.Frame(update_card, bg="#1A1A1A")
        update_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(update_inner, text="📱 ОБНОВЛЕНИЕ ЛАУНЧЕРА 1.0.7", font=("Segoe UI", 10, "bold"),
                bg="#1A1A1A", fg="#4A90D9").pack(anchor="w", pady=(0, 5))
        
        play_small = tk.Frame(update_inner, bg="#4A90D9", cursor="hand2")
        play_small.pack(pady=(5, 0))
        play_small.bind("<Button-1>", lambda e: self._quick_launch())
        
        play_small_inner = tk.Frame(play_small, bg="#4A90D9")
        play_small_inner.pack(padx=15, pady=5)
        tk.Label(play_small_inner, text="ИГРАТЬ", font=("Segoe UI", 9, "bold"),
                bg="#4A90D9", fg="#FFFFFF").pack()
        
        # Карточка "Последняя версия"
        version_card = tk.Frame(right_col, bg="#1A1A1A")
        version_card.pack(fill="x")
        
        ver_inner = tk.Frame(version_card, bg="#1A1A1A")
        ver_inner.pack(fill="both", padx=15, pady=12)
        
        tk.Label(ver_inner, text="📌 Последняя версия", font=("Segoe UI", 10, "bold"),
                bg="#1A1A1A", fg="#FFFFFF").pack(anchor="w", pady=(0, 5))
        tk.Label(ver_inner, text="ForgeOptiFine 1.20.2", font=("Segoe UI", 9),
                bg="#1A1A1A", fg="#888888").pack(anchor="w")

    def _show_installations_page(self) -> None:
        self._clear_content()
        
        # Заголовок
        header = tk.Frame(self.content_frame, bg="#0D0D0D")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="Установки", font=("Segoe UI", 20, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(side="left")
        
        # Кнопка "Новая установка"
        new_btn = tk.Frame(header, bg="#4A90D9", cursor="hand2")
        new_btn.pack(side="right")
        new_btn.bind("<Button-1>", lambda e: self._create_installation())
        
        new_inner = tk.Frame(new_btn, bg="#4A90D9")
        new_inner.pack(padx=20, pady=8)
        tk.Label(new_inner, text="+ Новая установка", font=("Segoe UI", 11, "bold"),
                bg="#4A90D9", fg="#FFFFFF").pack()
        
        # Список установок
        list_frame = tk.Frame(self.content_frame, bg="#0D0D0D")
        list_frame.pack(fill="both", expand=True)
        
        # Заголовок списка
        list_header = tk.Frame(list_frame, bg="#1A1A1A", height=35)
        list_header.pack(fill="x", pady=(0, 5))
        list_header.pack_propagate(False)
        
        headers = [("Имя установки", 0.35), ("Версия", 0.2), ("Тип", 0.15), ("Загрузчик", 0.15), ("Время игры", 0.15)]
        for text, weight in headers:
            tk.Label(list_header, text=text, font=("Segoe UI", 10, "bold"),
                    bg="#1A1A1A", fg="#AAAAAA").pack(side="left", fill="x", expand=True)
        
        # Элементы списка
        for inst in self._installations:
            item = tk.Frame(list_frame, bg="#121212", height=45, cursor="hand2")
            item.pack(fill="x", pady=2)
            item.pack_propagate(False)
            
            item_inner = tk.Frame(item, bg="#121212")
            item_inner.pack(fill="both", padx=10, pady=8)
            
            # Имя
            name_frame = tk.Frame(item_inner, bg="#121212")
            name_frame.pack(side="left", fill="x", expand=True)
            tk.Label(name_frame, text=inst["name"], font=("Segoe UI", 11),
                    bg="#121212", fg="#FFFFFF").pack(anchor="w")
            
            # Версия
            ver_frame = tk.Frame(item_inner, bg="#121212")
            ver_frame.pack(side="left", fill="x", expand=True)
            tk.Label(ver_frame, text=inst["version"], font=("Segoe UI", 10),
                    bg="#121212", fg="#AAAAAA").pack(anchor="w")
            
            # Тип
            type_frame = tk.Frame(item_inner, bg="#121212")
            type_frame.pack(side="left", fill="x", expand=True)
            type_color = "#4A90D9" if inst["type"] == "Релиз" else "#FF6B6B" if inst["type"] == "Снапшот" else "#50C878"
            tk.Label(type_frame, text=inst["type"], font=("Segoe UI", 10),
                    bg="#121212", fg=type_color).pack(anchor="w")
            
            # Загрузчик
            loader_frame = tk.Frame(item_inner, bg="#121212")
            loader_frame.pack(side="left", fill="x", expand=True)
            loader_text = inst.get("loader", "—")
            tk.Label(loader_frame, text=loader_text, font=("Segoe UI", 10),
                    bg="#121212", fg="#AAAAAA").pack(anchor="w")
            
            # Время
            time_frame = tk.Frame(item_inner, bg="#121212")
            time_frame.pack(side="left", fill="x", expand=True)
            tk.Label(time_frame, text=inst["time"], font=("Segoe UI", 10),
                    bg="#121212", fg="#888888").pack(anchor="w")
            
            # Кнопка Играть
            play_btn = tk.Label(item_inner, text="▶", font=("Segoe UI", 12),
                               bg="#121212", fg="#4A90D9", cursor="hand2")
            play_btn.pack(side="right", padx=10)
            
            item.bind("<Enter>", lambda e, i=item: i.configure(bg="#1E1E1E"))
            item.bind("<Leave>", lambda e, i=item: i.configure(bg="#121212"))
            play_btn.bind("<Button-1>", lambda e, v=inst["version"]: self._launch_version(v))

    def _show_servers_page(self) -> None:
        self._clear_content()
        
        # Заголовок
        header = tk.Frame(self.content_frame, bg="#0D0D0D")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="СЕРВЕРА", font=("Segoe UI", 20, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(side="left")
        
        # Кнопки справа
        right_header = tk.Frame(header, bg="#0D0D0D")
        right_header.pack(side="right")
        
        for text in ["Добавить свой сервер", "Помощь"]:
            btn = tk.Label(right_header, text=text, font=("Segoe UI", 10),
                          bg="#0D0D0D", fg="#4A90D9", cursor="hand2")
            btn.pack(side="left", padx=10)
        
        # Поле поиска
        search_frame = tk.Frame(self.content_frame, bg="#1A1A1A", height=40)
        search_frame.pack(fill="x", pady=(0, 15))
        search_frame.pack_propagate(False)
        
        search_inner = tk.Frame(search_frame, bg="#1A1A1A")
        search_inner.pack(fill="both", padx=15, pady=8)
        
        tk.Label(search_inner, text="🔍", font=("Segoe UI", 12),
                bg="#1A1A1A", fg="#888888").pack(side="left", padx=(0, 8))
        
        search_entry = tk.Entry(search_inner, bg="#1A1A1A", fg="#FFFFFF", font=("Segoe UI", 11),
                                bd=0, insertbackground="#FFFFFF")
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.insert(0, "Название сервера, категории или игры")
        search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, "end") if search_entry.get() == "Название сервера, категории или игры" else None)
        search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "Название сервера, категории или игры") if not search_entry.get() else None)
        
        # Список серверов
        for server in self._servers:
            card = tk.Frame(self.content_frame, bg="#1A1A1A")
            card.pack(fill="x", pady=5)
            
            inner = tk.Frame(card, bg="#1A1A1A")
            inner.pack(fill="both", padx=20, pady=18)
            
            # Заголовок с названием и онлайном
            top = tk.Frame(inner, bg="#1A1A1A")
            top.pack(fill="x")
            
            tk.Label(top, text=f"🔥 {server['name']}", font=("Segoe UI", 14, "bold"),
                    bg="#1A1A1A", fg="#FFFFFF").pack(side="left")
            
            online_frame = tk.Frame(top, bg="#1A1A1A")
            online_frame.pack(side="right")
            
            tk.Label(online_frame, text="●", font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#50C878").pack(side="left")
            tk.Label(online_frame, text=f" Онлайн {server['online']}", font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#AAAAAA").pack(side="left")
            
            # Описание
            tk.Label(inner, text=server["desc"], font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#888888").pack(anchor="w", pady=(5, 10))
            
            # Нижняя строка с IP и кнопкой
            bottom = tk.Frame(inner, bg="#1A1A1A")
            bottom.pack(fill="x")
            
            ip_frame = tk.Frame(bottom, bg="#1A1A1A")
            ip_frame.pack(side="left")
            
            tk.Label(ip_frame, text="🌐", font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#888888").pack(side="left")
            tk.Label(ip_frame, text=server["ip"], font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#4A90D9").pack(side="left", padx=5)
            tk.Label(ip_frame, text=server["version"], font=("Segoe UI", 9),
                    bg="#1A1A1A", fg="#888888").pack(side="left", padx=10)
            
            # Кнопка Играть
            play_btn = tk.Frame(bottom, bg="#4A90D9", cursor="hand2")
            play_btn.pack(side="right")
            
            play_inner = tk.Frame(play_btn, bg="#4A90D9")
            play_inner.pack(padx=20, pady=6)
            tk.Label(play_inner, text="Играть", font=("Segoe UI", 10, "bold"),
                    bg="#4A90D9", fg="#FFFFFF").pack()

    def _show_modpacks_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0D0D0D")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="Сборки", font=("Segoe UI", 20, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(side="left")
        
        # Сетка сборок
        grid = tk.Frame(self.content_frame, bg="#0D0D0D")
        grid.pack(fill="both", expand=True)
        
        modpacks = [
            ("Better MC", "1.20.1", "Forge", "200+ модов"),
            ("All The Mods 9", "1.20.1", "Forge", "400+ модов"),
            ("Fabulously Optimized", "1.20.4", "Fabric", "Оптимизация"),
            ("RLCraft", "1.12.2", "Forge", "Хардкор"),
        ]
        
        for i, (name, version, loader, desc) in enumerate(modpacks):
            card = tk.Frame(grid, bg="#1A1A1A")
            card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            grid.columnconfigure(i%2, weight=1)
            
            inner = tk.Frame(card, bg="#1A1A1A")
            inner.pack(fill="both", padx=18, pady=18)
            
            tk.Label(inner, text=name, font=("Segoe UI", 13, "bold"),
                    bg="#1A1A1A", fg="#FFFFFF").pack(anchor="w")
            tk.Label(inner, text=f"{version} • {loader}", font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#888888").pack(anchor="w", pady=(2, 5))
            tk.Label(inner, text=desc, font=("Segoe UI", 9),
                    bg="#1A1A1A", fg="#AAAAAA").pack(anchor="w")
            
            install_btn = tk.Frame(inner, bg="#4A90D9", cursor="hand2")
            install_btn.pack(pady=(15, 0))
            
            install_inner = tk.Frame(install_btn, bg="#4A90D9")
            install_inner.pack(padx=15, pady=5)
            tk.Label(install_inner, text="Установить", font=("Segoe UI", 9, "bold"),
                    bg="#4A90D9", fg="#FFFFFF").pack()

    def _show_news_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0D0D0D")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="Новости", font=("Segoe UI", 20, "bold"),
                bg="#0D0D0D", fg="#FFFFFF").pack(side="left")
        
        for title, desc, date in self._news_items:
            card = tk.Frame(self.content_frame, bg="#1A1A1A")
            card.pack(fill="x", pady=5)
            
            inner = tk.Frame(card, bg="#1A1A1A")
            inner.pack(fill="both", padx=20, pady=18)
            
            tk.Label(inner, text=title, font=("Segoe UI", 13, "bold"),
                    bg="#1A1A1A", fg="#4A90D9").pack(anchor="w")
            tk.Label(inner, text=desc, font=("Segoe UI", 10),
                    bg="#1A1A1A", fg="#AAAAAA").pack(anchor="w", pady=(5, 0))
            tk.Label(inner, text=date, font=("Segoe UI", 9),
                    bg="#1A1A1A", fg="#888888").pack(anchor="e")

    def _card_hover(self, card: tk.Frame, hover: bool) -> None:
        card.configure(bg="#252525" if hover else "#1A1A1A")
        for child in card.winfo_children():
            try:
                child.configure(bg="#252525" if hover else "#1A1A1A")
            except:
                pass

    def _load_news(self) -> None:
        self._news_items = [
            ("Обновление 1.21 уже здесь!", "Новые мобы, блоки и биомы", "Вчера"),
            ("XW Launcher v2.0", "Полностью новый интерфейс", "3 дня назад"),
            ("Снапшот 24w14a", "Экспериментальные функции", "Неделя назад"),
        ]

    def _load_versions_async(self) -> None:
        thread = threading.Thread(target=self._load_versions, daemon=True)
        thread.start()

    def _load_versions(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            versions = [v["id"] for v in manifest if v.get("type") == "release"][:30]
            self.root.after(0, lambda: self._versions_loaded(versions))
        except:
            pass

    def _versions_loaded(self, versions: list) -> None:
        self.versions = versions

    def _quick_launch(self) -> None:
        username = self.config.get("last_username", "Player")
        version = self.config.get("last_version", "")
        
        if not version and self.versions:
            version = self.versions[0]
        
        if not version:
            messagebox.showwarning("Внимание", "Версия не выбрана")
            return
        
        self._launch_game(username, version)

    def _launch_version(self, version: str) -> None:
        username = self.config.get("last_username", "Player")
        self._launch_game(username, version)

    def _launch_game(self, username: str, version: str) -> None:
        self._config["last_username"] = username
        self._config["last_version"] = version
        self._save_config()
        
        self._install_in_progress = True
        self._last_progress_change_at = time.time()
        
        thread = threading.Thread(target=self._install_and_launch, args=(username, version), daemon=True)
        thread.start()

    def _install_and_launch(self, username: str, version: str) -> None:
        try:
            minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
            
            options = {"username": username}
            command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
            subprocess.Popen(command, cwd=self.minecraft_dir)
            
            self.root.after(0, lambda: self._launch_success())
        except Exception as e:
            self.root.after(0, lambda: self._launch_error(e))

    def _launch_success(self) -> None:
        self._install_in_progress = False

    def _launch_error(self, error: Exception) -> None:
        self._install_in_progress = False
        messagebox.showerror("Ошибка", f"Не удалось запустить игру:\n{error}")

    def _create_installation(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая установка")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#1A1A1A")
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 350) // 2
        dialog.geometry(f"+{x}+{y}")
        
        inner = tk.Frame(dialog, bg="#1A1A1A")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Новая установка", font=("Segoe UI", 16, "bold"),
                bg="#1A1A1A", fg="#FFFFFF").pack(anchor="w", pady=(0, 20))
        
        # Имя
        tk.Label(inner, text="Имя установки", font=("Segoe UI", 10),
                bg="#1A1A1A", fg="#AAAAAA").pack(anchor="w")
        name_entry = tk.Entry(inner, bg="#0D0D0D", fg="#FFFFFF", font=("Segoe UI", 11), bd=0)
        name_entry.pack(fill="x", ipady=8, pady=(5, 15))
        
        # Версия
        tk.Label(inner, text="Версия", font=("Segoe UI", 10),
                bg="#1A1A1A", fg="#AAAAAA").pack(anchor="w")
        version_combo = ttk.Combobox(inner, values=self.versions, state="readonly", font=("Segoe UI", 11))
        version_combo.pack(fill="x", pady=(5, 15))
        if self.versions:
            version_combo.current(0)
        
        # Кнопки
        buttons = tk.Frame(inner, bg="#1A1A1A")
        buttons.pack(fill="x", pady=(10, 0))
        
        tk.Label(buttons, text="Отмена", font=("Segoe UI", 10),
                bg="#1A1A1A", fg="#888888", cursor="hand2").pack(side="right", padx=(10, 0))
        
        create_btn = tk.Frame(buttons, bg="#4A90D9", cursor="hand2")
        create_btn.pack(side="right")
        
        create_inner = tk.Frame(create_btn, bg="#4A90D9")
        create_inner.pack(padx=20, pady=8)
        tk.Label(create_inner, text="Создать", font=("Segoe UI", 10, "bold"),
                bg="#4A90D9", fg="#FFFFFF").pack()
        
        create_btn.bind("<Button-1>", lambda e: dialog.destroy())
        buttons.winfo_children()[0].bind("<Button-1>", lambda e: dialog.destroy())

    def _animate_progress(self) -> None:
        self.root.after(33, self._animate_progress)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F5>", lambda e: self._load_versions_async())


def main():
    root = tk.Tk()
    app = JustLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()