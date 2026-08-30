"""Private filesystem storage for original note documents."""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class NoteSourceStorage(FileSystemStorage):
    """Store note sources outside MEDIA_ROOT so Nginx cannot expose them."""

    def __init__(self) -> None:
        super().__init__(location=None, base_url=None)

    @property
    def base_location(self) -> str:
        return str(settings.NOTE_UPLOAD_ROOT)

    @property
    def location(self) -> str:
        return os.path.abspath(self.base_location)

    @property
    def base_url(self) -> None:
        return None


note_source_storage = NoteSourceStorage()
