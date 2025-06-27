import os
from PIL import Image


class StaticGrid:
    def __init__(self, grid_config, cell_size=10, templates_dir='templates', images_dir='images'):
        self.grid = grid_config
        self.cell_size = cell_size
        self.grid_size = len(grid_config)
        self.templates_dir = templates_dir
        self.images_dir = images_dir
        self.image = Image.new('RGB', (self.grid_size * cell_size, self.grid_size * cell_size), 'white')

    def load_template(self, name):
        path = os.path.join(self.templates_dir, name)
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    def load_image(self, name):
        path = os.path.join(self.images_dir, name)
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    def render_grid(self, black_template=None, white_template=None):
        black_img = self.load_template(black_template) if black_template else None
        white_img = self.load_template(white_template) if white_template else None

        for row in range(self.grid_size):
            for col in range(self.grid_size):
                x = col * self.cell_size
                y = row * self.cell_size
                if self.grid[row][col] == 1:
                    if black_img:
                        self.image.paste(black_img.resize((self.cell_size, self.cell_size)), (x, y), black_img)
                    else:
                        self.image.paste((0, 0, 0), [x, y, x + self.cell_size, y + self.cell_size])
                else:
                    if white_img:
                        self.image.paste(white_img.resize((self.cell_size, self.cell_size)), (x, y), white_img)
                    else:
                        self.image.paste((255, 255, 255), [x, y, x + self.cell_size, y + self.cell_size])

    def save(self, filename):
        self.image.save(filename)

    def get_image(self):
        return self.image
