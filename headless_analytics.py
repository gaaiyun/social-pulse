"""无 Streamlit / plotly 依赖的社媒分析函数集合。

v1 的 ContentAnalyzer / FanAnalyzer / SentimentAnalyzer 都耦合 plotly 图表
渲染。v2 这一层只算指标、返回 dataclass / dict，让脚本和 cron 任务能用。

覆盖范围：
- 内容表现：互动率 / 阅读完成率代理 / 爆款识别
- 粉丝增长：新增 / 流失 / 净增 / 留存代理
- 情感统计：基于 v1 sentiment_analyzer 的 SnowNLP 结果汇总
- 趋势检测：按平台 / 内容类型分组的环比变化
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# 默认列名映射（v1 sample_data 的中文列）
DEFAULT_CONTENT_COLS = {
    "id": "content_id", "title": "title", "platform": "platform",
    "reads": "reads", "likes": "likes", "comments": "comments",
    "shares": "shares", "type": "content_type",
    "publish_time": "publish_time", "keywords": "keywords",
}

DEFAULT_FAN_COLS = {
    "date": "date", "new_fans": "new_fans", "unfollows": "unfollows",
    "total_fans": "total_fans", "interactions": "interactions",
    "gender": "gender", "age": "age", "city": "city",
}

DEFAULT_COMMENT_COLS = {
    "comment": "comment", "date": "date",
    "content_id": "content_id", "platform": "platform",
}


# --- 内容表现 ---------------------------------------------------------------

@dataclass
class ContentMetrics:
    n_posts: int
    total_reads: int
    total_engagement: int    # likes + comments + shares
    avg_engagement_rate: float    # 平均互动率
    top_post: Optional[Dict] = None
    top_platform: Optional[str] = None
    top_platform_reads: int = 0
    n_viral: int = 0         # 顶级帖子数（top 20% by engagement_rate）
    viral_threshold: float = 0.0

    def to_dict(self) -> dict:
        return {k: (v if not isinstance(v, (np.integer, np.floating))
                    else float(v)) for k, v in self.__dict__.items()}


def compute_content_metrics(df: pd.DataFrame,
                            column_map: Optional[Dict] = None) -> ContentMetrics:
    cols = dict(DEFAULT_CONTENT_COLS)
    if column_map:
        cols.update(column_map)
    if df is None or len(df) == 0:
        raise ValueError("DataFrame 为空")
    for required in [cols["reads"], cols["likes"]]:
        if required not in df.columns:
            raise ValueError(f"缺必要列 {required}")

    df = df.copy()
    df["_engagement"] = (df.get(cols["likes"], 0).fillna(0)
                         + df.get(cols["comments"], 0).fillna(0)
                         + df.get(cols["shares"], 0).fillna(0))
    df["_engagement_rate"] = df["_engagement"] / df[cols["reads"]].replace(0, np.nan)

    total_reads = int(df[cols["reads"]].sum())
    total_eng = int(df["_engagement"].sum())
    avg_rate = float(df["_engagement_rate"].mean(skipna=True))
    n_posts = int(len(df))

    # Top post by engagement
    top_post = None
    if n_posts > 0:
        top_idx = df["_engagement"].idxmax()
        top_row = df.loc[top_idx]
        top_post = {
            "id": int(top_row.get(cols["id"], top_idx)) if pd.notna(top_row.get(cols["id"])) else None,
            "title": str(top_row.get(cols["title"], "")),
            "platform": str(top_row.get(cols["platform"], "")),
            "reads": int(top_row[cols["reads"]]),
            "engagement": int(top_row["_engagement"]),
        }

    # Top platform by total reads
    top_platform = None
    top_platform_reads = 0
    if cols["platform"] in df.columns:
        plat_reads = df.groupby(cols["platform"])[cols["reads"]].sum()
        if len(plat_reads) > 0:
            top_platform = str(plat_reads.idxmax())
            top_platform_reads = int(plat_reads.max())

    # Viral threshold = top 20%
    if n_posts >= 5:
        viral_thresh = float(df["_engagement_rate"].quantile(0.8, interpolation="linear"))
        n_viral = int((df["_engagement_rate"] >= viral_thresh).sum())
    else:
        viral_thresh = 0.0
        n_viral = 0

    return ContentMetrics(
        n_posts=n_posts, total_reads=total_reads, total_engagement=total_eng,
        avg_engagement_rate=avg_rate, top_post=top_post,
        top_platform=top_platform, top_platform_reads=top_platform_reads,
        n_viral=n_viral, viral_threshold=viral_thresh,
    )


def platform_breakdown(df: pd.DataFrame,
                       column_map: Optional[Dict] = None) -> Dict[str, Dict]:
    """按平台拆分：每个平台的 reads / engagement_rate。"""
    cols = dict(DEFAULT_CONTENT_COLS)
    if column_map:
        cols.update(column_map)
    if cols["platform"] not in df.columns:
        return {}

    df = df.copy()
    df["_engagement"] = (df.get(cols["likes"], 0).fillna(0)
                         + df.get(cols["comments"], 0).fillna(0)
                         + df.get(cols["shares"], 0).fillna(0))
    df["_engagement_rate"] = df["_engagement"] / df[cols["reads"]].replace(0, np.nan)

    out = {}
    for platform, group in df.groupby(cols["platform"]):
        out[str(platform)] = {
            "n_posts": int(len(group)),
            "total_reads": int(group[cols["reads"]].sum()),
            "total_engagement": int(group["_engagement"].sum()),
            "avg_engagement_rate": float(group["_engagement_rate"].mean(skipna=True)),
        }
    return out


def content_type_breakdown(df: pd.DataFrame,
                           column_map: Optional[Dict] = None) -> Dict[str, Dict]:
    cols = dict(DEFAULT_CONTENT_COLS)
    if column_map:
        cols.update(column_map)
    if cols["type"] not in df.columns:
        return {}

    df = df.copy()
    df["_engagement"] = (df.get(cols["likes"], 0).fillna(0)
                         + df.get(cols["comments"], 0).fillna(0)
                         + df.get(cols["shares"], 0).fillna(0))

    out = {}
    for ctype, group in df.groupby(cols["type"]):
        out[str(ctype)] = {
            "n_posts": int(len(group)),
            "total_reads": int(group[cols["reads"]].sum()),
            "total_engagement": int(group["_engagement"].sum()),
        }
    return out


# --- 粉丝增长 ---------------------------------------------------------------

@dataclass
class FanGrowthMetrics:
    period_start: str
    period_end: str
    n_days: int
    total_new: int
    total_unfollows: int
    net_growth: int
    starting_fans: int
    ending_fans: int
    growth_pct: float        # (ending - starting) / starting
    daily_net_avg: float
    churn_rate: float        # unfollows / starting_fans

    def to_dict(self) -> dict:
        return {k: (v if not isinstance(v, (np.integer, np.floating))
                    else float(v)) for k, v in self.__dict__.items()}


def compute_fan_growth(df: pd.DataFrame,
                       column_map: Optional[Dict] = None) -> FanGrowthMetrics:
    cols = dict(DEFAULT_FAN_COLS)
    if column_map:
        cols.update(column_map)
    if df is None or len(df) == 0:
        raise ValueError("DataFrame 为空")
    for c in [cols["date"], cols["new_fans"], cols["unfollows"]]:
        if c not in df.columns:
            raise ValueError(f"缺必要列 {c}")

    df = df.copy()
    df[cols["date"]] = pd.to_datetime(df[cols["date"]])
    df = df.sort_values(cols["date"])

    n_days = int(len(df))
    total_new = int(df[cols["new_fans"]].sum())
    total_unf = int(df[cols["unfollows"]].sum())
    net = total_new - total_unf

    starting = int(df[cols["total_fans"]].iloc[0]) if cols["total_fans"] in df.columns else 0
    ending = int(df[cols["total_fans"]].iloc[-1]) if cols["total_fans"] in df.columns else 0

    growth_pct = 0.0
    if starting > 0:
        growth_pct = float((ending - starting) / starting * 100)

    daily_net_avg = float(net / n_days) if n_days else 0.0
    churn = float(total_unf / starting * 100) if starting else 0.0

    return FanGrowthMetrics(
        period_start=str(df[cols["date"]].iloc[0].date()),
        period_end=str(df[cols["date"]].iloc[-1].date()),
        n_days=n_days,
        total_new=total_new, total_unfollows=total_unf,
        net_growth=net,
        starting_fans=starting, ending_fans=ending,
        growth_pct=growth_pct, daily_net_avg=daily_net_avg,
        churn_rate=churn,
    )


def demographic_breakdown(df: pd.DataFrame,
                          column_map: Optional[Dict] = None) -> Dict:
    """性别 / 年龄段 / Top 城市分布（基于粉丝表里的属性）。"""
    cols = dict(DEFAULT_FAN_COLS)
    if column_map:
        cols.update(column_map)
    df = df.copy()
    if cols["new_fans"] not in df.columns:
        return {}

    out = {}
    if cols["gender"] in df.columns:
        gender = df.groupby(cols["gender"])[cols["new_fans"]].sum().sort_values(ascending=False)
        out["gender"] = {str(k): int(v) for k, v in gender.items()}

    if cols["age"] in df.columns:
        # 把年龄分桶
        age = df[cols["age"]].dropna().astype(float)
        bins = [0, 18, 25, 35, 45, 100]
        labels = ["<18", "18-24", "25-34", "35-44", "45+"]
        age_bucket = pd.cut(age, bins=bins, labels=labels, right=False)
        bucket_counts = age_bucket.value_counts(sort=False)
        out["age_distribution"] = {str(k): int(v) for k, v in bucket_counts.items() if v > 0}

    if cols["city"] in df.columns:
        cities = df.groupby(cols["city"])[cols["new_fans"]].sum().sort_values(ascending=False).head(10)
        out["top_cities"] = {str(k): int(v) for k, v in cities.items()}

    return out


# --- 情感统计 ---------------------------------------------------------------

@dataclass
class SentimentSummary:
    n_comments: int
    n_positive: int
    n_neutral: int
    n_negative: int
    mean_score: float
    positive_pct: float
    negative_pct: float

    def to_dict(self) -> dict:
        return {k: (v if not isinstance(v, (np.integer, np.floating))
                    else float(v)) for k, v in self.__dict__.items()}


def summarize_sentiment(comments_df: pd.DataFrame,
                        score_col: str = "sentiment_score",
                        pos_threshold: float = 0.6,
                        neg_threshold: float = 0.4) -> SentimentSummary:
    """汇总已经打过 sentiment_score 的评论 DataFrame。

    score_col 是 v1 sentiment_analyzer 已经填好的列。空 df 抛 ValueError。
    """
    if comments_df is None or len(comments_df) == 0:
        raise ValueError("评论 DataFrame 为空")
    if score_col not in comments_df.columns:
        raise ValueError(f"缺 {score_col} 列；先用 v1 SentimentAnalyzer 算 sentiment_score")

    scores = comments_df[score_col].dropna()
    n = len(scores)
    n_pos = int((scores >= pos_threshold).sum())
    n_neg = int((scores <= neg_threshold).sum())
    n_neu = n - n_pos - n_neg

    return SentimentSummary(
        n_comments=n,
        n_positive=n_pos, n_neutral=n_neu, n_negative=n_neg,
        mean_score=float(scores.mean()),
        positive_pct=float(n_pos / n * 100) if n else 0.0,
        negative_pct=float(n_neg / n * 100) if n else 0.0,
    )
