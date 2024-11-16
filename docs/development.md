# Development Guide

This guide covers setting up and contributing to Labelingo. For architectural details and design decisions, see the [Design Document](design.md).

## Setup

After cloning the repository, you have two options for setting up your development environment:

### Option 1: Using Hatch (Recommended)

Hatch automatically manages virtual environments and dependencies:

```bash
# Install Hatch if you haven't already
uv tool install install hatch

# Create and enter development environment with all tools
hatch shell

# Or use specific feature environments
hatch shell cairo  # for Cairo support
hatch shell ocr    # for OCR support
hatch shell full   # for all features
```

Common development commands:
```bash
hatch run fmt        # format code
hatch run lint       # run linters
hatch run typecheck  # run type checker
```

### Option 2: Manual Setup

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

## OCR Backend Requirements

Different OCR backends have different system requirements:

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

To install all OCR dependencies:
```bash
hatch shell ocr  # if using Hatch
# or
uv pip install -e ".[ocr]"  # if using manual setup
```
