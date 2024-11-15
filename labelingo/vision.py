import base64
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Literal

import click
from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    BadRequestError,
)

from .response_cache import ResponseCache

from PIL import Image

import os
from dotenv import load_dotenv

# Lazy imports for OCR backends
def import_ocr_backend(backend: str):
    if backend == "tesseract":
        try:
            import pytesseract
            return pytesseract
        except ImportError:
            raise click.ClickException(
                "Tesseract backend requires pytesseract. Install with:\n"
                "  uv pip install -e '.[ocr]'  # if you're in the project directory\n"
                "  uv pip install 'labelingo[ocr]'  # if you installed from PyPI\n"
                "And install system dependencies:\n"
                "  brew install tesseract  # macOS\n"
                "  sudo apt-get install tesseract-ocr  # Ubuntu/Debian"
            )
    elif backend == "easyocr":
        try:
            import easyocr
            return easyocr
        except ImportError:
            raise click.ClickException(
                "EasyOCR backend requires easyocr. Install with:\n"
                "  uv pip install -e '.[ocr]'  # if you're in the project directory\n"
                "  uv pip install 'labelingo[ocr]'  # if you installed from PyPI"
            )
    elif backend == "paddleocr":
        try:
            from paddleocr import PaddleOCR
            return PaddleOCR
        except ImportError:
            raise click.ClickException(
                "PaddleOCR backend requires paddleocr. Install with:\n"
                "  pip install paddlepaddle  # CPU version\n"
                "  uv pip install -e '.[ocr]'\n\n"
                "If you get import errors after installation, try:\n"
                "  pip uninstall paddlepaddle paddlepaddle-gpu\n"
                "  pip install paddlepaddle"
            )
    return None


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
    from PIL import ExifTags, Image

    MAX_DIMENSION = 1568

    with Image.open(image_path) as img:
        # Get EXIF rotation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == "Orientation":
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

        # Rescale if necessary
        width, height = img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to RGB if necessary (e.g., for PNGs)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Save to bytes
        from io import BytesIO

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        return image_data, img.size


# Define the valid backend types
BackendType = Literal["claude", "tesseract", "easyocr", "paddleocr"]

@dataclass
class AnalysisSettings:
    image_path: Path
    target_lang: str
    backend: BackendType = "claude"
    no_cache: bool = False
    debug: bool = False

def analyze_ui(
    settings: AnalysisSettings,
) -> AnalysisResult:
    """Analyze UI screenshot using specified backend"""

    backends = {
        "claude": analyze_with_claude,
        "tesseract": analyze_with_tesseract,
        "easyocr": analyze_with_easyocr,
        "paddleocr": analyze_with_paddleocr
    }

    if settings.backend not in backends:
        raise ValueError(f"Unknown backend: {settings.backend}")

    if settings.debug:
        print(f"Using {settings.backend} backend...")

    if settings.backend == "claude":
        return analyze_with_claude(settings)
    else:
        elements = backends[settings.backend](settings.image_path, settings.target_lang)
        return AnalysisResult(
            image_dimensions=Image.open(settings.image_path).size,
            elements=elements
        )

