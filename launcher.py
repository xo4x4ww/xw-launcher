import json
import os
import subprocess
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import messagebox, ttk

import minecraft_launcher_lib


class JustLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("950x600")
        self.root.minsize(850, 500)
        self.root.configure(bg="#0a0a0a")
        
        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._install_in_progress = False
        self._current_page = "home"
        self._news_items = []
        self._servers = [
            {"name": "SURVIVAL", "desc": "Ванильное выживание. Ноль модов, ноль плагинов.", 
             "online": "21 / 100", "ip": "PLAY.SURVIVAL.NET", "version": "1.20.1"},
            {"name": "ANARCHY", "desc": "У нас разрешено всё, присоединяйся!", 
             "online": "84 / 200", "ip": "PLAY.ANARCHY.NET", "version": "1.8 - 1.20.1"},
        ]
        self._installations = [
            {"name": "Последняя версия", "version": "1.20.1", "type": "Релиз", "time": "10ч"},
            {"name": "Test", "version": "1.20-pre1", "type": "Снапшот", "time": "2ч"},
            {"name": "Create", "version": "1.19.2", "type": "Сборка", "loader": "Fabric", "time": "20ч"},
            {"name": "Старая версия", "version": "1.19", "type": "Релиз", "time": "20ч"},
        ]

        self._build_ui()
        self._load_versions_async()
        self._load_news()

    def _load_config(self) -> dict:
        default = {"last_username": "Player", "last_version": "", "username_history": ["Player"]}
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

    def _build_ui(self) -> None:
        # Главный контейнер с отступами как на скриншоте
        self.main_container = tk.Frame(self.root, bg="#0a0a0a")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Верхняя строка: XW Launcher | Player ▼
        self._build_header()
        
        # Основной контент
        content = tk.Frame(self.main_container, bg="#0a0a0a")
        content.pack(fill="both", expand=True, pady=(15, 10))
        
        # Левая панель навигации
        self._build_sidebar(content)
        
        # Правая область контента
        self.content_frame = tk.Frame(content, bg="#0a0a0a")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        # Нижняя панель
        self._build_footer()
        
        self._show_home_page()

    def _build_header(self) -> None:
        header = tk.Frame(self.main_container, bg="#0a0a0a", height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Левая часть - название лаунчера
        tk.Label(header, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        # Правая часть - Player и иконка
        right = tk.Frame(header, bg="#0a0a0a")
        right.pack(side="right")
        
        username = self.config.get("last_username", "Player")
        tk.Label(right, text=username, font=("Segoe UI", 11),
                bg="#0a0a0a", fg="#cccccc").pack(side="left")
        tk.Label(right, text=" ▼", font=("Segoe UI", 9),
                bg="#0a0a0a", fg="#777777").pack(side="left", padx=(2, 0))

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg="#0a0a0a", width=160)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Навигационные кнопки - просто текст без иконок
        nav_items = [
            ("Играть", "home"),
            ("Установки", "installations"),
            ("Сервера", "servers"),
            ("Сборки", "modpacks"),
            ("Новости", "news"),
        ]
        
        self.nav_buttons = {}
        for label, key in nav_items:
            btn = tk.Label(sidebar, text=label, font=("Segoe UI", 11),
                          bg="#0a0a0a", fg="#888888", anchor="w", cursor="hand2")
            btn.pack(fill="x", pady=3)
            
            if self._current_page == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 11, "bold"))
            
            btn.bind("<Enter>", lambda e, b=btn, k=key: self._nav_hover(b, k, True))
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._nav_hover(b, k, False))
            btn.bind("<Button-1>", lambda e, k=key: self._nav_click(k))
            
            self.nav_buttons[key] = btn

    def _build_footer(self) -> None:
        footer = tk.Frame(self.main_container, bg="#0a0a0a", height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        items = ["Аккаунты", "Настройки", "Папка игры"]
        for item in items:
            lbl = tk.Label(footer, text=item, font=("Segoe UI", 9),
                          bg="#0a0a0a", fg="#666666", cursor="hand2")
            lbl.pack(side="left", padx=(0, 25))
            
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg="#999999"))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg="#666666"))
            
            if item == "Папка игры":
                lbl.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))

    def _nav_hover(self, btn: tk.Label, key: str, hover: bool) -> None:
        if self._current_page == key:
            return
        btn.config(fg="#cccccc" if hover else "#888888")

    def _nav_click(self, key: str) -> None:
        self._current_page = key
        
        # Обновляем стили кнопок
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 11, "bold"))
            else:
                btn.config(fg="#888888", font=("Segoe UI", 11))
        
        # Показываем страницу
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
        
        # Приветствие
        username = self.config.get("last_username", "Player")
        tk.Label(self.content_frame, text=f"С возвращением, {username}!",
                font=("Segoe UI", 18, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        
        # Кнопка Играть
        play_btn = tk.Frame(self.content_frame, bg="#2a2a2a", cursor="hand2")
        play_btn.pack(anchor="w", pady=(0, 25))
        play_btn.bind("<Button-1>", lambda e: self._quick_launch())
        
        play_inner = tk.Frame(play_btn, bg="#2a2a2a")
        play_inner.pack(padx=40, pady=10)
        tk.Label(play_inner, text="Играть", font=("Segoe UI", 12, "bold"),
                bg="#2a2a2a", fg="#ffffff").pack()
        
        # Рекомендованные сервера (заголовок)
        tk.Label(self.content_frame, text="Рекомендованные сервера",
                font=("Segoe UI", 13, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 10))
        
        # Список серверов
        for server in self._servers[:2]:
            s_frame = tk.Frame(self.content_frame, bg="#0a0a0a")
            s_frame.pack(fill="x", pady=3)
            
            tk.Label(s_frame, text=f"• {server['name']}", font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#aaaaaa").pack(side="left")
            tk.Label(s_frame, text=server['online'], font=("Segoe UI", 9),
                    bg="#0a0a0a", fg="#4a9eff").pack(side="right")
        
        # Разделитель
        tk.Frame(self.content_frame, bg="#222222", height=1).pack(fill="x", pady=20)
        
        # Новости (заголовок)
        tk.Label(self.content_frame, text="Новости",
                font=("Segoe UI", 13, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 10))
        
        # Список новостей
        for title, desc in self._news_items[:3]:
            news_frame = tk.Frame(self.content_frame, bg="#0a0a0a")
            news_frame.pack(fill="x", pady=5)
            
            tk.Label(news_frame, text=title, font=("Segoe UI", 10, "bold"),
                    bg="#0a0a0a", fg="#4a9eff").pack(anchor="w")
            tk.Label(news_frame, text=desc, font=("Segoe UI", 9),
                    bg="#0a0a0a", fg="#777777").pack(anchor="w")

    def _show_installations_page(self) -> None:
        self._clear_content()
        
        # Заголовок и кнопка
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="Установки", font=("Segoe UI", 18, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        new_btn = tk.Label(header, text="+ Новая установка", font=("Segoe UI", 10),
                          bg="#0a0a0a", fg="#4a9eff", cursor="hand2")
        new_btn.pack(side="right")
        new_btn.bind("<Button-1>", lambda e: self._create_installation())
        
        # Заголовки столбцов
        cols = tk.Frame(self.content_frame, bg="#0a0a0a")
        cols.pack(fill="x", pady=(0, 5))
        
        tk.Label(cols, text="Имя установки", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=25, anchor="w").pack(side="left")
        tk.Label(cols, text="Версия", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=15, anchor="w").pack(side="left")
        tk.Label(cols, text="Тип", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=12, anchor="w").pack(side="left")
        tk.Label(cols, text="Время игры", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=10, anchor="w").pack(side="left")
        
        tk.Frame(self.content_frame, bg="#333333", height=1).pack(fill="x", pady=5)
        
        # Список установок
        for inst in self._installations:
            row = tk.Frame(self.content_frame, bg="#0a0a0a", cursor="hand2")
            row.pack(fill="x", pady=3)
            
            tk.Label(row, text=inst["name"], font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#ffffff", width=25, anchor="w").pack(side="left")
            tk.Label(row, text=inst["version"], font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#aaaaaa", width=15, anchor="w").pack(side="left")
            
            type_color = "#4a9eff" if inst["type"] == "Релиз" else "#ff6b6b" if inst["type"] == "Снапшот" else "#50c878"
            tk.Label(row, text=inst["type"], font=("Segoe UI", 10),
                    bg="#0a0a0a", fg=type_color, width=12, anchor="w").pack(side="left")
            
            tk.Label(row, text=inst["time"], font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#777777", width=10, anchor="w").pack(side="left")
            
            # Кнопка играть при наведении
            play_lbl = tk.Label(row, text="▶", font=("Segoe UI", 10),
                               bg="#0a0a0a", fg="#4a9eff")
            play_lbl.pack(side="right", padx=(0, 10))
            play_lbl.bind("<Button-1>", lambda e, v=inst["version"]: self._launch_version(v))
            
            row.bind("<Enter>", lambda e, r=row, p=play_lbl: self._row_hover(r, p, True))
            row.bind("<Leave>", lambda e, r=row, p=play_lbl: self._row_hover(r, p, False))

    def _show_servers_page(self) -> None:
        self._clear_content()
        
        # Заголовок
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="СЕРВЕРА", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        # Ссылки справа
        links = tk.Frame(header, bg="#0a0a0a")
        links.pack(side="right")
        
        for text in ["Добавить свой сервер", "Помощь"]:
            lbl = tk.Label(links, text=text, font=("Segoe UI", 9),
                          bg="#0a0a0a", fg="#4a9eff", cursor="hand2")
            lbl.pack(side="left", padx=(15, 0))
        
        # Поле поиска
        search = tk.Frame(self.content_frame, bg="#151515", height=35)
        search.pack(fill="x", pady=(0, 20))
        search.pack_propagate(False)
        
        search_inner = tk.Frame(search, bg="#151515")
        search_inner.pack(fill="both", padx=12, pady=7)
        
        tk.Label(search_inner, text="🔍", font=("Segoe UI", 11),
                bg="#151515", fg="#666666").pack(side="left", padx=(0, 8))
        
        entry = tk.Entry(search_inner, bg="#151515", fg="#ffffff", font=("Segoe UI", 10),
                        bd=0, insertbackground="#ffffff")
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, "Название сервера, категории или игры")
        entry.bind("<FocusIn>", lambda e: entry.delete(0, "end") if entry.get() == "Название сервера, категории или игры" else None)
        entry.bind("<FocusOut>", lambda e: entry.insert(0, "Название сервера, категории или игры") if not entry.get() else None)
        
        # Список серверов
        for server in self._servers:
            card = tk.Frame(self.content_frame, bg="#151515")
            card.pack(fill="x", pady=8)
            
            inner = tk.Frame(card, bg="#151515")
            inner.pack(fill="both", padx=20, pady=18)
            
            # Заголовок
            top = tk.Frame(inner, bg="#151515")
            top.pack(fill="x")
            
            tk.Label(top, text=server["name"], font=("Segoe UI", 13, "bold"),
                    bg="#151515", fg="#ffffff").pack(side="left")
            
            online_frame = tk.Frame(top, bg="#151515")
            online_frame.pack(side="right")
            
            tk.Label(online_frame, text="●", font=("Segoe UI", 9),
                    bg="#151515", fg="#50c878").pack(side="left")
            tk.Label(online_frame, text=f" Онлайн {server['online']}", font=("Segoe UI", 9),
                    bg="#151515", fg="#aaaaaa").pack(side="left")
            
            # Описание
            tk.Label(inner, text=server["desc"], font=("Segoe UI", 9),
                    bg="#151515", fg="#888888").pack(anchor="w", pady=(5, 12))
            
            # Нижняя строка
            bottom = tk.Frame(inner, bg="#151515")
            bottom.pack(fill="x")
            
            ip_frame = tk.Frame(bottom, bg="#151515")
            ip_frame.pack(side="left")
            
            tk.Label(ip_frame, text=server["ip"], font=("Segoe UI", 9),
                    bg="#151515", fg="#4a9eff").pack(side="left")
            tk.Label(ip_frame, text=server["version"], font=("Segoe UI", 8),
                    bg="#151515", fg="#666666").pack(side="left", padx=(10, 0))
            
            # Кнопка Играть
            play_btn = tk.Frame(bottom, bg="#2a2a2a", cursor="hand2")
            play_btn.pack(side="right")
            
            play_inner = tk.Frame(play_btn, bg="#2a2a2a")
            play_inner.pack(padx=20, pady=5)
            tk.Label(play_inner, text="Играть", font=("Segoe UI", 9, "bold"),
                    bg="#2a2a2a", fg="#ffffff").pack()

    def _show_modpacks_page(self) -> None:
        self._clear_content()
        
        tk.Label(self.content_frame, text="Сборки", font=("Segoe UI", 18, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        # ПОДБОРКА ЛУЧШИХ МОДОВ
        featured = tk.Frame(self.content_frame, bg="#151515")
        featured.pack(fill="x", pady=(0, 20))
        
        featured_inner = tk.Frame(featured, bg="#151515")
        featured_inner.pack(fill="both", padx=20, pady=18)
        
        tk.Label(featured_inner, text="ПОДБОРКА ЛУЧШИХ МОДОВ", font=("Segoe UI", 11, "bold"),
                bg="#151515", fg="#ff6b6b").pack(anchor="w")
        tk.Label(featured_inner, text="СООБЩЕСТВО", font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 0))
        
        # Сетка сборок
        modpacks = [
            ("Better MC", "1.20.1", "Forge"),
            ("All The Mods 9", "1.20.1", "Forge"),
            ("Fabulously Optimized", "1.20.4", "Fabric"),
            ("RLCraft", "1.12.2", "Forge"),
        ]
        
        grid = tk.Frame(self.content_frame, bg="#0a0a0a")
        grid.pack(fill="both", expand=True)
        
        for i, (name, version, loader) in enumerate(modpacks):
            card = tk.Frame(grid, bg="#151515")
            card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            grid.columnconfigure(i%2, weight=1)
            
            inner = tk.Frame(card, bg="#151515")
            inner.pack(fill="both", padx=18, pady=18)
            
            tk.Label(inner, text=name, font=("Segoe UI", 12, "bold"),
                    bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=f"{version} • {loader}", font=("Segoe UI", 9),
                    bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 12))
            
            install = tk.Frame(inner, bg="#2a2a2a", cursor="hand2")
            install.pack()
            
            install_inner = tk.Frame(install, bg="#2a2a2a")
            install_inner.pack(padx=15, pady=5)
            tk.Label(install_inner, text="Установить", font=("Segoe UI", 9),
                    bg="#2a2a2a", fg="#ffffff").pack()

    def _show_news_page(self) -> None:
        self._clear_content()
        
        tk.Label(self.content_frame, text="Новости", font=("Segoe UI", 18, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        for title, desc, date in self._news_items:
            card = tk.Frame(self.content_frame, bg="#151515")
            card.pack(fill="x", pady=5)
            
            inner = tk.Frame(card, bg="#151515")
            inner.pack(fill="both", padx=20, pady=18)
            
            tk.Label(inner, text=title, font=("Segoe UI", 12, "bold"),
                    bg="#151515", fg="#4a9eff").pack(anchor="w")
            tk.Label(inner, text=desc, font=("Segoe UI", 9),
                    bg="#151515", fg="#aaaaaa").pack(anchor="w", pady=(5, 0))
            tk.Label(inner, text=date, font=("Segoe UI", 8),
                    bg="#151515", fg="#666666").pack(anchor="e")

    def _row_hover(self, row: tk.Frame, play_btn: tk.Label, hover: bool) -> None:
        row.config(bg="#151515" if hover else "#0a0a0a")
        for child in row.winfo_children():
            if child != play_btn:
                child.config(bg="#151515" if hover else "#0a0a0a")
        play_btn.config(bg="#151515" if hover else "#0a0a0a")

    def _load_news(self) -> None:
        self._news_items = [
            ("Обновление 1.21 уже здесь!", "Новые мобы, блоки и биомы", "Вчера"),
            ("XW Launcher v2.0", "Полностью новый интерфейс", "3 дня назад"),
            ("Снапшот 24w14a", "Экспериментальные функции", "Неделя назад"),
            ("Совет дня", "Используйте установки для разных версий", "Сегодня"),
        ]

    def _load_versions_async(self) -> None:
        thread = threading.Thread(target=self._load_versions, daemon=True)
        thread.start()

    def _load_versions(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            self.versions = [v["id"] for v in manifest if v.get("type") == "release"][:30]
        except:
            pass

    def _quick_launch(self) -> None:
        username = self.config.get("last_username", "Player")
        version = self.config.get("last_version", "")
        
        if not version and self.versions:
            version = self.versions[0]
        
        if version:
            self._launch_game(username, version)

    def _launch_version(self, version: str) -> None:
        self._launch_game(self.config.get("last_username", "Player"), version)

    def _launch_game(self, username: str, version: str) -> None:
        self.config["last_username"] = username
        self.config["last_version"] = version
        self._save_config()
        
        self._install_in_progress = True
        
        def install_and_launch():
            try:
                minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                options = {"username": username}
                command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
                subprocess.Popen(command, cwd=self.minecraft_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self._install_in_progress = False
        
        threading.Thread(target=install_and_launch, daemon=True).start()

    def _create_installation(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая установка")
        dialog.geometry("400x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Новая установка", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        
        tk.Label(inner, text="Имя установки", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w")
        name_entry = tk.Entry(inner, bg="#0a0a0a", fg="#ffffff", font=("Segoe UI", 10), bd=0)
        name_entry.pack(fill="x", ipady=8, pady=(5, 15))
        name_entry.insert(0, "Новая установка")
        
        tk.Label(inner, text="Версия", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w")
        version_combo = ttk.Combobox(inner, values=self.versions, state="readonly", font=("Segoe UI", 10))
        version_combo.pack(fill="x", pady=(5, 15))
        if self.versions:
            version_combo.current(0)
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x", pady=(10, 0))
        
        tk.Label(buttons, text="Отмена", font=("Segoe UI", 9),
                bg="#151515", fg="#888888", cursor="hand2").pack(side="right", padx=(10, 0))
        buttons.winfo_children()[0].bind("<Button-1>", lambda e: dialog.destroy())
        
        create_btn = tk.Frame(buttons, bg="#2a2a2a", cursor="hand2")
        create_btn.pack(side="right")
        
        create_inner = tk.Frame(create_btn, bg="#2a2a2a")
        create_inner.pack(padx=20, pady=8)
        tk.Label(create_inner, text="Создать", font=("Segoe UI", 9, "bold"),
                bg="#2a2a2a", fg="#ffffff").pack()
        create_btn.bind("<Button-1>", lambda e: dialog.destroy())


def main():
    root = tk.Tk()
    app = JustLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()