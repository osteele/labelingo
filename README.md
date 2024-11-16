# Labelingo

Annotate UI screenshots with translations.

## Features

- Detects text in UI screenshots using multiple OCR backends
- Translates text using OpenAI and Claude Vision APIs
- Generates interactive SVG with annotations and translations
- Supports multiple OCR backends:
  - Claude Vision API
  - Tesseract OCR
  - EasyOCR (default)
  - PaddleOCR

## Installation

```bash
pip install labelingo
```

For OCR support:
```bash
pip install 'labelingo[ocr]'
```

## Configuration

The tool requires an API key for Claude Vision (default backend). Set it in your environment or in a `.env` file:

```bash
ANTHROPIC_API_KEY=your-claude-api-key
```

When using non-Claude backends (tesseract, easyocr, paddleocr), you can optionally set an OpenAI API key to improve translations:

```bash
OPENAI_API_KEY=your-openai-api-key  # Optional, for improved translations
```

You can get API keys from:
- Claude (required): <https://console.anthropic.com/>
- OpenAI (optional): <https://platform.openai.com/api-keys>

## Usage

Basic usage:
```bash
labelingo screenshot.png
```

Specify target language:
```bash
labelingo screenshot.png -l fr  # Translate to French
```

Preview result in browser:
```bash
labelingo screenshot.png --preview
```

Use different OCR backend:
```bash
labelingo screenshot.png --backend tesseract  # OpenAI key recommended for better translations
```

Full options:
```bash
labelingo --help
```

## OCR Backend Requirements

### Tesseract
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

### EasyOCR
No additional system requirements.

### PaddleOCR
```bash
pip install paddlepaddle  # CPU version
```

## Development

Clone and install in development mode:
```bash
git clone https://github.com/osteele/labelingo.git
cd labelingo
pip install -e '.[ocr]'
```

## Development Setup

After cloning the repository:

1. Install the package in development mode with dev dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

2. Install Node.js dependencies:
   ```bash
   npm install -g pyright
   ```

3. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

This will ensure code quality checks run automatically before each commit.

## License

MIT License. See LICENSE file.