def analyze_with_tesseract(image_path: Path, lang_code: str) -> List[UIElement]:
    """Analyze using Tesseract with support for multiple languages"""
    pytesseract = import_ocr_backend("tesseract")

    # Open and convert image to RGB mode
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Handle EXIF rotation
    try:
        for orientation in Image.ExifTags.TAGS.keys():
            if Image.ExifTags.TAGS[orientation] == 'Orientation':
                break

        exif = dict(image._getexif().items())
        if orientation in exif:
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        # No EXIF data or no orientation tag
        pass

    # Convert language code to Tesseract format
    lang_map = {
        'en': 'eng',
        'fr': 'fra',
        'de': 'deu',
        'es': 'spa',
        'it': 'ita',
        'pt': 'por',
        'zh': 'chi_sim',
        'ja': 'jpn',
        'ko': 'kor',
    }
    tesseract_lang = lang_map.get(lang_code, 'eng')  # Default to English if unknown

    # Configure Tesseract
    # PSM modes:
    # 3 = Fully automatic page segmentation, but no OSD (default)
    # 6 = Assume a uniform block of text
    # 7 = Treat the image as a single text line
    custom_config = f'--psm 3 --oem 3 -l {tesseract_lang}'

    try:
        # Get bounding boxes and text
        data = pytesseract.image_to_data(
            image,
            config=custom_config,
            output_type=pytesseract.Output.DICT,
            lang=tesseract_lang
        )

        elements = []
        current_block = None

        # Group by block_num and line_num to combine characters into text blocks
        for i in range(len(data['text'])):
            if not data['text'][i].strip():
                continue

            block_num = data['block_num'][i]
            line_num = data['line_num'][i]
            conf = int(data['conf'][i])

            if conf < 0:  # Skip low confidence detections
                continue

            if current_block and (current_block['block_num'] != block_num or
                                current_block['line_num'] != line_num):
                # Save the completed block
                elements.append(UIElement(
                    text=current_block['text'].strip(),
                    translation=current_block['text'].strip(),  # Same as text since no translation
                    bbox=(
                        current_block['x1'],
                        current_block['y1'],
                        current_block['x2'],
                        current_block['y2']
                    )
                ))
                current_block = None

            if not current_block:
                current_block = {
                    'block_num': block_num,
                    'line_num': line_num,
                    'text': data['text'][i],
                    'x1': data['left'][i],
                    'y1': data['top'][i],
                    'x2': data['left'][i] + data['width'][i],
                    'y2': data['top'][i] + data['height'][i]
                }
            else:
                # Extend current block
                current_block['text'] += ' ' + data['text'][i]
                current_block['x2'] = max(current_block['x2'],
                                        data['left'][i] + data['width'][i])
                current_block['y2'] = max(current_block['y2'],
                                        data['top'][i] + data['height'][i])

        # Add the last block if exists
        if current_block:
            elements.append(UIElement(
                text=current_block['text'].strip(),
                translation=current_block['text'].strip(),
                bbox=(
                    current_block['x1'],
                    current_block['y1'],
                    current_block['x2'],
                    current_block['y2']
                )
            ))

        if not elements:
            raise click.ClickException(
                "Tesseract didn't find any text in the image.\n"
                "Try adjusting the image quality or using a different backend."
            )

        return elements

    except pytesseract.TesseractError as e:
        raise click.ClickException(
            f"Tesseract OCR failed: {str(e)}\n"
            "Make sure Tesseract is properly installed and the language pack is available.\n"
            f"Current language code: {tesseract_lang}"
        )
    except Exception as e:
        # Re-raise other exceptions without the Tesseract-specific message
        raise click.ClickException(f"Error during OCR: {str(e)}")


def analyze_with_easyocr(image_path: Path, lang_code: str) -> List[UIElement]:
    """Analyze using EasyOCR with support for multiple languages"""
    easyocr = import_ocr_backend("easyocr")

    # Convert language code to EasyOCR format
    lang_map = {
        'en': ['en'],
        'fr': ['fr'],
        'de': ['de'],
        'es': ['es'],
        'it': ['it'],
        'pt': ['pt'],
        'zh': ['ch_sim'],  # Chinese simplified
        'ja': ['ja'],      # Japanese
        'ko': ['ko']       # Korean
    }

    easyocr_langs = lang_map.get(lang_code, ['en'])  # Default to English if unknown

    try:
        # Open and preprocess image
        image = Image.open(image_path)

        # Handle EXIF rotation
        try:
            for orientation in Image.ExifTags.TAGS.keys():
                if Image.ExifTags.TAGS[orientation] == 'Orientation':
                    break

            exif = dict(image._getexif().items())
            if orientation in exif:
                if exif[orientation] == 3:
                    image = image.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    image = image.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # No EXIF data or no orientation tag
            pass

        # Convert to RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Save preprocessed image to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            image.save(tmp.name, 'JPEG', quality=95)
            tmp_path = tmp.name

        try:
            reader = easyocr.Reader(easyocr_langs)
            results = reader.readtext(tmp_path)

            elements = []
            for box, text, conf in results:
                if conf > 0.5:  # Filter low confidence detections
                    # Convert box points to bbox format
                    x1 = min(point[0] for point in box)
                    y1 = min(point[1] for point in box)
                    x2 = max(point[0] for point in box)
                    y2 = max(point[1] for point in box)

                    elements.append(UIElement(
                        text=text,
                        translation=text,  # Same as text since no translation
                        bbox=(int(x1), int(y1), int(x2), int(y2))
                    ))

            return elements

        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass

    except ValueError as e:
        raise click.ClickException(
            f"EasyOCR language error: {str(e)}\n"
            f"Supported languages: {', '.join(lang_map.keys())}\n"
            "See https://www.jaided.ai/easyocr/ for full language list"
        )
    except Exception as e:
        raise click.ClickException(f"EasyOCR error: {str(e)}")


