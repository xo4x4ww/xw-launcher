import json
import os
import subprocess
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import messagebox, ttk

import minecraft_launcher_lib


class RoundedFrame(tk.Frame):
    """Фрейм с закругленными углами"""
    def __init__(self, parent, bg="#151515", radius=10, **kwargs):
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
        self.canvas.create_rounded_rect(0, 0, w, h, self.radius, fill=self.bg_color, outline="")
        self.canvas.create_window(2, 2, window=self.inner_frame, anchor="nw", width=w-4, height=h-4)


def create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Рисует закругленный прямоугольник на canvas"""
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


# Добавляем метод в Canvas
tk.Canvas.create_rounded_rect = create_rounded_rect


class RoundedButton(tk.Canvas):
    """Кнопка с закругленными углами"""
    def __init__(self, parent, text="", bg="#2a2a2a", fg="#ffffff", hover_bg="#3a3a3a", 
                 radius=6, command=None, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, **kwargs)
        self.bg_color = bg
        self.fg_color = fg
        self.hover_bg = hover_bg
        self.radius = radius
        self.command = command
        self.text = text
        self.is_hovered = False
        
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def _on_configure(self, event):
        self._draw()
    
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1 and h > 1:
            bg = self.hover_bg if self.is_hovered else self.bg_color
            self.create_rounded_rect(0, 0, w, h, self.radius, fill=bg, outline="")
            self.create_text(w//2, h//2, text=self.text, fill=self.fg_color, 
                           font=("Segoe UI", 10, "bold"))
    
    def _on_enter(self, event):
        self.is_hovered = True
        self._draw()
    
    def _on_leave(self, event):
        self.is_hovered = False
        self._draw()
    
    def _on_click(self, event):
        if self.command:
            self.command()


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
        self._current_page = "home"
        self._accounts = self.config.get("accounts", [{"username": "Player"}])
        self._current_account_index = 0
        
        self._servers = [
            {"name": "SURVIVAL", "desc": "Ванильное выживание. Ноль модов, ноль плагинов.", 
             "online": "21 / 100", "ip": "PLAY.SURVIVAL.NET", "version": "1.20.1"},
            {"name": "ANARCHY", "desc": "У нас разрешено всё, присоединяйся!", 
             "online": "84 / 200", "ip": "PLAY.ANARCHY.NET", "version": "1.8 - 1.20.1"},
            {"name": "CREATIVE", "desc": "Сервер для творчества и строительства.", 
             "online": "45 / 80", "ip": "PLAY.CREATIVE.NET", "version": "1.20.1"},
        ]
        
        self._mods = [
            {"name": "Fabric API", "version": "0.92.0", "author": "FabricMC", "enabled": True},
            {"name": "Sodium", "version": "0.5.8", "author": "jellysquid3", "enabled": True},
            {"name": "Lithium", "version": "0.12.1", "author": "jellysquid3", "enabled": True},
            {"name": "Iris Shaders", "version": "1.7.0", "author": "coderbot", "enabled": True},
            {"name": "Mod Menu", "version": "9.0.0", "author": "Prospector", "enabled": True},
            {"name": "REI", "version": "12.0.0", "author": "shedaniel", "enabled": False},
        ]

        self._build_ui()
        self._load_versions_async()

    def _load_config(self) -> dict:
        default = {
            "last_username": "Player", 
            "last_version": "", 
            "username_history": ["Player"],
            "accounts": [{"username": "Player"}],
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
            self.config["accounts"] = self._accounts
            with self.config_path.open("w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _build_ui(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()
            
        self.main_container = tk.Frame(self.root, bg="#0a0a0a")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=12)
        
        self._build_header()
        
        content = tk.Frame(self.main_container, bg="#0a0a0a")
        content.pack(fill="both", expand=True, pady=(12, 8))
        
        self._build_sidebar(content)
        
        self.content_frame = tk.Frame(content, bg="#0a0a0a")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(12, 0))
        
        self._build_footer()
        
        self._show_home_page()

    def _build_header(self) -> None:
        header = tk.Frame(self.main_container, bg="#0a0a0a", height=36)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        right = tk.Frame(header, bg="#0a0a0a")
        right.pack(side="right")
        
        current_account = self._accounts[self._current_account_index]
        username = current_account.get("username", "Player")
        
        self.profile_btn = tk.Menubutton(right, text=f"{username} ▼", font=("Segoe UI", 11),
                                         bg="#0a0a0a", fg="#cccccc", bd=0, cursor="hand2",
                                         activebackground="#0a0a0a", activeforeground="#ffffff")
        self.profile_btn.pack(side="left")
        
        self._update_profile_menu()

    def _update_profile_menu(self):
        profile_menu = tk.Menu(self.profile_btn, tearoff=0, bg="#151515", fg="#ffffff",
                               activebackground="#2a2a2a", activeforeground="#ffffff")
        
        for i, acc in enumerate(self._accounts):
            username = acc.get("username", "Player")
            check = "✓ " if i == self._current_account_index else "  "
            profile_menu.add_command(label=f"{check}{username}", 
                                    command=lambda idx=i: self._switch_account(idx))
        
        profile_menu.add_separator()
        profile_menu.add_command(label="➕ Добавить аккаунт", command=self._add_account)
        profile_menu.add_command(label="✏️ Управление аккаунтами", command=self._manage_accounts)
        profile_menu.add_separator()
        profile_menu.add_command(label="🚪 Выход", command=self.root.quit)
        
        self.profile_btn.config(menu=profile_menu)

    def _switch_account(self, index: int):
        self._current_account_index = index
        username = self._accounts[index]["username"]
        self.config["last_username"] = username
        self._save_config()
        self.profile_btn.config(text=f"{username} ▼")
        self._update_profile_menu()
        
        if self._current_page == "home":
            self._show_home_page()

    def _add_account(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить аккаунт")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        self._center_dialog(dialog, 350, 200)
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Добавить аккаунт", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        tk.Label(inner, text="Никнейм", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w")
        
        entry = tk.Entry(inner, bg="#0a0a0a", fg="#ffffff", font=("Segoe UI", 11), bd=0)
        entry.pack(fill="x", ipady=8, pady=(5, 20))
        entry.insert(0, f"Player{len(self._accounts) + 1}")
        entry.focus()
        entry.select_range(0, "end")
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x")
        
        tk.Label(buttons, text="Отмена", font=("Segoe UI", 9),
                bg="#151515", fg="#888888", cursor="hand2").pack(side="right", padx=(10, 0))
        buttons.winfo_children()[0].bind("<Button-1>", lambda e: dialog.destroy())
        
        def save():
            new_nick = entry.get().strip()
            if new_nick:
                self._accounts.append({"username": new_nick})
                self._save_config()
                self._update_profile_menu()
                dialog.destroy()
        
        save_btn = RoundedButton(buttons, text="Добавить", bg="#2a2a2a", fg="#ffffff", 
                                 hover_bg="#3a3a3a", command=save, width=90, height=32)
        save_btn.pack(side="right")
        
        entry.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _manage_accounts(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Управление аккаунтами")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        self._center_dialog(dialog, 400, 350)
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Управление аккаунтами", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        list_frame = tk.Frame(inner, bg="#151515")
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        for i, acc in enumerate(self._accounts):
            item = tk.Frame(list_frame, bg="#0a0a0a")
            item.pack(fill="x", pady=2)
            
            item_inner = tk.Frame(item, bg="#0a0a0a")
            item_inner.pack(fill="both", padx=12, pady=8)
            
            username = acc.get("username", "Player")
            current = " (текущий)" if i == self._current_account_index else ""
            tk.Label(item_inner, text=f"{username}{current}", font=("Segoe UI", 10),
                    bg="#0a0a0a", fg="#ffffff").pack(side="left")
            
            if i != self._current_account_index and len(self._accounts) > 1:
                del_btn = tk.Label(item_inner, text="🗑️", font=("Segoe UI", 10),
                                  bg="#0a0a0a", fg="#ff6b6b", cursor="hand2")
                del_btn.pack(side="right")
                del_btn.bind("<Button-1>", lambda e, idx=i: self._delete_account(idx, dialog))
        
        add_btn = RoundedButton(inner, text="➕ Добавить аккаунт", bg="#2a2a2a", fg="#ffffff",
                                hover_bg="#3a3a3a", command=lambda: [dialog.destroy(), self._add_account()],
                                width=160, height=36)
        add_btn.pack()
        
        tk.Label(inner, text="Закрыть", font=("Segoe UI", 9),
                bg="#151515", fg="#888888", cursor="hand2").pack(pady=(10, 0))
        inner.winfo_children()[-1].bind("<Button-1>", lambda e: dialog.destroy())
        
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _delete_account(self, index: int, dialog: tk.Toplevel):
        if len(self._accounts) <= 1:
            messagebox.showwarning("Внимание", "Нельзя удалить последний аккаунт")
            return
        
        del self._accounts[index]
        if self._current_account_index >= len(self._accounts):
            self._current_account_index = len(self._accounts) - 1
        
        username = self._accounts[self._current_account_index]["username"]
        self.config["last_username"] = username
        self._save_config()
        self.profile_btn.config(text=f"{username} ▼")
        self._update_profile_menu()
        
        dialog.destroy()
        self._manage_accounts()

    def _center_dialog(self, dialog, width, height):
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"+{x}+{y}")

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg="#0a0a0a", width=130)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        nav_items = [
            ("🎮 Играть", "home"),
            ("🌐 Сервера", "servers"),
            ("📦 Сборки", "modpacks"),
            ("🔧 Моды", "mods"),
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
            ("⚙️ Настройки", self._show_settings),
            ("📁 Папка игры", lambda: os.startfile(self.minecraft_dir)),
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
            "mods": self._show_mods_page,
        }
        pages.get(key, self._show_home_page)()

    def _clear_content(self) -> None:
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_home_page(self) -> None:
        self._clear_content()
        
        username = self._accounts[self._current_account_index]["username"]
        tk.Label(self.content_frame, text=f"С возвращением, {username}!",
                font=("Segoe UI", 18, "bold"), bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 8))
        
        # Выбор версии в закругленном фрейме
        version_card = RoundedFrame(self.content_frame, bg="#151515", radius=10)
        version_card.pack(fill="x", pady=(10, 20))
        
        inner = version_card.inner_frame
        inner.pack_propagate(False)
        inner.config(height=80)
        
        content = tk.Frame(inner, bg="#151515")
        content.pack(fill="both", padx=18, pady=15)
        
        tk.Label(content, text="Версия Minecraft:", font=("Segoe UI", 10),
                bg="#151515", fg="#aaaaaa").pack(side="left", padx=(0, 12))
        
        self.version_combo = ttk.Combobox(content, values=self.versions, state="readonly",
                                           font=("Segoe UI", 10), width=22)
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
        play_btn = RoundedButton(self.content_frame, text="🎮 ИГРАТЬ", bg="#2a2a2a", fg="#ffffff",
                                 hover_bg="#3a3a3a", command=self._launch_selected,
                                 width=180, height=44, radius=8)
        play_btn.pack(anchor="w", pady=(0, 25))
        
        # Карточка "НОВЫЙ СНАПШОТ"
        info_card = RoundedFrame(self.content_frame, bg="#151515", radius=10)
        info_card.pack(fill="x")
        
        info_inner = info_card.inner_frame
        info_content = tk.Frame(info_inner, bg="#151515")
        info_content.pack(fill="both", padx=18, pady=18)
        
        tk.Label(info_content, text="🆕 НОВЫЙ СНАПШОТ", font=("Segoe UI", 11, "bold"),
                bg="#151515", fg="#4a9eff").pack(anchor="w")
        tk.Label(info_content, text="ПОСЛЕДНЯЯ ВЕРСИЯ: 1.20.2", font=("Segoe UI", 10),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(5, 0))
        
        # Карточка "ОБНОВЛЕНИЕ ЛАУНЧЕРА"
        update_card = RoundedFrame(self.content_frame, bg="#151515", radius=10)
        update_card.pack(fill="x", pady=(10, 0))
        
        update_inner = update_card.inner_frame
        update_content = tk.Frame(update_inner, bg="#151515")
        update_content.pack(fill="both", padx=18, pady=18)
        
        tk.Label(update_content, text="📱 ОБНОВЛЕНИЕ ЛАУНЧЕРА 2.0", font=("Segoe UI", 11, "bold"),
                bg="#151515", fg="#4a9eff").pack(anchor="w")
        
        small_play = RoundedButton(update_content, text="ИГРАТЬ", bg="#2a2a2a", fg="#ffffff",
                                   hover_bg="#3a3a3a", command=self._launch_selected,
                                   width=100, height=32, radius=6)
        small_play.pack(anchor="w", pady=(10, 0))

    def _show_servers_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 12))
        
        tk.Label(header, text="СЕРВЕРА", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        links = tk.Frame(header, bg="#0a0a0a")
        links.pack(side="right")
        
        add_btn = tk.Label(links, text="➕ Добавить сервер", font=("Segoe UI", 9),
                          bg="#0a0a0a", fg="#4a9eff", cursor="hand2")
        add_btn.pack(side="left")
        add_btn.bind("<Button-1>", lambda e: self._add_server())
        
        # Поле поиска с закруглением
        search_card = RoundedFrame(self.content_frame, bg="#151515", radius=8)
        search_card.pack(fill="x", pady=(0, 16))
        search_card.inner_frame.config(height=40)
        search_card.inner_frame.pack_propagate(False)
        
        search_inner = tk.Frame(search_card.inner_frame, bg="#151515")
        search_inner.pack(fill="both", padx=12, pady=8)
        
        tk.Label(search_inner, text="🔍", font=("Segoe UI", 11),
                bg="#151515", fg="#666666").pack(side="left", padx=(0, 8))
        
        self.search_entry = tk.Entry(search_inner, bg="#151515", fg="#ffffff", font=("Segoe UI", 10),
                                      bd=0, insertbackground="#ffffff")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.insert(0, "Название сервера, категории или игры")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        
        for server in self._servers:
            self._create_server_card(server)

    def _create_server_card(self, server: dict) -> None:
        card = RoundedFrame(self.content_frame, bg="#151515", radius=10)
        card.pack(fill="x", pady=6)
        
        inner = card.inner_frame
        content = tk.Frame(inner, bg="#151515")
        content.pack(fill="both", padx=18, pady=16)
        
        top = tk.Frame(content, bg="#151515")
        top.pack(fill="x")
        
        tk.Label(top, text=server["name"], font=("Segoe UI", 13, "bold"),
                bg="#151515", fg="#ffffff").pack(side="left")
        
        online_frame = tk.Frame(top, bg="#151515")
        online_frame.pack(side="right")
        
        tk.Label(online_frame, text="●", font=("Segoe UI", 9),
                bg="#151515", fg="#50c878").pack(side="left")
        tk.Label(online_frame, text=f" Онлайн {server['online']}", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(side="left")
        
        tk.Label(content, text=server["desc"], font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(5, 12))
        
        bottom = tk.Frame(content, bg="#151515")
        bottom.pack(fill="x")
        
        ip_frame = tk.Frame(bottom, bg="#151515")
        ip_frame.pack(side="left")
        
        tk.Label(ip_frame, text=server["ip"], font=("Segoe UI", 9),
                bg="#151515", fg="#4a9eff").pack(side="left")
        tk.Label(ip_frame, text=server["version"], font=("Segoe UI", 8),
                bg="#151515", fg="#666666").pack(side="left", padx=(10, 0))
        
        play_btn = RoundedButton(bottom, text="Играть", bg="#2a2a2a", fg="#ffffff",
                                 hover_bg="#3a3a3a", command=lambda s=server: self._connect_server(s),
                                 width=80, height=30, radius=6)
        play_btn.pack(side="right")

    def _show_modpacks_page(self) -> None:
        self._clear_content()
        
        tk.Label(self.content_frame, text="Сборки", font=("Segoe UI", 18, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", pady=(0, 12))
        
        modpacks = [
            ("Better MC", "1.20.1", "Forge", "Улучшенный ванильный опыт"),
            ("All The Mods 9", "1.20.1", "Forge", "400+ модов"),
            ("Fabulously Optimized", "1.20.4", "Fabric", "Оптимизация и шейдеры"),
            ("RLCraft", "1.12.2", "Forge", "Хардкорное выживание"),
        ]
        
        grid = tk.Frame(self.content_frame, bg="#0a0a0a")
        grid.pack(fill="both", expand=True)
        
        for i, (name, version, loader, desc) in enumerate(modpacks):
            card = RoundedFrame(grid, bg="#151515", radius=10)
            card.grid(row=i//2, column=i%2, padx=4, pady=4, sticky="nsew")
            grid.columnconfigure(i%2, weight=1)
            
            inner = card.inner_frame
            content = tk.Frame(inner, bg="#151515")
            content.pack(fill="both", padx=16, pady=16)
            
            tk.Label(content, text=name, font=("Segoe UI", 12, "bold"),
                    bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(content, text=f"{version} • {loader}", font=("Segoe UI", 9),
                    bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 5))
            tk.Label(content, text=desc, font=("Segoe UI", 8),
                    bg="#151515", fg="#666666").pack(anchor="w")
            
            install_btn = RoundedButton(content, text="Установить", bg="#2a2a2a", fg="#ffffff",
                                        hover_bg="#3a3a3a", command=lambda n=name: self._install_modpack(n),
                                        width=90, height=30, radius=6)
            install_btn.pack(pady=(12, 0))

    def _show_mods_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 12))
        
        tk.Label(header, text="Моды", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        # ПОДБОРКА ЛУЧШИХ МОДОВ
        featured = RoundedFrame(self.content_frame, bg="#151515", radius=10)
        featured.pack(fill="x", pady=(0, 16))
        
        featured_inner = featured.inner_frame
        featured_content = tk.Frame(featured_inner, bg="#151515")
        featured_content.pack(fill="both", padx=18, pady=16)
        
        tk.Label(featured_content, text="🔥 ПОДБОРКА ЛУЧШИХ МОДОВ", font=("Segoe UI", 12, "bold"),
                bg="#151515", fg="#ff6b6b").pack(anchor="w")
        tk.Label(featured_content, text="СООБЩЕСТВО", font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 0))
        
        # Заголовки списка
        cols = tk.Frame(self.content_frame, bg="#0a0a0a")
        cols.pack(fill="x", pady=(0, 5))
        
        tk.Label(cols, text="Название", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=20, anchor="w").pack(side="left")
        tk.Label(cols, text="Версия", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=12, anchor="w").pack(side="left")
        tk.Label(cols, text="Автор", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=15, anchor="w").pack(side="left")
        tk.Label(cols, text="Статус", font=("Segoe UI", 9, "bold"),
                bg="#0a0a0a", fg="#666666", width=10, anchor="w").pack(side="left")
        
        tk.Frame(self.content_frame, bg="#2a2a2a", height=1).pack(fill="x", pady=5)
        
        for mod in self._mods:
            self._create_mod_row(mod)

    def _create_mod_row(self, mod: dict):
        row = tk.Frame(self.content_frame, bg="#0a0a0a")
        row.pack(fill="x", pady=2)
        
        tk.Label(row, text=mod["name"], font=("Segoe UI", 10),
                bg="#0a0a0a", fg="#ffffff", width=20, anchor="w").pack(side="left")
        tk.Label(row, text=mod["version"], font=("Segoe UI", 10),
                bg="#0a0a0a", fg="#aaaaaa", width=12, anchor="w").pack(side="left")
        tk.Label(row, text=mod["author"], font=("Segoe UI", 10),
                bg="#0a0a0a", fg="#aaaaaa", width=15, anchor="w").pack(side="left")
        
        status_color = "#50c878" if mod["enabled"] else "#ff6b6b"
        status_text = "✓ Вкл" if mod["enabled"] else "✗ Выкл"
        tk.Label(row, text=status_text, font=("Segoe UI", 9),
                bg="#0a0a0a", fg=status_color, width=10, anchor="w").pack(side="left")

    def _on_search_focus_in(self, event) -> None:
        if self.search_entry.get() == "Название сервера, категории или игры":
            self.search_entry.delete(0, "end")

    def _on_search_focus_out(self, event) -> None:
        if not self.search_entry.get():
            self.search_entry.insert(0, "Название сервера, категории или игры")

    def _show_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#151515")
        
        self._center_dialog(dialog, 400, 250)
        
        inner = tk.Frame(dialog, bg="#151515")
        inner.pack(fill="both", padx=25, pady=25)
        
        tk.Label(inner, text="Настройки", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(0, 15))
        
        tk.Label(inner, text=f"Папка игры: {self.minecraft_dir}", font=("Segoe UI", 9),
                bg="#151515", fg="#aaaaaa").pack(anchor="w", pady=5)
        
        open_btn = tk.Label(inner, text="📂 Открыть папку игры", font=("Segoe UI", 9),
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
        
        save_btn = RoundedButton(buttons, text="Сохранить", bg="#2a2a2a", fg="#ffffff",
                                 hover_bg="#3a3a3a", command=save_settings, width=90, height=32)
        save_btn.pack(side="right")

    def _add_server(self) -> None:
        messagebox.showinfo("Добавить сервер", "Функция добавления сервера в разработке")

    def _connect_server(self, server: dict) -> None:
        self._launch_game(self._accounts[self._current_account_index]["username"], 
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
            self.versions = ["1.20.1", "1.20", "1.19.4", "1.19.2", "1.18.2"]
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
                self._launch_game(self._accounts[self._current_account_index]["username"], version)

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