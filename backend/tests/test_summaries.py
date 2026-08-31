import json

import httpx
import pytest

from apps.radar.summaries import RadarItemSummarizer


@pytest.mark.django_db
def test_item_summary_is_generated_and_persisted_once(settings, radar_item):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = ""
    settings.LLM_REASONING_EFFORT = "low"
    settings.EXTERNAL_HTTP_TIMEOUT_SECONDS = 30
    calls = 0
    structured = {
        "核心内容": "研究一种新的推理方法。",
        "关键贡献": "资料显示其提出了新的方法。",
        "研究价值": "可为后续推理优化研究提供参考。",
        "局限与关注": "当前资料没有提供完整实验数据。",
    }

    def handler(request):
        nonlocal calls
        calls += 1
        request_json = json.loads(request.content)
        assert "tools" not in request_json
        assert request_json["text"]["format"]["name"] == "radar_item_summary"
        assert radar_item.title in request_json["input"]
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
        first = RadarItemSummarizer(client=client).summarize(radar_item)

    radar_item.refresh_from_db()
    second = RadarItemSummarizer().summarize(radar_item)

    assert calls == 1
    assert radar_item.ai_summary == structured
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["ai_summary"] == structured


@pytest.mark.django_db
def test_existing_item_summary_does_not_require_api_configuration(settings, radar_item):
    settings.LLM_API_KEY = ""
    radar_item.ai_summary = {"核心内容": "已经持久化的总结"}
    radar_item.save(update_fields=("ai_summary", "updated_at"))

    result = RadarItemSummarizer().summarize(radar_item)

    assert result["cached"] is True
    assert result["ai_summary"] == {"核心内容": "已经持久化的总结"}
