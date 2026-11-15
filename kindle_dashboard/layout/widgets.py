"""Build the JSON drawing commands understood by the C++ renderer."""

import re

LEFT, RIGHT = 24, 1424
HEADER_RULE_Y, FOOTER_RULE_Y = 124, 1030
HEADER_RULE_HEIGHT = 3
WEATHER_WIDTH = 600
BLACK, DARK, MUTED, RULE, PALE = 0, 16, 75, 177, 235


class Widgets:
    def __init__(self):
        self.items = []

    def text(self, x, y, content, size=36, *, gray=BLACK, align="left", bold=False,
             max_width=0, font="main-font.ttf", center_y=False, fit_width=False, emphasis=None):
        content = re.sub(r"[\t\r\n]+", " ", str(content)).strip()
        if content:
            self.items.append({
                "x": x, "y": y, "content": content,
                "size": size, "gray": gray, "align": align, "max_width": max_width,
                "font": font, "center_y": center_y, "bold": bold, "fit_width": fit_width,
            })
            if emphasis is not None:
                start, end = emphasis
                self.items[-1]["emphasis"] = [
                    len(content[:start].encode()), len(content[:end].encode()),
                ]

    def rect(self, x, y, right, bottom, gray=RULE):
        self.items.append({
            "type": "rect", "left": x, "top": y, "right": right, "bottom": bottom,
            "gray": gray,
        })

    def line(self, x, y, end, gray=RULE, thickness=2):
        self.rect(x, y, end, y + thickness, gray)
