from pathlib import Path
from typing import List
import os
import base64
from .vision import UIElement, get_rotated_image_data

class SVGAnnotator:
    def __init__(self, image_path: Path, width: int, height: int, max_width: int = 1200, debug: bool = False):
        """
        Initialize SVG annotator with image dimensions and optional max width.
        Will scale the image proportionally to fit within max_width.
        """
        self.image_path = image_path
        self.debug = debug

        # Calculate scale to fit within max_width while maintaining aspect ratio
        self.scale = min(1.0, max_width / width)
        self.width = int(width * self.scale)
        self.height = int(height * self.scale)

        if debug:
            print(f"SVG dimensions: {self.width}x{self.height}")
            print(f"Scale factor: {self.scale}")

    def annotate(self, elements: List[UIElement], output_path: Path) -> str:
        """Create SVG with callouts for all elements"""
        # Get rotated image data and encode as base64
        image_data, _ = get_rotated_image_data(self.image_path)
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        svg_lines = [
            f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
            f'  <image x="0" y="0" width="{self.width}" height="{self.height}" xlink:href="data:image/jpeg;base64,{image_base64}"/>',
            '  <style>',
            '    .callout { fill: red; stroke: white; stroke-width: 2; opacity: 0.8; }',
            '    .number { fill: white; font-family: Arial; font-size: 16px; }',
            '    .translation { fill: red; font-family: Arial; font-size: 14px; text-anchor: start; }',
            '    .box { fill: none; stroke: red; stroke-width: 2; opacity: 0.8; }',
            '  </style>'
        ]

        for idx, element in enumerate(elements):
            # Scale from image coordinates to SVG coordinates
            x1 = int(element.bbox[0] * self.scale)
            y1 = int(element.bbox[1] * self.scale)
            x2 = int(element.bbox[2] * self.scale)
            y2 = int(element.bbox[3] * self.scale)
            width = x2 - x1
            height = y2 - y1

            # Add bounding box
            svg_lines.append(f'  <rect class="box" x="{x1}" y="{y1}" width="{width}" height="{height}"/>')

            # Add callout circle with number (slightly offset from the box)
            circle_x = x1 - 20
            circle_y = y1 - 20
            if circle_x < 0: circle_x = x1 + width + 5
            if circle_y < 0: circle_y = y1 + 5

            svg_lines.extend([
                f'  <circle class="callout" cx="{circle_x + 12}" cy="{circle_y + 12}" r="12"/>',
                f'  <text class="number" x="{circle_x + 8}" y="{circle_y + 17}">{idx + 1}</text>'
            ])

            # Add translation (below the box)
            text_y = y2 + 20
            svg_lines.append(f'  <text class="translation" x="{x1}" y="{text_y}">{element.translation}</text>')

        svg_lines.append('</svg>')
        return '\n'.join(svg_lines)
