"""Provider registry and configuration-status helpers."""

from __future__ import annotations

from typing import Any

from apps.radar.models import RadarSource

from .arxiv import ArxivProvider
from .base import RemoteProvider
from .deepseek import DeepSeekProvider
from .github import GitHubProvider
from .huggingface import HuggingFaceProvider


def build_provider(source: RadarSource, **overrides: Any) -> RemoteProvider | None:
    if source.source_type == RadarSource.SourceType.ARXIV:
        return ArxivProvider(**overrides)
    if source.source_type == RadarSource.SourceType.GITHUB:
        return GitHubProvider(sync_state=source.sync_state, **overrides)
    if source.source_type == RadarSource.SourceType.HUGGINGFACE:
        return HuggingFaceProvider(**overrides)
    if source.source_type == RadarSource.SourceType.DEEPSEEK:
        return DeepSeekProvider(**overrides)
    return None


def provider_configuration_error(source_type: str) -> str | None:
    source = RadarSource(source_type=source_type)
    provider = build_provider(source)
    if provider is None:
        return "Provider adapter is not implemented."
    return provider.configuration_error()
