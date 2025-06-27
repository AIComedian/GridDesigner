import interactivegrid
import tkinter as tk
class StickFigure:
    def __init__(self, grid, center=None, position='standing'):
        if not isinstance(grid, interactivegrid.InteractiveGrid):
            global root
            self.grid = interactivegrid.InteractiveGrid(root)
        else:
            self.grid = grid

        if hasattr(self.grid, 'grid_width') and hasattr(self.grid, 'grid_height'):
            self.grid_width = self.grid.grid_width
            self.grid_height = self.grid.grid_height
        else:
            self.grid_width = self.grid.grid_size
            self.grid_height = self.grid.grid_size

        if center is None:
            self.center = [self.grid_width // 2, self.grid_height // 2]
        else:
            self.center = center

        self.position = position

        self.neck_len = 2
        self.head_radius = 3
        self.body_len = 10
        self.arm_len = 8
        self.elbow_offset = 4
        self.leg_len = 10
        self.knee_offset = 5
        self.joint_bar_width = 2

        self.joints = {}
        self.set_position(position)

    def set_position(self, position):
        c_x, c_y = self.center
        head_c = (c_x, c_y - self.neck_len - self.head_radius)
        neck = (c_x, c_y - self.neck_len)
        l_shoulder = (c_x - 1, c_y)
        shoulder = (c_x, c_y)
        r_shoulder = (c_x + 1, c_y)
        hip_y = c_y + self.body_len
        l_hip = (c_x - 1, hip_y)
        hip = (c_x, hip_y)
        r_hip = (c_x + 1, hip_y)
        l_elbow = (l_shoulder[0] - self.elbow_offset, l_shoulder[1] + self.elbow_offset)
        l_hand = (l_elbow[0] - (self.arm_len - self.elbow_offset), l_elbow[1])
        r_elbow = (r_shoulder[0] + self.elbow_offset, r_shoulder[1] + self.elbow_offset)
        r_hand = (r_elbow[0] + (self.arm_len - self.elbow_offset), r_elbow[1])
        l_knee = (l_hip[0] - self.knee_offset, l_hip[1] + self.knee_offset)
        l_foot = (l_knee[0], l_knee[1] + (self.leg_len - self.knee_offset))
        r_knee = (r_hip[0] + self.knee_offset, r_hip[1] + self.knee_offset)
        r_foot = (r_knee[0], r_knee[1] + (self.leg_len - self.knee_offset))

        self.joints = {
            'head_c': head_c,
            'neck': neck,
            'l_shoulder': l_shoulder,
            'shoulder': shoulder,
            'r_shoulder': r_shoulder,
            'l_hip': l_hip,
            'hip': hip,
            'r_hip': r_hip,
            'l_elbow': l_elbow,
            'r_elbow': r_elbow,
            'l_hand': l_hand,
            'r_hand': r_hand,
            'l_knee': l_knee,
            'r_knee': r_knee,
            'l_foot': l_foot,
            'r_foot': r_foot,
        }
        self.draw_figure()

    def draw_figure(self):
        g = self.grid
        j = self.joints
        g.grid = [[g.default_color for _ in range(g.grid_width)] for _ in range(g.grid_height)]
        g.draw_grid()
        fg = 1 - g.default_color  # Figure color is opposite of default
        g.draw_circle(int(j['head_c'][0]), int(j['head_c'][1]), self.head_radius, color=fg)
        g.draw_line(int(j['head_c'][0]), int(j['head_c'][1]+self.head_radius), int(j['neck'][0]), int(j['neck'][1]), color=fg)
        g.draw_line(int(j['l_shoulder'][0]), int(j['l_shoulder'][1]), int(j['r_shoulder'][0]), int(j['r_shoulder'][1]), color=fg)
        g.draw_line(int(j['shoulder'][0]), int(j['shoulder'][1]), int(j['hip'][0]), int(j['hip'][1]), color=fg)
        g.draw_line(int(j['l_hip'][0]), int(j['l_hip'][1]), int(j['r_hip'][0]), int(j['r_hip'][1]), color=fg)
        g.draw_line(int(j['l_shoulder'][0]), int(j['l_shoulder'][1]), int(j['l_elbow'][0]), int(j['l_elbow'][1]), color=fg)
        g.draw_line(int(j['l_elbow'][0]), int(j['l_elbow'][1]), int(j['l_hand'][0]), int(j['l_hand'][1]), color=fg)
        g.draw_line(int(j['r_shoulder'][0]), int(j['r_shoulder'][1]), int(j['r_elbow'][0]), int(j['r_elbow'][1]), color=fg)
        g.draw_line(int(j['r_elbow'][0]), int(j['r_elbow'][1]), int(j['r_hand'][0]), int(j['r_hand'][1]), color=fg)
        g.draw_line(int(j['l_hip'][0]), int(j['l_hip'][1]), int(j['l_knee'][0]), int(j['l_knee'][1]), color=fg)
        g.draw_line(int(j['l_knee'][0]), int(j['l_knee'][1]), int(j['l_foot'][0]), int(j['l_foot'][1]), color=fg)
        g.draw_line(int(j['r_hip'][0]), int(j['r_hip'][1]), int(j['r_knee'][0]), int(j['r_knee'][1]), color=fg)
        g.draw_line(int(j['r_knee'][0]), int(j['r_knee'][1]), int(j['r_foot'][0]), int(j['r_foot'][1]), color=fg)

    def get_diff_cells(self):
        return self.grid.get_diff_cells()

if __name__ == "__main__":
    # Create a root window
    root = tk.Tk()
    root.title("Stick Figure on Interactive Grid")

    # Create the grid (same size as your animation grid)
    grid = interactivegrid.InteractiveGrid(root, grid_width=120, grid_height=72, cell_size=10)

    # Create and draw a stick figure in the center
    stick_figure = StickFigure(grid)

    root.mainloop()