from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

# Define the valid backend types
BackendType = Literal["claude", "tesseract", "easyocr", "paddleocr"]


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
    image_dimensions: Tuple[int, int]  # width, height
    elements: List[UIElement]
    source_language: Optional[str] = None  # Add source language field
