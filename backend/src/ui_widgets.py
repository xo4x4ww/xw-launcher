import tkinter as tk
from tkinter import ttk

class RoundedFrame(tk.Frame):
    def __init__(self, parent, bg="#1a1a1a", radius=16, **kwargs):
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
        r = self.radius
        points = [
            r, 0, w - r, 0, w, 0, w, r,
            w, h - r, w, h, w - r, h, r, h,
            0, h, 0, h - r, 0, r, 0, 0,
        ]
        self.canvas.create_polygon(points, smooth=True, fill=self.bg_color, outline="")


class HoverButton(tk.Label):
    def __init__(self, parent, text, command=None, **kwargs):
        super().__init__(parent, text=text, cursor="hand2", **kwargs)
        self.default_fg = kwargs.get("fg", "#999999")
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


def setup_styles():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
                    fieldbackground="#1e1e1e",
                    background="#1e1e1e",
                    foreground="#ffffff",
                    arrowcolor="#777777",
                    selectbackground="#2a2a2a",
                    selectforeground="#ffffff",
                    bordercolor="#2a2a2a",
                    lightcolor="#1e1e1e",
                    darkcolor="#1e1e1e",
                    insertcolor="#ffffff")
    style.map("Dark.TCombobox",
              fieldbackground=[("readonly", "#1e1e1e"), ("active", "#252525")],
              background=[("readonly", "#1e1e1e"), ("active", "#252525")],
              foreground=[("readonly", "#ffffff"), ("active", "#ffffff")],
              arrowcolor=[("active", "#aaaaaa")])