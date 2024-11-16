# Labelingo

Annotate UI screenshots with translations.

## Features

- 🔍 Detects text in UI screenshots using multiple OCR backends
- 🌐 Translates text using OpenAI and Claude Vision APIs
- 🎨 Generates interactive SVG with annotations and translations
- 📁 Supports batch processing of multiple images

## Quick Start

1. Install:
```bash
pip install labelingo
```

1. Set up your API key:
```bash
export OPENAI_API_KEY=your-openai-api-key
```

1. Process an image:
```bash
labelingo screenshot.png            # Basic usage
labelingo screenshot.png -l fr      # Translate to French
labelingo *.png -o translated/     # Process multiple files
```

## Installation Options

For additional OCR back-end support:
```bash
pip install 'labelingo[ocr]'       # Install OCR backends
```

For PNG/PDF output:
```bash
pip install 'labelingo[cairo]'     # Install Cairo dependencies
```

For all features:
```bash
pip install 'labelingo[ocr,cairo]' # Install all optional dependencies
```

See [System Requirements](docs/installation.md) for platform-specific dependencies.

## Documentation

- [Command Line Reference](docs/commands.md) - Detailed usage and examples
- [Design Document](docs/design.md) - Architecture and design decisions
- [Development Guide](docs/development.md) - Setup and contribution guidelines

## License

MIT License. See LICENSE file.
