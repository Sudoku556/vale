#!/usr/bin/env python3
import re
import subprocess
import time
import tkinter as tk

PURPLE = "#9b59d0"
BG = "#3a1e5c"
BG_HOVER = "#54277f"
FG = "#ffffff"
BAR_HEIGHT = 46

def list_windows():
    try:
        out = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "."],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()
        ids = [i for i in out.splitlines() if i]
    except Exception:
        return []

    windows = []
    for wid in ids:
        try:
            name = subprocess.run(
                ["xdotool", "getwindowname", wid],
                capture_output=True, text=True, timeout=2
            ).stdout.strip()
        except Exception:
            continue
        if not name or name in ("Vale Launcher", "Vale Settings", "Vale Panel"):
            continue
        windows.append((wid, name))
    return windows

def get_volume():
    try:
        out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                              capture_output=True, text=True, timeout=2).stdout
        m = re.search(r'(\d+)%', out)
        vol = int(m.group(1)) if m else 0
        mute_out = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                                   capture_output=True, text=True, timeout=2).stdout
        muted = "yes" in mute_out.lower()
        return vol, muted
    except Exception:
        return 0, False

def change_volume(delta):
    sign = "+" if delta > 0 else ""
    subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{sign}{delta}%"])

def toggle_mute():
    subprocess.Popen(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])

def activate_window(wid):
    subprocess.Popen(["xdotool", "windowactivate", wid])

def launch_launcher():
    subprocess.Popen(
        ["python3", "/home/babi/vale/launcher/vale-launcher.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def launch_settings():
    subprocess.Popen(
        ["python3", "/home/babi/vale/settings/vale-settings.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def logout():
    subprocess.Popen(["sh", "-c",
        "pkill vwin; pkill -f vale-panel.py; pkill -f vale-launcher.py; "
        "pkill -f vale-settings.py; pkill -f vpaper.py"])

class Panel:
    def __init__(self, root):
        self.root = root
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()

        root.title("Vale Panel")
        root.overrideredirect(True)
        root.geometry(f"{w}x{BAR_HEIGHT}+0+{h - BAR_HEIGHT}")
        root.configure(bg=BG)
        root.attributes("-topmost", True)

        self.bar = tk.Frame(root, bg=BG, height=BAR_HEIGHT)
        self.bar.pack(fill="both", expand=True)

        self.vale_btn = tk.Label(
            self.bar, text=" V ", bg=BG, fg=FG,
            font=("Sans", 16, "bold"), padx=14
        )
        self.vale_btn.pack(side="left", fill="y")
        self.vale_btn.bind("<Button-1>", lambda e: launch_launcher())
        self._add_hover(self.vale_btn)

        self.win_frame = tk.Frame(self.bar, bg=BG)
        self.win_frame.pack(side="left", fill="y", padx=6)

        self.settings_btn = tk.Label(
            self.bar, text="⚙", bg=BG, fg=FG, font=("Sans", 14), padx=12
        )
        self.settings_btn.pack(side="right", fill="y")
        self.settings_btn.bind("<Button-1>", lambda e: launch_settings())
        self._add_hover(self.settings_btn)

        self.logout_btn = tk.Label(
            self.bar, text="⏻", bg=BG, fg=FG, font=("Sans", 14), padx=12
        )
        self.logout_btn.pack(side="right", fill="y")
        self.logout_btn.bind("<Button-1>", lambda e: logout())
        self._add_hover(self.logout_btn)

        self.volume_label = tk.Label(
            self.bar, text="", bg=BG, fg=FG, font=("Sans", 13), padx=12
        )
        self.volume_label.pack(side="right", fill="y")
        self.volume_label.bind("<Button-1>", lambda e: (toggle_mute(), self.tick_volume()))
        self.volume_label.bind("<Button-4>", lambda e: (change_volume(5), self.root.after(150, self.tick_volume)))
        self.volume_label.bind("<Button-5>", lambda e: (change_volume(-5), self.root.after(150, self.tick_volume)))
        self._add_hover(self.volume_label)

        self.clock_label = tk.Label(
            self.bar, text="", bg=BG, fg=FG, font=("Sans", 13, "bold"), padx=14
        )
        self.clock_label.pack(side="right", fill="y")

        self.refresh_windows()
        self.tick_clock()
        self.tick_volume()

    def _add_hover(self, widget):
        widget.bind("<Enter>", lambda e: widget.config(bg=BG_HOVER))
        widget.bind("<Leave>", lambda e: widget.config(bg=BG))

    def refresh_windows(self):
        for child in self.win_frame.winfo_children():
            child.destroy()
        for wid, name in list_windows():
            label = (name[:22] + "…") if len(name) > 22 else name
            btn = tk.Label(
                self.win_frame, text=label, bg=BG, fg=FG,
                font=("Sans", 11), padx=10
            )
            btn.pack(side="left", fill="y", padx=(0, 2))
            btn.bind("<Button-1>", lambda e, w=wid: activate_window(w))
            self._add_hover(btn)
        self.root.after(2000, self.refresh_windows)

    def tick_volume(self):
        vol, muted = get_volume()
        if muted:
            icon = "🔇"
        elif vol == 0:
            icon = "🔈"
        elif vol < 50:
            icon = "🔉"
        else:
            icon = "🔊"
        self.volume_label.config(text=f"{icon} {vol}%")
        self.root.after(3000, self.tick_volume)

    def tick_clock(self):
        self.clock_label.config(text=time.strftime("%H:%M"))
        self.root.after(1000, self.tick_clock)

if __name__ == "__main__":
    root = tk.Tk()
    Panel(root)
    root.mainloop()
