# (Modified) stickfigureanimation.py
# - Adds viewport modes: 'full', 'half', 'stick-figure'
# - Computes a viewport for each frame based on mode/padding/min size
# - draw_frame_on_canvas and draw_frame_to_image now crop/draw using viewport
# - run_animation_gui exposes controls to select mode/padding/min size
#
# Comments explain key steps so others can extend/maintain.

import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw
import imageio
import math


class StickFigureAnimation:
    def __init__(self):
        self.frames = []         # List of dicts: each dict is a stick figure frame
        self.timings = []        # List of durations (milliseconds) for each frame
        self.backgrounds = []    # List of backgrounds for each frame (can be None)
        self.frame_names = []    # List of JSON file names for each frame
        self.background_names = []  # List of background JSON file names
        self.grid_width = None
        self.grid_height = None
        self.default_color = 0
        self.cell_size = 10  # Initial cell size

        # Viewport controls (defaults keep old behaviour)
        # mode: 'full' (entire frame grid), 'half' (center half-size viewport), 'stick-figure' (auto crop to content)
        self.viewport_mode = 'full'
        self.viewport_padding = 2   # padding in cells around bounding box (for 'stick-figure')
        self.viewport_min_w = 16    # minimum viewport width in cells
        self.viewport_min_h = 16    # minimum viewport height in cells

    def add_frame_from_json(self, stick_figure_json, duration=200, background_json=None):
        with open(stick_figure_json, 'r') as f:
            frame_data = json.load(f)
        self.frames.append(frame_data)
        self.frame_names.append(stick_figure_json.split("/")[-1])
        self.timings.append(int(duration))
        if background_json:
            with open(background_json, 'r') as bgf:
                bg_data = json.load(bgf)
            self.backgrounds.append(bg_data)
            self.background_names.append(background_json.split("/")[-1])
        else:
            self.backgrounds.append(None)
            self.background_names.append("")
        self.grid_width = frame_data.get('grid_width', self.grid_width)
        self.grid_height = frame_data.get('grid_height', self.grid_height)
        self.default_color = frame_data.get('default_color', self.default_color)

    def load_animation_from_jsons(self, json_files, timings=None, background_jsons=None):
        self.frames = []
        self.timings = []
        self.backgrounds = []
        self.frame_names = []
        self.background_names = []
        for i, json_file in enumerate(json_files):
            with open(json_file, "r") as f:
                frame_data = json.load(f)
            self.frames.append(frame_data)
            self.frame_names.append(json_file.split("/")[-1])
            self.grid_width = frame_data.get('grid_width', self.grid_width)
            self.grid_height = frame_data.get('grid_height', self.grid_height)
            self.default_color = frame_data.get('default_color', self.default_color)
            if timings and i < len(timings):
                self.timings.append(int(timings[i]))
            else:
                self.timings.append(200)
            if background_jsons and i < len(background_jsons) and background_jsons[i]:
                with open(background_jsons[i], 'r') as bgf:
                    bg_data = json.load(bgf)
                self.backgrounds.append(bg_data)
                self.background_names.append(background_jsons[i].split("/")[-1])
            else:
                self.backgrounds.append(None)
                self.background_names.append("")

    def save_animation(self, filename):
        animation_data = {
            "frames": self.frames,
            "timings": self.timings,
            "backgrounds": self.backgrounds,
            "frame_names": self.frame_names,
            "background_names": self.background_names,
            "viewport_mode": self.viewport_mode,
            "viewport_padding": self.viewport_padding,
            "viewport_min_w": self.viewport_min_w,
            "viewport_min_h": self.viewport_min_h
        }
        with open(filename, "w") as f:
            json.dump(animation_data, f, indent=2)

    def load_animation(self, filename):
        with open(filename, "r") as f:
            data = json.load(f)
        self.frames = data["frames"]
        self.timings = data["timings"]
        self.backgrounds = data.get("backgrounds", [None]*len(self.frames))
        self.frame_names = data.get("frame_names", [f"Frame_{i+1}.json" for i in range(len(self.frames))])
        self.background_names = data.get("background_names", [""]*len(self.frames))
        # load viewport settings if present
        self.viewport_mode = data.get("viewport_mode", self.viewport_mode)
        self.viewport_padding = data.get("viewport_padding", self.viewport_padding)
        self.viewport_min_w = data.get("viewport_min_w", self.viewport_min_w)
        self.viewport_min_h = data.get("viewport_min_h", self.viewport_min_h)

        self.grid_width = self.frames[0].get('grid_width', self.grid_width)
        self.grid_height = self.frames[0].get('grid_height', self.grid_height)
        self.default_color = self.frames[0].get('default_color', self.default_color)

    def hex_to_rgb(hex_color):
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        return tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    # ---------- VIEWPORT CALCULATION ----------
    def compute_viewport(self, frame, mode=None, padding=None, min_w=None, min_h=None):
        """
        Compute (x0, y0, w, h) viewport in grid cell coordinates for given frame.
        mode: 'full', 'half', 'stick-figure'
        padding: integer padding (cells) to add around bounding box
        min_w/min_h: minimum width/height of viewport
        """
        mode = mode or self.viewport_mode
        padding = self.viewport_padding if padding is None else padding
        min_w = self.viewport_min_w if min_w is None else min_w
        min_h = self.viewport_min_h if min_h is None else min_h

        gw = frame.get('grid_width', self.grid_width)
        gh = frame.get('grid_height', self.grid_height)
        if mode == 'full':
            return (0, 0, gw, gh)
        elif mode == 'half':
            # Center a half-sized viewport (rounded)
            w = max(1, gw // 2)
            h = max(1, gh // 2)
            x0 = max(0, (gw - w) // 2)
            y0 = max(0, (gh - h) // 2)
            return (x0, y0, w, h)
        elif mode == 'stick-figure':
            # Compute bounding box of all non-default boxes in frame (and optionally background)
            boxes = frame.get('boxes', {})
            default_color = frame.get('default_color', self.default_color)
            # Collect coordinates where value != default_color
            xs, ys = [], []
            for key, val in boxes.items():
                try:
                    r, c = map(int, key.split(","))
                except Exception:
                    continue
                if val != default_color:
                    xs.append(c)
                    ys.append(r)
            # If no content, fallback to center partial or full depending on grid size
            if not xs or not ys:
                # no content: return a centered min viewport
                w = max(min_w, min(gw, min_w))
                h = max(min_h, min(gh, min_h))
                x0 = max(0, (gw - w) // 2)
                y0 = max(0, (gh - h) // 2)
                return (x0, y0, w, h)

            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)

            # Apply padding and clamp to grid
            x0 = max(0, min_x - padding)
            x1 = min(gw - 1, max_x + padding)
            y0 = max(0, min_y - padding)
            y1 = min(gh - 1, max_y + padding)

            w = x1 - x0 + 1
            h = y1 - y0 + 1

            # Enforce minimum sizes by expanding equally on both sides when possible
            if w < min_w:
                extra = min_w - w
                left_expand = extra // 2
                right_expand = extra - left_expand
                x0 = max(0, x0 - left_expand)
                x1 = min(gw - 1, x1 + right_expand)
                w = x1 - x0 + 1
            if h < min_h:
                extra = min_h - h
                top_expand = extra // 2
                bottom_expand = extra - top_expand
                y0 = max(0, y0 - top_expand)
                y1 = min(gh - 1, y1 + bottom_expand)
                h = y1 - y0 + 1

            # If expansion hit the edges and we still are smaller than min, ensure dims are clamped
            w = min(w, gw)
            h = min(h, gh)
            x0 = max(0, min(x0, gw - w))
            y0 = max(0, min(y0, gh - h))

            return (x0, y0, w, h)
        else:
            # unknown mode - fallback to full
            return (0, 0, gw, gh)

    # ---------- DRAWING (canvas & image) UPDATED TO USE VIEWPORT ----------
    def draw_frame_on_canvas(self, canvas, frame, background=None, cell_size=None, viewport=None):
        """
        Draws a frame on the provided Tk canvas. If viewport is provided as
        (x0, y0, w, h), only that region is drawn and mapped to canvas.
        """
        canvas.delete("all")
        grid_width = frame['grid_width']
        grid_height = frame['grid_height']
        default_color = frame.get('default_color', 0)
        cell_size = cell_size or self.cell_size

        # Compute viewport if not supplied (use current settings)
        if viewport is None:
            viewport = self.compute_viewport(frame)
        x0, y0, w, h = viewport

        # Optionally set canvas pixel size to viewport dimensions
        canvas.config(width=w * cell_size, height=h * cell_size)

        # Draw background cells limited to viewport
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(y0, y0 + h):
                for col in range(x0, x0 + w):
                    box_key = f"{row},{col}"
                    if box_key in bg_boxes:
                        val = bg_boxes[box_key]
                        color = 'black' if (val != 0) else 'white'
                        if bg_default == 1:
                            color = 'white' if (val == 0) else 'black'
                    else:
                        color = 'white' if bg_default == 0 else 'black'
                    x_pixel = (col - x0) * cell_size
                    y_pixel = (row - y0) * cell_size
                    canvas.create_rectangle(x_pixel, y_pixel,
                                             x_pixel + cell_size, y_pixel + cell_size,
                                             fill=color, outline='gray')

        # Draw stick figure boxes within viewport
        boxes = frame.get('boxes', {})
        for row in range(y0, y0 + h):
            for col in range(x0, x0 + w):
                box_key = f"{row},{col}"
                if box_key in boxes:
                    val = boxes[box_key]
                    color = 'black' if (val != 0) else 'white'
                    if default_color == 1:
                        color = 'white' if (val == 0) else 'black'
                    if 'stick_figure_color' in frame:
                        color = frame['stick_figure_color']
                    x_pixel = (col - x0) * cell_size
                    y_pixel = (row - y0) * cell_size
                    canvas.create_rectangle(x_pixel, y_pixel,
                                             x_pixel + cell_size, y_pixel + cell_size,
                                             fill=color, outline='gray')

    def draw_frame_to_image(self, frame, background=None, cell_size=None, viewport=None):
        """
        Draw a PIL Image for the provided frame using viewport cropping.
        """
        grid_width = frame['grid_width']
        grid_height = frame['grid_height']
        default_color = frame.get('default_color', 0)
        cell_size = cell_size or self.cell_size

        # Compute viewport if not supplied
        if viewport is None:
            viewport = self.compute_viewport(frame)
        x0, y0, w, h = viewport

        img = Image.new('RGB', (w * cell_size, h * cell_size), 'white')
        draw = ImageDraw.Draw(img)

        # Draw background limited to viewport
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(y0, y0 + h):
                for col in range(x0, x0 + w):
                    box_key = f"{row},{col}"
                    if box_key in bg_boxes:
                        val = bg_boxes[box_key]
                        color = (0, 0, 0) if (val != 0) else (255, 255, 255)
                        if bg_default == 1:
                            color = (255,255,255) if (val == 0) else (0,0,0)
                    else:
                        color = (255,255,255) if bg_default == 0 else (0,0,0)
                    x0p = (col - x0) * cell_size
                    y0p = (row - y0) * cell_size
                    draw.rectangle([x0p, y0p, x0p + cell_size, y0p + cell_size], fill=color, outline=(180,180,180))

        # Draw boxes limited to viewport
        boxes = frame.get('boxes', {})
        for row in range(y0, y0 + h):
            for col in range(x0, x0 + w):
                box_key = f"{row},{col}"
                if box_key in boxes:
                    val = boxes[box_key]
                    color = (0,0,0) if (val != 0) else (255,255,255)
                    if default_color == 1:
                        color = (255,255,255) if (val == 0) else (0,0,0)
                    x0p = (col - x0) * cell_size
                    y0p = (row - y0) * cell_size
                    draw.rectangle([x0p, y0p, x0p + cell_size, y0p + cell_size], fill=color, outline=(180,180,180))
        return img

    def export_to_video(self, filename="animation.mp4", fps=5):
        images = []
        for i, frame in enumerate(self.frames):
            background = self.backgrounds[i] if i < len(self.backgrounds) else None
            viewport = self.compute_viewport(frame)  # compute viewport for each frame
            img = self.draw_frame_to_image(frame, background, cell_size=self.cell_size, viewport=viewport)
            frame_duration = int(self.timings[i])
            repeats = max(1, int((fps * frame_duration) / 1000))
            for _ in range(repeats):
                images.append(img.copy())
        imageio.mimsave(filename, [img for img in images], fps=fps)
        return True

    # ---------- GUI / Player ----------
    def run_animation_gui(self):
        root = tk.Tk()
        root.title("Stick Figure Animation Editor & Player")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        main_frame = tk.Frame(root)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Canvas and resizability logic
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg='white')
        canvas.pack(fill=tk.BOTH, expand=True)

        # Button frame
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, pady=8)

        # Viewport control frame
        viewport_frame = tk.Frame(btn_frame)
        viewport_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(viewport_frame, text="Viewport:").pack(side=tk.LEFT)
        viewport_var = tk.StringVar(value=self.viewport_mode)
        viewport_menu = tk.OptionMenu(viewport_frame, viewport_var, 'full', 'half', 'stick-figure')
        viewport_menu.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="Padding").pack(side=tk.LEFT)
        padding_var = tk.IntVar(value=self.viewport_padding)
        padding_spin = tk.Spinbox(viewport_frame, from_=0, to=50, width=4, textvariable=padding_var)
        padding_spin.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="Min W").pack(side=tk.LEFT)
        minw_var = tk.IntVar(value=self.viewport_min_w)
        minw_spin = tk.Spinbox(viewport_frame, from_=4, to=500, width=4, textvariable=minw_var)
        minw_spin.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="Min H").pack(side=tk.LEFT)
        minh_var = tk.IntVar(value=self.viewport_min_h)
        minh_spin = tk.Spinbox(viewport_frame, from_=4, to=500, width=4, textvariable=minh_var)
        minh_spin.pack(side=tk.LEFT)

        # Listbox for frames
        frame_listbox = tk.Listbox(main_frame, width=60)
        frame_listbox.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        running = {'flag': False, 'loop': False}
        current_cell_size = [self.cell_size]  # Mutable to be shared

        def get_frame_label(idx):
            name = self.frame_names[idx] if idx < len(self.frame_names) else f"Frame_{idx+1}.json"
            duration = self.timings[idx] if idx < len(self.timings) else 200
            return f"Frame {idx+1} : {name} : {duration} ms"

        def update_listbox():
            frame_listbox.delete(0, tk.END)
            for i in range(len(self.frames)):
                frame_listbox.insert(tk.END, get_frame_label(i))

        def draw_frame_index(idx):
            if idx < 0 or idx >= len(self.frames):
                return
            # Update viewport selections from UI controls
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())

            frame = self.frames[idx]
            background = self.backgrounds[idx] if idx < len(self.backgrounds) else None
            # compute viewport (we may want to scale cell_size to fit canvas area)
            viewport = self.compute_viewport(frame)
            # determine cell_size to fit current canvas bounding box if the canvas is bigger/smaller
            # but for simplicity, use the computed cell_size (allow resize handler to override)
            self.draw_frame_on_canvas(canvas, frame, background, cell_size=current_cell_size[0], viewport=viewport)

        def on_listbox_select(evt):
            idxs = frame_listbox.curselection()
            if idxs:
                idx = idxs[0]
                draw_frame_index(idx)

        frame_listbox.bind("<<ListboxSelect>>", on_listbox_select)

        def add_frame():
            stick_path = filedialog.askopenfilename(title="Add Stick Figure Frame JSON",
                                                    filetypes=[("JSON files", "*.json")])
            if not stick_path:
                return
            bg_path = filedialog.askopenfilename(title="Add Background JSON (optional)",
                                                 filetypes=[("JSON files", "*.json")])
            self.add_frame_from_json(stick_path, 200, bg_path if bg_path else None)
            update_listbox()
            draw_frame_index(len(self.frames)-1)

        def set_background_for_frame():
            idxs = frame_listbox.curselection()
            if not idxs:
                messagebox.showinfo("Frame Select", "Please select a frame to set its background.")
                return
            idx = idxs[0]
            bg_path = filedialog.askopenfilename(title="Add Background JSON",
                                                 filetypes=[("JSON files", "*.json")])
            if not bg_path:
                return
            with open(bg_path, 'r') as f:
                bg_data = json.load(f)
            self.backgrounds[idx] = bg_data
            self.background_names[idx] = bg_path.split("/")[-1]
            update_listbox()
            draw_frame_index(idx)

        def save_animation():
            filename = filedialog.asksaveasfilename(title="Save Animation JSON",
                                                    filetypes=[("JSON files", "*.json")],
                                                    defaultextension=".json")
            if not filename:
                return
            # Also persist viewport settings
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.save_animation(filename)
            messagebox.showinfo("Saved", f"Animation saved as {filename}")

        def load_animation():
            filename = filedialog.askopenfilename(title="Load Animation JSON",
                                                  filetypes=[("JSON files", "*.json")])
            if not filename:
                return
            self.load_animation(filename)
            # push loaded viewport to controls
            viewport_var.set(self.viewport_mode)
            padding_var.set(self.viewport_padding)
            minw_var.set(self.viewport_min_w)
            minh_var.set(self.viewport_min_h)
            update_listbox()
            draw_frame_index(0)
            messagebox.showinfo("Loaded", f"Loaded animation {filename}")

        def export_video():
            filename = filedialog.asksaveasfilename(title="Export to MP4",
                                                    filetypes=[("MP4 Video", "*.mp4")],
                                                    defaultextension=".mp4")
            if not filename:
                return
            fps = 5
            try:
                # Use UI-specified viewport when exporting
                self.viewport_mode = viewport_var.get()
                self.viewport_padding = int(padding_var.get())
                self.viewport_min_w = int(minw_var.get())
                self.viewport_min_h = int(minh_var.get())
                self.export_to_video(filename, fps=fps)
                messagebox.showinfo("Exported", f"Exported animation as {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

        def play_animation(loop=False):
            running['flag'] = True
            running['loop'] = loop

            def step(index):
                if not running['flag']:
                    return
                if index >= len(self.frames):
                    if running['loop']:
                        index = 0
                    else:
                        running['flag'] = False
                        return
                draw_frame_index(index)
                frame_duration = self.timings[index]
                root.after(frame_duration, lambda: step(index+1))

            step(0)

        def stop_animation():
            running['flag'] = False

        def edit_duration():
            idxs = frame_listbox.curselection()
            if not idxs:
                messagebox.showinfo("Frame Select", "Please select a frame to edit its duration.")
                return
            idx = idxs[0]
            current_duration = self.timings[idx]
            new_duration = simpledialog.askinteger("Edit Frame Duration",
                                                   f"Set new duration (ms) for Frame {idx+1}:",
                                                   initialvalue=current_duration,
                                                   minvalue=1)
            if new_duration is not None:
                self.timings[idx] = int(new_duration)
                update_listbox()

        # Buttons
        add_btn = tk.Button(btn_frame, text="Add Frame", command=add_frame)
        add_btn.pack(side=tk.LEFT, padx=5)
        set_bg_btn = tk.Button(btn_frame, text="Set/Change BG", command=set_background_for_frame)
        set_bg_btn.pack(side=tk.LEFT, padx=5)
        edit_duration_btn = tk.Button(btn_frame, text="Edit Duration", command=edit_duration)
        edit_duration_btn.pack(side=tk.LEFT, padx=5)
        save_btn = tk.Button(btn_frame, text="Save Animation", command=save_animation)
        save_btn.pack(side=tk.LEFT, padx=5)
        load_btn = tk.Button(btn_frame, text="Load Animation", command=load_animation)
        load_btn.pack(side=tk.LEFT, padx=5)
        export_btn = tk.Button(btn_frame, text="Export Video", command=export_video)
        export_btn.pack(side=tk.LEFT, padx=5)
        start_btn = tk.Button(btn_frame, text="Start", command=lambda: play_animation(loop=False))
        start_btn.pack(side=tk.LEFT, padx=5)
        replay_btn = tk.Button(btn_frame, text="Replay", command=lambda: play_animation(loop=True))
        replay_btn.pack(side=tk.LEFT, padx=5)
        stop_btn = tk.Button(btn_frame, text="Stop", command=stop_animation)
        stop_btn.pack(side=tk.LEFT, padx=5)

        # Double-click on frame to edit duration
        def on_double_click(event):
            edit_duration()

        frame_listbox.bind("<Double-Button-1>", on_double_click)

        # Redraw animation whenever window is resized
        def resize_canvas(event):
            # Only recalculate if grid size known and frames present
            if self.grid_width and self.grid_height and self.frames:
                new_width = event.width
                new_height = event.height
                # compute cell size based on current viewport for the selected frame
                idx = frame_listbox.curselection()
                idx = idx[0] if idx else 0
                frame = self.frames[idx]
                viewport = self.compute_viewport(frame)
                _, _, vw, vh = viewport
                if vw > 0 and vh > 0:
                    cell_size_w = new_width // vw
                    cell_size_h = new_height // vh
                    cell_size = max(1, min(cell_size_w, cell_size_h))
                    current_cell_size[0] = cell_size
                    # force canvas to be a multiple of cell size
                    canvas.config(width=vw * cell_size,
                                  height=vh * cell_size)
                    draw_frame_index(idx)

        canvas.bind("<Configure>", resize_canvas)
        canvas.update_idletasks()

        # Draw first frame if available
        if self.frames:
            draw_frame_index(0)
            update_listbox()

        root.mainloop()


if __name__ == "__main__":
    anim = StickFigureAnimation()
    #anim.load_animation_from_jsons(["frame_templates/waving/highWave1.json", "frame_templates/waving/highWave2.json"], timings=[200,200])
    #anim.load_animation_from_jsons(["stand - wide stance.json", "wave1.json", "wave2.json"], timings=[200, 200, 400])
    #anim.run_animation(background_json="centerstage1.json")
    anim.run_animation_gui()