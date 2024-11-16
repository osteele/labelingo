import base64
import html
import io
from typing import List

from PIL import Image

from .ocr import UIElement


class SVGAnnotator:

    def __init__(
        self,
        image: Image.Image,
        max_width: int = 800,
        max_height: int = 800,
        debug: bool = False,
    ):
        """Initialize SVG annotator with image dimensions and optional max width."""
        self.image = image
        self.debug = debug

        # Calculate scale to fit within max_width while maintaining aspect ratio
        self.scale = min(1.0, max_width / image.width, max_height / image.height)
        self.width = int(image.width * self.scale)
        self.height = int(image.height * self.scale)

        # Add margins for text annotations on both sides
        self.left_margin = 250
        self.right_margin = 200
        self.bottom_margin = 50  # Add margin for title below image
        self.total_width = self.width + self.left_margin + self.right_margin
        self.total_height = (
            self.height + self.bottom_margin
        )  # Add bottom margin to total height

        if debug:
            print(f"SVG dimensions: {self.total_width}x{self.total_height}")
            print(f"Scale factor: {self.scale}")

    def estimate_text_width(self, text: str, font_size: int = 13) -> int:
        """Rough estimate of text width in pixels."""
        # This is a rough approximation - adjust multiplier as needed
        return int(len(text) * (font_size * 0.6))

    def annotate(self, elements: List[UIElement], title: str | None = None) -> str:
        """Create SVG with numbered callouts and translations"""
        # Convert image to bytes
        buffer = io.BytesIO()
        self.image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        svg_lines = [
            f'<svg width="{self.total_width}" height="{self.total_height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
            "  <style>",
            "    .callout { fill: #FF595E; stroke: white; stroke-width: 2; opacity: 0.7; }",
            "    .number { fill: #1982C4; font-family: 'Arial', sans-serif; font-weight: bold; font-size: 14px; }",
            "    .translation { font-family: 'Arial', sans-serif; font-size: 13px; }",
            "    .translation .japanese { color: #666666; font-style: italic; }",
            "    .connector { stroke: url(#lineGradient); stroke-width: 2; fill: none; stroke-linecap: round; }",
            "    .connector-outline { stroke: white; stroke-width: 4; fill: none; stroke-linecap: round; opacity: 0.6; }",
            "    .box { fill: none; stroke: #FF595E; stroke-width: 1.5; opacity: 0.6; }",
            "    .title { fill: #1982C4; font-family: 'Arial', sans-serif; font-size: 18px; font-weight: bold; }",
            "  </style>",
            f'  <image x="{self.left_margin}" y="0" width="{self.width}" height="{self.height}" xlink:href="data:image/jpeg;base64,{image_base64}"/>',
            "  <defs>",
            '    <linearGradient id="lineGradient">',
            '      <stop offset="0%" stop-color="#FF0000" stop-opacity="0.9"/>',
            '      <stop offset="100%" stop-color="#FF0000" stop-opacity="0.7"/>',
            "    </linearGradient>",
            '    <text id="measure-text" class="translation" visibility="hidden"></text>',
            "  </defs>",
        ]

        # Add connectors and callouts
        for i, element in enumerate(elements, start=1):
            text = html.escape(element.text)
            translation = (
                html.escape(element.translation) if element.translation else None
            )

            # Skip drawing boxes and connectors for elements with null bounding boxes
            has_bbox = any(coord != 0 for coord in element.bbox)

            if has_bbox:
                # Calculate positions, applying scale factor
                x1 = int(element.bbox[0] * self.scale) + self.left_margin
                y1 = int(element.bbox[1] * self.scale)
                x2 = int(element.bbox[2] * self.scale) + self.left_margin
                y2 = int(element.bbox[3] * self.scale)

                # Calculate center points
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # Determine whether to place label on left or right
                on_right = center_x > (self.left_margin + self.width / 2)

                # Connect to left or right edge of box depending on label position
                if on_right:
                    connect_x = (
                        x2  # Connect to right edge of box for labels on the right
                    )
                else:
                    connect_x = x1  # Connect to left edge of box for labels on the left

                # Text position based on side
                if on_right:
                    text_x = self.left_margin + self.width + 10
                    start_x = text_x
                    ctrl1_x = text_x - 30
                else:
                    text_x = 10
                    # Calculate label width
                    if element.translation and element.translation != element.text:
                        label_text = f"{i}. {text} — {element.translation}"
                    else:
                        label_text = f"{i}. {text}"
                    text_width = self.estimate_text_width(label_text)
                    start_x = text_x + text_width
                    ctrl1_x = start_x + 30

                text_y = min(self.height - 20, 25 * i)

                # Adjust control points based on side
                if on_right:
                    ctrl2_x = (ctrl1_x + connect_x) / 2
                else:
                    ctrl2_x = (ctrl1_x + connect_x) / 2

                ctrl1_y = text_y
                ctrl2_y = (text_y + center_y) / 2

                svg_lines.append(
                    f'  <path class="connector-outline" d="M {start_x} {text_y} '
                    f"C {ctrl1_x} {ctrl1_y}, "
                    f"{ctrl2_x} {ctrl2_y}, "
                    f'{connect_x} {center_y}"/>'
                )
                svg_lines.append(
                    f'  <path class="connector" d="M {start_x} {text_y} '
                    f"C {ctrl1_x} {ctrl1_y}, "
                    f"{ctrl2_x} {ctrl2_y}, "
                    f'{connect_x} {center_y}"/>'
                )

                svg_lines.append(
                    f'  <rect class="box" x="{x1}" y="{y1}" '
                    f'width="{x2-x1}" height="{y2-y1}"/>'
                )
            else:
                # For elements without bbox, alternate between left and right
                on_right = i % 2 == 0
                text_x = (self.left_margin + self.width + 10) if on_right else 10
                text_y = min(self.height - 20, 25 * i)

            # Update text display format
            if element.translation and element.translation != element.text:
                display_text = (
                    f'<tspan class="number">{i}.</tspan> '
                    f'<tspan class="japanese">{text}</tspan> '
                    f'<tspan class="separator"> — </tspan> '
                    f'<tspan class="english">{element.translation}</tspan>'
                )
            else:
                display_text = f"{i}. {text}"

            svg_lines.append(
                f'  <text class="translation" x="{text_x}" y="{text_y}">'
                f'{display_text}</text>'
            )

        # Add title below the image if provided
        if title:
            title_y = self.height + 30  # Position title 30px below the image
            title_x = self.left_margin + (self.width / 2)  # Center title horizontally
            title_element = f"""
                <text class="title" x="{title_x}" y="{title_y}" text-anchor="middle">
                    {html.escape(title)}
                </text>
            """
            svg_lines.append(title_element)

        svg_lines.append('</svg>')
        return '\n'.join(svg_lines)
