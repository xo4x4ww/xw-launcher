import json
from pathlib import Path

class Config:
    def __init__(self):
        self.path = Path(__file__).with_name("launcher_config.json")
        self.data = self._load()

    def _load(self):
        default = {
            "last_username": "Player",
            "last_version": "",
            "accounts": [{"username": "Player"}],
            "ram_allocation": 2048,
            "close_launcher": True,
        }
        if not self.path.exists():
            return default
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            default.update(saved)
            if not default.get("accounts"):
                default["accounts"] = [{"username": "Player"}]
        except:
            pass
        return default

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except:
            pass

    @property
    def accounts(self):
        return self.data["accounts"]

    @accounts.setter
    def accounts(self, value):
        self.data["accounts"] = value

    @property
    def last_username(self):
        return self.data["last_username"]

    @last_username.setter
    def last_username(self, value):
        self.data["last_username"] = value

    @property
    def last_version(self):
        return self.data["last_version"]

    @last_version.setter
    def last_version(self, value):
        self.data["last_version"] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value