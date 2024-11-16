import io
import locale
import sys
import webbrowser
from pathlib import Path
from typing import Optional, cast

import click
from PIL import Image

from .annotator import SVGAnnotator
from .ocr import AnalysisSettings, analyze_ui
from .types import BackendType
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
    "--backend",
    type=click.Choice(["claude", "tesseract", "easyocr", "paddleocr"]),
    default="easyocr",
    help="OCR backend to use for text detection",
)
def main(
    image_path: str,
    output: Optional[str],
    language: Optional[str],
    preview: bool,
    open_file_flag: bool,
    debug: bool,
    no_cache: bool,
    backend: str,
):
    """Annotate images with translations."""
    input_path = Path(image_path)

    # Load and rotate image based on EXIF
    try:
        image_data, _ = get_rotated_image_data(input_path)
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise click.ClickException(f"Failed to load image: {str(e)}")

    # Default output path: replace extension with -annotated.svg
    if not output:
        output = str(
            input_path.with_stem(input_path.stem + "-annotated").with_suffix(".svg")
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

    svg_content = annotator.annotate(analysis.elements)

    # Write SVG file
    with open(output, "w") as f:
        f.write(svg_content)

    if debug:
        print(f"Created SVG file: {output}")

    # Handle preview/open options
    if preview:
        try:
            webbrowser.open(f"file://{Path(output).absolute()}")
        except Exception as e:
            print(f"Failed to open preview in browser: {e}", file=sys.stderr)

    if open_file_flag:
        open_file(Path(output).absolute())


if __name__ == "__main__":
    main()
