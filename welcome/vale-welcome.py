#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import ttk

BG = "#1a1a24"
PANEL_BG = "#232333"
FG = "#e6e6e6"
MARKER = os.path.expanduser("~/.config/vale/.welcomed")


def rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_vailo(canvas, ox=0, oy=0, scale=1.0):
    def X(x): return ox + x * scale
    def Y(y): return oy + y * scale
    def S(s): return max(1, int(s * scale))

    canvas.create_oval(X(115), Y(295), X(265), Y(315), fill="#2a2a3a", outline="")

    for (x1, y1, x2, y2) in [(150, 90, 150, 68), (190, 90, 190, 62), (230, 90, 230, 68)]:
        canvas.create_line(X(x1), Y(y1), X(x2), Y(y2), fill="#6b3491", width=S(3), capstyle=tk.ROUND)

    for (cx, cy, r, color) in [(150, 64, 9, "#ff757f"), (190, 58, 10, "#41a6b5"), (230, 64, 9, "#ffc777")]:
        canvas.create_oval(X(cx - r), Y(cy - r), X(cx + r), Y(cy + r), fill=color, outline="")

    for (x1, y1, x2, y2) in [(150, 258, 150, 288), (210, 258, 210, 288)]:
        canvas.create_line(X(x1), Y(y1), X(x2), Y(y2), fill="#7c3fa1", width=S(22), capstyle=tk.ROUND)
    for (cx, cy) in [(150, 292), (210, 292)]:
        canvas.create_oval(X(cx - 16), Y(cy - 8), X(cx + 16), Y(cy + 8), fill="#6b3491", outline="")

    canvas.create_line(X(120), Y(200), X(85), Y(235), fill="#8a4bc4", width=S(22), capstyle=tk.ROUND)
    canvas.create_oval(X(71), Y(221), X(99), Y(249), fill="#8a4bc4", outline="")
    canvas.create_line(X(260), Y(190), X(305), Y(130), fill="#8a4bc4", width=S(22), capstyle=tk.ROUND)
    canvas.create_oval(X(291), Y(116), X(319), Y(144), fill="#8a4bc4", outline="")

    rounded_rect(canvas, X(110), Y(90), X(270), Y(260), S(40), fill="#9b59d0", outline="#6b3491", width=S(3))

    canvas.create_oval(X(139), Y(129), X(171), Y(161), fill="#ffffff", outline="")
    canvas.create_oval(X(209), Y(129), X(241), Y(161), fill="#ffffff", outline="")
    canvas.create_oval(X(151), Y(141), X(165), Y(155), fill="#3a1f4d", outline="")
    canvas.create_oval(X(221), Y(141), X(235), Y(155), fill="#3a1f4d", outline="")
    canvas.create_oval(X(153), Y(142), X(157), Y(146), fill="#ffffff", outline="")
    canvas.create_oval(X(223), Y(142), X(227), Y(146), fill="#ffffff", outline="")

    canvas.create_line(X(165), Y(172), X(190), Y(190), X(215), Y(172),
                        smooth=True, fill="#3a1f4d", width=S(5), capstyle=tk.ROUND)

    canvas.create_line(X(165), Y(205), X(190), Y(235), X(215), Y(205),
                        fill="#ffffff", width=S(12), capstyle=tk.ROUND, joinstyle=tk.ROUND)


class VailoWelcome:
    def __init__(self, root, first_run):
        self.root = root
        root.configure(bg=BG)
        if first_run:
            self.build_first_run()
        else:
            self.build_browser()

    def build_first_run(self):
        w, h = 480, 480
        self.root.overrideredirect(True)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.canvas = tk.Canvas(self.root, width=w, height=h, bg=BG, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.advance)

        self.messages = [
            "Hi! I'm Vailo.\nWelcome to Vale.",
            "This is your desktop.\nMake yourself comfortable.",
            "Vwin handles your windows.\nVpaper has your wallpaper.\nAnd I'm here so things\ndon't get boring.",
        ]
        self.msg_index = 0
        self.scale = 0.0
        self.animate_grow()

    def animate_grow(self):
        self.scale += 0.12
        s = min(self.scale, 1.0)
        self.canvas.delete("all")
        ox = 240 - 190 * s
        draw_vailo(self.canvas, ox=ox, oy=60, scale=s)
        self.text_id = self.canvas.create_text(240, 400, text="", fill=FG, font=("Sans", 14), justify="center")
        self.hint_id = self.canvas.create_text(240, 455, text="", fill="#8888aa", font=("Sans", 10))
        if s < 1.0:
            self.root.after(25, self.animate_grow)
        else:
            self.show_message()

    def show_message(self):
        self.canvas.itemconfig(self.text_id, text=self.messages[self.msg_index])
        last = self.msg_index == len(self.messages) - 1
        self.canvas.itemconfig(self.hint_id, text="click to finish" if last else "click to continue")

    def advance(self, event):
        self.msg_index += 1
        if self.msg_index >= len(self.messages):
            self.finish()
        else:
            self.show_message()

    def finish(self):
        os.makedirs(os.path.dirname(MARKER), exist_ok=True)
        with open(MARKER, "w") as f:
            f.write("1\n")
        self.root.destroy()

    def build_browser(self):
        self.root.title("Vale Welcome")
        self.root.geometry("520x420")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

        tabs = {
            "Welcome": "Welcome to Vale \u2014 a desktop environment\nbuilt from scratch, window manager and all.",
            "About Vale": "Vale is a custom X11 desktop environment.\nWM: Vwin. Wallpaper: Vpaper.\nBuilt piece by piece, from spec, not copied.",
            "Shortcuts": (
                "Super \u2014 open launcher\n"
                "Alt + left-drag \u2014 move window\n"
                "Alt + right-drag \u2014 resize window\n"
                "Drag window edges/corners \u2014 resize\n"
                "Volume keys \u2014 adjust volume\n"
                "Print Screen \u2014 screenshot to ~/Pictures"
            ),
            "Components": (
                "Vwin \u2014 the window manager\n"
                "Vpaper \u2014 wallpaper tool\n"
                "Vale Panel \u2014 taskbar, volume, power\n"
                "Vale Launcher \u2014 app launcher (Super key)\n"
                "Vale Settings \u2014 splash style, wallpaper\n"
                "Vailo \u2014 that's me!"
            ),
        }
        for name, text in tabs.items():
            frame = tk.Frame(nb, bg=PANEL_BG)
            nb.add(frame, text=name)
            tk.Label(frame, text=text, bg=PANEL_BG, fg=FG, font=("Sans", 12),
                     justify="left", anchor="nw").pack(padx=20, pady=20, anchor="w")

        vailo_frame = tk.Frame(nb, bg=BG)
        nb.add(vailo_frame, text="Meet Vailo")
        vcanvas = tk.Canvas(vailo_frame, width=380, height=355, bg=BG, highlightthickness=0)
        vcanvas.pack(pady=10)
        draw_vailo(vcanvas, ox=0, oy=0, scale=1.0)
        tk.Label(vailo_frame, text="Hi, I'm Vailo. I live here now.",
                 bg=BG, fg=FG, font=("Sans", 12)).pack()


if __name__ == "__main__":
    first_run = "--first-run" in sys.argv
    if first_run and os.path.exists(MARKER):
        sys.exit(0)
    root = tk.Tk()
    VailoWelcome(root, first_run)
    root.mainloop()
