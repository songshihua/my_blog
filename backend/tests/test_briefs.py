import json

import httpx
import pytest
from django.core.cache import cache

from apps.radar.briefs import RadarBriefGenerator


@pytest.mark.django_db
def test_brief_generator_uses_only_supplied_radar_items(settings, radar_item):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = ""
    settings.LLM_REASONING_EFFORT = "low"
    settings.EXTERNAL_HTTP_TIMEOUT_SECONDS = 30
    settings.RADAR_BRIEF_ITEM_LIMIT = 20
    settings.RADAR_BRIEF_CACHE_SECONDS = 900
    cache.clear()

    structured = {
        "title": "今日推理研究简报",
        "overview": "今天的资料聚焦推理效率。",
        "highlights": [{"item_id": radar_item.id, "insight": "该工作值得跟进。"}],
        "trends": ["推理效率仍是重点。"],
        "watchlist": ["关注后续公开实验。"],
    }

    def handler(request):
        request_json = json.loads(request.content)
        assert "tools" not in request_json
        assert request_json["text"]["format"]["type"] == "json_schema"
        assert f'"id": {radar_item.id}' in request_json["input"]
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(structured)}],
                    }
                ],
            },
        )

    with httpx.Client(
        base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
    ) as client:
        result = RadarBriefGenerator(client=client).generate()

    assert result["title"] == "今日推理研究简报"
    assert result["highlights"] == [
        {
            "item_id": radar_item.id,
            "title": radar_item.title,
            "url": radar_item.original_url,
            "insight": "该工作值得跟进。",
        }
    ]
    assert result["source_count"] == 1
    assert result["cached"] is False


@pytest.mark.django_db
def test_brief_generator_reuses_cached_result(settings, radar_item):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = ""
    settings.LLM_REASONING_EFFORT = "low"
    settings.EXTERNAL_HTTP_TIMEOUT_SECONDS = 30
    settings.RADAR_BRIEF_ITEM_LIMIT = 20
    settings.RADAR_BRIEF_CACHE_SECONDS = 900
    cache.clear()
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "title": "简报",
                                        "overview": "概览",
                                        "highlights": [
                                            {"item_id": radar_item.id, "insight": "重点"}
                                        ],
                                        "trends": [],
                                        "watchlist": [],
                                    }
                                ),
                            }
                        ],
                    }
                ],
            },
        )

    with httpx.Client(
        base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
    ) as client:
        generator = RadarBriefGenerator(client=client)
        first = generator.generate()
        second = generator.generate()

    assert calls == 1
    assert first["cached"] is False
    assert second["cached"] is True
