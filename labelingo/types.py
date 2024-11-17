from dataclasses import dataclass
from typing import List, Literal, Tuple

# Define the valid backend types
OcrServiceType = Literal["claude", "tesseract", "easyocr", "paddleocr"]
TranslationService = Literal["openai", "claude"]

OutputFormat = Literal["svg", "png", "pdf"]


@dataclass
class AnalysisSettings:
    target_lang: str
    ocr_service: OcrServiceType = "easyocr"
    translation_service: TranslationService = "openai"
    no_cache: bool = False
    debug: bool = False


@dataclass
class UIElement:
    text: str
    translation: str | None
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2


@dataclass
class AnalysisResult:
    elements: List[UIElement]
    source_language: str | None = None
    title: str | None = None
