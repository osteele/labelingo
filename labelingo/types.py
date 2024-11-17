from dataclasses import dataclass
from typing import List, Literal, Tuple

# Define the valid backend types
SceneAnalysisService = Literal["openai", "claude"]
LabelLocationService = Literal["claude", "tesseract", "easyocr", "paddleocr"]

OutputFormat = Literal["svg", "png", "pdf"]


@dataclass
class AnalysisSettings:
    target_lang: str
    scene_analysis_service: SceneAnalysisService = "openai"
    label_location_service: LabelLocationService = "easyocr"
    no_cache: bool = False
    debug: bool = False


@dataclass
class UIElement:
    text: str
    translation: str | None = None
    bbox: Tuple[int, int, int, int] | None = None  # x1, y1, x2, y2


@dataclass
class AnalysisResult:
    elements: List[UIElement]
    source_language: str | None = None
    title: str | None = None
