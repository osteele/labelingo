# Command Line Reference

## Basic Usage

```bash
labelingo IMAGE [IMAGE...]           # Process one or more images
labelingo --help                     # Show help message
```

## Arguments

`IMAGE [IMAGE...]`
: One or more image files to process. Supports glob patterns (e.g., `*.png`).

## Options

### Output Control

`-o, --output DIRECTORY`
: Save output files to specified directory. Directory will be created if it doesn't exist.
```bash
labelingo image.png -o outputs/      # Save to outputs/image-annotated.svg
labelingo *.png -o translated/       # Process multiple files to translated/ directory
```

`-t, --type [svg|png|pdf]`
: Specify output format. Defaults to SVG if not specified.
```bash
labelingo image.png --type pdf       # Output as PDF
labelingo *.png -t png -o pngs/     # Convert all PNGs to annotated PNGs
```

### Translation Options

`-l, --language LANG`
: Target language for translations (e.g., 'fr' for French, 'ja' for Japanese). Defaults to system locale.
```bash
labelingo image.png -l fr           # Translate to French
labelingo *.png -l ja              # Translate multiple files to Japanese
```

`--backend [claude|tesseract|easyocr|paddleocr]`
: OCR backend to use for text detection. Defaults to easyocr.
```bash
labelingo image.png --backend claude        # Use Claude Vision API
labelingo image.png --backend tesseract     # Use Tesseract OCR
```

### Preview and Opening

`--preview/--no-preview`
: Open result in web browser after processing.
```bash
labelingo image.png --preview       # View result in browser
```

`--open`
: Open result with system default application.
```bash
labelingo image.png --open          # Open with default app
```

### Cache Control

`--no-cache`
: Skip using cached responses for this run.
```bash
labelingo image.png --no-cache      # Force fresh processing
```

`--clear-cache`
: Clear all cached responses and exit.
```bash
labelingo --clear-cache             # Remove all cached responses
```

### Debugging

`--debug/--no-debug`
: Show debug information during processing.
```bash
labelingo image.png --debug         # Show detailed processing info
```

## Examples

### Basic Operations

Process a single image:
```bash
labelingo screenshot.png
```

Process multiple specific files:
```bash
labelingo login.png settings.png profile.png
```

Process all PNG files in current directory:
```bash
labelingo *.png
```

### Output Management

Save all processed files to a specific directory:
```bash
labelingo screenshots/*.png -o translated/
```

Convert multiple files to PDF:
```bash
labelingo ui/*.png --type pdf -o pdfs/
```

### Language and Backend Combinations

Process multiple files in Japanese using Claude backend:
```bash
labelingo *.png -l ja --backend claude
```

Use Tesseract OCR with French translation:
```bash
labelingo screenshot.png -l fr --backend tesseract
```

### Debug and Testing

Process with debug output and preview:
```bash
labelingo image.png --debug --preview
```

Force fresh processing without cache:
```bash
labelingo image.png --no-cache --debug
```
