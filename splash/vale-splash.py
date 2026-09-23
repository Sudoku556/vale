#!/usr/bin/env python3
import os
import tkinter as tk

CONFIG_PATH = os.path.expanduser("~/.config/vale/config")
PURPLE = "#9b59d0"
BG = "#0d0d12"
BAR_BG = "#2a2a35"

def load_config():
    cfg = {"SPLASH_STYLE": "wordmark"}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg

def draw_v(canvas, cx, cy, size, color):
    half = size / 2
    thick = size * 0.24
    points = [
        cx - half, cy - half,
        cx - half + thick, cy - half,
        cx, cy + half - thick * 0.4,
        cx + half - thick, cy - half,
        cx + half, cy - half,
        cx + thick * 0.35, cy + half,
        cx - thick * 0.35, cy + half,
    ]
    canvas.create_polygon(points, fill=color, outline="")

class Splash:
    def __init__(self, root, style):
        self.root = root
        self.style = style
        self.angle = 0
        self.bar_pos = 0

        root.attributes("-fullscreen", True)
        root.overrideredirect(True)
        root.configure(bg=BG)

        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        self.canvas = tk.Canvas(root, width=w, height=h, bg=BG, highlightthickness=0)
        self.canvas.pack()

        cx, cy = w // 2, h // 2

        if style == "throbber":
            draw_v(self.canvas, cx, cy - 60, 140, PURPLE)
            self.arc = self.canvas.create_arc(
                cx - 40, cy + 110, cx + 40, cy + 190,
                start=0, extent=100, style="arc", outline=PURPLE, width=6
            )
            self.animate_throbber()
        else:
            # V logo and "Vale" text side by side, vertically centered together
            logo_size = 90
            gap = 24
            text_font = ("Sans", 40, "bold")

            # measure text width first so the pair can be centered as one unit
            temp_id = self.canvas.create_text(0, 0, text="Vale", font=text_font)
            bbox = self.canvas.bbox(temp_id)
            text_w = bbox[2] - bbox[0]
            self.canvas.delete(temp_id)

            total_w = logo_size + gap + text_w
            start_x = cx - total_w // 2

            logo_cx = start_x + logo_size // 2
            draw_v(self.canvas, logo_cx, cy, logo_size, PURPLE)

            text_x = start_x + logo_size + gap
            self.canvas.create_text(
                text_x, cy, text="Vale", fill=PURPLE,
                font=text_font, anchor="w"
            )

            # fedora-style loading bar underneath
            bar_w, bar_h = 260, 4
            bar_x = cx - bar_w // 2
            bar_y = cy + 90
            self.canvas.create_rectangle(
                bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                fill=BAR_BG, outline=""
            )
            self.bar_x = bar_x
            self.bar_y = bar_y
            self.bar_w = bar_w
            self.bar_h = bar_h
            self.chunk_w = 70
            self.chunk = self.canvas.create_rectangle(
                bar_x, bar_y, bar_x + self.chunk_w, bar_y + bar_h,
                fill=PURPLE, outline=""
            )
            self.animate_bar()

        root.after(2500, root.destroy)

    def animate_throbber(self):
        self.angle = (self.angle + 12) % 360
        self.canvas.itemconfig(self.arc, start=self.angle)
        self.root.after(30, self.animate_throbber)

    def animate_bar(self):
        self.bar_pos = (self.bar_pos + 8) % (self.bar_w + self.chunk_w)
        x0 = self.bar_x - self.chunk_w + self.bar_pos
        x1 = x0 + self.chunk_w
        # clip chunk so it doesn't visually spill outside the track
        clipped_x0 = max(x0, self.bar_x)
        clipped_x1 = min(x1, self.bar_x + self.bar_w)
        if clipped_x1 > clipped_x0:
            self.canvas.coords(self.chunk, clipped_x0, self.bar_y, clipped_x1, self.bar_y + self.bar_h)
        else:
            self.canvas.coords(self.chunk, 0, 0, 0, 0)
        self.root.after(20, self.animate_bar)

if __name__ == "__main__":
    import sys
    cfg = load_config()
    style = sys.argv[1] if len(sys.argv) > 1 else cfg.get("SPLASH_STYLE", "wordmark")
    root = tk.Tk()
    Splash(root, style)
    root.mainloop()
