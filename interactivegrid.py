import tkinter as tk

class InteractiveGrid:
    def __init__(self, root, grid_width=120, grid_height=72, cell_size=10, default_color=0):
        """
        default_color: 0 for white, 1 for black.
        """
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.cell_size = cell_size
        self.canvas_width = grid_width * cell_size
        self.canvas_height = grid_height * cell_size
        self.default_color = default_color  # Now set at init!
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack()

        # 0 = white, 1 = black
        self.grid = [[self.default_color for _ in range(grid_width)] for _ in range(grid_height)]
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.on_click)

    def draw_grid(self):
        self.canvas.delete("all")
        for row in range(self.grid_height):
            for col in range(self.grid_width):
                color = 'black' if self.grid[row][col] else 'white'
                x0 = col * self.cell_size
                y0 = row * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')

    def on_click(self, event):
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if 0 <= row < self.grid_height and 0 <= col < self.grid_width:
            # Toggle cell
            self.grid[row][col] = 1 - self.grid[row][col]
            self.draw_cell(row, col)

    def draw_cell(self, row, col):
        x0 = col * self.cell_size
        y0 = row * self.cell_size
        x1 = x0 + self.cell_size
        y1 = y0 + self.cell_size
        color = 'black' if self.grid[row][col] else 'white'
        self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='gray')

    def check_cordinates(self, x, y):
        return 0 <= x < self.grid_width and 0 <= y < self.grid_height

    def draw_line(self, x0, y0, x1, y1, color=1):
        if self.check_cordinates(x0, y0) and self.check_cordinates(x1, y1):
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            x, y = x0, y0
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            if dx > dy:
                err = dx / 2.0
                while x != x1:
                    if self.check_cordinates(x, y):
                        self.grid[y][x] = color
                        self.draw_cell(y, x)
                    err -= dy
                    if err < 0:
                        y += sy
                        err += dx
                    x += sx
            else:
                err = dy / 2.0
                while y != y1:
                    if self.check_cordinates(x, y):
                        self.grid[y][x] = color
                        self.draw_cell(y, x)
                    err -= dx
                    if err < 0:
                        x += sx
                        err += dy
                    y += sy
            if self.check_cordinates(x, y):
                self.grid[y][x] = color
                self.draw_cell(y, x)
        else:
            return "coordinates are not valid"

    def draw_circle(self, cx, cy, radius, color=1):
        if radius < 1:
            raise ValueError("Minimum radius is 1 (3 grid squares diameter)")
        x = radius
        y = 0
        d = 1 - radius
        while x >= y:
            circle_points = [
                (cx + x, cy + y),
                (cx + y, cy + x),
                (cx - y, cy + x),
                (cx - x, cy + y),
                (cx - x, cy - y),
                (cx - y, cy - x),
                (cx + y, cy - x),
                (cx + x, cy - y),
            ]
            for px, py in circle_points:
                if self.check_cordinates(px, py):
                    self.grid[py][px] = color
                    self.draw_cell(py, px)
            y += 1
            if d <= 0:
                d = d + 2 * y + 1
            else:
                x -= 1
                d = d + 2 * (y - x) + 1

    def draw_minimum_circle(self, cx, cy, color=1):
        self.draw_circle(cx, cy, radius=1, color=color)

    def get_diff_cells(self):
        """Return dict of {(row, col): color} for squares different from default_color."""
        diffs = {}
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                if self.grid[r][c] != self.default_color:
                    diffs[(r, c)] = self.grid[r][c]
        return diffs

# --- Run the app
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Interactive Grid")
    # 120x72 grid, each cell 10x10 = 1200x720 window (good for stick figures and animation)
    app = InteractiveGrid(root, grid_width=120, grid_height=72, cell_size=10)

    # Example: Draw a minimum circle at (10, 10)
    app.draw_minimum_circle(10, 10)
    # Example: Draw a larger circle at (30, 30) with radius 8
    app.draw_circle(30, 30, radius=8)

    root.mainloop()