class Stroke:
    def __init__(self, points, color, thickness, mode="draw"):
        self.points = points  # Lista de [x, y]
        self.color = color    # (r, g, b)
        self.thickness = thickness
        self.mode = mode      # draw | erase | enhance
