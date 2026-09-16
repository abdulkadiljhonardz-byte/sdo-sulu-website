from pathlib import Path
import warnings

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"}
BLOCKED_UPLOAD_EXTENSIONS = {".php", ".exe", ".sh", ".bat", ".js", ".html", ".htm"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def validate_secure_upload(upload):
    extension = Path(upload.name).suffix.lower()
    if extension in BLOCKED_UPLOAD_EXTENSIONS or extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("This file type is not permitted.")
    if upload.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Files must not exceed 10 MB.")


def validate_secure_image_upload(upload):
    """Validate both the filename and decoded content of a portal image."""
    validate_secure_upload(upload)
    extension = Path(upload.name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png"}:
        raise ValidationError("Images must be JPG or PNG files.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                width, height = image.size
                image_format = image.format
                image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("The uploaded file is not a safe, valid image.") from exc
    finally:
        upload.seek(0)
    if image_format not in {"JPEG", "PNG"}:
        raise ValidationError("Images must contain JPG or PNG data.")
    if width * height > 40_000_000:
        raise ValidationError("The image dimensions are too large.")
    extension_matches = {
        "JPEG": {".jpg", ".jpeg"},
        "PNG": {".png"},
    }
    if extension not in extension_matches[image_format]:
        raise ValidationError("The image filename does not match its actual format.")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
