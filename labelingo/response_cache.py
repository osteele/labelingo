from pathlib import Path
import hashlib
import json
from typing import Optional
import sys

class ResponseCache:
    def __init__(self, cache_dir: Path = Path.home() / ".labelingo" / "cache", debug: bool = False):
        self.cache_dir = cache_dir
        self.debug = debug
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, image_path: Path, target_lang: str, prompt: str) -> str:
        """Generate cache key from image content and prompt"""
        with open(image_path, "rb") as f:
            image_hash = hashlib.md5(f.read()).hexdigest()
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        return f"{image_hash}_{target_lang}_{prompt_hash}"

    def get(self, image_path: Path, target_lang: str, prompt: str) -> Optional[str]:
        """Retrieve cached Claude response"""
        cache_key = self._get_cache_key(image_path, target_lang, prompt)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    return f.read()
            except Exception as e:
                if self.debug:
                    print(f"Warning: Invalid cache file, will reanalyze. Error: {e}", file=sys.stderr)
                cache_file.unlink(missing_ok=True)
                return None
        return None

    def set(self, image_path: Path, target_lang: str, prompt: str, response: str):
        """Cache Claude's response"""
        cache_key = self._get_cache_key(image_path, target_lang, prompt)
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            f.write(response)
