#!/usr/bin/env python3
import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog

CONFIG_PATH = os.path.expanduser("~/.config/vale/config")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VPAPER_PATH = os.path.join(BASE_DIR, "wallpaper", "vpaper.py")
SPLASH_PATH = os.path.join(BASE_DIR, "splash", "vale-splash.py")
DEFAULT_WALLPAPER = os.path.join(BASE_DIR, "wallpaper", "vale_wallpaper.png")
PURPLE = "#9b59d0"
BG = "#1e1e2e"

def load_config():
    cfg = {"SPLASH_STYLE": "wordmark", "WALLPAPER": DEFAULT_WALLPAPER, "WALLPAPER_MODE": "fill"}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        for k, v in cfg.items():
            f.write(f"{k}={v}\n")

class Settings:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()

        root.title("Vale Settings")
        root.geometry("420x420")
        root.configure(bg=BG)

        tk.Label(root, text="Vale Settings", font=("Sans", 18, "bold"),
                 bg=BG, fg=PURPLE).pack(pady=(20, 10))

        frame = tk.Frame(root, bg=BG)
        frame.pack(pady=5, padx=20, fill="x")
        tk.Label(frame, text="Splash screen style:", bg=BG, fg="white", font=("Sans", 11)).pack(anchor="w")
        self.style_var = tk.StringVar(value=self.cfg.get("SPLASH_STYLE", "wordmark"))
        ttk.Combobox(frame, textvariable=self.style_var, values=["wordmark", "throbber"], state="readonly").pack(fill="x", pady=(3, 0))
        tk.Button(frame, text="Test Splash", command=self.test_splash, bg="#3b3b52", fg="white",
                  relief="flat", font=("Sans", 10), padx=10).pack(anchor="e", pady=(6, 0))

        wp_frame = tk.Frame(root, bg=BG)
        wp_frame.pack(pady=5, padx=20, fill="x")
        tk.Label(wp_frame, text="Wallpaper (Vpaper):", bg=BG, fg="white", font=("Sans", 11)).pack(anchor="w")
        wp_sub = tk.Frame(wp_frame, bg=BG)
        wp_sub.pack(fill="x", pady=(3, 0))
        self.wp_var = tk.StringVar(value=self.cfg.get("WALLPAPER", DEFAULT_WALLPAPER))
        tk.Entry(wp_sub, textvariable=self.wp_var, font=("Sans", 10), bg="#2a2a3c", fg="white",
                 insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        tk.Button(wp_sub, text="Browse", command=self.browse_wallpaper, bg="#3b3b52", fg="white",
                  relief="flat", font=("Sans", 10), padx=10).pack(side="right")

        mode_frame = tk.Frame(root, bg=BG)
        mode_frame.pack(pady=5, padx=20, fill="x")
        tk.Label(mode_frame, text="Wallpaper scaling mode:", bg=BG, fg="white", font=("Sans", 11)).pack(anchor="w")
        self.mode_var = tk.StringVar(value=self.cfg.get("WALLPAPER_MODE", "fill"))
        ttk.Combobox(mode_frame, textvariable=self.mode_var, values=["fill", "scale", "center"], state="readonly").pack(fill="x", pady=(3, 0))

        tk.Button(root, text="Save", command=self.save, bg=PURPLE, fg="white",
                  relief="flat", font=("Sans", 12), padx=20, pady=6).pack(pady=12)
        self.status = tk.Label(root, text="", bg=BG, fg="#8be89b", font=("Sans", 10))
        self.status.pack()

    def test_splash(self):
        subprocess.Popen(["python3", SPLASH_PATH, self.style_var.get()],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def browse_wallpaper(self):
        filename = filedialog.askopenfilename(
            title="Select Wallpaper",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")]
        )
        if filename:
            self.wp_var.set(filename)

    def save(self):
        self.cfg["SPLASH_STYLE"] = self.style_var.get()
        self.cfg["WALLPAPER"] = self.wp_var.get().strip()
        self.cfg["WALLPAPER_MODE"] = self.mode_var.get().strip()
        save_config(self.cfg)

        ok = False
        try:
            subprocess.run(["python3", VPAPER_PATH], check=True, timeout=5)
            ok = True
        except Exception:
            ok = False

        self.status.config(text="Saved & applied!" if ok else "Saved. (Vpaper apply failed - is xwallpaper installed?)")

if __name__ == "__main__":
    root = tk.Tk()
    Settings(root)
    root.mainloop()
