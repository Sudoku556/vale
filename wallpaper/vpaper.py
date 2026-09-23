#!/usr/bin/env python3
import os
import subprocess

CONFIG_PATH = os.path.expanduser("~/.config/vale/config")
DEFAULT_WALLPAPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vale_wallpaper.png")

MODE_FLAGS = {
    "fill": "--zoom",
    "scale": "--stretch",
    "center": "--center",
}

def load_config():
    cfg = {"WALLPAPER": DEFAULT_WALLPAPER, "WALLPAPER_MODE": "fill"}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if v.strip():
                        cfg[k.strip()] = v.strip()
    return cfg

def set_wallpaper(path, mode="fill"):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        print(f"Vpaper: wallpaper not found: {path}")
        return False
    flag = MODE_FLAGS.get(mode, "--zoom")
    try:
        subprocess.run(["xwallpaper", flag, path], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Vpaper: failed to set wallpaper: {e}")
        return False

if __name__ == "__main__":
    cfg = load_config()
    set_wallpaper(cfg["WALLPAPER"], cfg["WALLPAPER_MODE"])
