class Entity:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        
        