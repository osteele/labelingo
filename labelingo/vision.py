from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from anthropic import (
    Anthropic,
    APIConnectionError,
    BadRequestError,
    APIError,
)
import base64
import json
import re
import sys
import click
import hashlib
from .response_cache import ResponseCache

@dataclass
class UIElement:
    text: str
    translation: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2

def get_analysis_prompt(target_lang: str) -> str:
    return f"""
    Analyze this UI screenshot. First, tell me the dimensions of the image you're analyzing.
    Then, for each text element or button:
    1. Identify its location using pixel coordinates (x1,y1,x2,y2 coordinates)
    2. Extract the original text
    3. Provide a translation to {target_lang} if the text is not already in {target_lang}

    Return the results in this exact JSON format:
    {{
        "image_dimensions": {{
            "width": width_in_pixels,
            "height": height_in_pixels
        }},
        "elements": [
            {{
                "bbox": [x1, y1, x2, y2],
                "text": "original text",
                "translation": "translation in {target_lang}"
            }}
        ]
    }}

    Notes:
    - Use pixel coordinates for bbox values
    - Include only text elements and buttons
    - If text is already in {target_lang}, use it as the translation
    """

@dataclass
class AnalysisResult:
    image_dimensions: Tuple[int, int]  # width, height
    elements: List[UIElement]

def get_rotated_image_data(image_path: Path) -> Tuple[bytes, Tuple[int, int]]:
    """Read image file, rotate according to EXIF, and return base64 data and dimensions"""
    from PIL import Image, ExifTags

    with Image.open(image_path) as img:
        # Get EXIF rotation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break

            exif = dict(img._getexif().items())
            if orientation in exif:
                if exif[orientation] == 3:
                    img = img.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    img = img.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # No EXIF data or no orientation tag
            pass

        # Convert to RGB if necessary (e.g., for PNGs)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        image_data = buffer.getvalue()

        return image_data, img.size

def analyze_ui(client: Anthropic, image_path: Path, target_lang: str, *, no_cache: bool = False, debug: bool = False) -> AnalysisResult:
    """Analyze UI screenshot and return dimensions and list of UI elements with translations"""
    print("Reading and processing image...")
    image_data, (actual_width, actual_height) = get_rotated_image_data(image_path)

    prompt = get_analysis_prompt(target_lang)
    cache = ResponseCache()
    cached_response = None if no_cache else cache.get(image_path, target_lang, prompt)

    if cached_response:
        if debug:
            print("Using cached analysis...")
        response_text = cached_response
    else:
        print("Analyzing image with Claude AI...")
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        try:
            print("Waiting for response...", end='', flush=True)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            print(" done")
            response_text = response.content[0].text
            cache.set(image_path, target_lang, prompt, response_text)
        except APIConnectionError as e:
            print(" failed")  # Complete the progress line in case of error
            raise click.ClickException(
                f"Failed to connect to Claude API: {str(e)}\n"
                "Please check your internet connection and try again."
            )
        except BadRequestError as e:
            print(" failed")
            raise click.ClickException(
                f"Bad request to Claude API: {str(e)}\n"
                f"Response details: {getattr(e, 'response', 'No response details available')}"
            )
        except APIError as e:
            print(" failed")
            raise click.ClickException(
                f"Claude API error: {str(e)}\n"
                f"Response details: {getattr(e, 'response', 'No response details available')}"
            )

    print("Processing response...")
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in response")

        data = json.loads(match.group(0))
        if debug:
            print("Raw response data:", data)

        claude_dims = data.get("image_dimensions", {})
        claude_width = claude_dims.get("width", 600)
        claude_height = claude_dims.get("height", 800)

        if debug:
            print(f"Claude dimensions: {claude_width}x{claude_height}")
            print(f"Actual dimensions: {actual_width}x{actual_height}")

        width_scale = actual_width / claude_width
        height_scale = actual_height / claude_height

        if debug:
            print(f"Scale factors: width={width_scale}, height={height_scale}")

        elements = [
            UIElement(
                text=elem["text"],
                translation=elem["translation"],
                bbox=(
                    int(elem["bbox"][0] * width_scale),
                    int(elem["bbox"][1] * height_scale),
                    int(elem["bbox"][2] * width_scale),
                    int(elem["bbox"][3] * height_scale)
                )
            )
            for elem in data["elements"]
        ]

        if debug and elements:
            print(f"First element bbox in Claude space: {data['elements'][0]['bbox']}")
            print(f"First element bbox in image space: {elements[0].bbox}")

        print(f"Found {len(data['elements'])} text elements")
        return AnalysisResult(
            image_dimensions=(actual_width, actual_height),
            elements=elements
        )

    except Exception as e:
        raise click.ClickException(f"Error processing response: {str(e)}")
