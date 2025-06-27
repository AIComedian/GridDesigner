import json
import tkinter as tk

class StickFigureAnimation:
    def __init__(self):
        self.frames = []   # List of dicts: each dict is a stick figure frame
        self.timings = []  # List of durations (milliseconds) for each frame

    def load_animation_from_jsons(self, json_files, timings=None):
        """Load a sequence of stick figure JSON files as frames."""
        self.frames = []
        self.timings = []
        for i, json_file in enumerate(json_files):
            with open(json_file, "r") as f:
                frame_data = json.load(f)
            self.frames.append(frame_data)
            # Use timings array if given, else default to 200ms for all
            if timings and i < len(timings):
                self.timings.append(int(timings[i]))
            else:
                self.timings.append(200)

    def add_frame(self, stick_figure_json, duration=200):
        """Add a single frame from a stick figure json and its duration (ms)."""
        with open(stick_figure_json, "r") as f:
            frame_data = json.load(f)
        self.frames.append(frame_data)
        self.timings.append(int(duration))

    def get_frame(self, index):
        """Return the stick figure dict and duration for a given frame index."""
        return self.frames[index], self.timings[index]

    def save_animation(self, filename):
        """Save the animation as a list of frames and timings."""
        animation_data = {
            "frames": self.frames,
            "timings": self.timings
        }
        with open(filename, "w") as f:
            json.dump(animation_data, f, indent=2)

    def load_animation(self, filename):
        """Load an animation from a file."""
        with open(filename, "r") as f:
            data = json.load(f)
        self.frames = data["frames"]
        self.timings = data["timings"]

    def run_animation(self, cell_size=10, default_color=None):
        """GUI: Play the animation with start, replay, and stop."""
        if not self.frames:
            print("No frames loaded!")
            return

        # Set up TKinter window
        root = tk.Tk()
        root.title("Stick Figure Animation")

        # Use frame size from first frame
        grid_width = self.frames[0]['grid_width']
        grid_height = self.frames[0]['grid_height']
        frame_default_color = self.frames[0].get("default_color", 0) if default_color is None else default_color

        canvas_width = grid_width * cell_size
        canvas_height = grid_height * cell_size

        # Layout with a main frame
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame, width=canvas_width, height=canvas_height, bg='white')
        canvas.pack(side=tk.TOP)

        # Buttons frame at bottom
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, pady=8)

        running = {'flag': False, 'loop': False}

        def draw_frame(frame):
            canvas.delete("all")
            boxes = frame['boxes']
            # Draw main body
            for row in range(grid_height):
                for col in range(grid_width):
                    box_key = f"{row},{col}"
                    # Determine cell color
                    if box_key in boxes:
                        val = boxes[box_key]
                        color = 'black' if (val != 0) else 'white'
                        if frame.get('default_color', frame_default_color) == 1:
                            color = 'white' if (val == 0) else 'black'
                    else:
                        color = 'white' if frame.get('default_color', frame_default_color) == 0 else 'black'
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')
            # Draw joints as red
            if 'joints' in frame:
                for pos in frame['joints'].values():
                    row, col = pos
                    x0 = col * cell_size
                    y0 = row * cell_size
                    x1 = x0 + cell_size
                    y1 = y0 + cell_size
                    canvas.create_rectangle(x0, y0, x1, y1, fill='red', outline='red')

        def play_animation(loop=False):
            running['flag'] = True
            running['loop'] = loop

            def step(index):
                if not running['flag']:
                    return
                frame, duration = self.get_frame(index)
                draw_frame(frame)
                next_index = index + 1
                if next_index < len(self.frames):
                    root.after(duration, lambda: step(next_index))
                elif running['loop']:
                    root.after(duration, lambda: step(0))
                else:
                    running['flag'] = False  # Stop after playing once

            step(0)

        def stop_animation():
            running['flag'] = False

        # Buttons
        start_btn = tk.Button(btn_frame, text="Start", command=lambda: play_animation(loop=False))
        start_btn.pack(side=tk.LEFT, padx=5)
        replay_btn = tk.Button(btn_frame, text="Replay", command=lambda: play_animation(loop=True))
        replay_btn.pack(side=tk.LEFT, padx=5)
        stop_btn = tk.Button(btn_frame, text="Stop", command=stop_animation)
        stop_btn.pack(side=tk.LEFT, padx=5)

        # Draw first frame on load for preview
        draw_frame(self.frames[0])

        root.mainloop()

if __name__ == "__main__":
    anim = StickFigureAnimation()
    anim.load_animation_from_jsons(["stand - wide stance.json", "wave1.json"], timings=[200, 400])
    anim.run_animation()