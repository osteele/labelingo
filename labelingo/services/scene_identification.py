from PIL import Image

from ..types import AnalysisResult, AnalysisSettings
from .claude import analyze_with_claude
from .openai import openai_scene_analysis


def identify_scene_properties(
    image: Image.Image, settings: AnalysisSettings
) -> AnalysisResult:
    """Identify the languages and suggest a title. Some services may also
    perform OCR and translation."""
    if settings.translation_service == "openai":
        return openai_scene_analysis(image, settings)
    elif settings.translation_service == "claude":
        return analyze_with_claude(image, settings)
    else:
        raise NotImplementedError(
            f"Translation service {settings.translation_service} not implemented"
        )
