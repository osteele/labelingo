from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

# Define the valid backend types
BackendType = Literal["claude", "tesseract", "easyocr", "paddleocr"]

OutputFormat = Literal["svg", "png", "pdf"]


@dataclass
class AnalysisSettings:
    target_lang: str
    backend: BackendType = "easyocr"
    no_cache: bool = False
    debug: bool = False


@dataclass
class UIElement:
    text: str
    translation: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2


@dataclass
class AnalysisResult:
    elements: List[UIElement]
    source_language: Optional[str] = None
    title: str | None = None
