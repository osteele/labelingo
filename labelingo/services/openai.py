import base64
import hashlib
import io
import json
from typing import Any, List

import click
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam
from PIL import Image
from pydantic import BaseModel

from ..response_cache import ResponseCache
from ..types import AnalysisSettings


class UITextElement(BaseModel):
    text: str
    translation: str


class UIAnalysis(BaseModel):
    title: str
    source_languages: List[str]
    elements: List[UITextElement]


def get_openai_analysis(
    image: Image.Image, settings: AnalysisSettings
) -> dict[str, Any]:
    """Get text analysis and translations from OpenAI Vision"""
    load_dotenv()
    client = OpenAI()

    # Scale to max 2048 on longest side
    max_long_edge = 2048
    max_short_edge = 768
    scale = min(max_long_edge / max(image.size), max_short_edge / min(image.size))
    if scale < 1.0:
        new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
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
    target_lang = settings.target_lang
    messages: List[ChatCompletionUserMessageParam] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                },
                {
                    "type": "text",
                    "text": f"Analyze this UI screenshot. Provide a brief descriptive title for the image. Identify the source languages as two-letter codes (e.g. 'en', 'zh', ja', etc.) and extract all UI text elements (labels, buttons, etc.). Provide translations to {target_lang}.",  # noqa: E501
                },
            ],
        }
    ]

    schema_hash = hashlib.sha256(
        json.dumps(messages, sort_keys=True).encode()
    ).hexdigest()
    cache_key = f"{api_endpoint}_{schema_hash}_{image_hash}"

    cache = ResponseCache()
    cached_response = cache.get(api_endpoint, cache_key)

    if cached_response:
        result_dict = json.loads(cached_response)
    else:
        try:
            print("Sending request to OpenAI API...")
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=UIAnalysis,
            )

            result = response.choices[0].message.parsed
            if not result:
                raise click.ClickException("No result from OpenAI API")
            result_dict = result.model_dump()
            cache.set(api_endpoint, cache_key, json.dumps(result_dict))

        except Exception as e:
            raise click.ClickException(f"OpenAI API error: {str(e)}")

    source_languages = result_dict.get("source_languages", [])
    if settings.debug:
        print(f"Detected source languages: {source_languages}")
        print(f"Title: {result_dict.get('title', '')}")
    if len(source_languages) > 1:
        source_languages = [ln.strip() for ln in source_languages if ln != target_lang]

    return dict(
        title=result_dict.get("title", None),
        source_language=source_languages[0],
        elements=result_dict.get("elements", []),
    )
