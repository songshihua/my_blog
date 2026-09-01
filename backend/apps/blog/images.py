"""Validation and normalization for images inserted through the note editor."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import ArticleImage

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 24_000_000
MAX_IMAGE_EDGE = 2_400


class NoteImageError(ValueError):
    """A safe image validation message for the local author."""


def save_note_image(uploaded_file: BinaryIO) -> ArticleImage:
    content = _read_upload(uploaded_file)
    original_filename = _safe_filename(getattr(uploaded_file, "name", ""))

    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise NoteImageError("仅支持 JPEG、PNG 和 WebP 图片。")
            width, height = source.size
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise NoteImageError("图片像素尺寸过大，请压缩后重试。")
            source.load()
            normalized = ImageOps.exif_transpose(source)
            normalized.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
            has_alpha = normalized.mode in {"RGBA", "LA"} or (
                normalized.mode == "P" and "transparency" in normalized.info
            )
            output = BytesIO()
            if has_alpha:
                normalized.convert("RGBA").save(output, format="PNG", optimize=True)
                extension = "png"
                content_type = "image/png"
            else:
                normalized.convert("RGB").save(
                    output,
                    format="JPEG",
                    quality=88,
                    optimize=True,
                    progressive=True,
                )
                extension = "jpg"
                content_type = "image/jpeg"
            rendered = output.getvalue()
            rendered_width, rendered_height = normalized.size
            if len(rendered) > settings.NOTE_IMAGE_UPLOAD_MAX_BYTES:
                raise NoteImageError("图片处理后仍然过大，请进一步压缩后重试。")
    except NoteImageError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise NoteImageError("图片文件损坏或内容无法识别。") from exc

    image = ArticleImage(
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=len(rendered),
        width=rendered_width,
        height=rendered_height,
    )
    image.file.save(f"image.{extension}", ContentFile(rendered), save=False)
    try:
        image.save()
    except Exception:
        if image.file.name:
            image.file.storage.delete(image.file.name)
        raise
    return image


def _read_upload(uploaded_file: BinaryIO) -> bytes:
    maximum = settings.NOTE_IMAGE_UPLOAD_MAX_BYTES
    declared_size = getattr(uploaded_file, "size", None)
    if isinstance(declared_size, int) and declared_size > maximum:
        raise NoteImageError(f"图片不能超过 {maximum // (1024 * 1024)} MB。")
    content = uploaded_file.read(maximum + 1)
    if not content:
        raise NoteImageError("上传图片不能为空。")
    if len(content) > maximum:
        raise NoteImageError(f"图片不能超过 {maximum // (1024 * 1024)} MB。")
    return content


def _safe_filename(value: object) -> str:
    name = Path(str(value or "image").replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        return "image"
    return name[:240]
