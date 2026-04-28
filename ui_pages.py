import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from ui_widgets import RoundedFrame, HoverButton

class Header(tk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, bg="#0d0d0d", height=36, **kwargs)
        self.pack_propagate(False)
        self.app = app

        tk.Label(self, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                 bg="#0d0d0d", fg="#ffffff").pack(side="left")

        right = tk.Frame(self, bg="#0d0d0d")
        right.pack(side="right")

        profile_frame = RoundedFrame(right, bg="#1a1a1a", radius=8)
        profile_frame.pack(side="left")
        profile_inner = tk.Frame(profile_frame.inner_frame, bg="#1a1a1a")
        profile_inner.pack(fill="both", padx=2, pady=2)

        self.username = app.current_username
        self.profile_btn = tk.Menubutton(
            profile_inner, text=f" {self.username} ▼ ", font=("Segoe UI", 10),
            bg="#1a1a1a", fg="#cccccc", bd=0, cursor="hand2",
            activebackground="#1a1a1a", activeforeground="#ffffff",
            padx=8, pady=4
        )
        self.profile_btn.pack()
        self._update_menu()

    def _update_menu(self):
        app = self.app
        menu = tk.Menu(self.profile_btn, tearoff=0, bg="#1a1a1a", fg="#cccccc",
                       activebackground="#2a2a2a", activeforeground="#ffffff", bd=0, font=("Segoe UI", 10))
        for i, acc in enumerate(app._accounts):
            check = "✓ " if i == app._current_account_index else "  "
            menu.add_command(label=f"{check}{acc['username']}",
                             command=lambda idx=i: app.switch_account(idx))
        menu.add_separator()
        menu.add_command(label="➕ Добавить аккаунт", command=lambda: AccountsManager(app).add_account())
        menu.add_command(label="✏️ Управление аккаунтами", command=lambda: AccountsManager(app).manage())
        menu.add_separator()
        menu.add_command(label="⚙️ Настройки", command=lambda: SettingsDialog(app))
        menu.add_command(label="📁 Папка игры", command=lambda: os.startfile(app.minecraft_dir))
        menu.add_separator()
        menu.add_command(label="🚪 Выход", command=self.app.root.quit)
        self.profile_btn.config(menu=menu)

    def update_username(self, name):
        self.username = name
        self.profile_btn.config(text=f" {name} ▼ ")
        self._update_menu()


class Sidebar(tk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, bg="#0d0d0d", width=190, **kwargs)
        self.pack_propagate(False)
        self.app = app
        self.nav_buttons = {}

        nav_frame = tk.Frame(self, bg="#0d0d0d")
        nav_frame.pack(fill="x", pady=(30, 0))

        items = [
            ("🏠 Главная", "home"),
            ("📰 Новости версий", "news"),
            ("📦 Сборки", "modpacks"),
            ("🔧 Моды", "mods"),
        ]
        for text, key in items:
            item_frame = tk.Frame(nav_frame, bg="#0d0d0d", height=44)
            item_frame.pack(fill="x", pady=3)
            item_frame.pack_propagate(False)
            btn = HoverButton(item_frame, text=text, fg="#999999", font=("Segoe UI", 12),
                              anchor="w", command=lambda k=key: app._show_page(k))
            btn.pack(fill="both", padx=10)
            self.nav_buttons[key] = (item_frame, btn)

        bottom_frame = tk.Frame(self, bg="#0d0d0d")
        bottom_frame.pack(side="bottom", fill="x", pady=15)
        for text, cmd in [
            ("👤 Аккаунты", lambda: AccountsManager(app).manage()),
            ("⚙️ Настройки", lambda: SettingsDialog(app)),
            ("📁 Папка игры", lambda: os.startfile(app.minecraft_dir))
        ]:
            HoverButton(bottom_frame, text=text, fg="#999999", font=("Segoe UI", 11),
                        anchor="w", command=cmd).pack(fill="x", padx=10, pady=4)

        self.set_active("home")

    def set_active(self, key):
        for k, (frame, btn) in self.nav_buttons.items():
            for w in frame.winfo_children():
                if isinstance(w, tk.Frame):
                    w.destroy()
            if k == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 12, "bold"))
                tk.Frame(frame, bg="#4a9eff", width=3).place(x=0, rely=0.15, height=30)
            else:
                btn.config(fg="#999999", font=("Segoe UI", 12))


