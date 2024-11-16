# Development Guide

## Setup

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
