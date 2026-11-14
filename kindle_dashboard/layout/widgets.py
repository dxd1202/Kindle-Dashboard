"""Build the JSON drawing commands understood by the C++ renderer."""

import re

LEFT, RIGHT = 58, 1390
DARK, MUTED, RULE, PALE = 16, 75, 177, 235


class Widgets:
    def __init__(self):
        self.items = []

    def text(self, x, y, content, size=36, *, gray=DARK, align="left", bold=False,
             max_width=0, font="main-font.ttf", center_y=False, fit_width=False):
        # The legacy renderer treats several characters as formatting commands.
        content = re.sub(r"[▷▶↑↓○\t\r\n]+", " ", str(content)).strip()
        if content:
            self.items.append({
                "x": x, "y": y, "content": ("▷" if bold else "") + content,
                "size": size, "gray": gray, "align": align, "max_width": max_width,
                "font": font, "center_y": center_y, "bold": bold, "fit_width": fit_width,
            })

    def rect(self, x, y, right, bottom, gray=RULE):
        self.items.append({
            "type": "rect", "left": x, "top": y, "right": right, "bottom": bottom,
            "gray": gray,
        })

    def line(self, x, y, end, gray=RULE, thickness=2):
        self.rect(x, y, end, y + thickness, gray)
