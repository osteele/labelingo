# Labelingo Design Document

## Overview

Labelingo is a tool for annotating UI screenshots with translations. It combines OCR (Optical Character Recognition) with AI-powered translation to create annotated SVG files that show both the original text and its translation.

## Architecture

```mermaid
graph TD
A[User Input] -->|Image & Target Lang| B[CLI Interface]
B -->|Settings| C[Analysis Engine]
subgraph Analysis
C -->|Image| D[OpenAI Vision]
C -->|Image| E[OCR Backend]
D -->|Text & Translations| F[Result Merger]
E -->|Text Locations| F
end
subgraph Caching
D <-->|Cache Check| G[Response Cache]
E <-->|Cache Check| G
end
F -->|Combined Results| H[SVG Generator]
H -->|SVG Content| I[Output File]
I -->|Preview| J[Web Browser]
I -->|Open| K[System Viewer]
style Analysis fill:#f5f5f5,stroke:#333,stroke-width:2px
style Caching fill:#f0f8ff,stroke:#333,stroke-width:2px
```

The system consists of four main components:

1. CLI Interface (`cli.py`)
2. OCR and Analysis Engine (`ocr.py`)
3. SVG Annotation Generator (`annotator.py`)
4. Utilities and Caching (`utils.py`, `response_cache.py`)

### Component Details

#### CLI Interface
- Handles command-line arguments and configuration
- Manages the workflow between components
- Provides options for output format and preview

#### OCR and Analysis Engine
Supports multiple backends for text detection:

1. **OpenAI Vision API**
   - Primary source for translations
   - Provides source language detection
   - Image preprocessing:
     - Scales images to max 2048px
     - Optimizes JPEG quality
   - Uses structured output format
   - Results are cached based on image content and analysis parameters

2. **OCR Backends**
   - Claude Vision API (default)
   - Tesseract OCR
   - EasyOCR
   - PaddleOCR
   - Each provides text location and content
   - Results are combined with OpenAI translations

#### SVG Annotation Generator
- Creates interactive SVG output
- Features:
  - Original screenshot as background
  - Bounding boxes around detected text
  - Curved connector lines
  - Numbered annotations with translations
  - Responsive scaling

#### Caching System
- Caches API responses to reduce costs and latency
- Cache keys include:
  - API endpoint
  - Image content hash
  - Schema/structure hash
  - Target language

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant OpenAI
    participant OCR
    participant Cache
    participant SVG
    participant Browser

    User->>CLI: Image & Target Language

    CLI->>OpenAI: Scale & Send Image

    alt Cache Hit
        OpenAI->>Cache: Check Cache
        Cache-->>OpenAI: Return Cached Result
    else Cache Miss
        OpenAI->>OpenAI: Analyze Text & Translate
        OpenAI->>Cache: Store Result
    end

    OpenAI-->>CLI: Text & Translations

    CLI->>OCR: Send Image

    alt Cache Hit
        OCR->>Cache: Check Cache
        Cache-->>OCR: Return Cached Result
    else Cache Miss
        OCR->>OCR: Detect Text Locations
        OCR->>Cache: Store Result
    end

    OCR-->>CLI: Text Locations

    CLI->>CLI: Merge Results

    CLI->>SVG: Generate Annotation
    SVG-->>CLI: SVG Content

    alt Preview Requested
        CLI->>Browser: Open SVG
    end

    CLI-->>User: Output File
```

1. User provides screenshot and target language
2. Image is preprocessed and scaled
3. OpenAI Vision analyzes for text and translations
4. Selected OCR backend processes for text locations
5. Results are merged:
   - OCR provides text locations
   - OpenAI provides translations
6. SVG generator creates annotated output
7. Result is displayed or saved

## Design Decisions

### Image Processing
- Max dimension of 2048px balances API costs with accuracy
- JPEG quality of 85% optimizes size vs. quality
- Lanczos resampling for best text clarity

### Caching Strategy
- Comprehensive cache keys prevent redundant API calls
- Schema versioning handles API changes
- File-based cache for persistence

### Translation Workflow
1. OpenAI Vision provides initial analysis
2. OCR backend provides precise text locations
3. Results are merged prioritizing:
   - OCR for text locations
   - OpenAI for translations
   - Source language detection

### Error Handling
- Graceful fallbacks for missing dependencies
- Clear error messages for API issues
- Debug mode for troubleshooting

## Future Improvements

1. **Parallel Processing**
   - Concurrent API calls for faster processing
   - Batch processing for multiple images

2. **UI Improvements**
   - Interactive web interface
   - Real-time preview
   - Custom annotation styles

3. **Enhanced Analysis**
   - Context-aware translations
   - UI element type detection
   - Alternative translation services

4. **Output Formats**
   - PDF export
   - HTML with interactive features
   - Translation memory export

## Dependencies

Core:
- click: CLI interface
- Pillow: Image processing
- anthropic: Claude API
- openai: OpenAI Vision API
- python-dotenv: Configuration

Optional (OCR):
- pytesseract
- easyocr
- paddleocr
- paddlepaddle

## Configuration

The system uses environment variables for API keys:
- `ANTHROPIC_API_KEY`: For Claude Vision API
- `OPENAI_API_KEY`: For OpenAI Vision API

These can be set in the environment or in a `.env` file.

## System Flow Diagram

```mermaid
graph TD