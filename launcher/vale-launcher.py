#!/usr/bin/env python3
import os
import subprocess
import tkinter as tk
import io

APP_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]

ICON_SEARCH_DIRS = [
    "/usr/share/icons/breeze/apps/32",
    "/usr/share/icons/breeze/apps/48",
    "/usr/share/icons/hicolor/32x32/apps",
    "/usr/share/icons/hicolor/48x48/apps",
    "/usr/share/icons/hicolor/scalable/apps",
    "/usr/share/pixmaps",
]

BG = "#1e1e2e"
BG_HOVER = "#3a3a52"
FG = "#e6e6e6"

_icon_cache = {}

def find_icon_file(icon_name):
    if not icon_name:
        return None
    if os.path.isabs(icon_name) and os.path.exists(icon_name):
        return icon_name
    for d in ICON_SEARCH_DIRS:
        for ext in (".png", ".svg"):
            p = os.path.join(d, icon_name + ext)
            if os.path.exists(p):
                return p
    return None

def load_icon(icon_name):
    if icon_name in _icon_cache:
        return _icon_cache[icon_name]
    path = find_icon_file(icon_name)
    photo = None
    if path:
        try:
            if path.endswith(".svg"):
                import cairosvg
                png_bytes = cairosvg.svg2png(url=path, output_width=28, output_height=28)
                photo = tk.PhotoImage(data=png_bytes)
            else:
                photo = tk.PhotoImage(file=path)
                w, h = photo.width(), photo.height()
                if w > 32:
                    factor = max(1, w // 28)
                    photo = photo.subsample(factor, factor)
        except Exception:
            photo = None
    _icon_cache[icon_name] = photo
    return photo

def parse_desktop_file(path):
    name = None
    exec_cmd = None
    icon = None
    no_display = False
    try:
        with open(path, "r", errors="ignore") as f:
            in_entry = False
            for line in f:
                line = line.strip()
                if line == "[Desktop Entry]":
                    in_entry = True
                    continue
                if line.startswith("[") and line != "[Desktop Entry]":
                    in_entry = False
                    continue
                if not in_entry:
                    continue
                if line.startswith("Name=") and name is None:
                    name = line[len("Name="):]
                elif line.startswith("Exec="):
                    exec_cmd = line[len("Exec="):]
                    exec_cmd = " ".join(p for p in exec_cmd.split() if not p.startswith("%"))
                elif line.startswith("Icon=") and icon is None:
                    icon = line[len("Icon="):]
                elif line.startswith("NoDisplay=true"):
                    no_display = True
    except OSError:
        return None
    if name and exec_cmd and not no_display:
        return (name, exec_cmd, icon)
    return None

def scan_apps():
    apps = {}
    for d in APP_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname.endswith(".desktop"):
                result = parse_desktop_file(os.path.join(d, fname))
                if result:
                    apps[result[0]] = (result[1], result[2])
    return sorted(apps.items())

class Launcher:
    def __init__(self, root):
        self.root = root
        self.apps = scan_apps()
        self.icon_refs = []
        self.selected_index = 0
        self.row_widgets = []

        root.title("Vale Launcher")
        root.geometry("480x420+400+280")
        root.configure(bg=BG)

        self.entry = tk.Entry(root, font=("Sans", 14), bg="#2a2a3a", fg="white",
                               insertbackground="white", relief="flat")
        self.entry.pack(fill="x", padx=10, pady=10, ipady=4)
        self.entry.bind("<KeyRelease>", self.on_key)
        self.entry.bind("<Return>", lambda e: self.launch_selected())
        self.entry.bind("<Escape>", lambda e: root.destroy())
        self.entry.bind("<Down>", lambda e: self.move_selection(1))
        self.entry.bind("<Up>", lambda e: self.move_selection(-1))

        canvas_frame = tk.Frame(root, bg=BG)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(canvas_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=BG)

        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.filtered = []
        self.refresh_list("")
        self.entry.focus_set()

    def refresh_list(self, query):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.row_widgets = []
        self.icon_refs = []

        q = query.lower()
        self.filtered = [a for a in self.apps if q in a[0].lower()]
        self.selected_index = 0

        for i, (name, (exec_cmd, icon_name)) in enumerate(self.filtered):
            row = tk.Frame(self.list_frame, bg=BG, cursor="hand2")
            row.pack(fill="x", pady=1)

            photo = load_icon(icon_name)
            if photo:
                self.icon_refs.append(photo)
                icon_lbl = tk.Label(row, image=photo, bg=BG, width=32)
            else:
                icon_lbl = tk.Label(row, text="  ", bg=BG, width=4)
            icon_lbl.pack(side="left", padx=(6, 8), pady=4)

            text_lbl = tk.Label(row, text=name, bg=BG, fg=FG, font=("Sans", 12), anchor="w")
            text_lbl.pack(side="left", fill="x", expand=True, pady=4)

            for widget in (row, icon_lbl, text_lbl):
                widget.bind("<Button-1>", lambda e, idx=i: self.launch_index(idx))
                widget.bind("<Enter>", lambda e, idx=i: self.highlight_row(idx))

            self.row_widgets.append(row)

        if self.row_widgets:
            self.highlight_row(0)

    def highlight_row(self, idx):
        for i, row in enumerate(self.row_widgets):
            bg = BG_HOVER if i == idx else BG
            row.configure(bg=bg)
            for child in row.winfo_children():
                child.configure(bg=bg)
        self.selected_index = idx

    def move_selection(self, delta):
        if not self.row_widgets:
            return
        new_idx = max(0, min(len(self.row_widgets) - 1, self.selected_index + delta))
        self.highlight_row(new_idx)
        self.canvas.yview_moveto(new_idx / max(1, len(self.row_widgets)))

    def on_key(self, event):
        if event.keysym in ("Down", "Up", "Return"):
            return
        self.refresh_list(self.entry.get())

    def launch_index(self, idx):
        if idx >= len(self.filtered):
            return
        _, (exec_cmd, _icon) = self.filtered[idx]
        subprocess.Popen(exec_cmd, shell=True, start_new_session=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.root.destroy()

    def launch_selected(self):
        self.launch_index(self.selected_index)

if __name__ == "__main__":
    root = tk.Tk()
    Launcher(root)
    root.mainloop()
