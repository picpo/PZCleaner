import os
import sys
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, Button
from tkinter import Tk, messagebox, filedialog, Toplevel, ttk, Label

# ================== Config ==================
HEIGHT = 2500  # Y dimension of the map
WIDTH = 3500   # X dimension of the map
TEXT_FILE_NAME = "strings_en.json"  # Change to "strings_en.json" for English
# ============================================

# ---------- Handle PyInstaller resource paths ----------
def resource_path(relative_path):
    """
    Get the path to a resource, works for PyInstaller or normal execution.
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller temporary folder
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- Load language JSON ----------
TEXT_FILE = resource_path(TEXT_FILE_NAME)
with open(TEXT_FILE, "r", encoding="utf-8") as f:
    T = json.load(f)

# ---------- Set Chinese font (Windows) ----------
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # Chinese font
matplotlib.rcParams['axes.unicode_minus'] = False    # Fix minus sign display

# ---------- Select save folder ----------
root = Tk()
root.withdraw()
SAVE_DIR = filedialog.askdirectory(title=T["select_save_title"])
root.destroy()

if not SAVE_DIR:
    print(T["no_folder_selected"])
    exit()

MAP_DIR = os.path.join(SAVE_DIR, "map")
if not os.path.exists(MAP_DIR):
    print(T["map_not_found"])
    exit()

# ---------- Load map grid ----------
def load_grid():
    """
    Traverse map folder and create a grid array with 1s where files exist.
    """
    grid = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    for folder in os.listdir(MAP_DIR):
        folder_path = os.path.join(MAP_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        try:
            x = int(folder)
        except ValueError:
            continue
        if not (0 <= x < WIDTH):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".bin"):
                continue
            try:
                y = int(fname[:-4])
            except ValueError:
                continue
            if not (0 <= y < HEIGHT):
                continue
            grid[y, x] = 1
    return grid

grid = load_grid()

# ---------- Plot grid ----------
fig, ax = plt.subplots(figsize=(14, 10))
im = ax.imshow(grid, cmap="gray", interpolation="nearest", aspect="auto")
ax.set_title(T["main_title"])
selected = [None]

# ---------- Rectangle selection with minimum unit 1 ----------
def onselect(eclick, erelease):
    if eclick.xdata is None or erelease.xdata is None:
        return
    x1 = int(eclick.xdata)
    y1 = int(eclick.ydata)
    x2 = int(erelease.xdata)
    y2 = int(erelease.ydata)
    if x1 == x2:
        x2 = x1 + 1
    if y1 == y2:
        y2 = y1 + 1
    selected[0] = (x1, y1, x2, y2)

rect = RectangleSelector(
    ax,
    onselect,
    useblit=True,
    button=[1],
    interactive=True
)

# ---------- Mouse wheel zoom ----------
def on_scroll(event):
    if event.inaxes != ax or event.xdata is None or event.ydata is None:
        return
    base_scale = 1.2
    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
    scale = 1 / base_scale if event.button == "up" else base_scale
    new_w = (cur_xlim[1] - cur_xlim[0]) * scale
    new_h = (cur_ylim[1] - cur_ylim[0]) * scale
    relx = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
    rely = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])
    ax.set_xlim([event.xdata - new_w * (1 - relx), event.xdata + new_w * relx])
    ax.set_ylim([event.ydata - new_h * (1 - rely), event.ydata + new_h * rely])
    ax.figure.canvas.draw_idle()

fig.canvas.mpl_connect("scroll_event", on_scroll)

# ---------- Delete selected area with GUI progress bar ----------
def delete_clicked(event):
    if selected[0] is None:
        root = Tk(); root.withdraw()
        messagebox.showwarning(T["warning_title"], T["no_area_selected"])
        root.destroy()
        return

    x1, y1, x2, y2 = selected[0]
    xs, xe = sorted([x1, x2])
    ys, ye = sorted([y1, y2])

    # Confirmation message with map coords and game coords (x8)
    msg = T["confirm_message"].format(
        xs=xs, xe=xe, ys=ys, ye=ye,
        rxs=xs * 8, rxe=xe * 8,
        rys=ys * 8, rye=ye * 8
    )

    root = Tk(); root.withdraw()
    ok = messagebox.askyesno(T["confirm_title"], msg)
    root.destroy()
    if not ok:
        return

    # ---------- Prepare GUI progress window ----------
    progress_win = Toplevel()
    progress_win.title("Deleting...")
    progress_label = Label(progress_win, text="Deleting files...")
    progress_label.pack(padx=10, pady=5)
    progress_bar = ttk.Progressbar(progress_win, length=400, mode='determinate')
    progress_bar.pack(padx=10, pady=10)
    progress_win.update()

    # Count total files for progress
    file_list = []
    for x in range(xs, xe + 1):
        col_dir = os.path.join(MAP_DIR, str(x))
        if not os.path.exists(col_dir):
            continue
        for y in range(ys, ye + 1):
            f = os.path.join(col_dir, f"{y}.bin")
            if os.path.exists(f):
                file_list.append(f)

    progress_bar['maximum'] = len(file_list)

    # ---------- Delete files and update progress ----------
    for idx, f in enumerate(file_list, start=1):
        try:
            os.remove(f)
        except:
            pass
        progress_bar['value'] = idx
        progress_win.update()

    # ---------- Close progress window ----------
    progress_win.destroy()

    # ---------- Refresh grid ----------
    grid[:] = load_grid()
    im.set_data(grid)
    ax.figure.canvas.draw_idle()

# ---------- Delete button GUI ----------
btn_ax = plt.axes([0.8, 0.01, 0.18, 0.05])
btn = Button(btn_ax, T["delete_button"])
btn.on_clicked(delete_clicked)

plt.show()
