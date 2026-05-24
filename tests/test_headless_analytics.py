"""headless_analytics.py 测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from headless_analytics import (
    ContentMetrics, FanGrowthMetrics, SentimentSummary,
    compute_content_metrics, compute_fan_growth,
    content_type_breakdown, demographic_breakdown,
    platform_breakdown, summarize_sentiment,
)


# --- 内容表现 ---------------------------------------------------------------

@pytest.fixture
def content_df() -> pd.DataFrame:
    rng = np.random.RandomState(0)
    n = 50
    return pd.DataFrame({
        "content_id": range(1, n + 1),
        "title": [f"内容 {i}" for i in range(n)],
        "platform": rng.choice(["微博", "微信", "小红书", "抖音"], n),
        "content_type": rng.choice(["图文", "视频", "直播"], n),
        "reads": rng.randint(1000, 100000, n),
        "likes": rng.randint(50, 5000, n),
        "comments": rng.randint(10, 500, n),
        "shares": rng.randint(5, 200, n),
    })


def test_content_metrics_returns_object(content_df):
    m = compute_content_metrics(content_df)
    assert isinstance(m, ContentMetrics)
    assert m.n_posts == 50


def test_content_total_reads_matches(content_df):
    m = compute_content_metrics(content_df)
    assert m.total_reads == int(content_df["reads"].sum())


def test_content_engagement_sum_correct(content_df):
    m = compute_content_metrics(content_df)
    expected = int((content_df["likes"] + content_df["comments"]
                    + content_df["shares"]).sum())
    assert m.total_engagement == expected


def test_content_top_post_has_max_engagement(content_df):
    m = compute_content_metrics(content_df)
    assert m.top_post is not None
    df = content_df.copy()
    df["_eng"] = df["likes"] + df["comments"] + df["shares"]
    expected_max = int(df["_eng"].max())
    assert m.top_post["engagement"] == expected_max


def test_content_n_viral_around_20_percent(content_df):
    m = compute_content_metrics(content_df)
    # top 20% → 约 10 篇
    assert 5 <= m.n_viral <= 15


def test_content_empty_df_raises():
    with pytest.raises(ValueError, match="为空"):
        compute_content_metrics(pd.DataFrame())


def test_content_missing_reads_raises():
    df = pd.DataFrame({"likes": [1, 2, 3]})
    with pytest.raises(ValueError, match="reads"):
        compute_content_metrics(df)


def test_content_to_dict_serializable(content_df):
    import json
    m = compute_content_metrics(content_df)
    json.dumps(m.to_dict(), ensure_ascii=False)


def test_platform_breakdown_keys_match_platforms(content_df):
    out = platform_breakdown(content_df)
    assert set(out.keys()) <= set(content_df["platform"].unique())


def test_platform_breakdown_n_posts_sum_matches(content_df):
    out = platform_breakdown(content_df)
    assert sum(v["n_posts"] for v in out.values()) == len(content_df)


def test_platform_breakdown_missing_column_returns_empty():
    df = pd.DataFrame({"reads": [100, 200], "likes": [1, 2]})
    assert platform_breakdown(df) == {}


def test_content_type_breakdown(content_df):
    out = content_type_breakdown(content_df)
    assert set(out.keys()) <= set(content_df["content_type"].unique())


# --- 粉丝增长 ---------------------------------------------------------------

@pytest.fixture
def fan_df() -> pd.DataFrame:
    rng = np.random.RandomState(1)
    n = 30
    dates = pd.date_range("2024-01-01", periods=n)
    new = rng.randint(100, 500, n)
    unf = rng.randint(20, 100, n)
    total = (10000 + (new - unf).cumsum()).tolist()
    return pd.DataFrame({
        "date": dates,
        "new_fans": new,
        "unfollows": unf,
        "total_fans": total,
        "interactions": rng.randint(500, 3000, n),
        "gender": rng.choice(["男", "女", "未知"], n),
        "age": rng.randint(15, 60, n),
        "city": rng.choice(["北京", "上海", "广州", "深圳", "杭州"], n),
    })


def test_fan_growth_returns_object(fan_df):
    g = compute_fan_growth(fan_df)
    assert isinstance(g, FanGrowthMetrics)
    assert g.n_days == 30


def test_fan_net_growth_correct(fan_df):
    g = compute_fan_growth(fan_df)
    expected = int(fan_df["new_fans"].sum() - fan_df["unfollows"].sum())
    assert g.net_growth == expected


def test_fan_starting_ending_match(fan_df):
    g = compute_fan_growth(fan_df)
    assert g.starting_fans == int(fan_df["total_fans"].iloc[0])
    assert g.ending_fans == int(fan_df["total_fans"].iloc[-1])


def test_fan_growth_pct_positive_when_growing(fan_df):
    g = compute_fan_growth(fan_df)
    # 新增大于流失 → growth_pct > 0
    if g.net_growth > 0:
        assert g.growth_pct > 0


def test_fan_growth_empty_df_raises():
    with pytest.raises(ValueError, match="为空"):
        compute_fan_growth(pd.DataFrame())


def test_fan_growth_missing_required_raises():
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3)})
    with pytest.raises(ValueError, match="缺必要列"):
        compute_fan_growth(df)


def test_demographic_breakdown_returns_dict(fan_df):
    out = demographic_breakdown(fan_df)
    assert "gender" in out
    assert "age_distribution" in out
    assert "top_cities" in out


def test_demographic_age_buckets_are_valid_labels(fan_df):
    out = demographic_breakdown(fan_df)
    expected_labels = {"<18", "18-24", "25-34", "35-44", "45+"}
    assert set(out["age_distribution"].keys()) <= expected_labels


def test_demographic_top_cities_max_10(fan_df):
    out = demographic_breakdown(fan_df)
    assert len(out["top_cities"]) <= 10


def test_demographic_missing_columns_returns_empty():
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5)})
    out = demographic_breakdown(df)
    assert out == {}


# --- 情感汇总 ---------------------------------------------------------------

def test_sentiment_summary_basic():
    df = pd.DataFrame({
        "sentiment_score": [0.9, 0.8, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1],
    })
    s = summarize_sentiment(df, pos_threshold=0.6, neg_threshold=0.4)
    assert s.n_comments == 8
    assert s.n_positive == 3   # 0.9, 0.8, 0.7
    # 0.5 是 neutral；0.4, 0.3, 0.2, 0.1 <= 0.4 是 negative
    assert s.n_negative == 4
    assert s.n_neutral == 1


def test_sentiment_summary_percentages_sum_correctly():
    df = pd.DataFrame({"sentiment_score": [0.9, 0.5, 0.2]})
    s = summarize_sentiment(df, pos_threshold=0.6, neg_threshold=0.4)
    # 33.3 + 33.3 + 33.3 = ~100
    total_pct = s.positive_pct + s.negative_pct + (
        s.n_neutral / s.n_comments * 100)
    assert abs(total_pct - 100.0) < 0.1


def test_sentiment_summary_empty_raises():
    with pytest.raises(ValueError, match="为空"):
        summarize_sentiment(pd.DataFrame())


def test_sentiment_summary_missing_score_col_raises():
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pytest.raises(ValueError, match="sentiment_score"):
        summarize_sentiment(df)


def test_sentiment_summary_to_dict_serializable():
    import json
    df = pd.DataFrame({"sentiment_score": [0.5, 0.7]})
    s = summarize_sentiment(df)
    json.dumps(s.to_dict(), ensure_ascii=False)
