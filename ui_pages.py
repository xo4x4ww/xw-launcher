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
            btn = HoverButton(item_frame, text=text, fg="#777777", font=("Segoe UI", 12),
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
            HoverButton(bottom_frame, text=text, fg="#777777", font=("Segoe UI", 11),
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
                btn.config(fg="#777777", font=("Segoe UI", 12))


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

        welcome = RoundedFrame(self, bg="#1a1a1a", radius=18)
        welcome.pack(fill="x", pady=(0, 25))

        w_content = tk.Frame(welcome.inner_frame, bg="#1a1a1a")
        w_content.pack(fill="both", padx=24, pady=20)
        tk.Label(w_content, text=f"{greet}, {username}!", font=("Segoe UI", 20, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w")
        tk.Label(w_content, text="Готовы к новым приключениям в Minecraft?",
                 font=("Segoe UI", 11), bg="#1a1a1a", fg="#999999").pack(anchor="w", pady=(4, 0))

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

        play_btn = tk.Button(self, text="▶ ИГРАТЬ", bg="#4a9eff", fg="#ffffff",
                             font=("Segoe UI", 13, "bold"), bd=0, padx=40, pady=12,
                             cursor="hand2", command=self._launch,
                             activebackground="#3a8eef", activeforeground="#ffffff")
        play_btn.pack(pady=(0, 30))

        # Карточки в строку, но не растягиваются бесконечно по высоте
        cards_frame = tk.Frame(self, bg="#0d0d0d")
        cards_frame.pack(fill="x")

        left_card = RoundedFrame(cards_frame, bg="#1a1a1a", radius=18)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left_card.config(height=140)
        left_card.pack_propagate(False)

        lc = tk.Frame(left_card.inner_frame, bg="#1a1a1a")
        lc.pack(fill="both", padx=20, pady=20)
        tk.Label(lc, text="📦", font=("Segoe UI", 32), bg="#1a1a1a", fg="#4a9eff").pack(anchor="w")
        tk.Label(lc, text="Сборки модов", font=("Segoe UI", 15, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(lc, text="Готовые сборки для любого стиля игры",
                 font=("Segoe UI", 9), bg="#1a1a1a", fg="#999999").pack(anchor="w")

        right_card = RoundedFrame(cards_frame, bg="#1a1a1a", radius=18)
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))
        right_card.config(height=140)
        right_card.pack_propagate(False)

        rc = tk.Frame(right_card.inner_frame, bg="#1a1a1a")
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
        self.destroy()
        self.__init__(self.master, self.app)
        self.pack(fill="both", expand=True)

    def _launch(self):
        version = self.version_combo.get()
        acc_name = self.account_combo.get()
        self.app.game_launcher.launch(version, acc_name, self.app._accounts, self.app)


class NewsPage(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#0d0d0d", **kwargs)
        self._build()

    def _build(self):
        tk.Label(self, text="Новости версий", font=("Segoe UI", 22, "bold"),
                 bg="#0d0d0d", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        news = [
            ("1.21.11", "Исправлены критические ошибки.", "10 апреля 2025"),
            ("1.21", "Tricky Trials — новые испытания.", "13 июня 2024"),
            ("1.20.5", "Armored Paws — броненосцы и волчья броня.", "23 апреля 2024"),
        ]
        for ver, desc, date in news:
            card = RoundedFrame(self, bg="#1a1a1a", radius=14)
            card.pack(fill="x", pady=6)
            inner = tk.Frame(card.inner_frame, bg="#1a1a1a")
            inner.pack(fill="both", padx=20, pady=18)
            tk.Label(inner, text=f"🆕 Minecraft {ver}", font=("Segoe UI", 13, "bold"),
                     bg="#1a1a1a", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=date, font=("Segoe UI", 9), bg="#1a1a1a", fg="#4a9eff").pack(anchor="w", pady=(2, 8))
            tk.Label(inner, text=desc, font=("Segoe UI", 10), bg="#1a1a1a", fg="#aaaaaa").pack(anchor="w")


class ModpacksPage(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#0d0d0d", **kwargs)
        self._build()

    def _build(self):
        tk.Label(self, text="Сборки модов", font=("Segoe UI", 22, "bold"),
                 bg="#0d0d0d", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        packs = [
            ("Better MC", "1.20.1", "Forge", "Улучшенный ванильный опыт", 150),
            ("All The Mods 9", "1.20.1", "Forge", "400+ модов", 420),
            ("Fabulously Optimized", "1.20.4", "Fabric", "Оптимизация и шейдеры", 45),
            ("RLCraft", "1.12.2", "Forge", "Хардкорное выживание", 120),
        ]
        for name, ver, loader, desc, cnt in packs:
            card = RoundedFrame(self, bg="#1a1a1a", radius=14)
            card.pack(fill="x", pady=6)
            inner = tk.Frame(card.inner_frame, bg="#1a1a1a")
            inner.pack(fill="both", padx=20, pady=18)
            tk.Label(inner, text=name, font=("Segoe UI", 14, "bold"), bg="#1a1a1a", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=f"{ver} • {loader} • {cnt} модов", font=("Segoe UI", 9),
                     bg="#1a1a1a", fg="#4a9eff").pack(anchor="w", pady=(2, 8))
            tk.Label(inner, text=desc, font=("Segoe UI", 9), bg="#1a1a1a", fg="#999999").pack(anchor="w")
            btn = tk.Button(inner, text="Установить", bg="#333333", fg="#ffffff", bd=0, padx=15, pady=5,
                            cursor="hand2", activebackground="#444444", activeforeground="#ffffff")
            btn.pack(anchor="w", pady=(12, 0))


class ModsPage(tk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, bg="#0d0d0d", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#0d0d0d")
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Моды", font=("Segoe UI", 22, "bold"),
                 bg="#0d0d0d", fg="#ffffff").pack(side="left")
        open_btn = tk.Button(header, text="📂 Открыть папку", bg="#333333", fg="#ffffff", bd=0, padx=15, pady=5,
                             cursor="hand2", command=self._open_mods_folder,
                             activebackground="#444444", activeforeground="#ffffff")
        open_btn.pack(side="right")

        if not self.app._installed_mods:
            empty = RoundedFrame(self, bg="#1a1a1a", radius=18)
            empty.pack(fill="both", expand=True)
            einner = tk.Frame(empty.inner_frame, bg="#1a1a1a")
            einner.pack(expand=True, padx=40, pady=40)
            tk.Label(einner, text="📦", font=("Segoe UI", 48), bg="#1a1a1a", fg="#888888").pack()
            tk.Label(einner, text="Нет установленных модов", font=("Segoe UI", 14, "bold"),
                     bg="#1a1a1a", fg="#ffffff").pack(pady=(10, 5))
            tk.Label(einner, text="Поместите файлы .jar в папку mods",
                     font=("Segoe UI", 10), bg="#1a1a1a", fg="#999999").pack()
            btn = tk.Button(einner, text="Открыть папку модов", bg="#4a9eff", fg="#ffffff", bd=0, padx=20, pady=8,
                            cursor="hand2", command=self._open_mods_folder,
                            activebackground="#3a8eef", activeforeground="#ffffff")
            btn.pack(pady=(20, 0))
        else:
            # Прокручиваемая область
            canvas = tk.Canvas(self, bg="#0d0d0d", highlightthickness=0)
            scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#0d0d0d")

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Заголовки колонок
            cols = tk.Frame(scrollable_frame, bg="#0d0d0d")
            cols.pack(fill="x", pady=(0, 8))
            tk.Label(cols, text="Название", font=("Segoe UI", 10, "bold"), bg="#0d0d0d", fg="#666666",
                     width=20, anchor="w").pack(side="left")
            tk.Label(cols, text="Версия мода", font=("Segoe UI", 10, "bold"), bg="#0d0d0d", fg="#666666",
                     width=15, anchor="w").pack(side="left")
            tk.Label(cols, text="Для Minecraft", font=("Segoe UI", 10, "bold"), bg="#0d0d0d", fg="#666666",
                     width=15, anchor="w").pack(side="left")
            tk.Frame(scrollable_frame, bg="#2a2a2a", height=1).pack(fill="x", pady=5)

            for mod in self.app._installed_mods:
                row = tk.Frame(scrollable_frame, bg="#0d0d0d")
                row.pack(fill="x", pady=2)
                tk.Label(row, text=mod.get("name", "?"), font=("Segoe UI", 10), bg="#0d0d0d", fg="#ffffff",
                         width=20, anchor="w").pack(side="left")
                tk.Label(row, text=mod.get("mod_version", "?"), font=("Segoe UI", 10), bg="#0d0d0d", fg="#aaaaaa",
                         width=15, anchor="w").pack(side="left")
                tk.Label(row, text=mod.get("mc_version", "?"), font=("Segoe UI", 10), bg="#0d0d0d", fg="#aaaaaa",
                         width=15, anchor="w").pack(side="left")

    def _open_mods_folder(self):
        mods_dir = os.path.join(self.app.minecraft_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        os.startfile(mods_dir)


class SettingsDialog:
    def __init__(self, app):
        self.app = app
        self.dialog = tk.Toplevel(app.root)
        self.dialog.title("Настройки")
        self.dialog.geometry("480x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(app.root)
        self.dialog.grab_set()
        self.dialog.configure(bg="#1a1a1a")
        self._center_dialog(480, 350)

        inner = tk.Frame(self.dialog, bg="#1a1a1a")
        inner.pack(fill="both", padx=30, pady=30)

        tk.Label(inner, text="Настройки", font=("Segoe UI", 20, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 24))

        ram_frame = tk.Frame(inner, bg="#1a1a1a")
        ram_frame.pack(fill="x", pady=4)
        tk.Label(ram_frame, text="Выделение памяти (MB)", font=("Segoe UI", 10),
                 bg="#1a1a1a", fg="#aaaaaa", width=28, anchor="w").pack(side="left")
        self.ram_var = tk.IntVar(value=self.app.config.get("ram_allocation", 2048))
        tk.Spinbox(ram_frame, from_=512, to=16384, increment=256, textvariable=self.ram_var, width=10,
                   bg="#0d0d0d", fg="#ffffff", bd=0).pack(side="left")

        close_frame = tk.Frame(inner, bg="#1a1a1a")
        close_frame.pack(fill="x", pady=15)
        self.close_var = tk.BooleanVar(value=self.app.config.get("close_launcher", True))
        tk.Checkbutton(close_frame, text="Закрывать лаунчер при запуске игры", variable=self.close_var,
                       bg="#1a1a1a", activebackground="#1a1a1a", selectcolor="#0d0d0d",
                       fg="#aaaaaa", font=("Segoe UI", 10)).pack(anchor="w")

        f_frame = tk.Frame(inner, bg="#1a1a1a")
        f_frame.pack(fill="x", pady=(10, 0))
        tk.Label(f_frame, text="Папка игры:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a1a", fg="#4a9eff").pack(anchor="w")
        tk.Label(f_frame, text=self.app.minecraft_dir, font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#888888").pack(anchor="w", pady=(2, 0))
        HoverButton(f_frame, text="📂 Открыть", fg="#4a9eff", font=("Segoe UI", 9),
                    command=lambda: os.startfile(self.app.minecraft_dir)).pack(anchor="w", pady=(5, 0))

        btn_frame = tk.Frame(inner, bg="#1a1a1a")
        btn_frame.pack(fill="x", pady=(20, 0))

        cancel_btn = tk.Button(btn_frame, text="Отмена", bg="#333333", fg="#ffffff",
                               font=("Segoe UI", 11), bd=0, padx=25, pady=10,
                               activebackground="#444444", activeforeground="#ffffff",
                               command=self.dialog.destroy)
        cancel_btn.pack(side="right", padx=(10, 0))

        save_btn = tk.Button(btn_frame, text="Сохранить", bg="#4a9eff", fg="#ffffff",
                             font=("Segoe UI", 11, "bold"), bd=0, padx=25, pady=10,
                             cursor="hand2", command=self._save,
                             activebackground="#3a8eef", activeforeground="#ffffff")
        save_btn.pack(side="right")

        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def _center_dialog(self, w, h):
        self.dialog.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - w) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

    def _save(self):
        self.app.config.set("ram_allocation", self.ram_var.get())
        self.app.config.set("close_launcher", self.close_var.get())
        self.app.config.save()
        self.dialog.destroy()
        messagebox.showinfo("Настройки", "Сохранено")


class AccountsManager:
    def __init__(self, app):
        self.app = app

    def add_account(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Добавить аккаунт")
        dialog.geometry("380x220")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.configure(bg="#1a1a1a")
        self._center_dialog(dialog, 380, 220)

        inner = tk.Frame(dialog, bg="#1a1a1a")
        inner.pack(fill="both", padx=28, pady=28)

        tk.Label(inner, text="Добавить оффлайн-аккаунт", font=("Segoe UI", 15, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 18))
        tk.Label(inner, text="Никнейм", font=("Segoe UI", 10),
                 bg="#1a1a1a", fg="#aaaaaa").pack(anchor="w")

        entry = tk.Entry(inner, bg="#0d0d0d", fg="#ffffff", font=("Segoe UI", 12),
                         bd=0, insertbackground="#ffffff")
        entry.pack(fill="x", ipady=10, pady=(6, 20))
        entry.insert(0, f"Player{len(self.app._accounts)+1}")
        entry.focus()
        entry.select_range(0, "end")

        btn_frame = tk.Frame(inner, bg="#1a1a1a")
        btn_frame.pack(fill="x")

        HoverButton(btn_frame, text="Отмена", fg="#999999", font=("Segoe UI", 10),
                    command=dialog.destroy).pack(side="right", padx=(12, 0))

        def save():
            name = entry.get().strip()
            if name:
                self.app.add_account(name)
                dialog.destroy()

        save_btn = tk.Button(btn_frame, text="Добавить", bg="#4a9eff", fg="#ffffff",
                             font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=6,
                             cursor="hand2", command=save,
                             activebackground="#3a8eef", activeforeground="#ffffff")
        save_btn.pack(side="right")
        entry.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def manage(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Управление аккаунтами")
        dialog.geometry("420x400")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.configure(bg="#1a1a1a")
        self._center_dialog(dialog, 420, 400)

        inner = tk.Frame(dialog, bg="#1a1a1a")
        inner.pack(fill="both", padx=28, pady=28)

        tk.Label(inner, text="Управление аккаунтами", font=("Segoe UI", 15, "bold"),
                 bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 18))

        list_frame = tk.Frame(inner, bg="#1a1a1a")
        list_frame.pack(fill="both", expand=True, pady=(0, 18))

        for i, acc in enumerate(self.app._accounts):
            item = RoundedFrame(list_frame, bg="#0d0d0d", radius=10)
            item.pack(fill="x", pady=2)
            sub = tk.Frame(item.inner_frame, bg="#0d0d0d")
            sub.pack(fill="both", padx=14, pady=10)
            cur = " (текущий)" if i == self.app._current_account_index else ""
            tk.Label(sub, text=f"{acc['username']}{cur}", font=("Segoe UI", 11),
                     bg="#0d0d0d", fg="#ffffff").pack(side="left")
            if i != self.app._current_account_index and len(self.app._accounts) > 1:
                HoverButton(sub, text="🗑️", fg="#ff6b6b", font=("Segoe UI", 12),
                            command=lambda idx=i: self._delete_account(idx, dialog)).pack(side="right")

        add_btn = tk.Button(inner, text="➕ Добавить аккаунт", bg="#333333", fg="#ffffff",
                            font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=8,
                            cursor="hand2", command=lambda: [dialog.destroy(), self.add_account()],
                            activebackground="#444444", activeforeground="#ffffff")
        add_btn.pack(pady=5)
        HoverButton(inner, text="Закрыть", fg="#999999", font=("Segoe UI", 10),
                    command=dialog.destroy).pack(pady=(10, 0))
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _delete_account(self, idx, dialog):
        if len(self.app._accounts) <= 1:
            messagebox.showwarning("Внимание", "Нельзя удалить последний аккаунт")
            return
        self.app.delete_account(idx)
        dialog.destroy()
        self.manage()

    def _center_dialog(self, dialog, w, h):
        dialog.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - w) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")