def analyze_with_paddleocr(image_path: Path, lang: str) -> List[UIElement]:
    """Analyze using PaddleOCR with support for multiple languages"""
    PaddleOCR = import_ocr_backend("paddleocr")
    ocr = PaddleOCR(use_angle_cls=True, lang=lang)

    results = ocr.ocr(str(image_path))

    elements = []
    for result in results:
        points = result[0]
        text = result[1][0]
        # Convert points to bbox format
        x1 = min(point[0] for point in points)
        y1 = min(point[1] for point in points)
        x2 = max(point[0] for point in points)
        y2 = max(point[1] for point in points)

        elements.append(UIElement(
            text=text,
            translation="",  # Would need separate translation step
            bbox=(int(x1), int(y1), int(x2), int(y2))
        ))
    return elements


def analyze_with_claude(
    settings: AnalysisSettings,
) -> AnalysisResult:
    """Analyze UI screenshot using Claude Vision"""
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise click.ClickException(
            "ANTHROPIC_API_KEY not found in environment or .env file.\n"
            "Please set it in your environment or create a .env file."
        )

    client = Anthropic(api_key=api_key)

    if settings.debug:
        print("Reading and processing image...")
    image_data, (actual_width, actual_height) = get_rotated_image_data(settings.image_path)

    # Calculate image hash
    image_hash = hashlib.sha256(image_data).hexdigest()

    prompt = get_analysis_prompt(settings.target_lang)
    # Combine image and prompt hashes
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    cache_key = f"{image_hash}_{prompt_hash}"
    api_endpoint = "https://api.anthropic.com/v1/"

    cache = ResponseCache()
    cached_response = None if settings.no_cache else cache.get(api_endpoint, cache_key)

    if cached_response:
        if settings.debug:
            print("Using cached analysis...")
        response_text = cached_response
    else:
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        try:
            print("Analyzing image with Claude AI...", end="", flush=True)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            print("done")
            response_text = response.content[0].text
            cache.set(api_endpoint, cache_key, response_text)
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

    if settings.debug:
        print("Response:", response_text)
    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in response")

        data = json.loads(match.group(0))
        if settings.debug:
            print("Raw response data:", data)

        claude_dims = data.get("image_dimensions", {})
        claude_width = claude_dims.get("width", 600)
        claude_height = claude_dims.get("height", 800)

        if settings.debug:
            print(f"Claude dimensions: {claude_width}x{claude_height}")
            print(f"Actual dimensions: {actual_width}x{actual_height}")

        width_scale = actual_width / claude_width
        height_scale = actual_height / claude_height

        if settings.debug:
            print(f"Scale factors: width={width_scale}, height={height_scale}")

        elements = [
            UIElement(
                text=elem["text"],
                translation=elem["translation"],
                bbox=(
                    int(elem["bbox"][0] * width_scale),
                    int(elem["bbox"][1] * height_scale),
                    int(elem["bbox"][2] * width_scale),
                    int(elem["bbox"][3] * height_scale),
                ),
            )
            for elem in data["elements"]
        ]

        if settings.debug and elements:
            print(f"First element bbox in Claude space: {data['elements'][0]['bbox']}")
            print(f"First element bbox in image space: {elements[0].bbox}")

        if settings.debug:
            print(f"Found {len(data['elements'])} text elements")
        return AnalysisResult(
            image_dimensions=(actual_width, actual_height), elements=elements
        )

    except Exception as e:
        raise click.ClickException(f"Error processing response: {str(e)}")
