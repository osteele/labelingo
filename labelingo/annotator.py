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

        # Add margin for text annotations on the left
        self.margin = 300  # Space for text on the left
        self.total_width = self.width + self.margin

        if debug:
            print(f"SVG dimensions: {self.total_width}x{self.height}")
            print(f"Scale factor: {self.scale}")

    def annotate(self, elements: List[UIElement]) -> str:
        """Create SVG with numbered callouts and translations"""
        # Convert image to bytes
        buffer = io.BytesIO()
        self.image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        svg_lines = [
            f'<svg width="{self.total_width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',  # noqa: E501
            "  <style>",
            "    .callout { fill: red; stroke: white; stroke-width: 2; opacity: 0.8; }",  # noqa: E501
            "    .number { fill: white; font-family: Arial; font-size: 16px; }",  # noqa: E501
            "    .translation { fill: black; font-family: Arial; font-size: 14px; }",  # noqa: E501
            "    .connector { stroke: red; stroke-width: 1.5; opacity: 0.6; fill: none; }",  # noqa: E501
            "    .box { fill: none; stroke: red; stroke-width: 2; opacity: 0.8; }",  # noqa: E501
            "  </style>",
            f'  <image x="{self.margin}" y="0" width="{self.width}" height="{self.height}" xlink:href="data:image/jpeg;base64,{image_base64}"/>',  # noqa: E501
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
                x1 = int(element.bbox[0] * self.scale) + self.margin
                y1 = int(element.bbox[1] * self.scale)
                x2 = int(element.bbox[2] * self.scale) + self.margin
                y2 = int(element.bbox[3] * self.scale)
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # Text position in left margin
                text_x = 10
                text_y = min(self.height - 20, 25 * i)

                # Add connector line from text to element
                start_x = text_x + 150
                ctrl1_x = text_x + 180
                ctrl2_x = (ctrl1_x + center_x) / 2
                ctrl1_y = text_y
                ctrl2_y = (text_y + center_y) / 2

                svg_lines.append(
                    f'  <path class="connector" d="M {start_x} {text_y} '
                    f"C {ctrl1_x} {ctrl1_y}, "
                    f"{ctrl2_x} {ctrl2_y}, "
                    f'{center_x} {center_y}"/>'
                )

                # Add bounding box around text in UI
                svg_lines.append(
                    f'  <rect class="box" x="{x1}" y="{y1}" '
                    f'width="{x2-x1}" height="{y2-y1}"/>'
                )

            # Text position for elements without bounding boxes
            if not has_bbox:
                text_x = 10
                text_y = min(self.height - 20, 25 * i)

            # Update text display format
            if element.translation and element.translation != element.text:
                display_text = f"{i}. {text} → {element.translation}"
            else:
                display_text = f"{i}. {text}"

            svg_lines.append(
                f'  <text class="translation" x="{text_x}" y="{text_y}">'
                f'{display_text}</text>'
            )

        svg_lines.append('</svg>')
        return '\n'.join(svg_lines)
