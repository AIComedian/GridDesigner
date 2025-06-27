import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import interactivegrid
import json
import os

class SetStickFigure(interactivegrid.InteractiveGrid):
    def __init__(self, root, grid_width=120, grid_height=72, cell_size=10, default_color=0, stick_figure_template=None):
        self.special_squares = {}
        self.root = root

        # Frame for controls and canvas
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(side=tk.TOP, fill=tk.X)
        self.save_button = tk.Button(self.button_frame, text="Save Stick Figure", command=self.save_stick_figure)
        self.save_button.pack(side=tk.LEFT)
        self.import_button = tk.Button(self.button_frame, text="Import Template", command=self.import_template)
        self.import_button.pack(side=tk.LEFT)

        # Call InteractiveGrid with main_frame as parent, so canvas is below buttons
        super().__init__(self.main_frame, grid_width, grid_height, cell_size, default_color)

        self.joint_names = [
            'head_c', 'neck', 'shoulder', 'l_shoulder', 'r_shoulder',
            'hip', 'l_hip', 'r_hip',
            'l_elbow', 'r_elbow', 'l_hand', 'r_hand',
            'l_knee', 'r_knee', 'l_foot', 'r_foot'
        ]
        self.joint_vars = {}
        self.max_joints = len(self.joint_names)

        # If a template is provided, use it; otherwise, use default stick figure template
        if stick_figure_template is not None:
            self.apply_template(stick_figure_template)
        else:
            self.load_default_template()
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.on_click)

    def load_default_template(self):
        # Import stickfigure.py and use its standing pose as template
        try:
            import stickfigure
            sf_grid = stickfigure.StickFigure(self)
            # Now, mark all non-default squares as contrast (not red) for editing
            for (row, col), color in self.get_diff_cells().items():
                self.grid[row][col] = color
                self.special_squares[(row, col)] = 0
            # Optionally, add default joints from stickfigure.py if desired
        except Exception as e:
            messagebox.showinfo("Error", f"Could not load default stick figure: {e}")

    def import_template(self):
        file_path = filedialog.askopenfilename(
            title="Import Stick Figure Template",
            filetypes=[("JSON files", "*.json")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                template = json.load(f)
            self.apply_template(template)
            self.draw_grid()
            messagebox.showinfo("Imported", f"Template {os.path.basename(file_path)} imported!")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def apply_template(self, template):
        # Clear grid and state
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                self.grid[r][c] = self.default_color
        self.special_squares = {}
        self.joint_vars = {}

        # Load joints
        if "joints" in template:
            self.joint_vars = {k: tuple(v) for k, v in template["joints"].items()}
        # Load diff boxes (including joints)
        if "boxes" in template:
            for key, color in template["boxes"].items():
                row, col = map(int, key.split(","))
                self.grid[row][col] = color
                if tuple([row, col]) in self.joint_vars.values():
                    self.special_squares[(row, col)] = 1
                else:
                    self.special_squares[(row, col)] = 0

    def draw_grid(self):
        self.canvas.delete("all")
        for row in range(self.grid_height):
            for col in range(self.grid_width):
                key = (row, col)
                if self.special_squares.get(key, 0) == 1:
                    color = 'red'
                elif self.grid[row][col] == self.default_color:
                    color = 'white' if self.default_color == 0 else 'black'
                else:
                    color = 'black' if self.default_color == 0 else 'white'
                x0 = col * self.cell_size
                y0 = row * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')

    def on_click(self, event):
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        key = (row, col)
        if not (0 <= row < self.grid_height and 0 <= col < self.grid_width):
            return

        # Cycle: default -> contrast -> red -> default
        current_state = 0
        if self.special_squares.get(key, 0) == 1:
            current_state = 2  # red
        elif self.grid[row][col] != self.default_color:
            current_state = 1  # contrast

        if current_state == 0:
            # Default -> contrast
            self.grid[row][col] = 1 if self.default_color == 0 else 0
            self.special_squares[key] = 0
        elif current_state == 1:
            # Contrast -> red
            reds = [k for k, v in self.special_squares.items() if v == 1]
            if len(reds) >= self.max_joints:
                messagebox.showerror("Too many joints", f"Cannot have more red joints than variables ({self.max_joints})")
                self.draw_grid()
                return
            self.special_squares[key] = 1
            joint = self.assign_joint_variable(key)
            if joint:
                self.joint_vars[joint] = key
        elif current_state == 2:
            # Red -> default
            self.special_squares[key] = 0
            self.grid[row][col] = self.default_color
            # Remove joint assignment
            for var, pos in list(self.joint_vars.items()):
                if pos == key:
                    del self.joint_vars[var]

        self.draw_grid()

    def assign_joint_variable(self, key):
        used_names = set(self.joint_vars.keys())
        avail = [n for n in self.joint_names if n not in used_names]
        prompt = f"Assign a joint variable for red square at {key}:\nAvailable: {avail}\n(Type a name or select from available)"
        name = simpledialog.askstring("Assign Joint", prompt, parent=self.root)
        if name is None:
            return None
        name = name.strip()
        if name not in self.joint_names:
            messagebox.showerror("Invalid Name", f"{name} is not a valid joint name.")
            return None
        if name in self.joint_vars:
            messagebox.showerror("Already Assigned", f"{name} is already assigned to {self.joint_vars[name]}.")
            return None
        return name

    def save_stick_figure(self):
        stick_name = simpledialog.askstring("Save Stick Figure", "Enter stick figure name:", parent=self.root)
        if not stick_name:
            return
        # Save only boxes that differ from default
        diff_cells = self.get_diff_cells()
        # Save joints as a dict of joint_name: [row, col]
        joints = {k: [v[0], v[1]] for k, v in self.joint_vars.items()}

        # Save all diff cells, including joints, as string keys for JSON
        boxes = {f"{row},{col}": self.grid[row][col] for (row, col) in diff_cells}

        data = {
            'name': stick_name,
            'joints': joints,
            'boxes': boxes,
            'default_color': self.default_color,
            'grid_width': self.grid_width,
            'grid_height': self.grid_height,
        }
        filename = stick_name
        if not filename.endswith('.json'):
            filename += '.json'
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"Stick figure '{stick_name}' saved as {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Set Stick Figure (Manual Joint Assignment)")
    set_stick = SetStickFigure(root)

    print()
    root.mainloop()