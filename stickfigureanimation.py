import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw
import imageio


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
            "background_names": self.background_names
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
        self.grid_width = self.frames[0].get('grid_width', self.grid_width)
        self.grid_height = self.frames[0].get('grid_height', self.grid_height)
        self.default_color = self.frames[0].get('default_color', self.default_color)

    def draw_frame_on_canvas(self, canvas, frame, background=None, cell_size=None):
        canvas.delete("all")
        grid_width = frame['grid_width']
        grid_height = frame['grid_height']
        default_color = frame.get('default_color', 0)
        cell_size = cell_size or self.cell_size

        # Draw background first
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(grid_height):
                for col in range(grid_width):
                    box_key = f"{row},{col}"
                    if box_key in bg_boxes:
                        val = bg_boxes[box_key]
                        color = 'black' if (val != 0) else 'white'
                        if bg_default == 1:
                            color = 'white' if (val == 0) else 'black'
                    else:
                        color = 'white' if bg_default == 0 else 'black'
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')
        # Draw stick figure over background
        boxes = frame['boxes']
        for row in range(grid_height):
            for col in range(grid_width):
                box_key = f"{row},{col}"
                if box_key in boxes:
                    val = boxes[box_key]
                    color = 'black' if (val != 0) else 'white'
                    if default_color == 1:
                        color = 'white' if (val == 0) else 'black'
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')

    def draw_frame_to_image(self, frame, background=None, cell_size=None):
        grid_width = frame['grid_width']
        grid_height = frame['grid_height']
        default_color = frame.get('default_color', 0)
        cell_size = cell_size or self.cell_size
        img = Image.new('RGB', (grid_width * cell_size, grid_height * cell_size), 'white')
        draw = ImageDraw.Draw(img)
        if background and "boxes" in background:
            bg_boxes = background["boxes"]
            bg_default = background.get('default_color', 0)
            for row in range(grid_height):
                for col in range(grid_width):
                    box_key = f"{row},{col}"
                    if box_key in bg_boxes:
                        val = bg_boxes[box_key]
                        color = (0,0,0) if (val != 0) else (255,255,255)
                        if bg_default == 1:
                            color = (255,255,255) if (val == 0) else (0,0,0)
                    else:
                        color = (255,255,255) if bg_default == 0 else (0,0,0)
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    draw.rectangle([x0, y0, x1, y1], fill=color, outline=(180,180,180))
        boxes = frame['boxes']
        for row in range(grid_height):
            for col in range(grid_width):
                box_key = f"{row},{col}"
                if box_key in boxes:
                    val = boxes[box_key]
                    color = (0,0,0) if (val != 0) else (255,255,255)
                    if default_color == 1:
                        color = (255,255,255) if (val == 0) else (0,0,0)
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    draw.rectangle([x0, y0, x1, y1], fill=color, outline=(180,180,180))
        return img

    def export_to_video(self, filename="animation.mp4", fps=5):
        images = []
        for i, frame in enumerate(self.frames):
            background = self.backgrounds[i] if i < len(self.backgrounds) else None
            img = self.draw_frame_to_image(frame, background)
            frame_duration = int(self.timings[i])
            repeats = max(1, int((fps * frame_duration) / 1000))
            for _ in range(repeats):
                images.append(img.copy())
        imageio.mimsave(filename, [img for img in images], fps=fps)
        return True

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
            frame = self.frames[idx]
            background = self.backgrounds[idx] if idx < len(self.backgrounds) else None
            self.draw_frame_on_canvas(canvas, frame, background, cell_size=current_cell_size[0])

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
            self.save_animation(filename)
            messagebox.showinfo("Saved", f"Animation saved as {filename}")

        def load_animation():
            filename = filedialog.askopenfilename(title="Load Animation JSON",
                                                  filetypes=[("JSON files", "*.json")])
            if not filename:
                return
            self.load_animation(filename)
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
                cell_size_w = new_width // self.grid_width
                cell_size_h = new_height // self.grid_height
                cell_size = max(1, min(cell_size_w, cell_size_h))
                current_cell_size[0] = cell_size
                # force canvas to be a multiple of cell size
                canvas.config(width=self.grid_width * cell_size,
                              height=self.grid_height * cell_size)
                idx = frame_listbox.curselection()
                idx = idx[0] if idx else 0
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
    #anim.load_animation_from_jsons(["highWave1.json", "highWave2.json"], timings=[200,200])
    #anim.load_animation_from_jsons(["stand - wide stance.json", "wave1.json", "wave2.json"], timings=[200, 200, 400])
    #anim.run_animation(background_json="centerstage1.json")
    anim.run_animation_gui()