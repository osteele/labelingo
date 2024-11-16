import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class ResponseCache:
    def __init__(
        self,
        cache_dir: Path = Path.home() / ".labelingo" / "cache",
        debug: bool = False,
    ):
        self.cache_dir = cache_dir
        self.debug = debug
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, api_endpoint: str, cache_key: str) -> Path:
        """Generate cache file path using combined hash of endpoint and key"""
        combined = f"{api_endpoint}:{cache_key}"
        full_hash = hashlib.sha256(combined.encode()).hexdigest()
        prefix, rest = full_hash[:2], full_hash[2:]
        subdir = self.cache_dir / prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{rest}.json"

    def _cleanup_old_cache(self, max_files: int = 100, max_age_days: int = 14):
        """Remove old cache files if there are too many"""
        cache_files = []
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                cache_files.extend(subdir.glob("*.json"))

        if len(cache_files) > max_files:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            for file in cache_files:
                try:
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < cutoff_date:
                        file.unlink()
                except Exception as e:
                    if self.debug:
                        print(
                            f"Warning: Failed to check/remove cache file {file}: {e}",
                            file=sys.stderr,
                        )

    def get(self, api_endpoint: str, cache_key: str) -> Optional[str]:
        """Retrieve cached Claude response"""
        cache_file = self._get_cache_path(api_endpoint, cache_key)

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    return f.read()
            except Exception as e:
                if self.debug:
                    print(
                        f"Warning: Invalid cache file, will reanalyze. Error: {e}",
                        file=sys.stderr,
                    )
                cache_file.unlink(missing_ok=True)
                return None
        return None

    def set(self, api_endpoint: str, cache_key: str, response: str) -> None:
        """Cache Claude's response"""
        cache_file = self._get_cache_path(api_endpoint, cache_key)
        with open(cache_file, "w") as f:
            f.write(response)
        self._cleanup_old_cache()
