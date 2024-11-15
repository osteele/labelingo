# Labelingo

Labelingo is a command-line tool that uses Anthropic's Claude to add callouts
and translations to UI screenshots. It automatically identifies UI elements,
translates them to your desired language, and annotates the image with numbered
callouts and translations.

## Features

- 🔍 Automatic UI element detection using Claude's vision capabilities
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

## Configuration

Create a `.env` file in the project root:

```text
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

Basic usage (translates to system language):
```bash
labelingo screenshot.png
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

## Requirements

- Python 3.9+
- Anthropic API key
- PIL/Pillow for image processing
- Click for CLI interface

## Credits

Written by Anthropic Claude.

Directed by Oliver Steele ([@osteele](https://github.com/osteele)).

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
