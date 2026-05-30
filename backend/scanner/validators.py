from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_uploaded_qr_image(uploaded_file):
    if not uploaded_file:
        raise ValidationError("Upload a QR image to analyze.")

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Supported QR formats: PNG, JPG, JPEG, WEBP, or BMP.")

    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValidationError("QR images must be 5 MB or smaller.")

    try:
        image = Image.open(uploaded_file)
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("The uploaded file is not a readable image.") from exc
    finally:
        uploaded_file.seek(0)


def normalize_search(value):
    return (value or "").strip()[:200]


def clean_status_filter(value):
    allowed = {"safe", "warning", "malicious", "invalid"}
    value = (value or "").strip().lower()
    return value if value in allowed else ""
