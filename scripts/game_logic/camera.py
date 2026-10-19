# scripts/game_logic/camera.py
"""2D-камера с поддержкой зума.

camera.x / camera.y — мировые координаты левого верхнего угла
видимой области. При зуме > 1 видимая область уменьшается,
и при рендере итоговая картинка масштабируется вверх.
"""


class Camera:
    MIN_ZOOM = 0.5
    MAX_ZOOM = 4.0

    def __init__(self, screen_w: int, screen_h: int, zoom: float = 1.0):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x = 0.0
        self.y = 0.0
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))

    # ------------------------------------------------------------------
    # Видимая область (в мировых пикселях)
    # ------------------------------------------------------------------
    @property
    def view_w(self) -> float:
        return self.screen_w / self.zoom

    @property
    def view_h(self) -> float:
        return self.screen_h / self.zoom

    # ------------------------------------------------------------------
    # Управление
    # ------------------------------------------------------------------
    def center_on(self, wx: float, wy: float) -> None:
        self.x = wx - self.view_w * 0.5
        self.y = wy - self.view_h * 0.5

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))

    def zoom_by(self, factor: float) -> None:
        self.set_zoom(self.zoom * factor)

    # ------------------------------------------------------------------
    # Преобразования
    # ------------------------------------------------------------------
    def world_to_screen(self, wx: float, wy: float):
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx: float, sy: float):
        return sx / self.zoom + self.x, sy / self.zoom + self.y
    