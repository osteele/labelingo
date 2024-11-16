import base64
import hashlib
import json
import os
import re
from typing import TYPE_CHECKING, Any, List, Optional

import click
from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    BadRequestError,
)
from dotenv import load_dotenv
from PIL import Image

from .openai_analysis import get_openai_analysis
from .response_cache import ResponseCache
from .types import AnalysisResult, AnalysisSettings, UIElement

# Type checking imports
if TYPE_CHECKING:
    import easyocr  # type: ignore # noqa: F401
    import pytesseract  # type: ignore # noqa: F401
    from paddleocr import PaddleOCR  # type: ignore  # noqa: F401

OCR_BACKEND_VERSION = 2

# Lazy imports for OCR backends
def import_ocr_backend(backend: str) -> Optional[Any]:
    """Import OCR backend module safely with proper type handling"""
    if backend == "tesseract":
        try:
            import pytesseract  # type: ignore  # noqa: I001

            return pytesseract
        except ImportError:
            raise click.ClickException(
                "Tesseract backend requires pytesseract. Install with:\n"
                "  uv pip install -e '.[ocr]'"
            )
    elif backend == "easyocr":
        try:
            import easyocr  # type: ignore  # noqa: I001

            return easyocr
        except ImportError:
            raise click.ClickException(
                "EasyOCR backend requires easyocr. Install with:\n"
                "  uv pip install -e '.[ocr]'"
            )
    elif backend == "paddleocr":
        try:
            from paddleocr import PaddleOCR  # type: ignore  # noqa: I001

            return PaddleOCR  # type: ignore
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


