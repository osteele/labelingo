import subprocess
import sys
from pathlib import Path
from shutil import which

import click

from ..svg_converter import check_cairo_installation
from ..types import OutputFormat
from .cairo import convert_with_cairo


def save_with_format(
    svg_content: str, output_path: str, format: OutputFormat, debug: bool = False
) -> None:
    """Save SVG content in the specified format."""
    # Ensure output path has the correct extension
    base_path = output_path.rsplit(".", 1)[0] if "." in output_path else output_path
    output_path = f"{base_path}.{format}"

    if format == "svg":
        with open(output_path, "w") as f:
            f.write(svg_content)
        return

    # Try external tools first
    success, tool_name = convert_with_external_tool(svg_content, output_path, format)
    if success:
        if debug:
            print(f"Debug: Created {format.upper()} file using {tool_name}")
            print(f"Debug: Created file size: {Path(output_path).stat().st_size} bytes")
        return

    # Fall back to Cairo if external tools aren't available
    if check_cairo_installation():
        return convert_with_cairo(svg_content, output_path, format, debug)

    # If all methods fail
    raise click.ClickException(
        f"Cannot create {format.upper()} file: No conversion tools available. Please install "  # noqa: E501
        "Inkscape, ImageMagick, or Cairo:\n"
        "  macOS: brew install inkscape\n"
        "  Linux: sudo apt-get install inkscape\n"
        "  Windows: Install Inkscape from the Windows Store or https://inkscape.org/"
    )


def convert_with_external_tool(
    svg_content: str, output_path: str, format: str
) -> tuple[bool, str]:
    """Try to convert SVG using external tools. Returns (success, tool_name)."""
    tool_info = _find_converter_tool()
    if not tool_info:
        return False, ""

    tool_name, command = tool_info
    temp_svg = Path(output_path).with_suffix(".svg")

    try:
        # Save temporary SVG file
        with open(temp_svg, "w") as f:
            f.write(svg_content)

        if tool_name == "inkscape":
            subprocess.run(
                [command, "--export-type", format, str(temp_svg), "-o", output_path],
                check=True,
                capture_output=True,
            )
        elif tool_name == "imagemagick":
            subprocess.run(
                [command, str(temp_svg), output_path], check=True, capture_output=True
            )
        elif tool_name == "librsvg":
            subprocess.run(
                [command, "-f", format, "-o", output_path, str(temp_svg)],
                check=True,
                capture_output=True,
            )

        return True, tool_name

    except subprocess.CalledProcessError as e:
        print(f"External tool error: {e.stderr.decode()}", file=sys.stderr)
        return False, ""
    finally:
        temp_svg.unlink(missing_ok=True)


def _find_converter_tool() -> tuple[str, str] | None:
    """Find available SVG converter tool. Returns (tool_name, command_name)."""
    tools = [
        ("inkscape", "inkscape"),
        ("imagemagick", "convert"),
        ("librsvg", "rsvg-convert"),
    ]

    for tool_name, command in tools:
        if which(command):
            return tool_name, command
    return None
