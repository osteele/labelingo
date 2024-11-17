from PIL import Image

from ..types import AnalysisResult, AnalysisSettings, UIElement
from .find_labels import (
    find_label_locations,
)
from .openai import get_openai_analysis


def analyze_ui(image: Image.Image, settings: AnalysisSettings) -> AnalysisResult:
    """Analyze UI screenshot using specified backend and OpenAI for translations"""

    # First get OpenAI analysis for translations
    openai_analysis = get_openai_analysis(image, settings)
    source_language = openai_analysis["source_language"]
    openai_translations = {
        elem["text"]: elem["translation"] for elem in openai_analysis["elements"]
    }

    # Get OCR results from selected backend
    result = find_label_locations(image, settings, openai_analysis, source_language)

    # Debug output for comparing OCR and OpenAI results
    if settings.debug:
        ocr_texts = {element.text for element in result.elements}
        openai_texts = set(openai_translations.keys())

        ocr_only = ocr_texts - openai_texts
        openai_only = openai_texts - ocr_texts

        if ocr_only:
            print("\nTexts found by OCR but not by OpenAI:")
            for text in sorted(ocr_only):
                print(f"  • {text}")

        if openai_only:
            print("\nTexts found by OpenAI but not by OCR:")
            for text in sorted(openai_only):
                print(f"  • {text}")

    # Update existing elements with translations
    for element in result.elements:
        if not element.translation or element.translation == element.text:
            element.translation = openai_translations.get(element.text, None)

    # Add elements for translations that don't have corresponding OCR results
    ocr_texts = {element.text for element in result.elements}
    for text, translation in openai_translations.items():
        if text not in ocr_texts:
            result.elements.append(
                UIElement(
                    text=text,
                    translation=translation,
                    bbox=(0, 0, 0, 0),  # Null bounding box
                )
            )

    return result
