import locale
import sys
import webbrowser
from pathlib import Path
from typing import Optional, cast

import click
from PIL import Image

from .annotator import SVGAnnotator
from .ocr import AnalysisSettings, BackendType, analyze_ui
from .utils import open_file


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

    # Default output path: replace extension with -annotated.svg
    if not output:
        output = str(
            input_path.with_stem(input_path.stem + "-annotated").with_suffix(".svg")
        )

    # Default language: use system locale
    if not language:
        locale_info = locale.getlocale()[0]
        language = locale_info.split("_")[0] if locale_info else "en"

    # Cast the backend string to BackendType since we know it's valid from
    # Click's Choice
    backend_type = cast(BackendType, backend.lower())

    settings = AnalysisSettings(
        image_path=Path(input_path),
        target_lang=language,
        backend=backend_type,
        no_cache=no_cache,
        debug=debug,
    )

    # Create annotator with debug flag
    image = Image.open(input_path)
    annotator = SVGAnnotator(input_path, image.width, image.height, debug=debug)

    # Process image and create SVG
    analysis = analyze_ui(settings)

    if debug and analysis.source_language:
        print(f"Detected source language: {analysis.source_language}")

    svg_content = annotator.annotate(analysis.elements, Path(output))

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
