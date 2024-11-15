import locale
import sys
import webbrowser
import platform
import subprocess
from pathlib import Path
import click
from PIL import Image
from anthropic import Anthropic
from .annotator import SVGAnnotator
from .vision import analyze_ui

def open_file(path: Path):
    """Open a file with the default system application"""
    try:
        if platform.system() == 'Darwin':       # macOS
            subprocess.run(['open', str(path)])
        elif platform.system() == 'Windows':    # Windows
            subprocess.run(['start', str(path)], shell=True)
        else:                                   # Linux and others
            subprocess.run(['xdg-open', str(path)])
    except Exception as e:
        print(f"Failed to open file: {e}", file=sys.stderr)

@click.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output SVG file path')
@click.option('--language', '-l', help='Target language for translations')
@click.option('--preview/--no-preview', default=False, help='Preview in web browser')
@click.option('--open', 'open_file_flag', is_flag=True, help='Open with system default application')
@click.option('--debug/--no-debug', default=False, help='Show debug information')
@click.option('--no-cache', is_flag=True, help='Skip using cached responses')
def main(image_path: str, output: str, language: str, preview: bool, open_file_flag: bool, debug: bool, no_cache: bool):
    """Annotate images with translations."""
    input_path = Path(image_path)

    # Default output path: replace extension with -annotated.svg
    if not output:
        output = str(input_path.with_stem(input_path.stem + '-annotated').with_suffix('.svg'))

    # Default language: use system locale
    if not language:
        try:
            language = locale.getlocale()[0].split('_')[0]  # Get language code from locale
        except (AttributeError, IndexError):
            language = 'en'  # Fallback to English

    # Create annotator with debug flag
    image = Image.open(input_path)
    annotator = SVGAnnotator(input_path, image.width, image.height, debug=debug)

    # Process image and create SVG
    client = Anthropic()
    analysis = analyze_ui(client, input_path, language, no_cache=no_cache, debug=debug)
    svg_content = annotator.annotate(analysis.elements, Path(output))

    # Write SVG file
    with open(output, 'w') as f:
        f.write(svg_content)

    if debug:
        print(f"Created SVG file: {output}")

    # Handle preview/open options
    if preview:
        try:
            webbrowser.open(f'file://{Path(output).absolute()}')
        except Exception as e:
            print(f"Failed to open preview in browser: {e}", file=sys.stderr)

    if open_file_flag:
        open_file(Path(output).absolute())

if __name__ == '__main__':
    main()
