import base64
import hashlib
import io
import json
import os
import re

import click
from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    BadRequestError,
)
from dotenv import load_dotenv
from PIL import Image

from ..response_cache import ResponseCache
from ..types import AnalysisResult, AnalysisSettings, UIElement


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

    # Scale to max 1568 on longest side
    max_long_edge = 1568
    scale = min(max_long_edge / max(image.size), 1.0)
    print(f"Image size: {image.size}")
    print(f"Scale factor: {scale}")
    if scale < 1.0:
        new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to JPEG bytes
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    image_data = buffer.getvalue()
    print(f"Image data size: {len(image_data)} bytes")

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
            print("Element[0]:", data["elements"][0])
            print("  bbox:", data["elements"][0]["bbox"])
            print("    x1:", data["elements"][0]["bbox"][0])
            print("    y1:", data["elements"][0]["bbox"][1])
            print("    x2:", data["elements"][0]["bbox"][2])
            print("    y2:", data["elements"][0]["bbox"][3])

        # Convert bbox from space of uploaded image to source image space
        rscale = 1 / scale * 5  # FIXME
        elements = [
            UIElement(
                text=elem["text"],
                translation=elem["translation"],
                bbox=(
                    int(elem["bbox"][0] * rscale),
                    int(elem["bbox"][1] * rscale),
                    int(elem["bbox"][2] * rscale),
                    int(elem["bbox"][3] * rscale),
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
            title=data.get("title", ""),
            source_language=data.get("source_languages", [])[0],
            elements=elements,
        )

    except Exception as e:
        raise click.ClickException(f"Error processing response: {str(e)}")


def get_analysis_prompt(target_lang: str) -> str:
    return f"""
    Analyze this UI screenshot. First, suggest a title for the image.
    Then, identify the source languages of the text in the image.
    Then, for each text element or button:
    1. Identify its location using pixel coordinates (x1,y1,x2,y2 coordinates)
    2. Extract the original text
    3. Provide a translation to {target_lang} if the text is not already in
        {target_lang}

    Return the results in this exact JSON format:
    {{
        "title": "image title",
        "source_languages": ["en", "zh", "ja", ...],
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
    - If text is already in {target_lang}, leave the translation empty
    """
