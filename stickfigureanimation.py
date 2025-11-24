"""
stickfigureanimation.py

Extended from the interactive editor/player to add a "headless" animation player
interface that other modules (or an LLM-driven controller) can import and call.

Features added here:
- All previous editor/player functionality is retained (run_animation_gui).
- New method play_animation_window(...) launches a minimal window that only
  displays the animation (no buttons, no frame list). This is suitable for
  embedding into an AI service that needs to present an animation on demand.
- play_animation_window accepts parameters to adjust cell size, looping, and
  whether to lock viewport to the union of all frames.
- The default minimal player sets the viewport mode to 'stick-figure' and
  locks to animation bounds to avoid camera jitter when playing small movements.
- Detailed comments added throughout to make it easy for other developers to
  follow and extend.

Usage (example at bottom):
- Import the module and call:
    anim = StickFigureAnimation()
    anim.load_animation("animation1.json")
    anim.play_animation_window(cell_size=8, loop=True)

Note: This file keeps rendering cell_size fixed (no automatic autoscale to host window).
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw
import imageio


class StickFigureAnimation:
    def __init__(self):
        # Animation data containers
        self.frames = []         # List[dict] - each frame dict contains 'boxes', 'grid_width', 'grid_height', etc.
        self.timings = []        # List[int] durations per frame in ms
        self.backgrounds = []    # List[Optional[dict]] per-frame background data
        self.frame_names = []    # Filenames or labels for frames
        self.background_names = []

        # Grid metadata - kept in sync when frames are added/loaded
        self.grid_width = None
        self.grid_height = None
        self.default_color = 0

        # Rendering config - kept fixed by design (no automatic window autoscale)
        self.cell_size = 10

        # Viewport configuration:
        # mode: 'full'|'half'|'stick-figure'
        # stick-figure = crop tightly to content (plus padding)
        self.viewport_mode = 'full'
        self.viewport_padding = 2
        self.viewport_min_w = 16
        self.viewport_min_h = 16

        # When True compute one viewport covering all frames (union) to avoid camera jumps
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
        # update grid metadata
        self.grid_width = frame_data.get('grid_width', self.grid_width)
        self.grid_height = frame_data.get('grid_height', self.grid_height)
        self.default_color = frame_data.get('default_color', self.default_color)

    def load_animation_from_jsons(self, json_files, timings=None, background_jsons=None):
        """Load multiple frames from JSON files, clearing existing animation data."""
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
        """Save animation data and viewport settings to a single JSON file."""
        animation_data = {
            "frames": self.frames,
            "timings": self.timings,
            "backgrounds": self.backgrounds,
            "frame_names": self.frame_names,
            "background_names": self.background_names,
            "viewport_mode": self.viewport_mode,
            "viewport_padding": self.viewport_padding,
            "viewport_min_w": self.viewport_min_w,
            "viewport_min_h": self.viewport_min_h,
            "lock_viewport": self.lock_viewport,
        }
        with open(filename, "w") as f:
            json.dump(animation_data, f, indent=2)

    def load_animation(self, filename):
        """Load an animation previously saved with save_animation."""
        with open(filename, "r") as f:
            data = json.load(f)
        self.frames = data["frames"]
        self.timings = data["timings"]
        self.backgrounds = data.get("backgrounds", [None] * len(self.frames))
        self.frame_names = data.get("frame_names", [f"Frame_{i+1}.json" for i in range(len(self.frames))])
        self.background_names = data.get("background_names", [""] * len(self.frames))
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
        """Convert hex such as '#rrggbb' to an (r,g,b) tuple."""
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        return tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    # -------------------------
    # Viewport calculation
    # -------------------------
    def compute_viewport(self, frame, mode=None, padding=None, min_w=None, min_h=None):
        """
        Compute a rectangular viewport for a single frame.

        Returns (x0, y0, w, h) in grid cell coordinates.
        - 'full' returns the entire grid
        - 'half' returns a centered half-size viewport
        - 'stick-figure' crops to non-default pixels with padding and minimum size
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

        # stick-figure: find bounding box of boxes != default_color
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', self.default_color)

        xs, ys = [], []
        for key, val in boxes.items():
            try:
                r, c = map(int, key.split(","))
            except Exception:
                continue
            if val != default_color:
                xs.append(c)
                ys.append(r)

        if not xs:
            # Nothing drawn — return a centered minimal viewport
            w = min(gw, min_w)
            h = min(gh, min_h)
            x0 = max(0, (gw - w) // 2)
            y0 = max(0, (gh - h) // 2)
            return (x0, y0, w, h)

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        x0 = max(0, min_x - padding)
        x1 = min(gw - 1, max_x + padding)
        y0 = max(0, min_y - padding)
        y1 = min(gh - 1, max_y + padding)

        w = x1 - x0 + 1
        h = y1 - y0 + 1

        # Enforce minimum viewport size by symmetric expansion where possible
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

        # Final clamps
        w = min(w, gw)
        h = min(h, gh)
        x0 = max(0, min(x0, gw - w))
        y0 = max(0, min(y0, gh - h))

        return (x0, y0, w, h)

    def compute_global_viewport(self, frames=None, padding=None, min_w=None, min_h=None):
        """
        Compute a single viewport that covers the union of all frames' content.
        Useful to avoid per-frame camera jumps when the subject moves slightly.
        """
        frames = frames or self.frames
        if not frames:
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

            xs, ys = [], []
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
            fmin_c, fmax_c = min(xs), max(xs)
            fmin_r, fmax_r = min(ys), max(ys)

            if min_c is None or fmin_c < min_c:
                min_c = fmin_c
            if max_c is None or fmax_c > max_c:
                max_c = fmax_c
            if min_r is None or fmin_r < min_r:
                min_r = fmin_r
            if max_r is None or fmax_r > max_r:
                max_r = fmax_r

        # nothing found across all frames
        if min_c is None:
            w = min(gw, min_w) if gw else min_w
            h = min(gh, min_h) if gh else min_h
            x0 = max(0, (gw - w) // 2) if gw else 0
            y0 = max(0, (gh - h) // 2) if gh else 0
            return (x0, y0, w, h)

        # apply padding then enforce minimums and clamps (same logic as single-frame)
        x0 = max(0, min_c - padding)
        x1 = min(gw - 1, max_c + padding)
        y0 = max(0, min_r - padding)
        y1 = min(gh - 1, max_r + padding)

        w = x1 - x0 + 1
        h = y1 - y0 + 1

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

        w = min(w, gw)
        h = min(h, gh)
        x0 = max(0, min(x0, gw - w))
        y0 = max(0, min(y0, gh - h))

        return (x0, y0, w, h)

    # -------------------------
    # Drawing functions
    # -------------------------
    def draw_frame_on_canvas(self, canvas, frame, background=None, cell_size=None, viewport=None):
        """
        Draw a frame on a Tk canvas according to the provided viewport.
        canvas size will be set to viewport_size * cell_size so drawing area exactly matches viewport.
        """
        canvas.delete("all")
        cell_size = cell_size or self.cell_size

        if viewport is None:
            viewport = self.compute_viewport(frame)
        x0, y0, w, h = viewport

        # Make canvas exactly the viewport size (no autoscaling)
        canvas.config(width=w * cell_size, height=h * cell_size)

        # Draw background cells inside viewport (if given)
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(y0, y0 + h):
                for col in range(x0, x0 + w):
                    key = f"{row},{col}"
                    if key in bg_boxes:
                        val = bg_boxes[key]
                        color = 'black' if (val != 0) else 'white'
                        if bg_default == 1:
                            color = 'white' if (val == 0) else 'black'
                    else:
                        color = 'white' if bg_default == 0 else 'black'
                    px = (col - x0) * cell_size
                    py = (row - y0) * cell_size
                    canvas.create_rectangle(px, py, px + cell_size, py + cell_size, fill=color, outline='gray')

        # Draw frame boxes inside viewport
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', 0)
        sf_color = frame.get('stick_figure_color', None)
        for row in range(y0, y0 + h):
            for col in range(x0, x0 + w):
                key = f"{row},{col}"
                if key in boxes:
                    val = boxes[key]
                    color = 'black' if (val != 0) else 'white'
                    if default_color == 1:
                        color = 'white' if (val == 0) else 'black'
                    if sf_color:
                        color = sf_color
                    px = (col - x0) * cell_size
                    py = (row - y0) * cell_size
                    canvas.create_rectangle(px, py, px + cell_size, py + cell_size, fill=color, outline='gray')

    def draw_frame_to_image(self, frame, background=None, cell_size=None, viewport=None):
        """
        Draw a frame to a PIL.Image using the viewport. The image size is viewport * cell_size.
        """
        cell_size = cell_size or self.cell_size
        if viewport is None:
            viewport = self.compute_viewport(frame)
        x0, y0, w, h = viewport

        img = Image.new('RGB', (w * cell_size, h * cell_size), 'white')
        draw = ImageDraw.Draw(img)

        # draw background
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(y0, y0 + h):
                for col in range(x0, x0 + w):
                    key = f"{row},{col}"
                    if key in bg_boxes:
                        val = bg_boxes[key]
                        color = (0, 0, 0) if (val != 0) else (255, 255, 255)
                        if bg_default == 1:
                            color = (255, 255, 255) if (val == 0) else (0, 0, 0)
                    else:
                        color = (255, 255, 255) if bg_default == 0 else (0, 0, 0)
                    xpix = (col - x0) * cell_size
                    ypix = (row - y0) * cell_size
                    draw.rectangle([xpix, ypix, xpix + cell_size, ypix + cell_size], fill=color, outline=(180, 180, 180))

        # draw frame boxes
        boxes = frame.get('boxes', {})
        default_color = frame.get('default_color', 0)
        sf_color = frame.get('stick_figure_color', None)
        for row in range(y0, y0 + h):
            for col in range(x0, x0 + w):
                key = f"{row},{col}"
                if key in boxes:
                    val = boxes[key]
                    color = (0, 0, 0) if (val != 0) else (255, 255, 255)
                    if default_color == 1:
                        color = (255,255,255) if (val == 0) else (0,0,0)
                    xpix = (col - x0) * cell_size
                    ypix = (row - y0) * cell_size
                    # Determine draw color when stick_figure_color present
                    if sf_color:
                        if isinstance(sf_color, str) and sf_color.startswith('#'):
                            draw_color = self.hex_to_rgb(sf_color)
                        else:
                            draw_color = (0,0,0) if str(sf_color).lower() == 'black' else (255,255,255)
                    else:
                        draw_color = color
                    draw.rectangle([xpix, ypix, xpix + cell_size, ypix + cell_size], fill=draw_color, outline=(180, 180, 180))
        return img

    # -------------------------
    # Export to video
    # -------------------------
    def export_to_video(self, filename="animation.mp4", fps=5):
        """
        Export animation frames to a video (MP4). Uses self.cell_size (no autoscaling).
        If lock_viewport is True a global viewport is used for all frames.
        """
        images = []
        global_viewport = None
        if self.lock_viewport:
            global_viewport = self.compute_global_viewport(self.frames)

        for i, frame in enumerate(self.frames):
            bg = self.backgrounds[i] if i < len(self.backgrounds) else None
            viewport = global_viewport if global_viewport is not None else self.compute_viewport(frame)
            img = self.draw_frame_to_image(frame, bg, cell_size=self.cell_size, viewport=viewport)
            frame_duration = int(self.timings[i])
            repeats = max(1, int((fps * frame_duration) / 1000))
            for _ in range(repeats):
                images.append(img.copy())
        # write video
        imageio.mimsave(filename, images, fps=fps)
        return True

    # -------------------------
    # Minimal animation-only window (new)
    # -------------------------
    def play_animation_window(self, animation_filename=None, cell_size=None, loop=False, fps=None, viewport_mode='stick-figure', lock_viewport=True):
        """
        Launch a minimal window that only plays the animation (no GUI controls).
        - animation_filename: optional path to an animation JSON saved by save_animation() or a single frame JSON.
            If provided, this method will load the animation before playing.
            If None, assumes frames are already loaded into the object.
        - cell_size: integer pixel size per grid cell; if None uses self.cell_size
        - loop: if True, loop the animation indefinitely
        - fps: optional export-ish frames-per-second. This method uses per-frame durations in self.timings for timing.
               If provided, it will be used only when durations are missing; otherwise timings[] control durations.
        - viewport_mode: one of 'full','half','stick-figure' - default 'stick-figure'
        - lock_viewport: if True compute global viewport and use it for entire playback (recommended)
        This function blocks until the animation window is closed. It is intended to be called by other modules.
        """
        # Load animation file if provided
        if animation_filename:
            # Support either complete animation JSON or single-frame JSONs
            # Try to parse as animation (saved collection) first
            try:
                with open(animation_filename, 'r') as f:
                    maybe = json.load(f)
                # Heuristic: if it has 'frames' key then it's the saved animation bundle
                if isinstance(maybe, dict) and 'frames' in maybe:
                    # Save to object and proceed
                    # Use load_animation-like assignment to populate data and viewport settings
                    self.frames = maybe.get('frames', [])
                    self.timings = maybe.get('timings', [200] * len(self.frames))
                    self.backgrounds = maybe.get('backgrounds', [None] * len(self.frames))
                    self.frame_names = maybe.get('frame_names', [f"Frame_{i+1}.json" for i in range(len(self.frames))])
                    self.background_names = maybe.get('background_names', [""] * len(self.frames))
                    # override viewport settings from arguments or saved file
                    self.viewport_mode = maybe.get('viewport_mode', viewport_mode)
                    self.viewport_padding = maybe.get('viewport_padding', self.viewport_padding)
                    self.viewport_min_w = maybe.get('viewport_min_w', self.viewport_min_w)
                    self.viewport_min_h = maybe.get('viewport_min_h', self.viewport_min_h)
                    self.lock_viewport = maybe.get('lock_viewport', lock_viewport)
                    # update grid meta from first frame, if present
                    if self.frames:
                        self.grid_width = self.frames[0].get('grid_width', self.grid_width)
                        self.grid_height = self.frames[0].get('grid_height', self.grid_height)
                        self.default_color = self.frames[0].get('default_color', self.default_color)
                else:
                    # treat as single-frame JSON
                    # Clear existing and add single frame
                    with open(animation_filename, 'r') as f2:
                        frame_data = json.load(f2)
                    self.frames = [frame_data]
                    self.timings = [200]
                    self.backgrounds = [None]
                    self.frame_names = [animation_filename.split("/")[-1]]
                    self.grid_width = frame_data.get('grid_width', self.grid_width)
                    self.grid_height = frame_data.get('grid_height', self.grid_height)
                    self.default_color = frame_data.get('default_color', self.default_color)
                    # use viewport_mode/lock_viewport provided in args
                    self.viewport_mode = viewport_mode
                    self.lock_viewport = lock_viewport
            except Exception as e:
                # If reading the file failed, raise for caller to handle
                raise RuntimeError(f"Could not load animation file '{animation_filename}': {e}")

        # Nothing to play
        if not self.frames:
            raise RuntimeError("No frames loaded to play. Load an animation before calling play_animation_window().")

        # Apply requested settings
        self.cell_size = self.cell_size if cell_size is None else int(cell_size)
        self.viewport_mode = viewport_mode
        self.lock_viewport = lock_viewport

        # Determine viewport for playback
        playback_viewport = None
        if self.lock_viewport:
            playback_viewport = self.compute_global_viewport(self.frames)
        else:
            # use stick-figure by default if caller didn't request otherwise
            playback_viewport = self.compute_viewport(self.frames[0])

        # Create a minimal Tk window and canvas sized to the viewport in pixels
        x0, y0, vw, vh = playback_viewport
        win = tk.Tk()
        win.title("Animation Player")
        canvas = tk.Canvas(win, width=vw * self.cell_size, height=vh * self.cell_size, bg='white')
        canvas.pack()

        # Play loop using after; convert frame durations (ms) -> schedule
        running = {'flag': True}

        def step(index):
            # stop if window was closed
            if not running['flag']:
                return
            if index >= len(self.frames):
                if loop:
                    index = 0
                else:
                    # finished - close the window and stop
                    win.destroy()
                    return
            frame = self.frames[index]
            bg = self.backgrounds[index] if index < len(self.backgrounds) else None

            # If not locking viewport, compute per-frame viewport (but caller requested stick-figure default)
            viewport = playback_viewport if self.lock_viewport else self.compute_viewport(frame)
            # draw the frame
            self.draw_frame_on_canvas(canvas, frame, background=bg, cell_size=self.cell_size, viewport=viewport)

            # determine duration to next frame: prefer timings[], if missing fall back to fps if provided, else 200ms
            duration = 200
            if index < len(self.timings):
                duration = int(self.timings[index])
            elif fps:
                duration = int(1000.0 / float(fps))
            # schedule next
            win.after(duration, lambda: step(index + 1))

        # capture window close so we stop the playback loop gracefully
        def on_close():
            running['flag'] = False
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", on_close)
        # kick off playback
        step(0)
        # block here until window is closed
        win.mainloop()

    # -------------------------
    # Full editor/player GUI (unchanged) - retained for dev convenience
    # -------------------------
    def run_animation_gui(self):
        """Run the full editor/player GUI with controls (this existed previously)."""
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

        # utilities
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
            # read UI viewport settings into object state
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()

            frame = self.frames[idx]
            bg = self.backgrounds[idx] if idx < len(self.backgrounds) else None

            # choose viewport
            if self.lock_viewport and len(self.frames) > 0:
                viewport = self.compute_global_viewport(self.frames)
            else:
                viewport = self.compute_viewport(frame)

            self.draw_frame_on_canvas(canvas, frame, background=bg, cell_size=self.cell_size, viewport=viewport)

        def on_listbox_select(evt):
            sel = frame_listbox.curselection()
            if sel:
                draw_frame_index(sel[0])

        frame_listbox.bind("<<ListboxSelect>>", on_listbox_select)

        # implementations for the control buttons (add, set bg, save, load, export)
        def add_frame():
            stick_path = filedialog.askopenfilename(title="Add Stick Figure Frame JSON",
                                                    filetypes=[("JSON files", "*.json")])
            if not stick_path:
                return
            bg_path = filedialog.askopenfilename(title="Add Background JSON (optional)",
                                                 filetypes=[("JSON files", "*.json")])
            self.add_frame_from_json(stick_path, 200, bg_path if bg_path else None)
            update_listbox()
            frame_listbox.selection_clear(0, tk.END)
            frame_listbox.selection_set(len(self.frames) - 1)
            draw_frame_index(len(self.frames) - 1)

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
            viewport_var.set(self.viewport_mode)
            padding_var.set(self.viewport_padding)
            minw_var.set(self.viewport_min_w)
            minh_var.set(self.viewport_min_h)
            lock_var.set(self.lock_viewport)
            update_listbox()
            if self.frames:
                frame_listbox.selection_set(0)
                draw_frame_index(0)
            messagebox.showinfo("Loaded", f"Loaded animation {filename}")

        def export_video():
            filename = filedialog.asksaveasfilename(title="Export to MP4",
                                                    filetypes=[("MP4 Video", "*.mp4")],
                                                    defaultextension=".mp4")
            if not filename:
                return
            self.viewport_mode = viewport_var.get()
            self.viewport_padding = int(padding_var.get())
            self.viewport_min_w = int(minw_var.get())
            self.viewport_min_h = int(minh_var.get())
            self.lock_viewport = lock_var.get()
            try:
                self.export_to_video(filename, fps=5)
                messagebox.showinfo("Exported", f"Exported animation as {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

        # play controls (uses same underlying draw_frame_on_canvas)
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
                self.draw_frame_on_canvas(canvas, frame, background=bg, cell_size=self.cell_size, viewport=viewport)
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

        # Double-click to edit duration
        def on_double_click(event):
            edit_duration()

        frame_listbox.bind("<Double-Button-1>", on_double_click)

        # Initialize listbox and draw first frame if available
        update_listbox()
        if self.frames:
            frame_listbox.selection_set(0)
            draw_frame_index(0)

        root.mainloop()


# -------------------------
# Example: minimal command mapping for quick programmatic deployment
# -------------------------
if __name__ == "__main__":
    """
    Example interface for a simple command -> animation mapping.
    This demonstrates how a higher-level system (LLM or script) can choose an animation by name.
    Replace 'animation1.json' with a real animation file you have.

    Run this file directly and type a command at the prompt (e.g. "wave") to play the mapped animation.
    """
    if input("Do you want to access the GUI?") == "yes":
        anim = StickFigureAnimation()
        anim.run_animation_gui()
    else:
    # Map simple commands to animation filenames
        command_map = {
            'wave': 'animations/animation1.json',   # example - replace with your actual file
        # add other mappings here, e.g. 'jump': 'jump_animation.json'
        }

    # Minimal text prompt to demo usage
        print("Demo: type a command like 'wave' to play the corresponding animation. Type 'quit' to exit.")
        while True:
            cmd = input("command> ").strip().lower()
            if cmd in ('q', 'quit', 'exit'):
                break
            if cmd not in command_map:
                print(f"No animation mapped for '{cmd}'. Available: {list(command_map.keys())}")
                continue
            filename = command_map[cmd]
            anim = StickFigureAnimation()
            try:
                # Play animation in a minimal window. This call blocks until the window is closed.
                anim.play_animation_window(animation_filename=filename, cell_size=10, loop=True, viewport_mode='stick-figure', lock_viewport=True)
            except Exception as e:
                print(f"Error playing animation '{filename}': {e}")