import json
import os
import subprocess
import threading
import tkinter as tk
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from datetime import datetime

import minecraft_launcher_lib


class RoundedFrame(tk.Frame):
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
        self.canvas.create_rounded_rect(0, 0, w, h, self.radius, fill=self.bg_color, outline="")


def create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
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


tk.Canvas.create_rounded_rect = create_rounded_rect


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg="#0a0a0a", **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=6)
        self.scrollbar.configure(bg="#2a2a2a", troughcolor="#151515", activebackground="#4a4a4a", bd=0)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.bind_mousewheel()
    
    def bind_mousewheel(self):
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", bg="#2a2a2a", fg="#ffffff", hover_bg="#3a3a3a", 
                 radius=12, command=None, font_size=10, padding_x=20, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, **kwargs)
        self.bg_color = bg
        self.fg_color = fg
        self.hover_bg = hover_bg
        self.radius = radius
        self.command = command
        self.text = text
        self.font_size = font_size
        self.padding_x = padding_x
        self.is_hovered = False
        self.is_pressed = False
        
        self.bind("<Configure>", self._on_configure)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
    
    def _on_configure(self, event):
        self._draw()
    
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w > 1 and h > 1:
            if self.is_pressed:
                bg = self._darken_color(self.hover_bg)
            elif self.is_hovered:
                bg = self.hover_bg
            else:
                bg = self.bg_color
            self.create_rounded_rect(0, 0, w, h, self.radius, fill=bg, outline="")
            self.create_text(w//2, h//2, text=self.text, fill=self.fg_color, 
                           font=("Segoe UI", self.font_size, "bold"))
    
    def _darken_color(self, color):
        if color.startswith("#"):
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            r = max(0, r - 20)
            g = max(0, g - 20)
            b = max(0, b - 20)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color
    
    def _on_enter(self, event):
        self.is_hovered = True
        self._draw()
        self.config(cursor="hand2")
    
    def _on_leave(self, event):
        self.is_hovered = False
        self.is_pressed = False
        self._draw()
        self.config(cursor="")
    
    def _on_press(self, event):
        self.is_pressed = True
        self._draw()
    
    def _on_release(self, event):
        self.is_pressed = False
        self._draw()
        if self.command:
            self.command()


class HoverLabel(tk.Label):
    def __init__(self, parent, hover_color="#ffffff", **kwargs):
        super().__init__(parent, **kwargs)
        self.default_fg = kwargs.get("fg", "#888888")
        self.hover_color = hover_color
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.config(cursor="hand2")
    
    def _on_enter(self, event):
        self.config(fg=self.hover_color)
    
    def _on_leave(self, event):
        self.config(fg=self.default_fg)


