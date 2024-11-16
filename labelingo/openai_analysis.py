import base64
import hashlib
import io
import json
from pathlib import Path
from typing import List as PyList

import click
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from pydantic import BaseModel

from .response_cache import ResponseCache


class UITextElement(BaseModel):
    text: str
    translation: str

class UIAnalysis(BaseModel):
    source_language: str
    elements: PyList[UITextElement]

def get_openai_analysis(image_path: Path, target_lang: str) -> dict:
    """Get text analysis and translations from OpenAI Vision"""
    load_dotenv()
    client = OpenAI()

    # Read and scale image
    image = Image.open(image_path)

    # Scale to max 2048 on longest side
    max_long_edge = 2048
    max_short_edge = 768
    scale = min(max_long_edge / max(image.size), max_short_edge / min(image.size))
    if scale < 1.0:
        new_size = tuple(int(dim * scale) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to JPEG bytes
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    image_data = buffer.getvalue()
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Create cache key components
    api_endpoint = "https://api.openai.com/v1/chat/completions"
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Schema hash includes the structure and target language
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
                {
                    "type": "text",
                    "text": f"Analyze this UI screenshot. Identify the source language as a two-letter code (e.g. 'en') and extract all UI text elements (labels, buttons, etc.). Provide translations to {target_lang}.",
                },
            ],
        }
    ]

    schema_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    cache_key = f"{api_endpoint}_{schema_hash}_{image_hash}"

    cache = ResponseCache()
    cached_response = cache.get(api_endpoint, cache_key)

    if cached_response:
        return json.loads(cached_response)

    try:
        print(f"Sending request to OpenAI API...")
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=UIAnalysis,
        )

        result = response.choices[0].message.parsed

        # Convert Pydantic model to dict for caching
        result_dict = result.model_dump()
        cache.set(api_endpoint, cache_key, json.dumps(result_dict))
        return result_dict

    except Exception as e:
        raise click.ClickException(f"OpenAI API error: {str(e)}")
