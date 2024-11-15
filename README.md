# Labelingo

Labelingo is a command-line tool that uses Anthropic's Claude to add callouts
and translations to UI screenshots. It automatically identifies UI elements,
translates them to your desired language, and annotates the image with numbered
callouts and translations.

## Features

- 🔍 Multiple OCR backends:
  - Claude Vision for cloud-based analysis
  - Tesseract for local processing
  - EasyOCR for enhanced Asian language support
  - PaddleOCR for state-of-the-art accuracy
- 🌐 Translation to any language, within the limits of LLM translation
    (defaults to system language)
- 🎯 Visual callouts with numbered circles
- 💾 Caching to avoid repeated API calls
- 🎨 Clean, readable SVG output
- 👀 Preview options for immediate viewing

## Installation

Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the repository:

```bash
git clone https://github.com/osteele/labelingo.git
cd labelingo
```

Install dependencies:

```bash
uv install
```

### Optional OCR Backends

To use alternative OCR backends:

```bash
# For PaddleOCR:
pip install paddlepaddle  # Install PaddlePaddle first
uv pip install -e '.[ocr]'  # Then install OCR dependencies

# For Tesseract:
brew install tesseract tesseract-lang  # macOS
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim  # Ubuntu/Debian
```

## Configuration

Create a `.env` file in the project root:

```text
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

Basic usage (using Claude backend):
```bash
labelingo screenshot.png
```

Using alternative OCR backends:
```bash
labelingo screenshot.png --backend tesseract
labelingo screenshot.png --backend easyocr
labelingo screenshot.png --backend paddleocr
```

Specify language:
```bash
labelingo screenshot.png --language fr  # Translate to French
labelingo screenshot.png -l es         # Translate to Spanish
```

Output options:
```bash
labelingo screenshot.png -o custom.svg          # Specify output file
labelingo screenshot.png --preview              # Open in web browser
labelingo screenshot.png --open                 # Open with system default app
```

Debug and cache options:
```bash
labelingo screenshot.png --debug                # Show debug information
labelingo screenshot.png --no-cache             # Skip using cached responses
```

## Options

- `--language, -l`: Target language for translations (defaults to system language)
- `--output, -o`: Output SVG file path (defaults to input-annotated.svg)
- `--preview`: Open the output in a web browser
- `--open`: Open the output with system default application
- `--debug`: Show debug information
- `--no-cache`: Skip using cached responses
- `--backend`: OCR backend to use (claude, tesseract, easyocr, paddleocr)

## Requirements

- Python 3.9+
- Anthropic API key (for Claude backend)
- Optional OCR backends:
  - Tesseract OCR
  - EasyOCR
  - PaddleOCR

## Credits

Written by Anthropic Claude.

Directed by Oliver Steele ([@osteele](https://github.com/osteele)).

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
