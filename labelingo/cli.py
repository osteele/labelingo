import io
import locale
import sys
import webbrowser
from pathlib import Path
from typing import cast

import click
from PIL import Image

from .annotator import SVGAnnotator
from .response_cache import ResponseCache
from .services import analyze_ui
from .svg_converter import save_with_format
from .types import (
    AnalysisSettings,
    LabelLocationService,
    OutputFormat,
    SceneAnalysisService,
)
from .utils import get_rotated_image_data, open_file


@click.command()
@click.argument("image_paths", type=click.Path(exists=True), nargs=-1, required=False)
@click.option("--output", "-o", type=click.Path(), help="Output directory for files")
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
@click.option("--clear-cache", is_flag=True, help="Clear all cached responses")
@click.option(
    "-t",
    "--type",
    "format",
    type=click.Choice(["svg", "png", "pdf"]),
    help="Output format type (default: inferred from output path, or svg)",
)
@click.option(
    "--scene-analysis",
    type=click.Choice(["openai", "claude"]),
    default="openai",
)
@click.option(
    "--label-location",
    type=click.Choice(["claude", "tesseract", "easyocr", "paddleocr"]),
    default="easyocr",
    help="OCR backend to use for text detection",
)
def main(
    image_paths: tuple[str, ...] | tuple[()],
    output: str | None,
    language: str | None,
    preview: bool,
    open_file_flag: bool,
    debug: bool,
    no_cache: bool,
    clear_cache: bool,
    format: str | None,
    label_location: str,
    scene_analysis: str,
):
    """Annotate UI screenshots with translations."""
    if clear_cache:
        cache = ResponseCache(debug=debug)
        cache.clear_cache()
        print("Cache cleared successfully")
        return

    if not image_paths:
        raise click.UsageError(
            "At least one image path is required unless using --clear-cache"
        )

    # Convert output to Path if specified
    output_dir = Path(output) if output else None
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True)

    # Default language: use system locale
    if not language:
        locale_info = locale.getlocale()[0]
        language = locale_info.split("_")[0] if locale_info else "en"

    label_location_service = cast(LabelLocationService, label_location.lower())
    scene_analysis = cast(SceneAnalysisService, scene_analysis.lower())
    settings = AnalysisSettings(
        target_lang=language,
        label_location_service=label_location_service,
        scene_analysis_service=scene_analysis,
        no_cache=no_cache,
        debug=debug,
    )

    for image_path in image_paths:
        try:
            process_image(
                Path(image_path),
                output_dir,
                settings,
                preview,
                open_file_flag,
                debug,
                format,
            )
        except Exception as e:
            print(f"Error processing {image_path}: {e}", file=sys.stderr)
            raise


def process_image(
    input_path: Path,
    output_dir: Path | None,
    settings: AnalysisSettings,
    preview: bool,
    open_file_flag: bool,
    debug: bool,
    format: str | None,
) -> None:
    """Process a single image file."""
    # Load and rotate image based on EXIF
    try:
        image_data = get_rotated_image_data(input_path)
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise click.ClickException(f"Failed to load image: {str(e)}")

    # Determine output path
    output_format = infer_output_format(None, format)
    if output_dir:
        output_path = str(output_dir / f"{input_path.stem}-annotated.{output_format}")
    else:
        output_path = str(
            input_path.parent / f"{input_path.stem}-annotated.{output_format}"
        )

    # Create annotator with debug flag
    annotator = SVGAnnotator(image, debug=debug)

    # Process image and create SVG
    analysis = analyze_ui(image, settings)

    # Generate SVG
    svg_content = annotator.annotate(analysis.elements, analysis.title)

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
