import tkinter as tk
from app import LauncherApp

def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()