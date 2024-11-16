import os
import platform
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from shutil import which

import click

from .types import OutputFormat


def _initialize_cairo():
    """Initialize cairo library with proper paths for macOS."""
    if platform.system() == "Darwin":
        # Try using pycairo first
        try:
            import cairo  # type: ignore # noqa: F401

            return  # If pycairo works, we're good
        except ImportError:
            pass

        # Fall back to cairocffi
        import ctypes.util

        homebrew_paths = [
            "/opt/homebrew/lib",
            "/opt/homebrew/Cellar/cairo/1.18.2/lib",
        ]

        for path in homebrew_paths:
            lib_path = Path(path) / "libcairo.2.dylib"
            if lib_path.exists():
                try:
                    ctypes.CDLL(str(lib_path))
                    os.environ["DYLD_LIBRARY_PATH"] = (
                        f"{path}:{os.environ.get('DYLD_LIBRARY_PATH', '')}"
                    )
                    return
                except Exception as e:
                    print(f"Failed to load {lib_path}: {e}", file=sys.stderr)

        raise RuntimeError(
            "Neither pycairo nor cairo library could be initialized. Please install cairo:\n"  # noqa: E501
            "    brew install cairo\n"
            "If already installed, try reinstalling:\n"
            "    brew reinstall cairo"
        )


_initialize_cairo()

try:
    import cairosvg

    CAIRO_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import cairosvg: {e}", file=sys.stderr)
    CAIRO_AVAILABLE = False


def check_cairo_installation() -> bool:
    """Check if cairo is properly installed and provide helpful messages if not."""
    if not find_spec("cairosvg"):
        return False

    if not CAIRO_AVAILABLE:
        platform = sys.platform
        if platform == "darwin":
            print(
                "Error: Cairo library not found. To install on macOS:", file=sys.stderr
            )
            print("  brew install cairo pango", file=sys.stderr)
        elif platform.startswith("linux"):
            print(
                "Error: Cairo library not found. To install on Linux:", file=sys.stderr
            )
            print(
                "  Ubuntu/Debian: sudo apt-get install libcairo2-dev libpango1.0-dev",
                file=sys.stderr,
            )
            print("  Fedora: sudo dnf install cairo-devel pango-devel", file=sys.stderr)
        elif platform == "win32":
            print(
                "Error: Cairo library not found. To install on Windows:",
                file=sys.stderr,
            )
            print(
                "  1. Install GTK3 runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer",
                file=sys.stderr,
            )
            print("  2. Add the GTK3 bin directory to your PATH", file=sys.stderr)
        return False
    return True


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
        try:
            # Configure font handling
            import os

            os.environ["PANGOCAIRO_BACKEND"] = "fc"
            os.environ["FONTCONFIG_PATH"] = "/usr/local/etc/fonts"

            # Add explicit font family to SVG if not present
            if "<text" in svg_content and "font-family" not in svg_content:
                svg_content = svg_content.replace(
                    "<text", '<text font-family="Arial, Helvetica, sans-serif"', 1
                )

            # Process SVG content to ensure transparency is handled correctly
            if "<svg" in svg_content:
                if 'fill="none"' not in svg_content:
                    svg_content = svg_content.replace("<svg", '<svg fill="none"', 1)
                if "xmlns:xlink" not in svg_content:
                    svg_content = svg_content.replace(
                        "<svg", '<svg xmlns:xlink="http://www.w3.org/1999/xlink"', 1
                    )

            encoded_content = svg_content.encode()
            if format == "png":
                cairosvg.svg2png(
                    bytestring=encoded_content,
                    write_to=output_path,
                    background_color="transparent",
                    scale=1,
                    unsafe=True,  # Enable better font handling
                )
            elif format == "pdf":
                cairosvg.svg2pdf(
                    bytestring=encoded_content,
                    write_to=output_path,
                    unsafe=True,  # Enable better font handling
                )

            if debug:
                print(f"Debug: Created {format.upper()} file using Cairo")
                print(
                    f"Debug: Created file size: {Path(output_path).stat().st_size} bytes"  # noqa: E501
                )
            return
        except Exception as e:
            if debug:
                print(f"Cairo conversion failed: {e}", file=sys.stderr)

    # If all methods fail
    raise click.ClickException(
        f"Cannot create {format.upper()} file: No conversion tools available. Please install "  # noqa: E501
        "Inkscape, ImageMagick, or Cairo:\n"
        "  macOS: brew install inkscape\n"
        "  Linux: sudo apt-get install inkscape\n"
        "  Windows: Install Inkscape from the Windows Store or https://inkscape.org/"
    )
