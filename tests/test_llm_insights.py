"""llm_insights.py 测试。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_insights import (
    InsightReport, LLMClient, LLMNotAvailable,
    _heuristic_insights, _strip_fences, generate_insights,
)


def _content_metrics(**overrides) -> dict:
    base = {
        "n_posts": 50, "total_reads": 1_000_000,
        "total_engagement": 50_000,
        "avg_engagement_rate": 0.05,
        "top_platform": "微博", "top_platform_reads": 500_000,
        "top_post": {"title": "爆款帖子", "platform": "微博",
                     "reads": 100_000, "engagement": 5000},
        "n_viral": 10, "viral_threshold": 0.1,
    }
    base.update(overrides)
    return base


def _fan_metrics(**overrides) -> dict:
    base = {
        "period_start": "2024-01-01", "period_end": "2024-01-31",
        "n_days": 31, "total_new": 5000, "total_unfollows": 1500,
        "net_growth": 3500, "starting_fans": 10000, "ending_fans": 13500,
        "growth_pct": 35.0, "daily_net_avg": 112.9, "churn_rate": 15.0,
    }
    base.update(overrides)
    return base


# --- LLMClient -------------------------------------------------------------

def test_default_models():
    assert LLMClient(backend="openai", api_key="x").model == "gpt-4o-mini"
    assert LLMClient(backend="deepseek", api_key="x").model == "deepseek-chat"


def test_chat_raises_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = LLMClient(backend="deepseek")
    with pytest.raises(LLMNotAvailable):
        c.chat("s", "u")


# --- _strip_fences ---------------------------------------------------------

def test_strip_fences_json():
    assert _strip_fences('```json\n{}\n```') == '{}'


def test_strip_fences_no_block():
    assert _strip_fences('{}') == '{}'


# --- _heuristic_insights ---------------------------------------------------

def test_heuristic_overview_mentions_posts():
    report = _heuristic_insights(_content_metrics(), _fan_metrics(), None, {}, {})
    assert "50" in report.overview
    assert "1," in report.overview or "1000000" in report.overview


def test_heuristic_top_post_in_recommendations():
    report = _heuristic_insights(_content_metrics(), _fan_metrics(), None, {}, {})
    assert any("爆款帖子" in r for r in report.content_recommendations)


def test_heuristic_high_churn_in_risks():
    fan = _fan_metrics(churn_rate=15.0)
    report = _heuristic_insights(_content_metrics(), fan, None, {}, {})
    assert any("流失" in r for r in report.risks)


def test_heuristic_negative_growth_in_risks():
    fan = _fan_metrics(growth_pct=-5.0)
    report = _heuristic_insights(_content_metrics(), fan, None, {}, {})
    assert any("净增长为负" in r for r in report.risks)


def test_heuristic_negative_sentiment_in_risks():
    sentiment = {"positive_pct": 50, "negative_pct": 30}
    report = _heuristic_insights(_content_metrics(), _fan_metrics(),
                                 sentiment, {}, {})
    assert any("负向" in r for r in report.risks)


def test_heuristic_low_engagement_in_risks():
    metrics = _content_metrics(avg_engagement_rate=0.001)
    report = _heuristic_insights(metrics, _fan_metrics(), None, {}, {})
    assert any("互动率" in r for r in report.risks)


def test_heuristic_top_platform_in_platform_recs():
    report = _heuristic_insights(_content_metrics(), _fan_metrics(), None, {}, {})
    assert any("微博" in r for r in report.platform_recommendations)


def test_heuristic_picks_best_content_type():
    content_types = {
        "图文": {"n_posts": 10, "total_reads": 100, "total_engagement": 500},
        "视频": {"n_posts": 15, "total_reads": 200, "total_engagement": 5000},
    }
    report = _heuristic_insights(_content_metrics(), _fan_metrics(), None,
                                 {}, content_types)
    assert any("视频" in r for r in report.content_recommendations)


def test_heuristic_no_risks_returns_placeholder():
    """全部 OK 时 risks 应有占位说明。"""
    fan = _fan_metrics(churn_rate=2.0, growth_pct=20.0)
    metrics = _content_metrics(avg_engagement_rate=0.1)
    report = _heuristic_insights(metrics, fan, {"positive_pct": 70,
                                                 "negative_pct": 5},
                                 {}, {})
    assert len(report.risks) >= 1
    assert any("未发现" in r for r in report.risks)


def test_heuristic_to_markdown_includes_sections():
    report = _heuristic_insights(_content_metrics(), _fan_metrics(), None, {}, {})
    md = report.to_markdown()
    assert "## 整体概览" in md
    assert "## 内容运营建议" in md
    assert "## 平台运营建议" in md
    assert "## 风险关注" in md


# --- generate_insights ----------------------------------------------------

def test_generate_without_llm_uses_heuristic():
    report = generate_insights(content_metrics=_content_metrics())
    assert report.backend == "heuristic"


def test_generate_with_mocked_llm():
    client = LLMClient(backend="deepseek", api_key="sk-test")
    client.chat = MagicMock(return_value=
        '{"overview": "整体不错", "content_recommendations": ["a", "b"], '
        '"platform_recommendations": ["x"], "risks": []}'
    )
    report = generate_insights(content_metrics=_content_metrics(),
                               llm_client=client)
    assert report.overview == "整体不错"
    assert len(report.content_recommendations) == 2
    assert "llm" in report.backend


def test_generate_llm_fallback_on_bad_json():
    client = LLMClient(backend="deepseek", api_key="sk-test")
    client.chat = MagicMock(return_value="not json")
    report = generate_insights(content_metrics=_content_metrics(),
                               llm_client=client)
    assert report.backend == "heuristic"


def test_generate_filters_empty_list_items():
    client = LLMClient(backend="deepseek", api_key="sk-test")
    client.chat = MagicMock(return_value=
        '{"overview": "x", "content_recommendations": ["a", "", null], '
        '"platform_recommendations": [], "risks": ["r1"]}'
    )
    report = generate_insights(content_metrics=_content_metrics(),
                               llm_client=client)
    assert report.content_recommendations == ["a"]


def test_generate_to_dict_serializable():
    import json
    report = generate_insights(content_metrics=_content_metrics())
    json.dumps(report.to_dict(), ensure_ascii=False)


def test_insight_report_to_markdown_no_recs():
    """空 recs 时仍能渲染整体概览。"""
    report = InsightReport(
        overview="只有概览", content_recommendations=[],
        platform_recommendations=[], risks=[], backend="heuristic",
    )
    md = report.to_markdown()
    assert "## 整体概览" in md
    assert "只有概览" in md
