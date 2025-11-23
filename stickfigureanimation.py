"""
Modified stickfigureanimation.py

- Adds viewport modes: 'full', 'half', 'stick-figure' (auto crop to content) but does NOT auto-scale to window.
- Adds option to "Lock to animation bounds" to compute a single global viewport that covers all frames.
- draw_frame_on_canvas and draw_frame_to_image accept an explicit viewport (x0, y0, w, h) and draw/crop using that.
- Export uses the locked/global viewport when lock_viewport is True; otherwise it uses per-frame viewport.
- Keeps a fixed cell_size for rendering and export (no automatic cell-size scaling).
- Includes comments to make it easy for other developers to continue.

Usage: replace the existing stickfigureanimation.py with this file.
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw
import imageio


class StickFigureAnimation:
    def __init__(self):
        # animation data
        self.frames = []         # List[dict] each dict is a frame (boxes, grid_width, grid_height, default_color)
        self.timings = []        # List[int] durations in ms
        self.backgrounds = []    # List[Optional[dict]] backgrounds per frame
        self.frame_names = []    # filenames for frames
        self.background_names = []

        # grid metadata (will be read from frames)
        self.grid_width = None
        self.grid_height = None
        self.default_color = 0

        # rendering configuration
        self.cell_size = 10  # kept fixed; we DO NOT auto-scale to window per your request

        # viewport configuration
        # mode: 'full' (show entire grid), 'half' (center half of grid), 'stick-figure' (crop to content)
        self.viewport_mode = 'full'
        self.viewport_padding = 2
        self.viewport_min_w = 16
        self.viewport_min_h = 16

        # locking behavior: if True compute a single viewport that covers all frames (prevents camera jumps)
        # default True to avoid per-frame jitter
        self.lock_viewport = True

    # -------------------------
    # Loading / saving frames
    # -------------------------
    def add_frame_from_json(self, stick_figure_json, duration=200, background_json=None):
        """Add a single frame JSON file to the animation."""
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
        # update grid meta from frame
        self.grid_width = frame_data.get('grid_width', self.grid_width)
        self.grid_height = frame_data.get('grid_height', self.grid_height)
        self.default_color = frame_data.get('default_color', self.default_color)

    def load_animation_from_jsons(self, json_files, timings=None, background_jsons=None):
        """Load multiple frames from JSON files (clears any existing animation)."""
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
        """Save entire animation (including viewport settings)."""
        animation_data = {
            "frames": self.frames,
            "timings": self.timings,
            "backgrounds": self.backgrounds,
            "frame_names": self.frame_names,
            "background_names": self.background_names,
            # persist viewport settings
            "viewport_mode": self.viewport_mode,
            "viewport_padding": self.viewport_padding,
            "viewport_min_w": self.viewport_min_w,
            "viewport_min_h": self.viewport_min_h,
            "lock_viewport": self.lock_viewport,
        }
        with open(filename, "w") as f:
            json.dump(animation_data, f, indent=2)

    def load_animation(self, filename):
        """Load an animation saved by save_animation."""
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
        self.lock_viewport = data.get("lock_viewport", self.lock_viewport)

        # update grid metadata from first frame
        if self.frames:
            self.grid_width = self.frames[0].get('grid_width', self.grid_width)
            self.grid_height = self.frames[0].get('grid_height', self.grid_height)
            self.default_color = self.frames[0].get('default_color', self.default_color)

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color string to RGB tuple (utility)."""
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        return tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    # -------------------------
    # Viewport computation
    # -------------------------
    def compute_viewport(self, frame, mode=None, padding=None, min_w=None, min_h=None):
        """
        Compute viewport (x0, y0, w, h) for a single frame.

        Parameters:
          frame: frame dict
          mode: overrides self.viewport_mode if provided
          padding/min_w/min_h: optional overrides

        Returns:
          tuple(x0, y0, w, h) in grid cell coordinates.
        """
        mode = mode or self.viewport_mode
        padding = self.viewport_padding if padding is None else padding
        min_w = self.viewport_min_w if min_w is None else min_w
        min_h = self.viewport_min_h if min_h is None else min_h

        gw = frame.get('grid_width', self.grid_width)
        gh = frame.get('grid_height', self.grid_height)

        if mode == 'full':
            return (0, 0, gw, gh)

        if mode == 'half':
            w = max(1, gw // 2)
            h = max(1, gh // 2)
            x0 = max(0, (gw - w) // 2)
            y0 = max(0, (gh - h) // 2)
            return (x0, y0, w, h)

        # stick-figure mode => compute bounding box of non-default boxes in this frame
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', self.default_color)

        xs = []
        ys = []
        for key, val in boxes.items():
            try:
                r, c = map(int, key.split(","))
            except Exception:
                continue
            if val != default_color:
                xs.append(c)
                ys.append(r)

        # no content case: return a centered minimum viewport
        if not xs:
            w = min(gw, min_w)
            h = min(gh, min_h)
            x0 = max(0, (gw - w) // 2)
            y0 = max(0, (gh - h) // 2)
            return (x0, y0, w, h)

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        x0 = max(0, min_x - padding)
        x1 = min(gw - 1, max_x + padding)
        y0 = max(0, min_y - padding)
        y1 = min(gh - 1, max_y + padding)

        w = x1 - x0 + 1
        h = y1 - y0 + 1

        # enforce minimum size by expanding symmetrically when possible
        if w < min_w:
            extra = min_w - w
            left = extra // 2
            right = extra - left
            x0 = max(0, x0 - left)
            x1 = min(gw - 1, x1 + right)
            w = x1 - x0 + 1
        if h < min_h:
            extra = min_h - h
            top = extra // 2
            bottom = extra - top
            y0 = max(0, y0 - top)
            y1 = min(gh - 1, y1 + bottom)
            h = y1 - y0 + 1

        # final clamp
        w = min(w, gw)
        h = min(h, gh)
        x0 = max(0, min(x0, gw - w))
        y0 = max(0, min(y0, gh - h))

        return (x0, y0, w, h)

    def compute_global_viewport(self, frames=None, padding=None, min_w=None, min_h=None):
        """
        Compute a single viewport covering the union of content from all frames.
        This prevents the camera jumping when content moves slightly between frames.

        Returns (x0, y0, w, h).
        """
        frames = frames or self.frames
        if not frames:
            # fallback to full of known grid size (or zeros)
            gw = self.grid_width or 0
            gh = self.grid_height or 0
            return (0, 0, gw, gh)

        padding = self.viewport_padding if padding is None else padding
        min_w = self.viewport_min_w if min_w is None else min_w
        min_h = self.viewport_min_h if min_h is None else min_h

        gw = self.grid_width or frames[0].get('grid_width', 0)
        gh = self.grid_height or frames[0].get('grid_height', 0)

        min_c = None
        max_c = None
        min_r = None
        max_r = None

        for frame in frames:
            gw = frame.get('grid_width', gw)
            gh = frame.get('grid_height', gh)
            boxes = frame.get('boxes', {})
            default_color = frame.get('default_color', self.default_color)

            xs = []
            ys = []
            for key, val in boxes.items():
                try:
                    r, c = map(int, key.split(","))
                except Exception:
                    continue
                if val != default_color:
                    xs.append(c)
                    ys.append(r)
            if not xs:
                continue
            fmin_c = min(xs)
            fmax_c = max(xs)
            fmin_r = min(ys)
            fmax_r = max(ys)

            if min_c is None or fmin_c < min_c:
                min_c = fmin_c
            if max_c is None or fmax_c > max_c:
                max_c = fmax_c
            if min_r is None or fmin_r < min_r:
                min_r = fmin_r
            if max_r is None or fmax_r > max_r:
                max_r = fmax_r

        # if no content found across all frames, return centered minimum/full
        if min_c is None:
            w = min(gw, min_w) if gw else min_w
            h = min(gh, min_h) if gh else min_h
            x0 = max(0, (gw - w) // 2) if gw else 0
            y0 = max(0, (gh - h) // 2) if gh else 0
            return (x0, y0, w, h)

        # apply padding
        x0 = max(0, min_c - padding)
        x1 = min(gw - 1, max_c + padding)
        y0 = max(0, min_r - padding)
        y1 = min(gh - 1, max_r + padding)

        w = x1 - x0 + 1
        h = y1 - y0 + 1

        # enforce minimums
        if w < min_w:
            extra = min_w - w
            left = extra // 2
            right = extra - left
            x0 = max(0, x0 - left)
            x1 = min(gw - 1, x1 + right)
            w = x1 - x0 + 1
        if h < min_h:
            extra = min_h - h
            top = extra // 2
            bottom = extra - top
            y0 = max(0, y0 - top)
            y1 = min(gh - 1, y1 + bottom)
            h = y1 - y0 + 1

        # final clamp
        w = min(w, gw)
        h = min(h, gh)
        x0 = max(0, min(x0, gw - w))
        y0 = max(0, min(y0, gh - h))

        return (x0, y0, w, h)

    # -------------------------
    # Drawing functions (canvas + image)
    # -------------------------
    def draw_frame_on_canvas(self, canvas, frame, background=None, cell_size=None, viewport=None):
        """
        Draw a frame to a Tk Canvas using a viewport.

        viewport: (x0, y0, w, h) in grid coordinates. If None, compute using self.compute_viewport(frame).
        cell_size: pixel size per cell. Defaults to self.cell_size.

        Important: This does NOT auto-scale to window size. canvas size is set to match viewport * cell_size.
        """
        canvas.delete("all")
        cell_size = cell_size or self.cell_size

        # compute viewport if not given
        if viewport is None:
            viewport = self.compute_viewport(frame)
        x0, y0, w, h = viewport

        # Set canvas pixel size to viewport size * cell_size so the canvas shows exactly the viewport
        canvas.config(width=w * cell_size, height=h * cell_size)

        # Draw background (if any) limited to viewport
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
                    canvas.create_rectangle(x_pixel, y_pixel, x_pixel + cell_size, y_pixel + cell_size, fill=color, outline='gray')

        # Draw frame's boxes limited to viewport
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', 0)
        sf_color = frame.get('stick_figure_color', None)  # optional override
        for row in range(y0, y0 + h):
            for col in range(x0, x0 + w):
                box_key = f"{row},{col}"
                if box_key in boxes:
                    val = boxes[box_key]
                    color = 'black' if (val != 0) else 'white'
                    if default_color == 1:
                        color = 'white' if (val == 0) else 'black'
                    if sf_color:
                        color = sf_color
                    x_pixel = (col - x0) * cell_size
                    y_pixel = (row - y0) * cell_size
                    canvas.create_rectangle(x_pixel, y_pixel, x_pixel + cell_size, y_pixel + cell_size, fill=color, outline='gray')

    def draw_frame_to_image(self, frame, background=None, cell_size=None, viewport=None):
        """
        Draw a frame to a PIL Image using a viewport.
        Returns a PIL.Image.
        """
        cell_size = cell_size or self.cell_size

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
                        color = (0,0,0) if (val != 0) else (255,255,255)
                        if bg_default == 1:
                            color = (255,255,255) if (val == 0) else (0,0,0)
                    else:
                        color = (255,255,255) if bg_default == 0 else (0,0,0)
                    x0p = (col - x0) * cell_size
                    y0p = (row - y0) * cell_size
                    draw.rectangle([x0p, y0p, x0p + cell_size, y0p + cell_size], fill=color, outline=(180,180,180))

        # Draw frame boxes limited to viewport
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', 0)
        sf_color = frame.get('stick_figure_color', None)
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
                    if sf_color:
                        # If stick_figure_color is present, prefer that (convert hex or named color to RGB)
                        if isinstance(sf_color, str) and sf_color.startswith('#'):
                            draw_color = self.hex_to_rgb(sf_color)
                        else:
                            # support simple names like 'black'/'white' for now
                            draw_color = (0,0,0) if sf_color.lower() == 'black' else (255,255,255)
                    else:
                        draw_color = color
                    draw.rectangle([x0p, y0p, x0p + cell_size, y0p + cell_size], fill=draw_color, outline=(180,180,180))

        return img

    # -------------------------
    # Export
    # -------------------------
    def export_to_video(self, filename="animation.mp4", fps=5):
        """
        Export animation to an MP4. If lock_viewport is True, compute a single viewport that
        covers all frames; otherwise compute a per-frame viewport.
        Uses fixed self.cell_size (no auto-scaling).
        """
        images = []

        # Precompute global viewport if requested
        global_viewport = None
        if self.lock_viewport:
            global_viewport = self.compute_global_viewport(self.frames)

        for i, frame in enumerate(self.frames):
            background = self.backgrounds[i] if i < len(self.backgrounds) else None
            viewport = global_viewport if global_viewport is not None else self.compute_viewport(frame)
            img = self.draw_frame_to_image(frame, background, cell_size=self.cell_size, viewport=viewport)
            frame_duration = int(self.timings[i])
            repeats = max(1, int((fps * frame_duration) / 1000))
            for _ in range(repeats):
                images.append(img.copy())

        # Write out using imageio
        imageio.mimsave(filename, images, fps=fps)
        return True

    # -------------------------
    # GUI: animation editor & player
    # -------------------------
    def run_animation_gui(self):
        """Run a simple Tk GUI to add frames, choose viewport mode, play, and export."""
        root = tk.Tk()
        root.title("Stick Figure Animation Editor & Player")

        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas frame (top)
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg='white')
        canvas.pack()

        # Controls frame (bottom)
        ctrl_frame = tk.Frame(main_frame)
        ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=6)

        # Viewport controls
        viewport_frame = tk.Frame(ctrl_frame)
        viewport_frame.pack(side=tk.LEFT, padx=6)
        tk.Label(viewport_frame, text="Viewport:").pack(side=tk.LEFT)
        viewport_var = tk.StringVar(value=self.viewport_mode)
        viewport_menu = tk.OptionMenu(viewport_frame, viewport_var, 'full', 'half', 'stick-figure')
        viewport_menu.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="Pad").pack(side=tk.LEFT)
        padding_var = tk.IntVar(value=self.viewport_padding)
        padding_spin = tk.Spinbox(viewport_frame, from_=0, to=50, width=4, textvariable=padding_var)
        padding_spin.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="MinW").pack(side=tk.LEFT)
        minw_var = tk.IntVar(value=self.viewport_min_w)
        minw_spin = tk.Spinbox(viewport_frame, from_=4, to=500, width=4, textvariable=minw_var)
        minw_spin.pack(side=tk.LEFT)
        tk.Label(viewport_frame, text="MinH").pack(side=tk.LEFT)
        minh_var = tk.IntVar(value=self.viewport_min_h)
        minh_spin = tk.Spinbox(viewport_frame, from_=4, to=500, width=4, textvariable=minh_var)
        minh_spin.pack(side=tk.LEFT)

        # Lock viewport checkbox
        lock_var = tk.BooleanVar(value=self.lock_viewport)
        lock_chk = tk.Checkbutton(viewport_frame, text="Lock to animation bounds", variable=lock_var)
        lock_chk.pack(side=tk.LEFT, padx=6)

        # Frame listbox for selecting frames
        frame_listbox = tk.Listbox(ctrl_frame, width=60)
        frame_listbox.pack(side=tk.LEFT, padx=6)

        # Buttons on the right
        btn_frame = tk.Frame(ctrl_frame)
        btn_frame.pack(side=tk.RIGHT, padx=6)
        add_btn = tk.Button(btn_frame, text="Add Frame", width=12, command=lambda: add_frame())
        add_btn.pack(pady=2)
        set_bg_btn = tk.Button(btn_frame, text="Set/Change BG", width=12, command=lambda: set_background_for_frame())
        set_bg_btn.pack(pady=2)
        edit_duration_btn = tk.Button(btn_frame, text="Edit Duration", width=12, command=lambda: edit_duration())
        edit_duration_btn.pack(pady=2)
        save_btn = tk.Button(btn_frame, text="Save Animation", width=12, command=lambda: save_animation())
        save_btn.pack(pady=2)
        load_btn = tk.Button(btn_frame, text="Load Animation", width=12, command=lambda: load_animation())
        load_btn.pack(pady=2)
        export_btn = tk.Button(btn_frame, text="Export Video", width=12, command=lambda: export_video())
        export_btn.pack(pady=2)
        start_btn = tk.Button(btn_frame, text="Start", width=12, command=lambda: play_animation(loop=False))
        start_btn.pack(pady=2)
        replay_btn = tk.Button(btn_frame, text="Replay", width=12, command=lambda: play_animation(loop=True))
        replay_btn.pack(pady=2)
        stop_btn = tk.Button(btn_frame, text="Stop", width=12, command=lambda: stop_animation())
        stop_btn.pack(pady=2)

        # utility to label frames
        def get_frame_label(idx):
            name = self.frame_names[idx] if idx < len(self.frame_names) else f"Frame_{idx+1}.json"
            duration = self.timings[idx] if idx < len(self.timings) else 200
            return f"Frame {idx+1} : {name} : {duration} ms"

        def update_listbox():
            frame_listbox.delete(0, tk.END)
            for i in range(len(self.frames)):
                frame_listbox.insert(tk.END, get_frame_label(i))

        def draw_frame_index(idx):
            """Draw the selected frame using viewport settings from the UI. DOES NOT auto-scale."""
            if idx < 0 or idx >= len(self.frames):
                return

            # read UI viewport settings into object state
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()

            frame = self.frames[idx]
            background = self.backgrounds[idx] if idx < len(self.backgrounds) else None

            # decide viewport: either global (locked) or per-frame
            if self.lock_viewport and len(self.frames) > 0:
                viewport = self.compute_global_viewport(self.frames)
            else:
                viewport = self.compute_viewport(frame)

            # draw using fixed cell_size and set canvas size accordingly
            self.draw_frame_on_canvas(canvas, frame, background, cell_size=self.cell_size, viewport=viewport)

        def on_listbox_select(evt):
            sel = frame_listbox.curselection()
            if sel:
                draw_frame_index(sel[0])

        frame_listbox.bind("<<ListboxSelect>>", on_listbox_select)

        # Button command implementations
        def add_frame():
            stick_path = filedialog.askopenfilename(title="Add Stick Figure Frame JSON",
                                                    filetypes=[("JSON files", "*.json")])
            if not stick_path:
                return
            bg_path = filedialog.askopenfilename(title="Add Background JSON (optional)",
                                                 filetypes=[("JSON files", "*.json")])
            self.add_frame_from_json(stick_path, 200, bg_path if bg_path else None)
            update_listbox()
            # select the newly added frame
            frame_listbox.selection_clear(0, tk.END)
            frame_listbox.selection_set(len(self.frames)-1)
            draw_frame_index(len(self.frames)-1)

        def set_background_for_frame():
            sel = frame_listbox.curselection()
            if not sel:
                messagebox.showinfo("Frame Select", "Please select a frame to set its background.")
                return
            idx = sel[0]
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
            # persist UI viewport settings into the animation
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()
            self.save_animation(filename)
            messagebox.showinfo("Saved", f"Animation saved as {filename}")

        def load_animation():
            filename = filedialog.askopenfilename(title="Load Animation JSON",
                                                  filetypes=[("JSON files", "*.json")])
            if not filename:
                return
            self.load_animation(filename)
            # update UI to reflect loaded viewport settings
            viewport_var.set(self.viewport_mode)
            padding_var.set(self.viewport_padding)
            minw_var.set(self.viewport_min_w)
            minh_var.set(self.viewport_min_h)
            lock_var.set(self.lock_viewport)
            update_listbox()
            if self.frames:
                frame_listbox.selection_clear(0, tk.END)
                frame_listbox.selection_set(0)
                draw_frame_index(0)
            messagebox.showinfo("Loaded", f"Loaded animation {filename}")

        def export_video():
            filename = filedialog.asksaveasfilename(title="Export to MP4",
                                                    filetypes=[("MP4 Video", "*.mp4")],
                                                    defaultextension=".mp4")
            if not filename:
                return
            # sync UI -> state
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()
            try:
                # export using current settings; fixed cell_size used
                self.export_to_video(filename, fps=5)
                messagebox.showinfo("Exported", f"Exported animation as {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

        # Play controls
        running = {'flag': False, 'loop': False}

        def play_animation(loop=False):
            if not self.frames:
                return
            running['flag'] = True
            running['loop'] = loop

            # sync UI -> state once at start
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()

            # if lock_viewport is True compute global viewport once here for playback consistency
            playback_viewport = None
            if self.lock_viewport:
                playback_viewport = self.compute_global_viewport(self.frames)

            def step(index):
                if not running['flag']:
                    return
                if index >= len(self.frames):
                    if running['loop']:
                        index = 0
                    else:
                        running['flag'] = False
                        return
                frame = self.frames[index]
                bg = self.backgrounds[index] if index < len(self.backgrounds) else None
                viewport = playback_viewport if playback_viewport is not None else self.compute_viewport(frame)
                self.draw_frame_on_canvas(canvas, frame, bg, cell_size=self.cell_size, viewport=viewport)
                frame_duration = self.timings[index]
                root.after(frame_duration, lambda: step(index + 1))

            step(0)

        def stop_animation():
            running['flag'] = False

        def edit_duration():
            sel = frame_listbox.curselection()
            if not sel:
                messagebox.showinfo("Frame Select", "Please select a frame to edit its duration.")
                return
            idx = sel[0]
            current_duration = self.timings[idx]
            new_duration = simpledialog.askinteger("Edit Frame Duration",
                                                   f"Set new duration (ms) for Frame {idx+1}:",
                                                   initialvalue=current_duration,
                                                   minvalue=1)
            if new_duration is not None:
                self.timings[idx] = int(new_duration)
                update_listbox()

        # double-click to edit duration
        def on_double_click(event):
            edit_duration()

        frame_listbox.bind("<Double-Button-1>", on_double_click)

        # Initialize listbox and draw first frame if available
        update_listbox()
        if self.frames:
            frame_listbox.selection_set(0)
            draw_frame_index(0)

        root.mainloop()


if __name__ == "__main__":
    anim = StickFigureAnimation()
    anim.run_animation_gui()