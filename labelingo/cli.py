import io
import locale
import sys
import webbrowser
from pathlib import Path
from typing import cast

import click
from PIL import Image

from .annotator import SVGAnnotator
from .svg_converter import save_with_format
from .ocr import AnalysisSettings, analyze_ui
from .types import BackendType, OutputFormat
from .utils import get_rotated_image_data, open_file


@click.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output SVG file path")
@click.option("--language", "-l", help="Target language for translations")
@click.option("--preview/--no-preview", default=False, help="Preview in web browser")
@click.option(
    "--open",
    "open_file_flag",
    is_flag=True,
    help="Open with system default application",
)
@click.option("--debug/--no-debug", default=False, help="Show debug information")
@click.option("--no-cache", is_flag=True, help="Skip using cached responses")
@click.option(
    "-t",
    "--type",
    "format",
    type=click.Choice(["svg", "png", "pdf"]),
    help="Output format type (default: inferred from output path, or svg)",
)
@click.option(
    "--backend",
    type=click.Choice(["claude", "tesseract", "easyocr", "paddleocr"]),
    default="easyocr",
    help="OCR backend to use for text detection",
)
def main(
    image_path: str,
    output: str | None,
    language: str | None,
    preview: bool,
    open_file_flag: bool,
    debug: bool,
    no_cache: bool,
    backend: str,
    format: str | None,
):
    """Annotate UI screenshots with translations."""
    input_path = Path(image_path)

    # Load and rotate image based on EXIF
    try:
        image_data = get_rotated_image_data(input_path)
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise click.ClickException(f"Failed to load image: {str(e)}")

    output_format = infer_output_format(output, format)

    # Determine output path
    if output:
        output_path = output
    else:
        input_path = Path(image_path)
        output_path = str(
            input_path.parent / f"{input_path.stem}-annotated.{output_format}"
        )

    # Default language: use system locale
    if not language:
        locale_info = locale.getlocale()[0]
        language = locale_info.split("_")[0] if locale_info else "en"

    backend_type = cast(BackendType, backend.lower())

    settings = AnalysisSettings(
        target_lang=language,
        backend=backend_type,
        no_cache=no_cache,
        debug=debug,
    )

    # Create annotator with debug flag
    annotator = SVGAnnotator(image, debug=debug)

    # Process image and create SVG
    analysis = analyze_ui(image, settings)

    # Generate SVG
    svg_content = annotator.annotate(analysis.elements)

    # Save in requested format
    if output_format == "svg":
        with open(output_path, "w") as f:
            f.write(svg_content)
    else:
        save_with_format(svg_content, output_path, output_format, debug)
    print(f"Saved to {output_path}")

    # Handle preview/open options
    if preview:
        try:
            webbrowser.open(f"file://{Path(output_path).absolute()}")
        except Exception as e:
            print(f"Failed to open preview in browser: {e}", file=sys.stderr)

    if open_file_flag:
        open_file(Path(output_path).absolute())


def infer_output_format(
    output_path: str | None, format: str | None = None
) -> OutputFormat:
    """Infer output format from file extension or format parameter."""
    if format:
        if format not in ["svg", "png", "pdf"]:
            raise click.ClickException(f"Unsupported format: {format}")
        return cast(OutputFormat, format)

    # Infer format from output file extension
    if output_path:
        ext = output_path.split(".")[-1].lower()
        if ext not in ["svg", "png", "pdf"]:
            return "svg"

    return "svg"


if __name__ == "__main__":
    main()