class ModernCombobox(tk.Frame):
    def __init__(self, parent, values=None, default="", width=25, **kwargs):
        super().__init__(parent, bg="#0a0a0a", **kwargs)
        self.values = values or []
        self.var = tk.StringVar(value=default)
        self.is_open = False
        
        self.button_frame = RoundedFrame(self, bg="#151515", radius=12)
        self.button_frame.pack(fill="x")
        
        self.button_inner = tk.Frame(self.button_frame.inner_frame, bg="#151515")
        self.button_inner.pack(fill="both", padx=14, pady=8)
        
        self.label = tk.Label(self.button_inner, textvariable=self.var, font=("Segoe UI", 11),
                              bg="#151515", fg="#ffffff", anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        
        self.arrow = tk.Label(self.button_inner, text="▼", font=("Segoe UI", 9),
                              bg="#151515", fg="#888888")
        self.arrow.pack(side="right")
        
        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        self.label.bind("<Button-1>", self._toggle)
        self.arrow.bind("<Enter>", self._on_enter)
        self.arrow.bind("<Leave>", self._on_leave)
        self.arrow.bind("<Button-1>", self._toggle)
        
        self.dropdown = None
    
    def _on_enter(self, event):
        self.button_frame.canvas.configure(bg="#1a1a1a")
        self.button_inner.configure(bg="#1a1a1a")
        self.label.configure(bg="#1a1a1a")
        self.arrow.configure(bg="#1a1a1a")
        self.config(cursor="hand2")
    
    def _on_leave(self, event):
        if not self.is_open:
            self.button_frame.canvas.configure(bg="#151515")
            self.button_inner.configure(bg="#151515")
            self.label.configure(bg="#151515")
            self.arrow.configure(bg="#151515")
        self.config(cursor="")
    
    def _toggle(self, event=None):
        if self.is_open:
            self._close_dropdown()
        else:
            self._open_dropdown()
    
    def _open_dropdown(self):
        if self.dropdown:
            self._close_dropdown()
        
        self.is_open = True
        self.arrow.config(text="▲")
        
        self.dropdown = tk.Toplevel(self)
        self.dropdown.wm_overrideredirect(True)
        self.dropdown.configure(bg="#151515")
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.dropdown.geometry(f"{self.winfo_width()}x{min(len(self.values) * 36 + 8, 200)}+{x}+{y}")
        
        canvas = tk.Canvas(self.dropdown, bg="#151515", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.dropdown, orient="vertical", command=canvas.yview, width=6)
        scrollbar.configure(bg="#2a2a2a", troughcolor="#151515", activebackground="#4a4a4a", bd=0)
        scrollable = tk.Frame(canvas, bg="#151515")
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar.pack(side="right", fill="y")
        
        for value in self.values:
            item = tk.Frame(scrollable, bg="#151515", height=36)
            item.pack(fill="x")
            item.pack_propagate(False)
            
            label = tk.Label(item, text=value, font=("Segoe UI", 11),
                            bg="#151515", fg="#ffffff", anchor="w")
            label.pack(fill="both", padx=14, pady=6)
            
            def on_enter(e, f=item, l=label):
                f.configure(bg="#2a2a2a")
                l.configure(bg="#2a2a2a")
            
            def on_leave(e, f=item, l=label):
                f.configure(bg="#151515")
                l.configure(bg="#151515")
            
            def on_click(e, v=value):
                self.var.set(v)
                self._close_dropdown()
            
            item.bind("<Enter>", on_enter)
            item.bind("<Leave>", on_leave)
            item.bind("<Button-1>", on_click)
            label.bind("<Enter>", on_enter)
            label.bind("<Leave>", on_leave)
            label.bind("<Button-1>", on_click)
        
        self.dropdown.bind("<FocusOut>", lambda e: self._close_dropdown())
        self.dropdown.focus_set()
    
    def _close_dropdown(self):
        self.is_open = False
        self.arrow.config(text="▼")
        if self.dropdown:
            self.dropdown.destroy()
            self.dropdown = None
        
        self.button_frame.canvas.configure(bg="#151515")
        self.button_inner.configure(bg="#151515")
        self.label.configure(bg="#151515")
        self.arrow.configure(bg="#151515")
    
    def get(self):
        return self.var.get()
    
    def set(self, value):
        self.var.set(value)
    
    def update_values(self, values):
        self.values = values


class JustLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("1000x600")
        self.root.minsize(900, 520)
        self.root.configure(bg="#0a0a0a")
        
        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config_path = Path(__file__).with_name("launcher_config.json")
        self.config = self._load_config()
        self.versions: list[str] = []
        self._current_page = "home"
        self._accounts = self.config.get("accounts", [{"username": "Player"}])
        self._current_account_index = 0
        self._installed_mods = []
        self._load_installed_mods()
        self._version_news = []
        self._load_version_news()

        self._build_ui()
        self._load_versions_async()

    def _load_config(self) -> dict:
        default = {
            "last_username": "Player", 
            "last_version": "", 
            "accounts": [{"username": "Player"}],
            "ram_allocation": 2048,
            "java_args": "",
            "close_launcher": True,
        }
        if not self.config_path.exists():
            return default
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                saved = json.load(f)
        except:
            return default
        default.update(saved)
        if "accounts" not in default or not default["accounts"]:
            default["accounts"] = [{"username": "Player"}]
        return default

    def _save_config(self) -> None:
        try:
            self.config["accounts"] = self._accounts
            with self.config_path.open("w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _load_installed_mods(self):
        mods_dir = os.path.join(self.minecraft_dir, "mods")
        if os.path.exists(mods_dir):
            for file in os.listdir(mods_dir):
                if file.endswith(".jar"):
                    self._installed_mods.append({
                        "name": file.replace(".jar", ""),
                        "file": file,
                        "enabled": not file.endswith(".disabled")
                    })

    def _load_version_news(self):
        self._version_news = [
            {
                "version": "1.21",
                "title": "Minecraft 1.21 - Tricky Trials",
                "description": "Новое обновление добавляет Trial Chambers, моба Breeze, медные лампы и многое другое. Исследуйте процедурно-генерируемые структуры и сражайтесь с новыми врагами.",
                "date": "13 июня 2024",
                "type": "release"
            },
            {
                "version": "1.20.5",
                "title": "Minecraft 1.20.5 - Armored Paws",
                "description": "Обновление добавляет броненосцев, волчью броню и новые варианты волков. Теперь вы можете защитить своих питомцев и исследовать новые биомы.",
                "date": "23 апреля 2024",
                "type": "release"
            },
            {
                "version": "1.20.4",
                "title": "Minecraft 1.20.4",
                "description": "Техническое обновление с исправлением багов и улучшением производительности. Рекомендуется для всех игроков.",
                "date": "7 декабря 2023",
                "type": "release"
            },
            {
                "version": "1.20.2",
                "title": "Minecraft 1.20.2",
                "description": "Обновление добавляет экспериментальный Villager Trade Rebalance, новые настройки мира и исправления ошибок.",
                "date": "21 сентября 2023",
                "type": "release"
            },
        ]

    def _build_ui(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()
            
        self.main_container = tk.Frame(self.root, bg="#0a0a0a")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=16)
        
        self._build_header()
        
        content = tk.Frame(self.main_container, bg="#0a0a0a")
        content.pack(fill="both", expand=True, pady=(16, 10))
        
        self._build_sidebar(content)
        
        self.content_frame = tk.Frame(content, bg="#0a0a0a")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(16, 0))
        
        self._show_home_page()

    def _build_header(self) -> None:
        header = tk.Frame(self.main_container, bg="#0a0a0a", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        logo_frame = tk.Frame(header, bg="#0a0a0a")
        logo_frame.pack(side="left")
        
        logo_canvas = tk.Canvas(logo_frame, width=32, height=32, bg="#0a0a0a", highlightthickness=0)
        logo_canvas.pack(side="left")
        logo_canvas.create_rectangle(6, 6, 26, 26, fill="#4a9eff", outline="", width=0)
        logo_canvas.create_polygon(16, 4, 28, 10, 28, 22, 16, 28, 4, 22, 4, 10, 
                                   fill="#6bafff", outline="", smooth=True)
        
        tk.Label(logo_frame, text="XW Launcher", font=("Segoe UI", 16, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left", padx=8)
        
        right = tk.Frame(header, bg="#0a0a0a")
        right.pack(side="right")
        
        current_account = self._accounts[self._current_account_index]
        username = current_account.get("username", "Player")
        
        profile_frame = RoundedFrame(right, bg="#151515", radius=12)
        profile_frame.pack(side="left")
        profile_frame.inner_frame.config(height=36)
        profile_frame.inner_frame.pack_propagate(False)
        
        profile_content = tk.Frame(profile_frame.inner_frame, bg="#151515")
        profile_content.pack(fill="both", padx=12, pady=6)
        
        self.profile_btn = tk.Menubutton(profile_content, text=f"{username} ▼", font=("Segoe UI", 11),
                                         bg="#151515", fg="#cccccc", bd=0, cursor="hand2",
                                         activebackground="#151515", activeforeground="#ffffff")
        self.profile_btn.pack()
        
        self._update_profile_menu()

    def _update_profile_menu(self):
        profile_menu = tk.Menu(self.profile_btn, tearoff=0, bg="#151515", fg="#ffffff",
                               activebackground="#2a2a2a", activeforeground="#ffffff", bd=0)
        
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
        entry.insert(0, f"Player{len(self._accounts) + 1}")
        entry.focus()
        entry.select_range(0, "end")
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x")
        
        cancel_btn = HoverLabel(buttons, text="Отмена", font=("Segoe UI", 10),
                               bg="#151515", fg="#888888", hover_color="#ffffff")
        cancel_btn.pack(side="right", padx=(12, 0))
        cancel_btn.bind("<Button-1>", lambda e: dialog.destroy())
        
        def save():
            new_nick = entry.get().strip()
            if new_nick:
                self._accounts.append({"username": new_nick})
                self._save_config()
                self._update_profile_menu()
                dialog.destroy()
        
        save_btn = RoundedButton(buttons, text="Добавить", bg="#4a9eff", fg="#ffffff", 
                                 hover_bg="#3a8eef", command=save, width=100, height=36, radius=10)
        save_btn.pack(side="right")
        
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
            item = RoundedFrame(list_frame, bg="#0a0a0a", radius=10)
            item.pack(fill="x", pady=3)
            
            item_inner = tk.Frame(item.inner_frame, bg="#0a0a0a")
            item_inner.pack(fill="both", padx=14, pady=10)
            
            username = acc.get("username", "Player")
            current = " (текущий)" if i == self._current_account_index else ""
            tk.Label(item_inner, text=f"{username}{current}", font=("Segoe UI", 11),
                    bg="#0a0a0a", fg="#ffffff").pack(side="left")
            
            if i != self._current_account_index and len(self._accounts) > 1:
                del_btn = HoverLabel(item_inner, text="🗑️", font=("Segoe UI", 12),
                                    bg="#0a0a0a", fg="#ff6b6b", hover_color="#ff4444")
                del_btn.pack(side="right")
                del_btn.bind("<Button-1>", lambda e, idx=i: self._delete_account(idx, dialog))
        
        add_btn = RoundedButton(inner, text="➕ Добавить аккаунт", bg="#4a9eff", fg="#ffffff",
                                hover_bg="#3a8eef", command=lambda: [dialog.destroy(), self._add_account()],
                                width=170, height=38, radius=10, font_size=10)
        add_btn.pack()
        
        close_btn = HoverLabel(inner, text="Закрыть", font=("Segoe UI", 10),
                              bg="#151515", fg="#888888", hover_color="#ffffff")
        close_btn.pack(pady=(12, 0))
        close_btn.bind("<Button-1>", lambda e: dialog.destroy())
        
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
        sidebar = tk.Frame(parent, bg="#0a0a0a", width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        nav_items = [
            ("🏠 Главная", "home"),
            ("📰 Новости версий", "news"),
            ("📦 Сборки", "modpacks"),
            ("🔧 Моды", "mods"),
        ]
        
        self.nav_buttons = {}
        for label, key in nav_items:
            btn_frame = tk.Frame(sidebar, bg="#0a0a0a", height=44)
            btn_frame.pack(fill="x", pady=2)
            btn_frame.pack_propagate(False)
            
            btn = HoverLabel(btn_frame, text=label, font=("Segoe UI", 12),
                            bg="#0a0a0a", fg="#888888", hover_color="#ffffff", anchor="w")
            btn.pack(fill="both", padx=10)
            
            if self._current_page == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 12, "bold"))
                indicator = tk.Frame(btn_frame, bg="#4a9eff", width=3)
                indicator.place(x=0, y=6, height=32)
            
            btn.bind("<Button-1>", lambda e, k=key: self._nav_click(k))
            
            self.nav_buttons[key] = (btn_frame, btn)
        
        sidebar_bottom = tk.Frame(sidebar, bg="#0a0a0a")
        sidebar_bottom.pack(side="bottom", fill="x", pady=10)
        
        accounts_btn = HoverLabel(sidebar_bottom, text="👤 Аккаунты", font=("Segoe UI", 11),
                                  bg="#0a0a0a", fg="#888888", hover_color="#ffffff", anchor="w",
                                  cursor="hand2")
        accounts_btn.pack(fill="x", padx=10, pady=4)
        accounts_btn.bind("<Button-1>", lambda e: self._manage_accounts())
        
        settings_btn = HoverLabel(sidebar_bottom, text="⚙️ Настройки", font=("Segoe UI", 11),
                                  bg="#0a0a0a", fg="#888888", hover_color="#ffffff", anchor="w",
                                  cursor="hand2")
        settings_btn.pack(fill="x", padx=10, pady=4)
        settings_btn.bind("<Button-1>", lambda e: self._show_settings())
        
        folder_btn = HoverLabel(sidebar_bottom, text="📁 Папка игры", font=("Segoe UI", 11),
                                bg="#0a0a0a", fg="#888888", hover_color="#ffffff", anchor="w",
                                cursor="hand2")
        folder_btn.pack(fill="x", padx=10, pady=4)
        folder_btn.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))

    def _nav_click(self, key: str) -> None:
        self._current_page = key
        
        for k, (frame, btn) in self.nav_buttons.items():
            for w in frame.winfo_children():
                if isinstance(w, tk.Frame):
                    w.destroy()
            
            if k == key:
                btn.config(fg="#ffffff", font=("Segoe UI", 12, "bold"))
                indicator = tk.Frame(frame, bg="#4a9eff", width=3)
                indicator.place(x=0, y=6, height=32)
            else:
                btn.config(fg="#888888", font=("Segoe UI", 12))
        
        pages = {
            "home": self._show_home_page,
            "news": self._show_news_page,
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
        
        welcome_card = RoundedFrame(self.content_frame, bg="#151515", radius=18)
        welcome_card.pack(fill="x", pady=(0, 20))
        
        welcome_inner = welcome_card.inner_frame
        welcome_content = tk.Frame(welcome_inner, bg="#151515")
        welcome_content.pack(fill="both", padx=24, pady=20)
        
        hour = datetime.now().hour
        greeting = "Доброе утро" if hour < 12 else "Добрый день" if hour < 18 else "Добрый вечер"
        
        tk.Label(welcome_content, text=f"{greeting}, {username}!", font=("Segoe UI", 20, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w")
        tk.Label(welcome_content, text="Готовы к новым приключениям в Minecraft?",
                font=("Segoe UI", 11), bg="#151515", fg="#888888").pack(anchor="w", pady=(4, 0))
        
        selectors_row = tk.Frame(self.content_frame, bg="#0a0a0a")
        selectors_row.pack(fill="x", pady=(0, 20))
        
        version_frame = tk.Frame(selectors_row, bg="#0a0a0a")
        version_frame.pack(side="left", padx=(0, 12))
        
        tk.Label(version_frame, text="Версия", font=("Segoe UI", 10, "bold"),
                bg="#0a0a0a", fg="#888888").pack(anchor="w", pady=(0, 6))
        
        self.version_combo = ModernCombobox(version_frame, values=self.versions, default="Загрузка...", width=200)
        self.version_combo.pack()
        if self.versions:
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            else:
                self.version_combo.set(self.versions[0])
        
        account_frame = tk.Frame(selectors_row, bg="#0a0a0a")
        account_frame.pack(side="left", padx=(12, 0))
        
        tk.Label(account_frame, text="Аккаунт", font=("Segoe UI", 10, "bold"),
                bg="#0a0a0a", fg="#888888").pack(anchor="w", pady=(0, 6))
        
        account_names = [acc["username"] for acc in self._accounts]
        current_acc = self._accounts[self._current_account_index]["username"]
        self.account_combo = ModernCombobox(account_frame, values=account_names, default=current_acc, width=200)
        self.account_combo.pack()
        
        play_btn = RoundedButton(self.content_frame, text="▶ ИГРАТЬ", bg="#4a9eff", fg="#ffffff",
                                 hover_bg="#3a8eef", command=self._launch_selected,
                                 width=180, height=50, radius=14, font_size=12)
        play_btn.pack(pady=(0, 20))
        
        info_row = tk.Frame(self.content_frame, bg="#0a0a0a")
        info_row.pack(fill="both", expand=True)
        
        left_info = tk.Frame(info_row, bg="#0a0a0a")
        left_info.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        info_card1 = RoundedFrame(left_info, bg="#151515", radius=18)
        info_card1.pack(fill="both", expand=True)
        
        info1_inner = info_card1.inner_frame
        info1_content = tk.Frame(info1_inner, bg="#151515")
        info1_content.pack(fill="both", padx=20, pady=20)
        
        tk.Label(info1_content, text="📦", font=("Segoe UI", 32),
                bg="#151515", fg="#4a9eff").pack(anchor="w")
        tk.Label(info1_content, text="Сборки модов", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(info1_content, text="Готовые сборки для любого стиля игры",
                font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w")
        
        right_info = tk.Frame(info_row, bg="#0a0a0a")
        right_info.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        info_card2 = RoundedFrame(right_info, bg="#151515", radius=18)
        info_card2.pack(fill="both", expand=True)
        
        info2_inner = info_card2.inner_frame
        info2_content = tk.Frame(info2_inner, bg="#151515")
        info2_content.pack(fill="both", padx=20, pady=20)
        
        mods_count = len(self._installed_mods)
        tk.Label(info2_content, text="🔧", font=("Segoe UI", 32),
                bg="#151515", fg="#50c878").pack(anchor="w")
        tk.Label(info2_content, text=f"Установлено модов: {mods_count}", font=("Segoe UI", 14, "bold"),
                bg="#151515", fg="#ffffff").pack(anchor="w", pady=(8, 4))
        tk.Label(info2_content, text="Управляйте модами во вкладке Моды",
                font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w")

    def _show_news_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 18))
        
        tk.Label(header, text="Новости версий", font=("Segoe UI", 22, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        tk.Label(header, text="История обновлений Minecraft", font=("Segoe UI", 10),
                bg="#0a0a0a", fg="#888888").pack(side="left", padx=(12, 0))
        
        scroll_frame = ScrollableFrame(self.content_frame, bg="#0a0a0a")
        scroll_frame.pack(fill="both", expand=True)
        
        for news in self._version_news:
            card = RoundedFrame(scroll_frame.scrollable_frame, bg="#151515", radius=18)
            card.pack(fill="x", pady=6)
            
            inner = card.inner_frame
            content = tk.Frame(inner, bg="#151515")
            content.pack(fill="both", padx=22, pady=22)
            
            header_frame = tk.Frame(content, bg="#151515")
            header_frame.pack(fill="x")
            
            type_emoji = "🆕" if news["type"] == "release" else "📸"
            tk.Label(header_frame, text=type_emoji, font=("Segoe UI", 24),
                    bg="#151515").pack(side="left", padx=(0, 12))
            
            text_frame = tk.Frame(header_frame, bg="#151515")
            text_frame.pack(side="left", fill="x", expand=True)
            
            tk.Label(text_frame, text=news["title"], font=("Segoe UI", 14, "bold"),
                    bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(text_frame, text=f"Версия {news['version']} • {news['date']}", font=("Segoe UI", 9),
                    bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(2, 0))
            
            tk.Label(content, text=news["description"], font=("Segoe UI", 10),
                    bg="#151515", fg="#aaaaaa", wraplength=550, justify="left").pack(anchor="w", pady=(12, 0))

    def _show_modpacks_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 18))
        
        tk.Label(header, text="Сборки модов", font=("Segoe UI", 22, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        modpacks = [
            {"name": "Better MC", "version": "1.20.1", "loader": "Forge", 
             "desc": "Улучшенный ванильный опыт с новыми биомами и структурами", "mods": 150},
            {"name": "All The Mods 9", "version": "1.20.1", "loader": "Forge", 
             "desc": "Огромная сборка с 400+ модами для бесконечных возможностей", "mods": 420},
            {"name": "Fabulously Optimized", "version": "1.20.4", "loader": "Fabric", 
             "desc": "Сборка для максимальной производительности и шейдеров", "mods": 45},
            {"name": "RLCraft", "version": "1.12.2", "loader": "Forge", 
             "desc": "Хардкорное выживание с драконами и реалистичной механикой", "mods": 120},
        ]
        
        scroll_frame = ScrollableFrame(self.content_frame, bg="#0a0a0a")
        scroll_frame.pack(fill="both", expand=True)
        
        grid = tk.Frame(scroll_frame.scrollable_frame, bg="#0a0a0a")
        grid.pack(fill="both", expand=True)
        
        for i, pack in enumerate(modpacks):
            card = RoundedFrame(grid, bg="#151515", radius=18)
            card.grid(row=i//2, column=i%2, padx=6, pady=6, sticky="nsew")
            grid.columnconfigure(i%2, weight=1)
            
            inner = card.inner_frame
            content = tk.Frame(inner, bg="#151515")
            content.pack(fill="both", padx=20, pady=20)
            
            tk.Label(content, text=pack["name"], font=("Segoe UI", 15, "bold"),
                    bg="#151515", fg="#ffffff").pack(anchor="w")
            tk.Label(content, text=f"{pack['version']} • {pack['loader']} • {pack['mods']} модов",
                    font=("Segoe UI", 9), bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(2, 8))
            tk.Label(content, text=pack["desc"], font=("Segoe UI", 9),
                    bg="#151515", fg="#888888", wraplength=250, justify="left").pack(anchor="w")
            
            install_btn = RoundedButton(content, text="Установить", bg="#2a2a2a", fg="#ffffff",
                                        hover_bg="#3a3a3a", command=lambda n=pack['name']: self._install_modpack(n),
                                        width=110, height=36, radius=10)
            install_btn.pack(anchor="w", pady=(16, 0))

    def _show_mods_page(self) -> None:
        self._clear_content()
        
        header = tk.Frame(self.content_frame, bg="#0a0a0a")
        header.pack(fill="x", pady=(0, 18))
        
        tk.Label(header, text="Моды", font=("Segoe UI", 22, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(side="left")
        
        open_mods_btn = RoundedButton(header, text="📂 Открыть папку", bg="#2a2a2a", fg="#ffffff",
                                      hover_bg="#3a3a3a", command=lambda: self._open_mods_folder(),
                                      width=140, height=36, radius=10, font_size=10)
        open_mods_btn.pack(side="right")
        
        featured = RoundedFrame(self.content_frame, bg="#151515", radius=18)
        featured.pack(fill="x", pady=(0, 18))
        
        featured_inner = featured.inner_frame
        featured_content = tk.Frame(featured_inner, bg="#151515")
        featured_content.pack(fill="both", padx=22, pady=18)
        
        tk.Label(featured_content, text="🔥 Рекомендуемые моды", font=("Segoe UI", 13, "bold"),
                bg="#151515", fg="#ff6b6b").pack(anchor="w")
        tk.Label(featured_content, text="Популярные моды для улучшения игры",
                font=("Segoe UI", 9), bg="#151515", fg="#888888").pack(anchor="w", pady=(2, 0))
        
        if self._installed_mods:
            scroll_frame = ScrollableFrame(self.content_frame, bg="#0a0a0a")
            scroll_frame.pack(fill="both", expand=True)
            
            cols = tk.Frame(scroll_frame.scrollable_frame, bg="#0a0a0a")
            cols.pack(fill="x", pady=(0, 8))
            
            tk.Label(cols, text="Название", font=("Segoe UI", 10, "bold"),
                    bg="#0a0a0a", fg="#666666", width=35, anchor="w").pack(side="left")
            tk.Label(cols, text="Статус", font=("Segoe UI", 10, "bold"),
                    bg="#0a0a0a", fg="#666666", width=15, anchor="w").pack(side="left")
            
            tk.Frame(scroll_frame.scrollable_frame, bg="#2a2a2a", height=1).pack(fill="x", pady=5)
            
            for mod in self._installed_mods:
                row = tk.Frame(scroll_frame.scrollable_frame, bg="#0a0a0a")
                row.pack(fill="x", pady=3)
                
                name_label = HoverLabel(row, text=mod["name"], font=("Segoe UI", 10),
                                       bg="#0a0a0a", fg="#ffffff", hover_color="#4a9eff",
                                       width=35, anchor="w")
                name_label.pack(side="left")
                
                status_color = "#50c878" if mod["enabled"] else "#ff6b6b"
                status_text = "✓ Включен" if mod["enabled"] else "✗ Отключен"
                tk.Label(row, text=status_text, font=("Segoe UI", 9),
                        bg="#0a0a0a", fg=status_color, width=15, anchor="w").pack(side="left")
        else:
            empty_card = RoundedFrame(self.content_frame, bg="#151515", radius=18)
            empty_card.pack(fill="both", expand=True)
            
            empty_inner = empty_card.inner_frame
            empty_content = tk.Frame(empty_inner, bg="#151515")
            empty_content.pack(expand=True, padx=40, pady=40)
            
            tk.Label(empty_content, text="📦", font=("Segoe UI", 48),
                    bg="#151515", fg="#888888").pack()
            tk.Label(empty_content, text="Нет установленных модов", font=("Segoe UI", 14, "bold"),
                    bg="#151515", fg="#ffffff").pack(pady=(10, 5))
            tk.Label(empty_content, text="Поместите файлы .jar в папку mods",
                    font=("Segoe UI", 10), bg="#151515", fg="#888888").pack()
            
            open_btn = RoundedButton(empty_content, text="Открыть папку модов", bg="#4a9eff", fg="#ffffff",
                                     hover_bg="#3a8eef", command=lambda: self._open_mods_folder(),
                                     width=160, height=40, radius=12)
            open_btn.pack(pady=(20, 0))

    def _open_mods_folder(self):
        mods_dir = os.path.join(self.minecraft_dir, "mods")
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir)
        os.startfile(mods_dir)

    def _show_settings(self) -> None:
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
        
        sections = [
            ("Система", [
                ("Выделение памяти (MB)", "ram_allocation", "spinbox", (512, 16384, 256)),
            ]),
            ("Java", [
                ("Аргументы Java", "java_args", "entry", None),
            ]),
            ("Поведение", [
                ("Закрывать лаунчер при запуске", "close_launcher", "check", None),
            ]),
        ]
        
        self.settings_widgets = {}
        
        for section_name, settings in sections:
            section_frame = tk.Frame(inner, bg="#151515")
            section_frame.pack(fill="x", pady=(0, 20))
            
            tk.Label(section_frame, text=section_name, font=("Segoe UI", 12, "bold"),
                    bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(0, 10))
            
            for label, key, wtype, options in settings:
                row = tk.Frame(section_frame, bg="#151515")
                row.pack(fill="x", pady=4)
                
                tk.Label(row, text=label, font=("Segoe UI", 10),
                        bg="#151515", fg="#aaaaaa", width=30, anchor="w").pack(side="left")
                
                if wtype == "spinbox":
                    var = tk.IntVar(value=self.config.get(key, 2048))
                    spin = tk.Spinbox(row, from_=options[0], to=options[1], increment=options[2],
                                     textvariable=var, bg="#0a0a0a", fg="#ffffff", bd=0,
                                     font=("Segoe UI", 10), width=10)
                    spin.pack(side="left")
                    self.settings_widgets[key] = var
                    
                elif wtype == "entry":
                    var = tk.StringVar(value=self.config.get(key, ""))
                    entry = tk.Entry(row, textvariable=var, bg="#0a0a0a", fg="#ffffff",
                                    font=("Segoe UI", 10), bd=0, width=30)
                    entry.pack(side="left", ipady=6)
                    self.settings_widgets[key] = var
                    
                elif wtype == "check":
                    var = tk.BooleanVar(value=self.config.get(key, False))
                    cb = tk.Checkbutton(row, variable=var, bg="#151515", 
                                       activebackground="#151515", bd=0)
                    cb.pack(side="left")
                    self.settings_widgets[key] = var
        
        folder_frame = tk.Frame(inner, bg="#151515")
        folder_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(folder_frame, text="Папка игры", font=("Segoe UI", 12, "bold"),
                bg="#151515", fg="#4a9eff").pack(anchor="w", pady=(0, 10))
        
        folder_row = tk.Frame(folder_frame, bg="#151515")
        folder_row.pack(fill="x")
        
        tk.Label(folder_row, text=self.minecraft_dir, font=("Segoe UI", 9),
                bg="#151515", fg="#888888").pack(side="left")
        
        open_btn = HoverLabel(folder_row, text="📂 Открыть", font=("Segoe UI", 9),
                             bg="#151515", fg="#4a9eff", hover_color="#ffffff")
        open_btn.pack(side="right")
        open_btn.bind("<Button-1>", lambda e: os.startfile(self.minecraft_dir))
        
        buttons = tk.Frame(inner, bg="#151515")
        buttons.pack(fill="x", pady=(8, 0))
        
        cancel_btn = HoverLabel(buttons, text="Отмена", font=("Segoe UI", 10),
                               bg="#151515", fg="#888888", hover_color="#ffffff")
        cancel_btn.pack(side="right", padx=(12, 0))
        cancel_btn.bind("<Button-1>", lambda e: dialog.destroy())
        
        def save_settings():
            for key, var in self.settings_widgets.items():
                if isinstance(var, tk.IntVar):
                    self.config[key] = var.get()
                elif isinstance(var, tk.StringVar):
                    self.config[key] = var.get()
                elif isinstance(var, tk.BooleanVar):
                    self.config[key] = var.get()
            self._save_config()
            dialog.destroy()
            messagebox.showinfo("Настройки", "Настройки успешно сохранены")
        
        save_btn = RoundedButton(buttons, text="Сохранить", bg="#4a9eff", fg="#ffffff",
                                 hover_bg="#3a8eef", command=save_settings, width=100, height=38, radius=10)
        save_btn.pack(side="right")
        
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _install_modpack(self, name: str) -> None:
        messagebox.showinfo("Установка сборки", 
                           f"Для установки сборки {name} скачайте её с официального сайта\n"
                           "и импортируйте через лаунчер.")

    def _load_versions_async(self) -> None:
        thread = threading.Thread(target=self._load_versions, daemon=True)
        thread.start()

    def _load_versions(self) -> None:
        try:
            manifest = minecraft_launcher_lib.utils.get_version_list()
            versions = [v["id"] for v in manifest if v.get("type") == "release"][:20]
            self.versions = versions
            self.root.after(0, self._update_version_combo)
        except:
            self.versions = ["1.21", "1.20.6", "1.20.5", "1.20.4", "1.20.2", "1.20.1", "1.19.4", "1.19.2", "1.18.2"]
            self.root.after(0, self._update_version_combo)

    def _update_version_combo(self) -> None:
        if hasattr(self, 'version_combo'):
            self.version_combo.update_values(self.versions)
            last = self.config.get("last_version")
            if last in self.versions:
                self.version_combo.set(last)
            elif self.versions:
                self.version_combo.set(self.versions[0])

    def _launch_selected(self) -> None:
        if hasattr(self, 'version_combo') and hasattr(self, 'account_combo'):
            version = self.version_combo.get()
            account_name = self.account_combo.get()
            
            for i, acc in enumerate(self._accounts):
                if acc["username"] == account_name:
                    self._current_account_index = i
                    self.config["last_username"] = account_name
                    self.profile_btn.config(text=f"{account_name} ▼")
                    self._update_profile_menu()
                    break
            
            if version and version != "Загрузка...":
                self._launch_game(account_name, version)

    def _launch_game(self, username: str, version: str) -> None:
        self.config["last_version"] = version
        self._save_config()
        
        if self.config.get("close_launcher", True):
            self.root.iconify()
        
        def install_and_launch():
            try:
                minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                options = {"username": username}
                if self.config.get("ram_allocation"):
                    options["ram"] = str(self.config["ram_allocation"])
                if self.config.get("java_args"):
                    options["java_args"] = self.config["java_args"]
                command = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, options)
                subprocess.Popen(command, cwd=self.minecraft_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка запуска", str(e)))
                self.root.after(0, self.root.deiconify)
        
        threading.Thread(target=install_and_launch, daemon=True).start()


def main():
    root = tk.Tk()
    app = JustLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()