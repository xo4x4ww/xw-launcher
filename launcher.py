import json
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from datetime import datetime

import minecraft_launcher_lib


class RoundedFrame(tk.Frame):
    """Статическая рамка с закруглёнными углами (без интерактивности)"""
    def __init__(self, parent, bg="#151515", radius=16, **kwargs):
        super().__init__(parent, bg=parent["bg"], **kwargs)
        self.radius = radius
        self.bg_color = bg

        self.canvas = tk.Canvas(self, bg=parent["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.inner_frame = tk.Frame(self.canvas, bg=bg)
        self.inner_frame.pack(fill="both", expand=True, padx=1, pady=1)

        self.canvas.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        self.canvas.delete("all")
        w, h = event.width, event.height
        self._create_rounded_rect(0, 0, w, h, self.radius, fill=self.bg_color, outline="")

    @staticmethod
    def _create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)


class HoverButton(tk.Label):
    """Кнопка с изменением цвета при наведении"""
    def __init__(self, parent, text, command=None, **kwargs):
        super().__init__(parent, text=text, cursor="hand2", **kwargs)
        self.default_fg = kwargs.get("fg", "#888888")
        self.hover_fg = "#ffffff"
        self.command = command
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        self.config(fg=self.hover_fg)

    def _on_leave(self, e):
        self.config(fg=self.default_fg)

    def _on_click(self, e):
        if self.command:
            self.command()


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("1000x600")
        self.root.minsize(900, 520)
        self.root.configure(bg="#0a0a0a")

        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions = []
        self._accounts = self.config.get("accounts", [{"username": "Player"}])
        self._current_account_index = 0
        self._installed_mods = self._scan_mods()
        self._current_page = "home"

        self._load_versions_async()
        self._build_ui()

    # ---------- Конфигурация ----------
    def _load_config(self):
        default = {
            "last_username": "Player",
            "last_version": "",
            "accounts": [{"username": "Player"}],
            "ram_allocation": 2048,
            "close_launcher": True,
        }
        if not self.config_path.exists():
            return default
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            default.update(saved)
            if not default.get("accounts"):
                default["accounts"] = [{"username": "Player"}]
        except:
            pass
        return default

    def _save_config(self):
        try:
            self.config["accounts"] = self._accounts
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _scan_mods(self):
        mods_dir = os.path.join(self.minecraft_dir, "mods")
        mods = []
        if os.path.exists(mods_dir):
            for f in os.listdir(mods_dir):
                if f.endswith(".jar"):
                    mods.append({"name": f.replace(".jar", ""), "file": f, "enabled": True})
        return mods

    # ---------- Версии ----------
    def _load_versions_async(self):
        def worker():
            try:
                manifest = minecraft_launcher_lib.utils.get_version_list()
                vers = [v["id"] for v in manifest if v.get("type") == "release"][:20]
            except:
                vers = ["1.21.11", "1.21", "1.20.6", "1.20.4", "1.20.2", "1.20.1", "1.19.4"]
            self.versions = vers
            self.root.after(0, self._update_version_combobox)
        threading.Thread(target=worker, daemon=True).start()

    def _update_version_combobox(self):
        if hasattr(self, "version_combo"):
            self.version_combo["values"] = self.versions
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            elif self.versions:
                self.version_combo.set(self.versions[0])

    # ---------- UI ----------
    def _build_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        # Главный контейнер
        main = tk.Frame(self.root, bg="#0a0a0a")
        main.pack(fill="both", expand=True, padx=30, pady=20)

        # Верхняя панель: логотип + меню
        self._build_header(main)

        # Контентная область
        self.content_frame = tk.Frame(main, bg="#0a0a0a")
        self.content_frame.pack(fill="both", expand=True, pady=(20, 0))

        self._show_home_page()

    def _build_header(self, parent):
        header = tk.Frame(parent, bg="#0a0a0a", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Логотип
        logo_frame = tk.Frame(header, bg="#0a0a0a")
        logo_frame.pack(side="left")
        tk.Label(logo_frame, text="XW Launcher", font=("Segoe UI", 18, "bold"),
                 bg="#0a0a0a", fg="#ffffff").pack(side="left")

        # Меню навигации
        nav_frame = tk.Frame(header, bg="#0a0a0a")
        nav_frame.pack(side="left", padx=40)

        self.nav_buttons = {}
        pages = [
            ("Главная", "home"),
            ("Новости версий", "news"),
            ("Сборки", "modpacks"),
            ("Моды", "mods"),
        ]
        for text, key in pages:
            btn = HoverButton(nav_frame, text=text, fg="#888888", font=("Segoe UI", 12),
                              command=lambda k=key: self._nav_click(k))
            btn.pack(side="left", padx=15)
            self.nav_buttons[key] = btn

        # Профиль
        right = tk.Frame(header, bg="#0a0a0a")
        right.pack(side="right")

        username = self._accounts[self._current_account_index]["username"]
        self.profile_btn = tk.Menubutton(
            right, text=f"{username} ▼", font=("Segoe UI", 11),
            bg="#151515", fg="#cccccc", bd=0, cursor="hand2",
            activebackground="#151515", activeforeground="#ffffff"
        )
        self.profile_btn.pack()
        self._update_profile_menu()

    def _update_profile_menu(self):
        menu = tk.Menu(self.profile_btn, tearoff=0, bg="#151515", fg="#ffffff",
                       activebackground="#2a2a2a", activeforeground="#ffffff")
        for i, acc in enumerate(self._accounts):
            check = "✓ " if i == self._current_account_index else "  "
            menu.add_command(label=f"{check}{acc['username']}",
                             command=lambda idx=i: self._switch_account(idx))
        menu.add_separator()
        menu.add_command(label="➕ Добавить аккаунт", command=self._add_account)
        menu.add_command(label="✏️ Управление аккаунтами", command=self._manage_accounts)
        menu.add_separator()
        menu.add_command(label="⚙️ Настройки", command=self._show_settings)
        menu.add_command(label="📁 Папка игры", command=lambda: os.startfile(self.minecraft_dir))
        menu.add_separator()
        menu.add_command(label="🚪 Выход", command=self.root.quit)
        self.profile_btn.config(menu=menu)

    def _switch_account(self, idx):
        self._current_account_index = idx
        self.config["last_username"] = self._accounts[idx]["username"]
        self._save_config()
        self.profile_btn.config(text=f"{self._accounts[idx]['username']} ▼")
        self._update_profile_menu()
        if self._current_page == "home":
            self._show_home_page()

    def _add_account(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить аккаунт")
        dialog.geometry("380x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        self._center_dialog(dialog, 380, 220)

        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=28, pady=28)

        tk.Label(inner, text="Добавить оффлайн-аккаунт", font=("Segoe UI", 15, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 18))
        tk.Label(inner, text="Никнейм", font=("Segoe UI", 10),
                 bg="#151515", fg="#aaaaaa").pack(anchor="w")

        entry = tk.Entry(inner, bg="#0a0a0a", fg="#ffffff", font=("Segoe UI", 12),
                         bd=0, insertbackground="#ffffff")
        entry.pack(fill="x", ipady=10, pady=(6, 20))
        entry.insert(0, f"Player{len(self._accounts)+1}")
        entry.focus()
        entry.select_range(0, "end")

        btn_frame = tk.Frame(inner, bg="#151515")
        btn_frame.pack(fill="x")

        HoverButton(btn_frame, text="Отмена", fg="#888888", font=("Segoe UI", 10),
                    command=dialog.destroy).pack(side="right", padx=(12, 0))

        def save():
            name = entry.get().strip()
            if name:
                self._accounts.append({"username": name})
                self._save_config()
                self._update_profile_menu()
                dialog.destroy()

        btn = tk.Button(btn_frame, text="Добавить", bg="#4a9eff", fg="#ffffff",
                        font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=8,
                        cursor="hand2", command=save)
        btn.pack(side="right")
        entry.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _manage_accounts(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Управление аккаунтами")
        dialog.geometry("420x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        self._center_dialog(dialog, 420, 400)

        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=28, pady=28)

        tk.Label(inner, text="Управление аккаунтами", font=("Segoe UI", 15, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 18))

        list_frame = tk.Frame(inner, bg="#151515")
        list_frame.pack(fill="both", expand=True, pady=(0, 18))

        for i, acc in enumerate(self._accounts):
            item = tk.Frame(list_frame, bg="#0a0a0a")
            item.pack(fill="x", pady=2)

            sub = tk.Frame(item, bg="#0a0a0a")
            sub.pack(fill="both", padx=14, pady=10)

            cur = " (текущий)" if i == self._current_account_index else ""
            tk.Label(sub, text=f"{acc['username']}{cur}", font=("Segoe UI", 11),
                     bg="#0a0a0a", fg="#ffffff").pack(side="left")

            if i != self._current_account_index and len(self._accounts) > 1:
                HoverButton(sub, text="🗑️", fg="#ff6b6b", font=("Segoe UI", 12),
                            command=lambda idx=i: self._delete_account(idx, dialog)).pack(side="right")

        HoverButton(inner, text="➕ Добавить аккаунт", fg="#4a9eff", font=("Segoe UI", 11, "bold"),
                    command=lambda: [dialog.destroy(), self._add_account()]).pack(pady=5)
        HoverButton(inner, text="Закрыть", fg="#888888", font=("Segoe UI", 10),
                    command=dialog.destroy).pack(pady=(10, 0))
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _delete_account(self, idx, dialog):
        if len(self._accounts) <= 1:
            messagebox.showwarning("Внимание", "Нельзя удалить последний аккаунт")
            return
        del self._accounts[idx]
        if self._current_account_index >= len(self._accounts):
            self._current_account_index = len(self._accounts) - 1
        self.config["last_username"] = self._accounts[self._current_account_index]["username"]
        self._save_config()
        self.profile_btn.config(text=f"{self._accounts[self._current_account_index]['username']} ▼")
        self._update_profile_menu()
        dialog.destroy()
        self._manage_accounts()

    def _center_dialog(self, dialog, w, h):
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

    def _nav_click(self, key):
        self._current_page = key
        # Обновить активный пункт меню
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 12, "bold"))
            else:
                btn.config(fg="#888888", font=("Segoe UI", 12))

        pages = {
            "home": self._show_home_page,
            "news": self._show_news_page,
            "modpacks": self._show_modpacks_page,
            "mods": self._show_mods_page,
        }
        pages[key]()

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    # ---------- Главная страница ----------
    def _show_home_page(self):
        self._clear_content()

        username = self._accounts[self._current_account_index]["username"]
        hour = datetime.now().hour
        greet = "Доброе утро" if hour < 12 else "Добрый день" if hour < 18 else "Добрый вечер"

        # Приветствие
        welcome_card = RoundedFrame(self.content_frame, bg="#151515", radius=18)
        welcome_card.pack(fill="x", pady=(0, 25))

        w_inner = welcome_card.inner_frame
        w_content = tk.Frame(w_inner, bg="#151515")
        w_content.pack(fill="both", padx=24, pady=20)

        tk.Label(w_content, text=f"{greet}, {username}!", font=("Segoe UI", 20, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w")
        tk.Label(w_content, text="Готовы к новым приключениям в Minecraft?",
                 font=("Segoe UI", 11), bg="#151515", fg="#888888").pack(anchor="w", pady=(4, 0))

        # Строка с выбором версии и аккаунта
        row = tk.Frame(self.content_frame, bg="#0a0a0a")
        row.pack(fill="x", pady=(0, 25))

        # Версия
        vf = tk.Frame(row, bg="#0a0a0a")
        vf.pack(side="left", padx=(0, 30))
        tk.Label(vf, text="Версия", font=("Segoe UI", 10, "bold"), bg="#0a0a0a", fg="#888888").pack(anchor="w", pady=(0, 6))
        self.version_combo = ttk.Combobox(vf, values=self.versions, state="readonly", font=("Segoe UI", 11), width=22)
        self.version_combo.pack()
        if self.versions:
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            else:
                self.version_combo.set(self.versions[0])

        # Аккаунт
        af = tk.Frame(row, bg="#0a0a0a")
        af.pack(side="left")
        tk.Label(af, text="Аккаунт", font=("Segoe UI", 10, "bold"), bg="#0a0a0a", fg="#888888").pack(anchor="w", pady=(0, 6))
        acc_names = [acc["username"] for acc in self._accounts]
        self.account_combo = ttk.Combobox(af, values=acc_names, state="readonly", font=("Segoe UI", 11), width=22)
        self.account_combo.set(self._accounts[self._current_account_index]["username"])
        self.account_combo.pack()

        # Кнопка ИГРАТЬ
        play_btn = tk.Button(self.content_frame, text="▶ ИГРАТЬ", bg="#4a9eff", fg="#ffffff",
                             font=("Segoe UI", 13, "bold"), bd=0, padx=50, pady=14,
                             cursor="hand2", command=self._launch_selected)
        play_btn.pack(pady=(0, 30))

        # Две карточки в ряд
        cards_row = tk.Frame(self.content_frame, bg="#0a0a0a")
        cards_row.pack(fill="both", expand=True)

        # Левая карточка (Сборки)
        left_card = RoundedFrame(cards_row, bg="#151515", radius=18)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        l_inner = left_card.inner_frame
        l_content = tk.Frame(l_inner, bg="#151515")
        l_content.pack(fill="both", padx=20, pady=20)

        tk.Label(l_content, text="📦", font=("Segoe UI", 32), bg="#151515", fg="#4a9eff").pack(anchor="w")
        tk.Label(l_content, text="Сборки модов", font=("Segoe UI", 15, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(l_content, text="Готовые сборки для любого стиля игры",
                 font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w")

        # Правая карточка (Моды)
        right_card = RoundedFrame(cards_row, bg="#151515", radius=18)
        right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        r_inner = right_card.inner_frame
        r_content = tk.Frame(r_inner, bg="#151515")
        r_content.pack(fill="both", padx=20, pady=20)

        mod_count = len(self._installed_mods)
        tk.Label(r_content, text="🔧", font=("Segoe UI", 32), bg="#151515", fg="#50c878").pack(anchor="w")
        tk.Label(r_content, text=f"Установлено модов: {mod_count}", font=("Segoe UI", 15, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(r_content, text="Управляйте модами во вкладке Моды",
                 font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w")

    # ---------- Остальные страницы (заглушки) ----------
    def _show_news_page(self):
        self._clear_content()
        tk.Label(self.content_frame, text="Новости версий", font=("Segoe UI", 22, "bold"),
                 bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        news = [
            ("1.21.11", "Исправлены критические ошибки.", "10 апреля 2025"),
            ("1.21", "Tricky Trials — новые испытания.", "13 июня 2024"),
        ]
        for ver, desc, date in news:
            card = RoundedFrame(self.content_frame, bg="#151515", radius=14)
            card.pack(fill="x", pady=6)
            inner = tk.Frame(card.inner_frame, bg="#151515")
            inner.pack(fill="both", padx=20, pady=18)
            tk.Label(inner, text=f"🆕 Minecraft {ver}", font=("Segoe UI", 13, "bold"),
                     bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=date, font=("Segoe UI", 9), bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(2, 8))
            tk.Label(inner, text=desc, font=("Segoe UI", 10), bg="#151515", fg="#aaaaaa").pack(anchor="w")

    def _show_modpacks_page(self):
        self._clear_content()
        tk.Label(self.content_frame, text="Сборки модов", font=("Segoe UI", 22, "bold"),
                 bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 20))
        packs = [
            ("Better MC", "1.20.1", "Forge", "Улучшенный ванильный опыт", 150),
            ("All The Mods 9", "1.20.1", "Forge", "400+ модов", 420),
        ]
        for name, ver, loader, desc, cnt in packs:
            card = RoundedFrame(self.content_frame, bg="#151515", radius=14)
            card.pack(fill="x", pady=6)
            inner = tk.Frame(card.inner_frame, bg="#151515")
            inner.pack(fill="both", padx=20, pady=18)
            tk.Label(inner, text=name, font=("Segoe UI", 14, "bold"), bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(inner, text=f"{ver} • {loader} • {cnt} модов", font=("Segoe UI", 9),
                     bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(2, 8))
            tk.Label(inner, text=desc, font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w")
            tk.Button(inner, text="Установить", bg="#2a2a2a", fg="#ffffff", bd=0, padx=15, pady=5,
                      cursor="hand2").pack(anchor="w", pady=(12, 0))

    def _show_mods_page(self):
        self._clear_content()
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Моды", font=("Segoe UI", 22, "bold"),
                 bg="#0a0a0a", fg="#ffffff").pack(side="left")
        tk.Button(header, text="📂 Открыть папку", bg="#2a2a2a", fg="#ffffff", bd=0, padx=15, pady=5,
                  cursor="hand2", command=self._open_mods_folder).pack(side="right")

        if not self._installed_mods:
            empty = RoundedFrame(self.content_frame, bg="#151515", radius=18)
            empty.pack(fill="both", expand=True)
            einner = tk.Frame(empty.inner_frame, bg="#151515")
            einner.pack(expand=True, padx=40, pady=40)
            tk.Label(einner, text="📦", font=("Segoe UI", 48), bg="#151515", fg="#888888").pack()
            tk.Label(einner, text="Нет установленных модов", font=("Segoe UI", 14, "bold"),
                     bg="#151515", fg="#ffffff").pack(pady=(10, 5))
            tk.Label(einner, text="Поместите файлы .jar в папку mods",
                     font=("Segoe UI", 10), bg="#151515", fg="#888888").pack()
            tk.Button(einner, text="Открыть папку модов", bg="#4a9eff", fg="#ffffff", bd=0, padx=20, pady=8,
                      cursor="hand2", command=self._open_mods_folder).pack(pady=(20, 0))
        else:
            # Таблица
            cols = tk.Frame(self.content_frame, bg="#0a0a0a")
            cols.pack(fill="x", pady=(0, 8))
            tk.Label(cols, text="Название", font=("Segoe UI", 10, "bold"), bg="#0a0a0a", fg="#666666",
                     width=40, anchor="w").pack(side="left")
            tk.Label(cols, text="Статус", font=("Segoe UI", 10, "bold"), bg="#0a0a0a", fg="#666666",
                     width=15, anchor="w").pack(side="left")
            tk.Frame(self.content_frame, bg="#2a2a2a", height=1).pack(fill="x", pady=5)

            for mod in self._installed_mods:
                row = tk.Frame(self.content_frame, bg="#0a0a0a")
                row.pack(fill="x", pady=2)
                tk.Label(row, text=mod["name"], font=("Segoe UI", 10), bg="#0a0a0a", fg="#ffffff",
                         width=40, anchor="w").pack(side="left")
                status = "✓ Включен" if mod["enabled"] else "✗ Отключен"
                color = "#50c878" if mod["enabled"] else "#ff6b6b"
                tk.Label(row, text=status, font=("Segoe UI", 9), bg="#0a0a0a", fg=color,
                         width=15, anchor="w").pack(side="left")

    def _open_mods_folder(self):
        mods_dir = os.path.join(self.minecraft_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        os.startfile(mods_dir)

    # ---------- Настройки ----------
    def _show_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        self._center_dialog(dialog, 500, 450)

        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=30, pady=30)

        tk.Label(inner, text="Настройки", font=("Segoe UI", 20, "bold"),
                 bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 24))

        settings = [
            ("Выделение памяти (MB)", "ram_allocation", "spin", (512, 16384)),
            ("Аргументы Java", "java_args", "entry", None),
            ("Закрывать лаунчер при запуске", "close_launcher", "check", None),
        ]
        widgets = {}
        for label, key, typ, opts in settings:
            row = tk.Frame(inner, bg="#151515")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=("Segoe UI", 10), bg="#151515", fg="#aaaaaa",
                     width=28, anchor="w").pack(side="left")
            if typ == "spin":
                var = tk.IntVar(value=self.config.get(key, 2048))
                tk.Spinbox(row, from_=opts[0], to=opts[1], textvariable=var, width=10,
                           bg="#0a0a0a", fg="#ffffff", bd=0).pack(side="left")
                widgets[key] = var
            elif typ == "entry":
                var = tk.StringVar(value=self.config.get(key, ""))
                tk.Entry(row, textvariable=var, bg="#0a0a0a", fg="#ffffff", bd=0, width=30).pack(side="left", ipady=6)
                widgets[key] = var
            elif typ == "check":
                var = tk.BooleanVar(value=self.config.get(key, False))
                tk.Checkbutton(row, variable=var, bg="#151515", activebackground="#151515").pack(side="left")
                widgets[key] = var

        # Папка игры
        f_frame = tk.Frame(inner, bg="#151515")
        f_frame.pack(fill="x", pady=(15, 0))
        tk.Label(f_frame, text="Папка игры:", font=("Segoe UI", 10, "bold"),
                 bg="#151515", fg="#4a9eff").pack(anchor="w")
        tk.Label(f_frame, text=self.minecraft_dir, font=("Segoe UI", 9),
                 bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 0))
        HoverButton(f_frame, text="📂 Открыть", fg="#4a9eff", font=("Segoe UI", 9),
                    command=lambda: os.startfile(self.minecraft_dir)).pack(anchor="w", pady=(5, 0))

        # Кнопки
        btn_frame = tk.Frame(inner, bg="#151515")
        btn_frame.pack(fill="x", pady=(20, 0))
        HoverButton(btn_frame, text="Отмена", fg="#888888", font=("Segoe UI", 10),
                    command=dialog.destroy).pack(side="right", padx=(12, 0))

        def save():
            for k, v in widgets.items():
                if isinstance(v, tk.IntVar):
                    self.config[k] = v.get()
                elif isinstance(v, tk.StringVar):
                    self.config[k] = v.get()
                elif isinstance(v, tk.BooleanVar):
                    self.config[k] = v.get()
            self._save_config()
            dialog.destroy()
            messagebox.showinfo("Настройки", "Сохранено")

        tk.Button(btn_frame, text="Сохранить", bg="#4a9eff", fg="#ffffff",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=8,
                  cursor="hand2", command=save).pack(side="right")
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ---------- Запуск ----------
    def _launch_selected(self):
        version = self.version_combo.get()
        acc_name = self.account_combo.get()
        for i, acc in enumerate(self._accounts):
            if acc["username"] == acc_name:
                self._current_account_index = i
                self.config["last_username"] = acc_name
                self.profile_btn.config(text=f"{acc_name} ▼")
                break
        self.config["last_version"] = version
        self._save_config()

        if self.config.get("close_launcher", True):
            self.root.iconify()

        def worker():
            try:
                minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                opts = {"username": acc_name}
                if self.config.get("ram_allocation"):
                    opts["ram"] = str(self.config["ram_allocation"])
                cmd = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, opts)
                subprocess.Popen(cmd, cwd=self.minecraft_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                self.root.after(0, self.root.deiconify)

        threading.Thread(target=worker, daemon=True).start()


def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()