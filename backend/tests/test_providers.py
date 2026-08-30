import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

import httpx
import pytest

from apps.radar.models import RadarItem
from apps.radar.providers.arxiv import ArxivProvider
from apps.radar.providers.base import ProviderResponseError
from apps.radar.providers.deepseek import DeepSeekProvider
from apps.radar.providers.github import GitHubProvider
from apps.radar.providers.huggingface import HuggingFaceProvider


def test_arxiv_provider_maps_atom_feed_and_removes_version_suffix(settings):
    settings.ARXIV_SEARCH_QUERY = ""
    settings.AI_RADAR_KEYWORDS = ["KV Cache", "LLM serving"]
    settings.EXTERNAL_HTTP_USER_AGENT = "SS-LAB-Radar-Test/1.0"
    atom = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <updated>2026-08-29T00:00:00Z</updated>
      <entry>
        <id>http://arxiv.org/abs/2608.12345v2</id>
        <updated>2026-08-29T01:00:00Z</updated>
        <published>2026-08-28T01:00:00Z</published>
        <title>  Faster KV Cache\n  Management </title>
        <summary> A bounded cache strategy for LLM serving. </summary>
        <author><name>Example Researcher</name></author>
        <arxiv:primary_category term="cs.LG" />
        <category term="cs.LG" />
        <category term="cs.DC" />
      </entry>
    </feed>"""

    def handler(request):
        assert request.headers["User-Agent"] == "SS-LAB-Radar-Test/1.0"
        assert request.url.params["search_query"] == (
            '(all:"KV Cache" OR all:"LLM serving")'
        )
        assert request.url.params["sortBy"] == "submittedDate"
        assert request.url.params["max_results"] == "20"
        return httpx.Response(200, text=atom)

    with httpx.Client(
        base_url="https://export.arxiv.org", transport=httpx.MockTransport(handler)
    ) as client:
        batch = ArxivProvider(client=client).fetch(limit=100)

    assert len(batch.records) == 1
    record = batch.records[0]
    assert record.external_id == "2608.12345"
    assert record.original_url == "https://arxiv.org/abs/2608.12345"
    assert record.title == "Faster KV Cache Management"
    assert record.authors == ["Example Researcher"]
    assert record.metadata["primary_category"] == "cs.LG"


def configure_github(settings, *, token=""):
    settings.GITHUB_TOKEN = token
    settings.GITHUB_API_VERSION = "2026-03-10"
    settings.GITHUB_DISCOVERY_QUERY = "llm"
    settings.GITHUB_DISCOVERY_LOOKBACK_DAYS = 30
    settings.GITHUB_DISCOVERY_MIN_STARS = 10
    settings.GITHUB_DISCOVERY_SORT = "stars"


def github_repository(repository_id=42):
    return {
        "id": repository_id,
        "name": "inference-lab",
        "full_name": "community/inference-lab",
        "description": "LLM serving and KV Cache experiments",
        "html_url": "https://github.com/community/inference-lab",
        "homepage": "https://example.com/demo",
        "private": False,
        "fork": False,
        "archived": False,
        "created_at": "2026-08-01T00:00:00Z",
        "updated_at": "2026-08-28T00:00:00Z",
        "pushed_at": "2026-08-29T00:00:00Z",
        "owner": {"login": "community"},
        "topics": ["llm-serving", "kv-cache"],
        "language": "Python",
        "stargazers_count": 120,
        "forks_count": 30,
        "open_issues_count": 4,
        "license": {"spdx_id": "MIT"},
        "default_branch": "main",
    }


def test_github_provider_discovers_recent_starred_public_repository(settings):
    configure_github(settings)

    def handler(request):
        assert request.url.path == "/search/repositories"
        assert request.headers.get("Authorization") is None
        assert request.url.params["q"] == (
            "llm in:name,description,topics stars:>=10 "
            "pushed:>=2026-07-30 archived:false is:public"
        )
        assert request.url.params["sort"] == "stars"
        assert request.url.params["order"] == "desc"
        assert request.url.params["per_page"] == "20"
        return httpx.Response(
            200,
            headers={
                "ETag": '"search-etag"',
                "X-RateLimit-Remaining": "9",
                "X-RateLimit-Resource": "search",
            },
            json={
                "total_count": 123,
                "incomplete_results": False,
                "items": [github_repository()],
            },
        )

    with httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        batch = GitHubProvider(client=client, today=date(2026, 8, 29)).fetch(limit=20)

    assert batch.sync_state["etag"] == '"search-etag"'
    assert batch.sync_state["mode"] == "discovery"
    assert batch.sync_state["snapshot_complete"] is False
    assert batch.sync_state["total_count"] == 123
    assert len(batch.records) == 1
    record = batch.records[0]
    assert record.external_id == "42"
    assert record.kind == RadarItem.Kind.REPOSITORY
    assert record.authors == ["community"]
    assert record.metadata["stars"] == 120
    assert record.metadata["discovery_mode"] == "public_search_v1"
    assert record.project is None


def test_github_provider_honors_matching_search_etag(settings):
    configure_github(settings, token="secret-token")
    search_query = (
        "llm in:name,description,topics stars:>=10 "
        "pushed:>=2026-07-30 archived:false is:public"
    )

    def handler(request):
        assert request.headers["Authorization"] == "Bearer secret-token"
        assert request.headers["If-None-Match"] == '"old-etag"'
        return httpx.Response(304, headers={"ETag": '"old-etag"'})

    with httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        batch = GitHubProvider(
            client=client,
            today=date(2026, 8, 29),
            sync_state={
                "mode": "discovery",
                "query": search_query,
                "limit": 10,
                "sort": "stars",
                "etag": '"old-etag"',
            },
        ).fetch(limit=10)

    assert batch.not_modified is True
    assert batch.records == []


def test_github_provider_ignores_stale_etag_and_deduplicates_results(settings):
    configure_github(settings)

    def handler(request):
        assert "If-None-Match" not in request.headers
        fork = {**github_repository(99), "fork": True}
        return httpx.Response(
            200,
            json={
                "total_count": 3,
                "incomplete_results": True,
                "items": [github_repository(), github_repository(), fork],
            },
        )

    with httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        batch = GitHubProvider(
            client=client,
            today=date(2026, 8, 29),
            sync_state={
                "mode": "discovery",
                "query": "an older query",
                "limit": 10,
                "sort": "stars",
                "etag": '"stale-etag"',
            },
        ).fetch(limit=10)

    assert [record.external_id for record in batch.records] == ["42"]
    assert batch.sync_state["incomplete_results"] is True
    assert batch.sync_state["snapshot_complete"] is False


def test_github_provider_rejects_invalid_search_response(settings):
    configure_github(settings)

    def handler(_request):
        return httpx.Response(200, json=[])

    with httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ProviderResponseError, match="unexpected response shape"):
            GitHubProvider(client=client, today=date(2026, 8, 29)).fetch(limit=10)


class FakeHuggingFaceApi:
    def list_models(self, **kwargs):
        assert kwargs["token"] is False
        return [
            SimpleNamespace(
                id="example/serving-model",
                author="example",
                private=False,
                created_at=datetime(2026, 8, 1, tzinfo=UTC),
                last_modified=datetime(2026, 8, 29, tzinfo=UTC),
                tags=["vllm", "quantization"],
                downloads=1200,
                likes=18,
                gated=False,
                sha="abc123",
                pipeline_tag="text-generation",
                library_name="transformers",
            )
        ]

    def list_datasets(self, **kwargs):
        assert kwargs["token"] is False
        return [
            SimpleNamespace(
                id="example/inference-benchmark",
                author="example",
                private=False,
                created_at=datetime(2026, 8, 2, tzinfo=UTC),
                last_modified=datetime(2026, 8, 28, tzinfo=UTC),
                tags=["llm-serving"],
                downloads=300,
                likes=5,
                gated=False,
                sha="def456",
                description="Inference serving benchmark dataset.",
            )
        ]


def test_huggingface_provider_reads_models_and_datasets(settings):
    settings.HUGGINGFACE_AUTHOR = ""
    settings.HUGGINGFACE_SEARCH = "llm inference"
    settings.HUGGINGFACE_TOKEN = ""
    settings.HUGGINGFACE_INCLUDE_DATASETS = True

    batch = HuggingFaceProvider(api=FakeHuggingFaceApi()).fetch(limit=4)

    assert [record.kind for record in batch.records] == [
        RadarItem.Kind.MODEL,
        RadarItem.Kind.DATASET,
    ]
    assert batch.records[0].external_id == "model:example/serving-model"
    assert batch.records[1].external_id == "dataset:example/inference-benchmark"


def test_deepseek_provider_requires_search_and_validates_source(settings):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = "deepseek-v4-flash"
    settings.LLM_LOOKBACK_DAYS = 7
    settings.LLM_REASONING_EFFORT = "low"
    settings.LLM_VERIFY_SOURCE_URLS = True
    settings.AI_RADAR_KEYWORDS = ["LLM serving"]
    settings.AI_RADAR_ALLOWED_DOMAINS = ["arxiv.org"]

    structured = {
        "items": [
            {
                "title": "Verified inference research",
                "source_url": "https://arxiv.org/abs/2608.12345",
                "kind": "paper",
                "published_at": "2026-08-28T00:00:00Z",
                "summary": "A new serving method.",
                "authors": ["Researcher"],
                "topics": ["LLM serving"],
                "why_it_matters": "Improves serving efficiency.",
                "evidence": "The primary arXiv page reports the method.",
                "confidence": "high",
            }
        ]
    }

    def handler(request):
        if request.url.host == "api.deepseek.com":
            request_json = json.loads(request.content)
            assert request_json["tool_choice"] == {"type": "web_search"}
            assert request_json["text"]["format"]["type"] == "json_schema"
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {"type": "web_search_call", "status": "completed"},
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": json.dumps(structured)}
                            ],
                        },
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300},
                },
            )
        assert request.method == "HEAD"
        assert request.url.host == "arxiv.org"
        return httpx.Response(200)

    with httpx.Client(
        base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
    ) as client:
        batch = DeepSeekProvider(client=client).fetch(limit=3)

    assert len(batch.records) == 1
    assert batch.records[0].kind == RadarItem.Kind.PAPER
    assert batch.records[0].ai_summary["研究价值"] == "Improves serving efficiency."
    assert batch.sync_state["usage"]["total_tokens"] == 300


def test_deepseek_provider_rejects_response_without_web_search(settings):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = ""
    settings.LLM_LOOKBACK_DAYS = 7
    settings.LLM_REASONING_EFFORT = "low"
    settings.LLM_VERIFY_SOURCE_URLS = False
    settings.AI_RADAR_KEYWORDS = ["LLM serving"]
    settings.AI_RADAR_ALLOWED_DOMAINS = ["arxiv.org"]

    def handler(_request):
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"items": []}'}],
                    }
                ],
            },
        )

    with httpx.Client(
        base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ProviderResponseError, match="required web search"):
            DeepSeekProvider(client=client).fetch(limit=3)


def test_deepseek_provider_rejects_non_ascii_api_key(settings):
    settings.LLM_API_KEY = "请替换为真实密钥"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.AI_RADAR_KEYWORDS = ["LLM serving"]
    settings.AI_RADAR_ALLOWED_DOMAINS = ["arxiv.org"]

    assert DeepSeekProvider().configuration_error() == (
        "LLM_API_KEY must contain only ASCII characters."
    )


def test_deepseek_provider_does_not_retry_metered_request(settings):
    settings.LLM_API_KEY = "test-key"
    settings.LLM_BASE_URL = "https://api.deepseek.com"
    settings.LLM_MODEL = "deepseek-v4-pro"
    settings.LLM_FALLBACK_MODEL = ""
    settings.LLM_LOOKBACK_DAYS = 7
    settings.LLM_REASONING_EFFORT = "low"
    settings.LLM_VERIFY_SOURCE_URLS = False
    settings.AI_RADAR_KEYWORDS = ["LLM serving"]
    settings.AI_RADAR_ALLOWED_DOMAINS = ["arxiv.org"]
    request_count = 0

    def handler(_request):
        nonlocal request_count
        request_count += 1
        return httpx.Response(503)

    with httpx.Client(
        base_url="https://api.deepseek.com", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ProviderResponseError, match="HTTP 503"):
            DeepSeekProvider(client=client).fetch(limit=3)

    assert request_count == 1
