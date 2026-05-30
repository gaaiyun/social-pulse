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
    keyword_sentiment, platform_breakdown, posting_time_analysis,
    sentiment_trend, summarize_sentiment, top_negative_comments,
    viral_features,
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


# --- 发布时段分析 -----------------------------------------------------------

@pytest.fixture
def timed_content_df() -> pd.DataFrame:
    rng = np.random.RandomState(7)
    n = 60
    # 发布时间横跨多天多个小时
    times = pd.date_range("2024-03-01 00:00", periods=n, freq="3h")
    return pd.DataFrame({
        "content_id": range(1, n + 1),
        "title": [f"标题{i}" * (1 + i % 3) for i in range(n)],
        "platform": rng.choice(["微博", "小红书"], n),
        "content_type": rng.choice(["图文", "视频"], n),
        "reads": rng.randint(1000, 50000, n),
        "likes": rng.randint(50, 5000, n),
        "comments": rng.randint(10, 500, n),
        "shares": rng.randint(5, 200, n),
        "publish_time": times,
        "keywords": rng.choice(["科技,AI", "生活,日常", "旅行,风景"], n),
    })


def test_posting_time_returns_best_hour_and_dow(timed_content_df):
    out = posting_time_analysis(timed_content_df)
    assert 0 <= out["best_hour"] <= 23
    assert 0 <= out["best_dayofweek"] <= 6
    assert len(out["by_hour"]) > 0


def test_posting_time_missing_column_returns_empty():
    df = pd.DataFrame({"reads": [1, 2], "likes": [1, 2]})
    assert posting_time_analysis(df) == {}


def test_posting_time_serializable(timed_content_df):
    import json
    json.dumps(posting_time_analysis(timed_content_df), ensure_ascii=False)


# --- 爆款特征 ---------------------------------------------------------------

def test_viral_features_counts_split(timed_content_df):
    out = viral_features(timed_content_df, top_percent=0.2)
    assert out["n_viral"] >= 1
    assert out["n_viral"] + out["n_normal"] == len(timed_content_df)


def test_viral_features_has_title_length(timed_content_df):
    out = viral_features(timed_content_df)
    assert out["viral_title_avg_length"] is not None
    assert out["viral_title_avg_length"] > 0


def test_viral_features_keywords_are_list(timed_content_df):
    out = viral_features(timed_content_df)
    assert isinstance(out["viral_top_keywords"], list)


def test_viral_features_too_few_rows_returns_empty():
    df = pd.DataFrame({"reads": [100, 200], "likes": [1, 2]})
    assert viral_features(df) == {}


def test_viral_features_serializable(timed_content_df):
    import json
    json.dumps(viral_features(timed_content_df), ensure_ascii=False)


# --- 情感日趋势 -------------------------------------------------------------

@pytest.fixture
def scored_comments_df() -> pd.DataFrame:
    return pd.DataFrame({
        "comment": ["很好", "一般", "太差了", "喜欢", "失望", "推荐"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-02",
                 "2024-01-02", "2024-01-03", "2024-01-03"],
        "sentiment_score": [0.9, 0.5, 0.1, 0.8, 0.2, 0.7],
    })


def test_sentiment_trend_groups_by_day(scored_comments_df):
    out = sentiment_trend(scored_comments_df)
    assert len(out) == 3            # 三天
    assert out[0]["date"] == "2024-01-01"
    assert out[0]["n_comments"] == 2


def test_sentiment_trend_sorted_ascending(scored_comments_df):
    out = sentiment_trend(scored_comments_df)
    dates = [r["date"] for r in out]
    assert dates == sorted(dates)


def test_sentiment_trend_missing_col_raises():
    df = pd.DataFrame({"sentiment_score": [0.5]})
    with pytest.raises(ValueError, match="date"):
        sentiment_trend(df)


def test_sentiment_trend_empty_raises():
    with pytest.raises(ValueError, match="为空"):
        sentiment_trend(pd.DataFrame())


# --- 关键词情感 -------------------------------------------------------------

def test_keyword_sentiment_finds_hits(scored_comments_df):
    out = keyword_sentiment(scored_comments_df, ["太差", "喜欢"])
    assert "太差" in out
    assert out["太差"]["n_comments"] == 1
    assert out["太差"]["mean_score"] < 0.4


def test_keyword_sentiment_skips_no_hits(scored_comments_df):
    out = keyword_sentiment(scored_comments_df, ["不存在的词"])
    assert out == {}


def test_keyword_sentiment_missing_col_raises():
    df = pd.DataFrame({"comment": ["x"]})
    with pytest.raises(ValueError, match="sentiment_score"):
        keyword_sentiment(df, ["x"])


# --- 负面评论提取 -----------------------------------------------------------

def test_top_negative_returns_worst_first(scored_comments_df):
    out = top_negative_comments(scored_comments_df, neg_threshold=0.4)
    assert len(out) == 2            # 0.1, 0.2
    assert out[0]["score"] <= out[1]["score"]
    assert out[0]["score"] == pytest.approx(0.1)


def test_top_negative_respects_top_n(scored_comments_df):
    out = top_negative_comments(scored_comments_df, neg_threshold=1.0, top_n=3)
    assert len(out) == 3


def test_top_negative_serializable(scored_comments_df):
    import json
    json.dumps(top_negative_comments(scored_comments_df), ensure_ascii=False)


def test_top_negative_missing_col_raises():
    df = pd.DataFrame({"comment": ["x"]})
    with pytest.raises(ValueError, match="sentiment_score"):
        top_negative_comments(df)
