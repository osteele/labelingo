import click
from PIL import Image

from ..types import AnalysisResult, AnalysisSettings, UIElement
from .find_labels import (
    find_label_locations,
)
from .scene_identification import identify_scene_properties


def analyze_ui(image: Image.Image, settings: AnalysisSettings) -> AnalysisResult:
    """Analyze UI screenshot using specified backend and OpenAI for translations"""

    # First get scene analysis
    scene_analysis = identify_scene_properties(image, settings)
    source_language = scene_analysis.source_language
    if not source_language:
        raise click.ClickException("Source language not found")

    # Get label locations results from selected service
    if settings.label_location_service is None:
        return scene_analysis

    label_location_analysis = find_label_locations(
        image, settings, scene_analysis, source_language
    )

    # Debug output for comparing scene analysis and label location results
    if settings.debug:
        scene_analysis_strings = {elem.text for elem in scene_analysis.elements}
        label_location_strings = {
            elem.text for elem in label_location_analysis.elements
        }

        label_locations_only = label_location_strings - scene_analysis_strings
        scene_analysis_only = scene_analysis_strings - label_location_strings

        if label_locations_only:
            print(f"\nTexts found by OCR but not by {settings.scene_analysis_service}:")
            for text in sorted(label_locations_only):
                print(f"  • {text}")

        if scene_analysis_only:
            print(f"\nTexts found by {settings.scene_analysis_service} but not by OCR:")
            for text in sorted(scene_analysis_only):
                print(f"  • {text}")

    # Update existing elements with translations
    translations = {elem.text: elem.translation for elem in scene_analysis.elements}
    for element in label_location_analysis.elements:
        text = element.text
        if not element.translation or element.translation == text:
            element.translation = translations.get(text, None)

    # Add elements for translations that don't have corresponding OCR results
    label_location_strings = {
        element.text for element in label_location_analysis.elements
    }
    for text, translation in translations.items():
        if text not in label_location_strings:
            label_location_analysis.elements.append(
                UIElement(text=text, translation=translation)
            )

    return label_location_analysis
