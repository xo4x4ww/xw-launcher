import subprocess
import threading
from tkinter import messagebox
import minecraft_launcher_lib

class VersionLoader:
    def __init__(self, root, config):
        self.root = root
        self.config = config

    def load_versions_async(self, callback):
        def worker():
            try:
                manifest = minecraft_launcher_lib.utils.get_version_list()
                vers = [v["id"] for v in manifest if v.get("type") == "release"][:20]
            except:
                vers = ["1.21.11", "1.21", "1.20.6", "1.20.4", "1.20.2", "1.20.1", "1.19.4"]
            self.root.after(0, lambda: callback(vers))
        threading.Thread(target=worker, daemon=True).start()


class GameLauncher:
    def __init__(self, root, config, minecraft_dir):
        self.root = root
        self.config = config
        self.minecraft_dir = minecraft_dir

    def launch(self, version, acc_name, accounts, app):
        # Обновляем текущего пользователя
        for i, acc in enumerate(accounts):
            if acc["username"] == acc_name:
                app._current_account_index = i
                self.config.last_username = acc_name
                break
        self.config.last_version = version
        self.config.save()

        if self.config.get("close_launcher", True):
            self.root.iconify()

        def worker():
            try:
                minecraft_launcher_lib.install.install_minecraft_version(version, self.minecraft_dir)
                opts = {"username": acc_name}
                if self.config.get("ram_allocation"):
                    opts["ram"] = str(self.config.get("ram_allocation"))
                cmd = minecraft_launcher_lib.command.get_minecraft_command(version, self.minecraft_dir, opts)
                subprocess.Popen(cmd, cwd=self.minecraft_dir)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка запуска", str(e)))
                self.root.after(0, self.root.deiconify)

        threading.Thread(target=worker, daemon=True).start()