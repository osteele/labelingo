import base64
import html
import io
from typing import List

from PIL import Image

from .types import UIElement


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

        # Font sizes
        self.font_family = "'Helvetica Neue', Helvetica, Arial, sans-serif"
        self.number_font_size = 16
        self.text_font_size = 15
        self.title_font_size = 20

        # Calculate margins based on longest text
        self.bottom_margin = 50  # Keep fixed bottom margin for title
        self.left_margin = 0  # Will be set in annotate()
        self.right_margin = 0  # Will be set in annotate()

    def estimate_text_width(self, text: str, font_size: int = 15) -> int:
        """Rough estimate of text width in pixels."""
        # This is a rough approximation - adjust multiplier as needed
        return int(
            len(text) * (font_size * 0.65)
        )  # Increased multiplier for larger font

    def annotate(self, elements: List[UIElement], title: str | None = None) -> str:
        """Create SVG with numbered callouts and translations"""
        # Calculate required margins based on longest text
        max_left_text = 0
        max_right_text = 0

        for i, element in enumerate(elements, start=1):
            if element.translation and element.translation != element.text:
                text = f"{i}. {element.text} — {element.translation}"
            else:
                text = f"{i}. {element.text}"
            text_width = self.estimate_text_width(text, self.text_font_size)

            # Determine which side based on position (will match final placement)
            if any(coord != 0 for coord in element.bbox):
                center_x = (element.bbox[0] + element.bbox[2]) / 2 * self.scale
                if center_x > self.width / 2:
                    max_right_text = max(max_right_text, text_width)
                else:
                    max_left_text = max(max_left_text, text_width)
            else:
                # For elements without bbox, alternate sides
                if i % 2 == 0:
                    max_right_text = max(max_right_text, text_width)
                else:
                    max_left_text = max(max_left_text, text_width)

        # Set margins with padding
        self.left_margin = max_left_text + 60  # Add padding for connectors
        self.right_margin = max_right_text + 60
        self.total_width = self.width + self.left_margin + self.right_margin
        self.total_height = self.height + self.bottom_margin

        # Convert image to bytes
        buffer = io.BytesIO()
        self.image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        svg_lines = [
            f'<svg width="{self.total_width}" height="{self.total_height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',  # noqa: E501
            "  <defs>",
            '    <linearGradient id="lineGradient">',
            '      <stop offset="0%" stop-color="#FF0000" stop-opacity="0.9"/>',
            '      <stop offset="100%" stop-color="#FF0000" stop-opacity="0.7"/>',
            "    </linearGradient>",
            "  </defs>",
            "  <style>",
            "    .callout { fill: #FF595E; stroke: white; stroke-width: 2; opacity: 0.7; }",  # noqa: E501
            f"    .number {{ fill: #1982C4; font-family: {self.font_family}; font-weight: bold; font-size: {self.number_font_size}px; }}",  # noqa: E501
            f"    .translation {{ font-family: {self.font_family}; font-size: {self.text_font_size}px; }}",  # noqa: E501
            "    .text-background { fill: white; }",
            f"    .japanese {{ font-family: {self.font_family}; color: #666666; font-style: italic; }}",  # noqa: E501
            "    .connector { stroke: #E85D75; stroke-width: 2; fill: none; stroke-linecap: round; opacity: 0.9; }",  # noqa: E501
            "    .connector-outline { stroke: white; stroke-width: 4; fill: none; stroke-linecap: round; opacity: 0.6; }",  # noqa: E501
            "    .box { fill: none; stroke: #E85D75; stroke-width: 1.5; opacity: 0.6; rx: 6px; ry: 6px; }",  # noqa: E501
            f"    .title {{ fill: #1982C4; font-family: {self.font_family}; font-size: {self.title_font_size}px; font-weight: bold; }}",  # noqa: E501
            f"    .bullet {{ fill: #666666; font-family: {self.font_family}; font-size: 14px; }}",  # noqa: E501
            "  </style>",
            f'  <image x="{self.left_margin}" y="0" width="{self.width}" height="{self.height}" xlink:href="data:image/jpeg;base64,{image_base64}"/>',  # noqa: E501
        ]

        # Sort elements by their vertical position (y coordinate)
        def get_y_position(element: UIElement) -> float:
            if any(coord != 0 for coord in element.bbox):
                return element.bbox[1] * self.scale
            return float("inf")  # Put elements without bbox at the end

        sorted_elements = sorted(
            enumerate(elements, start=1), key=lambda x: get_y_position(x[1])
        )

        # Track vertical positions for left and right sides to prevent overlap
        left_y = 0
        right_y = 0
        min_y_spacing = 25  # Minimum vertical space between labels

        # Process sorted elements
        for i, element in sorted_elements:
            text = html.escape(element.text)
            translation = (
                html.escape(element.translation) if element.translation else None
            )
            has_bbox = any(coord != 0 for coord in element.bbox)

            if has_bbox:
                # Add padding to bounding boxes
                box_padding = 4
                x1 = int(element.bbox[0] * self.scale) + self.left_margin - box_padding
                y1 = int(element.bbox[1] * self.scale) - box_padding
                x2 = int(element.bbox[2] * self.scale) + self.left_margin + box_padding
                y2 = int(element.bbox[3] * self.scale) + box_padding
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # Determine label side based on box position
                on_right = center_x > (self.left_margin + self.width / 2)

                # Calculate vertical position for label, avoiding overlap
                if on_right:
                    text_y = max(center_y, right_y + min_y_spacing)
                    right_y = text_y
                else:
                    text_y = max(center_y, left_y + min_y_spacing)
                    left_y = text_y

                # Calculate connector points
                if on_right:
                    connect_x = x2  # right edge
                    text_x = self.left_margin + self.width + 40
                    start_x = text_x - 20
                else:
                    connect_x = x1  # left edge
                    text_x = 10
                    # Don't extend connector past the text
                    start_x = text_x  # Changed from extending leftward

                # Draw connectors...
                ctrl1_x = start_x + (30 if not on_right else -30)
                ctrl2_x = (ctrl1_x + connect_x) / 2
                ctrl1_y = text_y
                ctrl2_y = (text_y + center_y) / 2

                # Add connector paths and box...
                svg_lines.append(
                    f'  <path class="connector-outline" d="M {start_x} {text_y} C {ctrl1_x} {ctrl1_y}, {ctrl2_x} {ctrl2_y}, {connect_x} {center_y}"/>'  # noqa: E501
                )
                svg_lines.append(
                    f'  <path class="connector" d="M {start_x} {text_y} C {ctrl1_x} {ctrl1_y}, {ctrl2_x} {ctrl2_y}, {connect_x} {center_y}"/>'  # noqa: E501
                )
                svg_lines.append(
                    f'  <rect class="box" x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}"/>'  # noqa: E501
                )

                # Format text with number
                if element.translation and element.translation != element.text:
                    display_text = (
                        f'<tspan class="number">{i}.</tspan> '
                        f'<tspan class="japanese">{text}</tspan> '
                        f'<tspan class="separator"> — </tspan> '
                        f'<tspan class="english">{translation}</tspan>'
                    )
                else:
                    display_text = f'<tspan class="number">{i}.</tspan> {text}'
            else:
                # Handle elements without bounding boxes
                on_right = i % 2 == 0
                if on_right:
                    text_y = max(self.height - 150 + (i * 25), right_y + min_y_spacing)
                    right_y = text_y
                    text_x = self.left_margin + self.width + 40
                else:
                    text_y = max(self.height - 150 + (i * 25), left_y + min_y_spacing)
                    left_y = text_y
                    text_x = 10

                # Use bullet point (•) instead of number for items without bbox
                if element.translation and element.translation != element.text:
                    display_text = (
                        f'<tspan class="bullet">•</tspan> '
                        f'<tspan class="japanese">{text}</tspan> '
                        f'<tspan class="separator"> — </tspan> '
                        f'<tspan class="english">{element.translation}</tspan>'
                    )
                else:
                    display_text = f'<tspan class="bullet">•</tspan> {text}'

            # Add the text label with background
            text_height = 20  # Approximate height of text
            text_padding = 5  # Padding around text
            if element.translation and element.translation != element.text:
                label_text = f"{i}. {text} — {element.translation}"
            else:
                label_text = f"{i}. {text}"
            text_width = self.estimate_text_width(label_text)

            # Draw background rectangle first
            svg_lines.append(
                f'  <rect class="text-background" x="{text_x - text_padding}" '
                f'y="{text_y - text_height + text_padding}" '
                f'width="{text_width + 2*text_padding}" '
                f'height="{text_height + text_padding}" />'
            )

            # Then draw the text
            svg_lines.append(
                f'  <text class="translation" x="{text_x}" y="{text_y}">'
                f"{display_text}</text>"
            )

        # Add title if provided...

        # Add title below the image if provided
        if title:
            title_y = self.height + 30  # Position title 30px below the image
            title_x = self.left_margin + (self.width / 2)  # Center title horizontally
            svg_lines.append(
                f'  <text class="title" x="{title_x}" y="{title_y}" text-anchor="middle">'  # noqa: E501
                f"{html.escape(title)}</text>"
            )

        # Close the SVG tag
        svg_lines.append("</svg>")

        return "\n".join(svg_lines)