class HomePage(tk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, bg="#0d0d0d", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        app = self.app
        username = app.current_username
        hour = datetime.now().hour
        greet = "Доброе утро" if hour < 12 else "Добрый день" if hour < 18 else "Добрый вечер"

        # Приветственная карточка
        welcome = RoundedFrame(self, bg="#1a1a1a", radius=18)
        welcome.pack(fill="x", pady=(0, 25))
        w_content = tk.Frame(welcome.inner_frame, bg="#1a1a1a")
        w_content.pack(fill="both", padx=24, pady=20)
        tk.Label(w_content, text=f"{greet}, {username}!", font=("Segoe UI", 20, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w")
        tk.Label(w_content, text="Готовы к новым приключениям в Minecraft?",
                 font=("Segoe UI", 11), bg="#1a1a1a", fg="#999999").pack(anchor="w", pady=(4, 0))

        # Выбор версии и аккаунта
        row = tk.Frame(self, bg="#0d0d0d")
        row.pack(fill="x", pady=(0, 25))

        vf = tk.Frame(row, bg="#0d0d0d")
        vf.pack(side="left", padx=(0, 30))
        tk.Label(vf, text="Версия", font=("Segoe UI", 10, "bold"), bg="#0d0d0d", fg="#999999").pack(anchor="w", pady=(0, 6))
        self.version_combo = ttk.Combobox(vf, values=[], state="readonly",
                                          font=("Segoe UI", 11), width=22, style="Dark.TCombobox")
        self.version_combo.pack()
        if hasattr(app, 'versions') and app.versions:
            self.update_versions(app.versions)

        af = tk.Frame(row, bg="#0d0d0d")
        af.pack(side="left")
        tk.Label(af, text="Аккаунт", font=("Segoe UI", 10, "bold"), bg="#0d0d0d", fg="#999999").pack(anchor="w", pady=(0, 6))
        self.account_combo = ttk.Combobox(af, values=[], state="readonly",
                                          font=("Segoe UI", 11), width=22, style="Dark.TCombobox")
        self.account_combo.pack()
        self.update_accounts([a["username"] for a in app._accounts], app._current_account_index)

        # Кнопка ИГРАТЬ
        play_btn = tk.Button(self, text="▶ ИГРАТЬ", bg="#4a9eff", fg="#ffffff",
                             font=("Segoe UI", 13, "bold"), bd=0, padx=40, pady=12,
                             cursor="hand2", command=self._launch,
                             activebackground="#3a8eef", activeforeground="#ffffff")
        play_btn.pack(pady=(0, 30))

        # Информационные карточки
        cards = tk.Frame(self, bg="#0d0d0d")
        cards.pack(fill="both", expand=True)

        left = RoundedFrame(cards, bg="#1a1a1a", radius=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        lc = tk.Frame(left.inner_frame, bg="#1a1a1a")
        lc.pack(fill="both", padx=20, pady=20)
        tk.Label(lc, text="📦", font=("Segoe UI", 32), bg="#1a1a1a", fg="#4a9eff").pack(anchor="w")
        tk.Label(lc, text="Сборки модов", font=("Segoe UI", 15, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(lc, text="Готовые сборки для любого стиля игры",
                 font=("Segoe UI", 9), bg="#1a1a1a", fg="#999999").pack(anchor="w")

        right = RoundedFrame(cards, bg="#1a1a1a", radius=18)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        rc = tk.Frame(right.inner_frame, bg="#1a1a1a")
        rc.pack(fill="both", padx=20, pady=20)
        mod_count = len(self.app._installed_mods)
        tk.Label(rc, text="🔧", font=("Segoe UI", 32), bg="#1a1a1a", fg="#50c878").pack(anchor="w")
        tk.Label(rc, text=f"Установлено модов: {mod_count}", font=("Segoe UI", 15, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(rc, text="Управляйте модами во вкладке Моды",
                 font=("Segoe UI", 9), bg="#1a1a1a", fg="#999999").pack(anchor="w")

    def update_versions(self, versions):
        self.version_combo["values"] = versions
        last = self.app.config.last_version
        if last in versions:
            self.version_combo.set(last)
        elif versions:
            self.version_combo.set(versions[0])

    def update_accounts(self, names, current_idx):
        self.account_combo["values"] = names
        if 0 <= current_idx < len(names):
            self.account_combo.set(names[current_idx])

    def refresh_greeting(self):
        # Для простоты пересоздаём страницу
        self.destroy()
        self.__init__(self.master, self.app)
        self.pack(fill="both", expand=True)

    def _launch(self):
        version = self.version_combo.get()
        acc_name = self.account_combo.get()
        self.app.game_launcher.launch(version, acc_name, self.app._accounts, self.app)