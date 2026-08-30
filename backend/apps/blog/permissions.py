"""Fail-closed permissions for the local-only browser authoring flow."""

from django.conf import settings
from rest_framework.permissions import BasePermission


class CanUseLocalNoteImport(BasePermission):
    message = "前端笔记管理仅在受信任的本地开发环境中开放。"

    def has_permission(self, request, _view) -> bool:
        if not settings.DEBUG or not settings.NOTE_BROWSER_IMPORT_ENABLED:
            return False
        if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
            return False
        return request.headers.get("Origin", "") in set(settings.CORS_ALLOWED_ORIGINS)
