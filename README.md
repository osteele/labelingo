# Labelingo

Annotate UI screenshots with translations.

## Features

- 🔍 Detects text in UI screenshots using multiple OCR backends
- 🌐 Translates text using OpenAI and Claude Vision APIs
- 🎨 Generates interactive SVG with annotations and translations
- 🔧 Supports multiple OCR backends:
  - 🤖 Claude Vision API
  - 📝 Tesseract OCR
  - 📷 EasyOCR (default)
  - 🚀 PaddleOCR

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

## Development

See [development.md](docs/development.md) for setup instructions and development guidelines.

## License

MIT License. See LICENSE file.
