"""Bounded, synchronous import of local Markdown, DOCX, and text PDF notes."""

from __future__ import annotations

import hashlib
import math
import re
import stat
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import Article, ArticleSourceFile, Category

MAX_EXTRACTED_CHARACTERS = 1_000_000
MAX_PDF_PAGES = 100
MAX_DOCX_MEMBERS = 1_500
MAX_DOCX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_DOCX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 200

FORMAT_BY_EXTENSION = {
    ".md": ArticleSourceFile.SourceFormat.MARKDOWN,
    ".markdown": ArticleSourceFile.SourceFormat.MARKDOWN,
    ".docx": ArticleSourceFile.SourceFormat.DOCX,
    ".pdf": ArticleSourceFile.SourceFormat.PDF,
}

ALLOWED_CONTENT_TYPES = {
    ArticleSourceFile.SourceFormat.MARKDOWN: {
        "",
        "application/octet-stream",
        "text/markdown",
        "text/plain",
    },
    ArticleSourceFile.SourceFormat.DOCX: {
        "",
        "application/octet-stream",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    ArticleSourceFile.SourceFormat.PDF: {
        "",
        "application/octet-stream",
        "application/pdf",
    },
}


class NoteImportError(ValueError):
    """A safe validation message that can be returned to the local author."""


class DuplicateNoteError(NoteImportError):
    """The same source bytes have already been imported."""


@dataclass(frozen=True, slots=True)
class ExtractedNote:
    body_markdown: str
    outline: list[dict[str, object]]
    source_format: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str


def import_note(
    uploaded_file: BinaryIO,
    *,
    category: Category,
    title: str = "",
    summary: str = "",
) -> Article:
    """Validate, extract, persist, and privately store one uploaded note."""

    extracted = extract_uploaded_note(uploaded_file)
    if ArticleSourceFile.objects.filter(sha256=extracted.sha256).exists():
        raise DuplicateNoteError("该文件已经导入过，请勿重复上传。")

    normalized_title = _clean_text(title, 200)
    if not normalized_title and extracted.outline:
        normalized_title = _clean_text(extracted.outline[0].get("text"), 200)
    if not normalized_title:
        normalized_title = _clean_text(Path(extracted.original_filename).stem, 200)
    if not normalized_title:
        normalized_title = f"导入笔记 {extracted.sha256[:8]}"

    normalized_summary = _clean_text(summary, 1000) or _derive_summary(extracted.body_markdown)
    article_slug = _build_slug(normalized_title, extracted.sha256)
    saved_name = ""
    try:
        with transaction.atomic():
            article = Article.objects.create(
                title=normalized_title,
                slug=article_slug,
                summary=normalized_summary,
                body_markdown=extracted.body_markdown,
                category=category,
                status=Article.Status.PUBLISHED,
                published_at=timezone.now(),
                reading_minutes=_reading_minutes(extracted.body_markdown),
                is_demo=False,
                seo_title=normalized_title,
                seo_description=normalized_summary[:240],
            )
            source = ArticleSourceFile(
                article=article,
                original_filename=extracted.original_filename,
                source_format=extracted.source_format,
                content_type=extracted.content_type,
                size_bytes=extracted.size_bytes,
                sha256=extracted.sha256,
                outline=extracted.outline,
            )
            source.file.save(
                extracted.original_filename,
                ContentFile(_read_uploaded_file(uploaded_file, allow_rewind=True)),
                save=False,
            )
            saved_name = source.file.name
            source.save()
    except Exception:
        if saved_name:
            ArticleSourceFile._meta.get_field("file").storage.delete(saved_name)
        raise
    return article


def extract_uploaded_note(uploaded_file: BinaryIO) -> ExtractedNote:
    content = _read_uploaded_file(uploaded_file)
    original_filename = _safe_filename(getattr(uploaded_file, "name", ""))
    extension = Path(original_filename).suffix.lower()
    source_format = FORMAT_BY_EXTENSION.get(extension)
    if source_format is None:
        raise NoteImportError("仅支持 .md、.markdown、.docx 和 .pdf 文件。")

    content_type = str(getattr(uploaded_file, "content_type", "") or "")
    content_type = content_type.split(";", maxsplit=1)[0].strip().lower()[:120]
    if content_type not in ALLOWED_CONTENT_TYPES[source_format]:
        raise NoteImportError("文件扩展名与浏览器声明的内容类型不匹配。")

    if source_format == ArticleSourceFile.SourceFormat.MARKDOWN:
        body = _extract_markdown(content)
    elif source_format == ArticleSourceFile.SourceFormat.DOCX:
        body = _extract_docx(content)
    else:
        body = _extract_pdf(content)

    body = body.strip()
    if not body:
        raise NoteImportError("文件中没有可用于展示的文字内容。")
    if len(body) > MAX_EXTRACTED_CHARACTERS:
        raise NoteImportError("文件提取后的正文过长，已拒绝导入。")

    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass
    return ExtractedNote(
        body_markdown=body,
        outline=extract_outline(body),
        source_format=source_format,
        original_filename=original_filename,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def extract_outline(markdown: str) -> list[dict[str, object]]:
    outline: list[dict[str, object]] = []
    used: dict[str, int] = {}
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", stripped)
        if not match:
            continue
        text = _plain_markdown(match.group(2))[:200]
        if not text:
            continue
        base = _heading_id(text) or f"section-{len(outline) + 1}"
        used[base] = used.get(base, 0) + 1
        anchor = base if used[base] == 1 else f"{base}-{used[base]}"
        outline.append({"id": anchor, "text": text, "level": len(match.group(1))})
        if len(outline) >= 200:
            break
    return outline


def _read_uploaded_file(uploaded_file: BinaryIO, *, allow_rewind: bool = False) -> bytes:
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        if allow_rewind:
            raise NoteImportError("无法重新读取上传文件，请重新选择文件。") from None

    maximum = settings.NOTE_UPLOAD_MAX_BYTES
    content = bytearray()
    chunks = getattr(uploaded_file, "chunks", None)
    iterator = chunks() if callable(chunks) else iter(lambda: uploaded_file.read(64 * 1024), b"")
    for chunk in iterator:
        content.extend(chunk)
        if len(content) > maximum:
            raise NoteImportError(f"文件不能超过 {maximum // (1024 * 1024)} MB。")
    if not content:
        raise NoteImportError("上传文件不能为空。")
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass
    return bytes(content)


def _extract_markdown(content: bytes) -> str:
    if content.startswith(b"PK") or b"%PDF-" in content[:1024]:
        raise NoteImportError("Markdown 文件内容与扩展名不匹配。")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise NoteImportError("Markdown 文件必须使用 UTF-8 编码。") from exc
    if "\x00" in text:
        raise NoteImportError("Markdown 文件包含无效的二进制内容。")
    return text


def _validate_docx_archive(content: bytes) -> None:
    if not content.startswith(b"PK"):
        raise NoteImportError("DOCX 文件结构无效。")
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCX_MEMBERS:
                raise NoteImportError("DOCX 内部文件数量异常。")
            names = {member.filename for member in members}
            required = {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(names):
                raise NoteImportError("DOCX 缺少必要的 Word 文档结构。")

            expanded = 0
            for member in members:
                name = member.filename
                path = PurePosixPath(name)
                file_mode = (member.external_attr >> 16) & 0o170000
                if (
                    not name
                    or "\\" in name
                    or path.is_absolute()
                    or ".." in path.parts
                    or member.flag_bits & 0x1
                    or file_mode == stat.S_IFLNK
                ):
                    raise NoteImportError("DOCX 包含不安全的内部路径或加密内容。")
                lowered = name.casefold()
                if lowered.endswith("vbaproject.bin") or lowered.startswith("word/embeddings/"):
                    raise NoteImportError("暂不支持带宏或嵌入对象的 Word 文件。")
                if member.file_size > MAX_DOCX_MEMBER_BYTES:
                    raise NoteImportError("DOCX 内部单个文件过大。")
                expanded += member.file_size
                if expanded > MAX_DOCX_EXPANDED_BYTES:
                    raise NoteImportError("DOCX 解压后体积异常。")
                if member.file_size and not member.compress_size:
                    raise NoteImportError("DOCX 压缩结构异常。")
                if (
                    member.compress_size
                    and (member.file_size / member.compress_size) > MAX_DOCX_COMPRESSION_RATIO
                ):
                    raise NoteImportError("DOCX 压缩比异常。")
                if lowered.endswith(".xml"):
                    xml_prefix = archive.read(member)[:4096].upper()
                    if b"<!DOCTYPE" in xml_prefix or b"<!ENTITY" in xml_prefix:
                        raise NoteImportError("DOCX 包含不安全的 XML 声明。")
    except (BadZipFile, OSError) as exc:
        raise NoteImportError("DOCX 文件损坏或结构无效。") from exc


def _extract_docx(content: bytes) -> str:
    _validate_docx_archive(content)
    try:
        document = Document(BytesIO(content))
    except (ValueError, KeyError, OSError) as exc:
        raise NoteImportError("无法读取该 DOCX 文件。") from exc

    blocks: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style_name = str(block.style.name if block.style else "")
            heading = re.match(r"^(?:Heading|标题)\s*([1-6])$", style_name, re.I)
            if heading:
                blocks.append(f"{'#' * int(heading.group(1))} {text}")
            elif "List Bullet" in style_name:
                blocks.append(f"- {text}")
            elif "List Number" in style_name:
                blocks.append(f"1. {text}")
            else:
                blocks.append(text)
        elif isinstance(block, Table):
            rows = [[_escape_table_cell(cell.text) for cell in row.cells] for row in block.rows]
            if not rows or not rows[0]:
                continue
            width = max(len(row) for row in rows)
            normalized = [row + [""] * (width - len(row)) for row in rows]
            blocks.append("| " + " | ".join(normalized[0]) + " |")
            blocks.append("| " + " | ".join(["---"] * width) + " |")
            blocks.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return "\n\n".join(blocks)


def _extract_pdf(content: bytes) -> str:
    if b"%PDF-" not in content[:1024]:
        raise NoteImportError("PDF 文件内容与扩展名不匹配。")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise NoteImportError("暂不支持加密 PDF。")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise NoteImportError(f"PDF 最多支持 {MAX_PDF_PAGES} 页。")
        pages: list[str] = []
        total_characters = 0
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            total_characters += len(text)
            if total_characters > MAX_EXTRACTED_CHARACTERS:
                raise NoteImportError("PDF 提取后的文字过长。")
            pages.append(text)
    except NoteImportError:
        raise
    except (PdfReadError, ValueError, TypeError, KeyError) as exc:
        raise NoteImportError("PDF 文件损坏或无法安全解析。") from exc
    if not pages:
        raise NoteImportError("PDF 中没有可提取文字，暂不支持扫描件 OCR。")
    return "\n\n---\n\n".join(pages)


def _safe_filename(value: object) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", "", str(value or ""))
    filename = text.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    filename = filename[:240]
    if not filename or filename in {".", ".."}:
        raise NoteImportError("文件名无效。")
    return filename


def _clean_text(value: object, maximum: int) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()[:maximum]


def _plain_markdown(value: str) -> str:
    text = re.sub(r"!\[([^]]*)]\([^)]*\)", r"\1", value)
    text = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    return " ".join(text.split())


def _heading_id(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-_")[:120]


def _derive_summary(markdown: str) -> str:
    lines = []
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith(("#", "|", "---")):
            continue
        lines.append(_plain_markdown(stripped.lstrip("-*+>0123456789. ")))
        if len(" ".join(lines)) >= 240:
            break
    summary = " ".join(part for part in lines if part).strip()
    return (summary or "由本地文件导入的技术笔记。")[:500]


def _build_slug(title: str, sha256: str) -> str:
    base = slugify(title)[:180] or "note"
    return f"{base}-{sha256[:10]}"[:220]


def _reading_minutes(markdown: str) -> int:
    text = _plain_markdown(markdown)
    return max(1, min(120, math.ceil(len(text) / 500)))


def _escape_table_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