def get_analysis_prompt(target_lang: str) -> str:
    return f"""
    Analyze this UI screenshot. First, tell me the dimensions of the image
    you're analyzing. Then, for each text element or button:
    1. Identify its location using pixel coordinates (x1,y1,x2,y2 coordinates)
    2. Extract the original text
    3. Provide a translation to {target_lang} if the text is not already in
        {target_lang}

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


def analyze_ui(image: Image.Image, settings: AnalysisSettings) -> AnalysisResult:
    """Analyze UI screenshot using specified backend and OpenAI for translations"""

    # First get OpenAI analysis for translations
    openai_analysis = get_openai_analysis(image, settings)
    source_language = openai_analysis["source_language"]
    openai_translations = {
        elem["text"]: elem["translation"] for elem in openai_analysis["elements"]
    }

    # Get OCR results from selected backend
    if settings.backend == "claude":
        result = analyze_with_claude(image, settings)
    else:
        backend_fn = {
            "tesseract": analyze_with_tesseract,
            "easyocr": analyze_with_easyocr,
            "paddleocr": analyze_with_paddleocr,
        }[settings.backend]

        # Calculate cache key using backend name, version, and image hash
        image_hash = hashlib.sha256(image.tobytes()).hexdigest()
        cache_key = f"ocr_{settings.backend}_v{OCR_BACKEND_VERSION}_{image_hash}"

        cache = ResponseCache()
        cached_json = None if settings.no_cache else cache.get("ocr", cache_key)

        if cached_json is not None:
            try:
                cached_data = json.loads(cached_json)
                elements = [
                    UIElement(
                        text=elem["text"],
                        translation=elem["translation"],
                        bbox=tuple(elem["bbox"]),
                    )
                    for elem in cached_data
                ]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load cached data: {e}")
                elements = None

        if cached_json is None or elements is None:
            print(f"Analyzing with {settings.backend} backend...")
            elements = backend_fn(image, source_language)
            # Cache the elements as JSON
            elements_data = [
                {"text": elem.text, "translation": elem.translation, "bbox": elem.bbox}
                for elem in elements
            ]
            cache.set("ocr", cache_key, json.dumps(elements_data))

        result = AnalysisResult(
            title=openai_analysis.get("title", None),
            elements=elements,
            source_language=source_language,
        )

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


def analyze_with_tesseract(image: Image.Image, lang_code: str) -> List[UIElement]:
    """Analyze using Tesseract with support for multiple languages"""
    pytesseract = import_ocr_backend("tesseract")
    if pytesseract is None:
        raise click.ClickException("Failed to import pytesseract")

    # Define tesseract_lang at the start to avoid unbound variable
    lang_map = {
        "en": "eng",
        "fr": "fra",
        "de": "deu",
        "es": "spa",
        "it": "ita",
        "pt": "por",
        "zh": "chi_sim",
        "ja": "jpn",
        "ko": "kor",
    }
    tesseract_lang = lang_map.get(lang_code, "eng")  # Default to English if unknown

    try:
        # Open and convert image to RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Configure Tesseract
        custom_config = f"--psm 3 --oem 3 -l {tesseract_lang}"

        # Get bounding boxes and text
        data = pytesseract.image_to_data(
            image,
            config=custom_config,
            output_type=pytesseract.Output.DICT,
            lang=tesseract_lang
        )

        elements: List[UIElement] = []
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
                elements.append(
                    UIElement(
                        text=current_block["text"].strip(),
                        translation=current_block["text"].strip(),
                        # Same as text since no translation
                        bbox=(
                            current_block["x1"],
                            current_block["y1"],
                            current_block["x2"],
                            current_block["y2"],
                        ),
                    )
                )
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
            "Make sure Tesseract is properly installed and the language pack is available.\n"  # noqa: E501
            f"Current language code: {tesseract_lang}"
        )
    except Exception as e:
        # Re-raise other exceptions without the Tesseract-specific message
        raise click.ClickException(f"Error during OCR: {str(e)}")


def analyze_with_easyocr(
    image: Image.Image, lang_code: str, debug: bool = False
) -> List[UIElement]:
    """Analyze using EasyOCR with support for multiple languages"""
    easyocr = import_ocr_backend("easyocr")
    if easyocr is None:
        raise click.ClickException("Failed to import easyocr")

    # Define language map at the start
    easyocr_lang_map = {
        "en": "en",
        "fr": "fr",
        "de": "de",
        "es": "es",
        "it": "it",
        "pt": "pt",
        "zh": "ch_sim",
        "ja": "ja",
        "ko": "ko",
    }

    # Create reader with proper error handling
    try:
        reader = getattr(easyocr, "Reader")([lang_code])
        if reader is None:
            raise click.ClickException("Failed to create EasyOCR reader")

        # Save preprocessed image to a temporary file
        import sys
        import tempfile  # Import sys here for stderr

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            image.save(tmp.name, 'JPEG', quality=95)
            tmp_path = tmp.name

        try:
            results = reader.readtext(tmp_path)

            elements: List[UIElement] = []
            for box, text, conf in results:
                if conf > 0:  # Filter low confidence detections
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
            except (OSError, IOError) as e:
                if debug:  # Use the debug parameter instead of settings
                    print(
                        f"Warning: Failed to remove temporary file {tmp_path}: {e}",
                        file=sys.stderr,
                    )

    except ValueError as e:
        raise click.ClickException(
            f"EasyOCR language error: {str(e)}\n"
            f"Supported languages: {', '.join(easyocr_lang_map.keys())}\n"
            "See https://www.jaided.ai/easyocr/ for full language list"
        )
    except Exception as e:
        raise click.ClickException(f"EasyOCR error: {str(e)}")


def analyze_with_paddleocr(image: Image.Image, lang: str) -> List[UIElement]:
    """Analyze using PaddleOCR with support for multiple languages"""
    PaddleOCR = import_ocr_backend("paddleocr")
    if PaddleOCR is None:
        raise click.ClickException("Failed to import PaddleOCR")

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        if ocr is None:
            raise click.ClickException("Failed to create PaddleOCR instance")

        results = ocr.ocr(image)
        if results is None:
            raise click.ClickException("PaddleOCR returned no results")

        elements: List[UIElement] = []  # Explicitly type the list
        for result in results:
            if not result or len(result) < 2:  # Basic validation
                continue

            points = result[0]
            if not points:  # Skip if no bounding box
                continue

            text = result[1][0] if result[1] else ""
            if not text:  # Skip empty text
                continue

            # Convert points to bbox format
            x1 = min(float(point[0]) for point in points)
            y1 = min(float(point[1]) for point in points)
            x2 = max(float(point[0]) for point in points)
            y2 = max(float(point[1]) for point in points)

            elements.append(
                UIElement(
                    text=str(text),
                    translation="",  # Would need separate translation step
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                )
            )

        if not elements:
            raise click.ClickException(
                "PaddleOCR didn't find any text in the image.\n"
                "Try adjusting the image quality or using a different backend."
            )

        return elements

    except Exception as e:
        raise click.ClickException(f"PaddleOCR error: {str(e)}")


def analyze_with_claude(
    image: Image.Image,
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

    # Calculate image hash
    image_hash = hashlib.sha256(image.tobytes()).hexdigest()

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
        image_base64 = base64.b64encode(image.tobytes()).decode("utf-8")

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

            # Handle response content safely
            content = response.content
            if not content:
                raise click.ClickException("Empty response from Claude")

            # Cast the message to Any to avoid type checking issues
            from typing import Any, cast

            message = cast(Any, content[0])

            # Access content safely
            response_text = getattr(message, "text", None)
            if not response_text:
                raise click.ClickException("No text in Claude's response")

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
                f"Response details: {getattr(e, 'response', 'No response details available')}"  # noqa: E501
            )
        except APIError as e:
            print(" failed")
            raise click.ClickException(
                f"Claude API error: {str(e)}\n"
                f"Response details: {getattr(e, 'response', 'No response details available')}"  # noqa: E501
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
            print(f"Actual dimensions: {image.width}x{image.height}")

        width_scale = image.width / claude_width
        height_scale = image.height / claude_height

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
        return AnalysisResult(elements=elements)

    except Exception as e:
        raise click.ClickException(f"Error processing response: {str(e)}")
