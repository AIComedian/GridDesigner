import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import interactivegrid
import json

class SetBackground(interactivegrid.InteractiveGrid):
    def __init__(self, root, grid_width=120, grid_height=72, cell_size=10, default_color=0, background_template=None):
        self.root = root
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(side=tk.TOP, fill=tk.X)

        self.save_button = tk.Button(self.button_frame, text="Save Background", command=self.save_background)
        self.save_button.pack(side=tk.LEFT)
        self.import_button = tk.Button(self.button_frame, text="Import Background", command=self.import_background)
        self.import_button.pack(side=tk.LEFT)

        super().__init__(self.main_frame, grid_width, grid_height, cell_size, default_color)

        if background_template is not None:
            self.apply_template(background_template)
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.on_click)

    def apply_template(self, template):
        # Clear grid
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                self.grid[r][c] = self.default_color
        # Load diff boxes
        if "boxes" in template:
            for key, color in template["boxes"].items():
                row, col = map(int, key.split(","))
                self.grid[row][col] = color

    def save_background(self):
        name = simpledialog.askstring("Save Background", "Enter background name:", parent=self.root)
        if not name:
            return
        diff_cells = self.get_diff_cells()
        boxes = {f"{row},{col}": self.grid[row][col] for (row, col) in diff_cells}
        data = {
            'name': name,
            'boxes': boxes,
            'default_color': self.default_color,
            'grid_width': self.grid_width,
            'grid_height': self.grid_height,
        }
        filename = name
        if not filename.endswith('.json'):
            filename += '.json'
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"Background '{name}' saved as {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def import_background(self):
        file_path = filedialog.askopenfilename(
            title="Import Background Template",
            filetypes=[("JSON files", "*.json")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                template = json.load(f)
            self.apply_template(template)
            self.draw_grid()
            messagebox.showinfo("Imported", f"Template {file_path} imported!")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Set Background Scene")
    bg = SetBackground(root)
    root.mainloop()