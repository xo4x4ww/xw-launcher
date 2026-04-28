import os
import re
import tkinter as tk
from pathlib import Path
from config import Config
from ui_widgets import RoundedFrame, HoverButton, setup_styles
from ui_pages import (
    Header, Sidebar, HomePage, NewsPage, ModpacksPage, ModsPage,
    SettingsDialog, AccountsManager
)
from minecraft import VersionLoader, GameLauncher


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XW Launcher")
        self.root.geometry("1000x600")
        self.root.minsize(900, 520)
        self.root.configure(bg="#0d0d0d")

        self.minecraft_dir = os.path.join(str(Path.home()), ".minecraft")
        self.config = Config()
        self.version_loader = VersionLoader(self.root, self.config)
        self.game_launcher = GameLauncher(self.root, self.config, self.minecraft_dir)

        self._accounts = self.config.accounts
        self._current_account_index = 0
        self._current_page = "home"
        self._installed_mods = self._scan_mods()
        self.versions = []

        setup_styles()
        self.version_loader.load_versions_async(self._update_version_combobox)
        self._build_ui()

    def _scan_mods(self):
        mods_dir = os.path.join(self.minecraft_dir, "mods")
        mods = []
        if os.path.exists(mods_dir):
            for f in os.listdir(mods_dir):
                if f.endswith(".jar"):
                    base = f[:-4]                     # удаляем расширение
                    mod_name = base
                    mod_ver = "?"
                    mc_ver = "?"

                    # Шаблон 1: Имя-1.2.3-mc1.20.1 (Forge)
                    m = re.match(r'^(.+?)-(\d+\.\d+(?:\.\d+)?(?:-[^.]*)?)[\-_+]?mc(\d+\.\d+(?:\.\d+)?)$',
                                 base, re.IGNORECASE)
                    if m:
                        mod_name = m.group(1)
                        mod_ver  = m.group(2)
                        mc_ver   = m.group(3)
                    else:
                        # Шаблон 2: Имя-1.2.3+1.20.1 (Fabric / Quilt)
                        m = re.match(r'^(.+?)-(\d+\.\d+(?:\.\d+)?)[+_](\d+\.\d+(?:\.\d+)?)$',
                                     base, re.IGNORECASE)
                        if m:
                            mod_name = m.group(1)
                            mod_ver  = m.group(2)
                            mc_ver   = m.group(3)
                        else:
                            # Шаблон 3: Имя-1.2.3 (только версия мода)
                            m = re.match(r'^(.+?)-(\d+\.\d+(?:\.\d+)?)$', base)
                            if m:
                                mod_name = m.group(1)
                                mod_ver  = m.group(2)
                            # Иначе оставляем значения по умолчанию

                    # Очищаем название: заменяем дефисы и подчёркивания на пробелы, убираем лишние пробелы
                    clean_name = re.sub(r'[-_]+', ' ', mod_name).strip()
                    mods.append({
                        "name": clean_name if clean_name else base,
                        "file": f,
                        "mod_version": mod_ver,
                        "mc_version": mc_ver
                    })
        return mods

    def _update_version_combobox(self, versions):
        self.versions = versions
        if hasattr(self, "home_page") and self.home_page:
            self.home_page.update_versions(versions)

    @property
    def current_account(self):
        return self._accounts[self._current_account_index]

    @property
    def current_username(self):
        return self.current_account["username"]

    def switch_account(self, idx):
        self._current_account_index = idx
        self.config.last_username = self._accounts[idx]["username"]
        self.config.save()
        self._update_profile_ui()
        if hasattr(self, "home_page") and self.home_page:
            self.home_page.update_accounts([a["username"] for a in self._accounts], self._current_account_index)
            self.home_page.refresh_greeting()

    def add_account(self, username):
        self._accounts.append({"username": username})
        self._current_account_index = len(self._accounts) - 1
        self.config.last_username = username
        self.config.accounts = self._accounts
        self.config.save()
        self._update_profile_ui()
        if hasattr(self, "home_page") and self.home_page:
            self.home_page.update_accounts([a["username"] for a in self._accounts], self._current_account_index)
            self.home_page.refresh_greeting()

    def delete_account(self, idx):
        if len(self._accounts) <= 1:
            return False
        del self._accounts[idx]
        if self._current_account_index >= len(self._accounts):
            self._current_account_index = len(self._accounts) - 1
        self.config.last_username = self._accounts[self._current_account_index]["username"]
        self.config.accounts = self._accounts
        self.config.save()
        self._update_profile_ui()
        if hasattr(self, "home_page") and self.home_page:
            self.home_page.update_accounts([a["username"] for a in self._accounts], self._current_account_index)
            self.home_page.refresh_greeting()
        return True

    def _update_profile_ui(self):
        if hasattr(self, "header") and self.header:
            self.header.update_username(self.current_username)

    def _build_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        main = tk.Frame(self.root, bg="#0d0d0d")
        main.pack(fill="both", expand=True, padx=25, pady=20)

        self.header = Header(main, self)
        self.header.pack(fill="x")

        content = tk.Frame(main, bg="#0d0d0d")
        content.pack(fill="both", expand=True, pady=(15, 0))

        self.sidebar = Sidebar(content, self)
        self.sidebar.pack(side="left", fill="y")

        self.content_frame = tk.Frame(content, bg="#0d0d0d")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(20, 0))

        self._show_page("home")

    def _show_page(self, page_key):
        self._current_page = page_key
        self.sidebar.set_active(page_key)
        for w in self.content_frame.winfo_children():
            w.destroy()

        if page_key == "home":
            self.home_page = HomePage(self.content_frame, self)
            self.home_page.pack(fill="both", expand=True)
        elif page_key == "news":
            NewsPage(self.content_frame).pack(fill="both", expand=True)
        elif page_key == "modpacks":
            ModpacksPage(self.content_frame).pack(fill="both", expand=True)
        elif page_key == "mods":
            mods_page = ModsPage(self.content_frame, self)
            mods_page.pack(fill="both", expand=True)