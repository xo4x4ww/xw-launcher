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
        self.root.geometry("900x550")
        self.root.minsize(800, 480)
        self.root.configure(bg="#0a0a0a")
        
        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._install_in_progress = False
        self._current_page = "home"
        self._servers = [
            {"name": "SURVIVAL", "desc": "Ванильное выживание. Ноль модов, ноль плагинов.", 
             "online": "21 / 100", "ip": "PLAY.SURVIVAL.NET", "version": "1.20.1"},
            {"name": "ANARCHY", "desc": "У нас разрешено всё, присоединяйся!", 
             "online": "84 / 200", "ip": "PLAY.ANARCHY.NET", "version": "1.8 - 1.20.1"},
            {"name": "CREATIVE", "desc": "Сервер для творчества и строительства.", 
             "online": "45 / 80", "ip": "PLAY.CREATIVE.NET", "version": "1.20.1"},
        ]

        self._build_ui()
        self._load_versions_async()

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
        for w in self.root.winfo_children():
            w.destroy()
            
        self.main_container = tk.Frame(self.root, bg="#0a0a0a")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)
        
        self._build_header()
        
        content = tk.Frame(self.main_container, bg="#0a0a0a")
        content.pack(fill="both", expand=True, pady=(15, 10))
        
        self._build_sidebar(content)
        
        self.content_frame = tk.Frame(content, bg="#0a0a0a")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        self._build_footer()
        
        self._show_home_page()

    def _build_header(self) -> None:
        header = tk.Frame(self.main_container, bg="#0a0a0a", height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        right = tk.Frame(header, bg="#0a0a0a")
        right.pack(side="right")
        
        username = self.config.get("last_username", "Player")
        
        # Выпадающее меню для ника
        self.profile_btn = tk.Menubutton(right, text=f"{username} ▼", font=("Segoe UI", 11),
                                         bg="#0a0a0a", fg="#cccccc", bd=0, cursor="hand2",
                                         activebackground="#0a0a0a", activeforeground="#ffffff")
        self.profile_btn.pack(side="left")
        
        profile_menu = tk.Menu(self.profile_btn, tearoff=0, bg="#151515", fg="#ffffff",
                               activebackground="#2a2a2a", activeforeground="#ffffff")
        profile_menu.add_command(label="Сменить ник", command=self._change_nickname)
        profile_menu.add_separator()
        profile_menu.add_command(label="Выход", command=self.root.quit)
        self.profile_btn.config(menu=profile_menu)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg="#0a0a0a", width=140)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        nav_items = [
            ("Играть", "home"),
            ("Сервера", "servers"),
            ("Сборки", "modpacks"),
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
        
        items = [
            ("Аккаунты", self._change_nickname),
            ("Настройки", self._show_settings),
            ("Папка игры", lambda: os.startfile(self.minecraft_dir)),
        ]
        
        for text, cmd in items:
            lbl = tk.Label(footer, text=text, font=("Segoe UI", 9),
                          bg="#0a0a0a", fg="#666666", cursor="hand2")
            lbl.pack(side="left", padx=(0, 25))
            
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg="#999999"))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg="#666666"))
            lbl.bind("<Button-1>", lambda e, c=cmd: c())

    def _nav_hover(self, btn: tk.Label, key: str, hover: bool) -> None:
        if self._current_page == key:
            return
        btn.config(fg="#cccccc" if hover else "#888888")

    def _nav_click(self, key: str) -> None:
        self._current_page = key
        
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 11, "bold"))
            else:
                btn.config(fg="#888888", font=("Segoe UI", 11))
        
        pages = {
            "home": self._show_home_page,
            "servers": self._show_servers_page,
            "modpacks": self._show_modpacks_page,
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
                font=("Segoe UI", 18, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 10))
        
        # Выбор версии
        version_frame = tk.Frame(self.content_frame, bg="#0a0a0a")
        version_frame.pack(fill="x", pady=(10, 15))
        
        tk.Label(version_frame, text="Версия:", font=("Segoe UI", 10),
                bg="#0a0a0a", fg="#aaaaaa").pack(side="left", padx=(0, 10))
        
        self.version_combo = ttk.Combobox(version_frame, values=self.versions, state="readonly",
                                           font=("Segoe UI", 10), width=20)
        self.version_combo.pack(side="left")
        if self.versions:
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            else:
                self.version_combo.current(0)
        else:
            self.version_combo.set("Загрузка...")
        
        # Кнопка Играть
        play_btn = tk.Frame(self.content_frame, bg="#2a2a2a", cursor="hand2")
        play_btn.pack(anchor="w", pady=(0, 25))
        play_btn.bind("<Button-1>", lambda e: self._launch_selected())
        play_btn.bind("<Enter>", lambda e: play_btn.config(bg="#3a3a3a"))
        play_btn.bind("<Leave>", lambda e: play_btn.config(bg="#2a2a2a"))
        
        play_inner = tk.Frame(play_btn, bg="#2a2a2a")
        play_inner.pack(padx=40, pady=10)
        tk.Label(play_inner, text="Играть", font=("Segoe UI", 12, "bold"),
                bg="#2a2a2a", fg="#ffffff").pack()
        play_btn.bind("<Enter>", lambda e: play_inner.config(bg="#3a3a3a") or play_btn.config(bg="#3a3a3a"))
        play_btn.bind("<Leave>", lambda e: play_inner.config(bg="#2a2a2a") or play_btn.config(bg="#2a2a2a"))
        
        # Рекомендованные сервера
        tk.Label(self.content_frame, text="Рекомендованные сервера",
                font=("Segoe UI", 13, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 10))
        
        for server in self._servers[:2]:
            s_frame = tk.Frame(self.content_frame, bg="#0a0a0a")
            s_frame.pack(fill="x", pady=3)
            
            tk.Label(s_frame, text=f"• {server['name']}", font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#aaaaaa").pack(side="left")
            tk.Label(s_frame, text=server['online'], font=("Segoe UI", 9),
                    bg="#0a0a0a", fg="#4a9eff").pack(side="right")
        
        # Разделитель
        tk.Frame(self.content_frame, bg="#222222", height=1).pack(fill="x", pady=20)
        
        # Информация о последней версии
        info_frame = tk.Frame(self.content_frame, bg="#151515")
        info_frame.pack(fill="x")
        
        info_inner = tk.Frame(info_frame, bg="#151515")
        info_inner.pack(fill="both", padx=20, pady=18)
        
        tk.Label(info_inner, text="НОВЫЙ СНАПШОТ", font=("Segoe UI", 10, "bold"),
                bg="#151515", fg="#4a9eff").pack(anchor="w")
        tk.Label(info_inner, text="ПОСЛЕДНЯЯ ВЕРСИЯ: 1.20.2", font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(5, 0))

    def _show_servers_page(self) -> None:
        self._clear_content()
        
        # Заголовок
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 15))
        
        tk.Label(header, text="СЕРВЕРА", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        links = tk.Frame(header, bg="#0a0a0a")
        links.pack(side="right")
        
        add_btn = tk.Label(links, text="Добавить свой сервер", font=("Segoe UI", 9),
                          bg="#0a0a0a", fg="#4a9eff", cursor="hand2")
        add_btn.pack(side="left", padx=(15, 0))
        add_btn.bind("<Button-1>", lambda e: self._add_server())
        
        # Поле поиска
        search = tk.Frame(self.content_frame, bg="#151515", height=35)
        search.pack(fill="x", pady=(0, 20))
        search.pack_propagate(False)
        
        search_inner = tk.Frame(search, bg="#151515")
        search_inner.pack(fill="both", padx=12, pady=7)
        
        tk.Label(search_inner, text="🔍", font=("Segoe UI", 11),
                bg="#151515", fg="#666666").pack(side="left", padx=(0, 8))
        
        self.search_entry = tk.Entry(search_inner, bg="#151515", fg="#ffffff", font=("Segoe UI", 10),
                                      bd=0, insertbackground="#ffffff")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.insert(0, "Название сервера, категории или игры")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        
        # Список серверов
        for server in self._servers:
            self._create_server_card(server)

    def _create_server_card(self, server: dict) -> None:
        card = tk.Frame(self.content_frame, bg="#151515")
        card.pack(fill="x", pady=8)
        
        inner = tk.Frame(card, bg="#151515")
        inner.pack(fill="both", padx=20, pady=18)
        
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
        
        tk.Label(inner, text=server["desc"], font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(5, 12))
        
        bottom = tk.Frame(inner, bg="#151515")
        bottom.pack(fill="x")
        
        ip_frame = tk.Frame(bottom, bg="#151515")
        ip_frame.pack(side="left")
        
        tk.Label(ip_frame, text=server["ip"], font=("Segoe UI", 9),
                bg="#151515", fg="#4a9eff").pack(side="left")
        tk.Label(ip_frame, text=server["version"], font=("Segoe UI", 8),
                bg="#151515", fg="#666666").pack(side="left", padx=(10, 0))
        
        play_btn = tk.Frame(bottom, bg="#2a2a2a", cursor="hand2")
        play_btn.pack(side="right")
        play_btn.bind("<Enter>", lambda e: play_btn.config(bg="#3a3a3a"))
        play_btn.bind("<Leave>", lambda e: play_btn.config(bg="#2a2a2a"))
        play_btn.bind("<Button-1>", lambda e, s=server: self._connect_server(s))
        
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
        
        modpacks = [
            ("Better MC", "1.20.1", "Forge", "Улучшенный ванильный опыт"),
            ("All The Mods 9", "1.20.1", "Forge", "400+ модов"),
            ("Fabulously Optimized", "1.20.4", "Fabric", "Оптимизация и шейдеры"),
            ("RLCraft", "1.12.2", "Forge", "Хардкорное выживание"),
        ]
        
        grid = tk.Frame(self.content_frame, bg="#0a0a0a")
        grid.pack(fill="both", expand=True)
        
        for i, (name, version, loader, desc) in enumerate(modpacks):
            card = tk.Frame(grid, bg="#151515", cursor="hand2")
            card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            grid.columnconfigure(i%2, weight=1)
            
            inner = tk.Frame(card, bg="#151515")
            inner.pack(fill="both", padx=18, pady=18)
            
            tk.Label(inner, text=name, font=("Segoe UI", 12, "bold"),
                    bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=f"{version} • {loader}", font=("Segoe UI", 9),
                    bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 5))
            tk.Label(inner, text=desc, font=("Segoe UI", 8),
                    bg="#151515", fg="#666666").pack(anchor="w")
            
            install = tk.Frame(inner, bg="#2a2a2a", cursor="hand2")
            install.pack(pady=(12, 0))
            install.bind("<Button-1>", lambda e, n=name: self._install_modpack(n))
            install.bind("<Enter>", lambda e, f=install: f.config(bg="#3a3a3a"))
            install.bind("<Leave>", lambda e, f=install: f.config(bg="#2a2a2a"))
            
            install_inner = tk.Frame(install, bg="#2a2a2a")
            install_inner.pack(padx=15, pady=5)
            tk.Label(install_inner, text="Установить", font=("Segoe UI", 9),
                    bg="#2a2a2a", fg="#ffffff").pack()

    def _on_search_focus_in(self, event) -> None:
        if self.search_entry.get() == "Название сервера, категории или игры":
            self.search_entry.delete(0, "end")

    def _on_search_focus_out(self, event) -> None:
        if not self.search_entry.get():
            self.search_entry.insert(0, "Название сервера, категории или игры")

    def _change_nickname(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Сменить ник")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 180) // 2
        dialog.geometry(f"+{x}+{y}")
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Сменить никнейм", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        tk.Label(inner, text="Новый никнейм", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w")
        
        entry = tk.Entry(inner, bg="#0a0a0a", fg="#ffffff", font=("Segoe UI", 11), bd=0)
        entry.pack(fill="x", ipady=8, pady=(5, 20))
        entry.insert(0, self.config.get("last_username", "Player"))
        entry.focus()
        entry.select_range(0, "end")
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x")
        
        tk.Label(buttons, text="Отмена", font=("Segoe UI", 9),
                bg="#151515", fg="#888888", cursor="hand2").pack(side="right", padx=(10, 0))
        buttons.winfo_children()[0].bind("<Button-1>", lambda e: dialog.destroy())
        
        def save_nick():
            new_nick = entry.get().strip()
            if new_nick:
                self.config["last_username"] = new_nick
                history = self.config.get("username_history", [])
                if new_nick in history:
                    history.remove(new_nick)
                history.insert(0, new_nick)
                self.config["username_history"] = history[:8]
                self._save_config()
                self.profile_btn.config(text=f"{new_nick} ▼")
                dialog.destroy()
        
        save_btn = tk.Frame(buttons, bg="#2a2a2a", cursor="hand2")
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: save_nick())
        
        save_inner = tk.Frame(save_btn, bg="#2a2a2a")
        save_inner.pack(padx=20, pady=8)
        tk.Label(save_inner, text="Сохранить", font=("Segoe UI", 9, "bold"),
                bg="#2a2a2a", fg="#ffffff").pack()
        
        entry.bind("<Return>", lambda e: save_nick())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _show_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Настройки", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        tk.Label(inner, text=f"Папка игры: {self.minecraft_dir}", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w", pady=5)
        
        open_btn = tk.Label(inner, text="Открыть папку игры", font=("Segoe UI", 9),
                           bg="#151515", fg="#4a9eff", cursor="hand2")
        open_btn.pack(anchor="w", pady=5)
        open_btn.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))
        
        tk.Label(inner, text="Память (MB):", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w", pady=(15, 5))
        
        ram_var = tk.IntVar(value=self.config.get("ram_allocation", 2048))
        ram_spin = tk.Spinbox(inner, from_=512, to=8192, increment=256, textvariable=ram_var,
                              bg="#0a0a0a", fg="#ffffff", bd=0, width=10)
        ram_spin.pack(anchor="w")
        
        def save_settings():
            self.config["ram_allocation"] = ram_var.get()
            self._save_config()
            dialog.destroy()
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x", pady=(20, 0))
        
        tk.Label(buttons, text="Отмена", font=("Segoe UI", 9),
                bg="#151515", fg="#888888", cursor="hand2").pack(side="right", padx=(10, 0))
        buttons.winfo_children()[0].bind("<Button-1>", lambda e: dialog.destroy())
        
        save_btn = tk.Frame(buttons, bg="#2a2a2a", cursor="hand2")
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: save_settings())
        
        save_inner = tk.Frame(save_btn, bg="#2a2a2a")
        save_inner.pack(padx=20, pady=8)
        tk.Label(save_inner, text="Сохранить", font=("Segoe UI", 9, "bold"),
                bg="#2a2a2a", fg="#ffffff").pack()

    def _add_server(self) -> None:
        messagebox.showinfo("Добавить сервер", "Функция добавления сервера в разработке")

    def _connect_server(self, server: dict) -> None:
        self._launch_game(self.config.get("last_username", "Player"), 
                         server["version"].split(" - ")[0].strip())

    def _install_modpack(self, name: str) -> None:
        messagebox.showinfo("Установка", f"Установка сборки {name}")

    def _load_versions_async(self) -> None:
        thread = threading.Thread(target=self._load_versions, daemon=True)
        thread.start()

    def _load_versions(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            versions = [v["id"] for v in manifest if v.get("type") == "release"][:30]
            self.versions = versions
            self.root.after(0, self._update_version_combo)
        except:
            self.versions = ["1.20.1", "1.20", "1.19.4", "1.19.2"]
            self.root.after(0, self._update_version_combo)

    def _update_version_combo(self) -> None:
        if hasattr(self, 'version_combo'):
            self.version_combo["values"] = self.versions
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            elif self.versions:
                self.version_combo.current(0)

    def _launch_selected(self) -> None:
        if hasattr(self, 'version_combo'):
            version = self.version_combo.get()
            if version and version != "Загрузка...":
                self._launch_game(self.config.get("last_username", "Player"), version)

    def _launch_game(self, username: str, version: str) -> None:
        self.config["last_version"] = version
        self._save_config()
        
        def install_and_launch():
            try:
                minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                options = {"username": username}
                command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
                subprocess.Popen(command, cwd=self.minecraft_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        threading.Thread(target=install_and_launch, daemon=True).start()


def main():
    root = tk.Tk()
    app = JustLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()