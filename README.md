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
pip install labelingo  # Basic installation with SVG support
```

For OCR support:
```bash
pip install 'labelingo[ocr]'  # Install OCR backends
```

For PNG and PDF output support:
```bash
pip install 'labelingo[cairo]'  # Install Cairo dependencies
```

For all features:
```bash
pip install 'labelingo[ocr,cairo]'  # Install all optional dependencies
```

### System Requirements

For PNG and PDF output support, you'll need to install the Cairo graphics library:

**macOS:**
```bash
# For Intel Macs:
brew install cairo pango

# For M1/M2 Macs, you may need to reinstall cairo for arm64:
brew uninstall cairo pango
brew install cairo pango
pip uninstall cairosvg cairocffi
pip install cairosvg cairocffi
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libcairo2-dev libpango1.0-dev
```

**Fedora:**
```bash
sudo dnf install cairo-devel pango-devel
```

**Windows:**
1. Install GTK3 runtime from [GTK for Windows Runtime Environment Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)
2. Add the GTK3 bin directory to your PATH

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

Clear response cache:
```bash
labelingo --clear-cache  # Remove all cached responses
```

Specify output format:
```bash
labelingo screenshot.png --format svg  # Output as SVG
labelingo screenshot.png --format png  # Output as PNG
labelingo screenshot.png --format pdf  # Output as PDF
# Or use file extension:
labelingo screenshot.png -o output.pdf  # Output as PDF
```

Full options:
```bash
labelingo --help
```

## Documentation

- [Design Document](docs/design.md) - Architecture, data flow, and design decisions
- [Development Guide](docs/development.md) - Setup instructions and contribution guidelines

## Development

See [development.md](docs/development.md) for setup instructions and development guidelines.

## License

MIT License. See LICENSE file.
