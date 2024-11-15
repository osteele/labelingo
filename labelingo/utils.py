import platform
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import ExifTags, Image


def open_file(path: Path):
    """Open a file with the default system application"""
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(path)])
        elif platform.system() == "Windows":  # Windows
            subprocess.run(["start", str(path)], shell=True)
        else:  # Linux and others
            subprocess.run(["xdg-open", str(path)])
    except Exception as e:
        print(f"Failed to open file: {e}", file=sys.stderr)


def get_rotated_image_data(image_path: Path) -> Tuple[bytes, Tuple[int, int]]:
    """Read image file, rotate according to EXIF, and return base64 data and dimensions"""
    MAX_DIMENSION = 1568

    with preprocess_image(image_path) as img:
        # Rescale if necessary
        width, height = img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        return image_data, img.size


def preprocess_image(image_path: Path) -> Image.Image:
    """Open image, handle EXIF rotation, convert to RGB"""
    img = Image.open(image_path)

    # Handle EXIF rotation
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

    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")

    return img


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """Get image dimensions, accounting for EXIF rotation"""
    with preprocess_image(image_path) as img:
        return img.size
