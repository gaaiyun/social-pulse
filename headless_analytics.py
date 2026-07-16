"""无 Streamlit / plotly 依赖的社媒分析函数集合。

仪表板里的 ContentAnalyzer / FanAnalyzer / SentimentAnalyzer 都耦合 plotly
图表渲染，没法脚本化。这一层只算指标、返回 dataclass / dict，让命令行、
定时任务和报表脚本能直接拿到结构化结果。

覆盖范围：
- 内容表现：互动率 / 爆款识别 / 平台 & 内容类型分解
- 发布时段：按小时 / 星期几的平均互动率，找最优发布窗口
- 爆款拆解：高互动 vs 普通内容的标题长度 / 关键词 / 发布时段差异
- 粉丝增长：新增 / 流失 / 净增 / 留存代理 + 人口学画像
- 情感分析：基于 SnowNLP 打分的汇总 / 日趋势 / 关键词情感 / 负面反馈提取
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


def _series_or_zero(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column].fillna(0)
    return pd.Series(0, index=df.index, dtype="float64")


def _add_engagement_columns(df: pd.DataFrame, cols: Dict) -> None:
    df["_engagement"] = (
        _series_or_zero(df, cols["likes"])
        + _series_or_zero(df, cols["comments"])
        + _series_or_zero(df, cols["shares"])
    )
    reads = df[cols["reads"]].fillna(0)
    df["_engagement_rate"] = (
        df["_engagement"].div(reads.where(reads.ne(0))).fillna(0.0)
    )


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
    _add_engagement_columns(df, cols)

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

    # 没有曝光时，互动率被定义为 0 只为保证 JSON 有限，不能据此判成爆款。
    eligible_for_viral = df[df[cols["reads"]].fillna(0) > 0]
    if len(eligible_for_viral) >= 5:
        viral_thresh = float(
            eligible_for_viral["_engagement_rate"].quantile(
                0.8, interpolation="linear"
            )
        )
        n_viral = int(
            (eligible_for_viral["_engagement_rate"] >= viral_thresh).sum()
        )
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
    _add_engagement_columns(df, cols)

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
    _add_engagement_columns(df, cols)

    out = {}
    for ctype, group in df.groupby(cols["type"]):
        out[str(ctype)] = {
            "n_posts": int(len(group)),
            "total_reads": int(group[cols["reads"]].sum()),
            "total_engagement": int(group["_engagement"].sum()),
        }
    return out


def posting_time_analysis(df: pd.DataFrame,
                          column_map: Optional[Dict] = None) -> Dict:
    """按发布小时 / 星期几统计平均互动率，定位最优发布窗口。

    需要 publish_time 列（可被 pandas 解析）。星期几 0=周一、6=周日。
    """
    cols = dict(DEFAULT_CONTENT_COLS)
    if column_map:
        cols.update(column_map)
    if cols["publish_time"] not in df.columns:
        return {}

    df = df.copy()
    df["_dt"] = pd.to_datetime(df[cols["publish_time"]], errors="coerce")
    df = df.dropna(subset=["_dt"])
    if len(df) == 0:
        return {}

    _add_engagement_columns(df, cols)

    df["_hour"] = df["_dt"].dt.hour
    df["_dow"] = df["_dt"].dt.dayofweek

    by_hour = df.groupby("_hour")["_engagement_rate"].mean()
    by_dow = df.groupby("_dow")["_engagement_rate"].mean()

    return {
        "best_hour": int(by_hour.idxmax()),
        "best_dayofweek": int(by_dow.idxmax()),
        "by_hour": {int(h): float(v) for h, v in by_hour.items()},
        "by_dayofweek": {int(d): float(v) for d, v in by_dow.items()},
    }


def viral_features(df: pd.DataFrame,
                   top_percent: float = 0.2,
                   column_map: Optional[Dict] = None) -> Dict:
    """对比爆款（互动率前 top_percent）与普通内容的特征差异。

    输出标题平均长度、发布高峰时段、高频关键词、内容类型分布的对照，
    用来回答「爆款长什么样」。数据不足 5 篇时返回空字典。
    """
    cols = dict(DEFAULT_CONTENT_COLS)
    if column_map:
        cols.update(column_map)
    if df is None or len(df) < 5:
        return {}
    if cols["reads"] not in df.columns:
        raise ValueError(f"缺必要列 {cols['reads']}")

    df = df.copy()
    _add_engagement_columns(df, cols)
    df = df[df[cols["reads"]].fillna(0) > 0]
    if len(df) < 5:
        return {}

    thresh = float(df["_engagement_rate"].quantile(1 - top_percent))
    viral = df[df["_engagement_rate"] >= thresh]
    normal = df[df["_engagement_rate"] < thresh]

    def _title_len(sub: pd.DataFrame) -> Optional[float]:
        if cols["title"] not in sub.columns or len(sub) == 0:
            return None
        return float(sub[cols["title"]].astype(str).str.len().mean())

    def _peak_hours(sub: pd.DataFrame) -> List[int]:
        if cols["publish_time"] not in sub.columns or len(sub) == 0:
            return []
        hours = pd.to_datetime(sub[cols["publish_time"]], errors="coerce").dt.hour.dropna()
        if len(hours) == 0:
            return []
        return [int(h) for h in hours.mode().tolist()]

    def _top_keywords(sub: pd.DataFrame, k: int = 10) -> List[str]:
        if cols["keywords"] not in sub.columns or len(sub) == 0:
            return []
        bag: List[str] = []
        for kw in sub[cols["keywords"]].dropna():
            if isinstance(kw, str):
                # 兼容中英文逗号
                parts = kw.replace("，", ",").split(",")
                bag.extend(p.strip() for p in parts if p.strip())
        if not bag:
            return []
        return pd.Series(bag).value_counts().head(k).index.tolist()

    def _type_dist(sub: pd.DataFrame) -> Dict[str, int]:
        if cols["type"] not in sub.columns or len(sub) == 0:
            return {}
        return {str(k): int(v) for k, v in sub[cols["type"]].value_counts().items()}

    return {
        "viral_threshold": thresh,
        "n_viral": int(len(viral)),
        "n_normal": int(len(normal)),
        "viral_title_avg_length": _title_len(viral),
        "normal_title_avg_length": _title_len(normal),
        "viral_peak_hours": _peak_hours(viral),
        "viral_top_keywords": _top_keywords(viral),
        "viral_content_type_dist": _type_dist(viral),
    }


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
    growth_pct: float        # 可观测净流量 / 起始存量
    daily_net_avg: float
    churn_rate: float        # unfollows / starting_fans
    stock_flow_check_available: bool
    stock_flow_consistent: Optional[bool]
    stock_flow_gap: Optional[int]
    max_abs_stock_flow_gap: Optional[int]

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

    daily_net = df[cols["new_fans"]] - df[cols["unfollows"]]
    if cols["total_fans"] in df.columns:
        first_net = int(
            daily_net.iloc[0]
        )
        starting = int(df[cols["total_fans"]].iloc[0]) - first_net
        ending = int(df[cols["total_fans"]].iloc[-1])
        expected_stock = starting + daily_net.cumsum()
        gaps = df[cols["total_fans"]] - expected_stock
        stock_flow_check_available = True
        stock_flow_gap = int(gaps.iloc[-1])
        max_abs_stock_flow_gap = int(gaps.abs().max())
        stock_flow_consistent = bool(gaps.eq(0).all())
    else:
        starting = 0
        ending = net
        stock_flow_check_available = False
        stock_flow_gap = None
        max_abs_stock_flow_gap = None
        stock_flow_consistent = None

    growth_pct = 0.0
    if starting > 0:
        growth_pct = float(net / starting * 100)

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
        stock_flow_check_available=stock_flow_check_available,
        stock_flow_consistent=stock_flow_consistent,
        stock_flow_gap=stock_flow_gap,
        max_abs_stock_flow_gap=max_abs_stock_flow_gap,
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


def sentiment_trend(comments_df: pd.DataFrame,
                    score_col: str = "sentiment_score",
                    date_col: str = "date",
                    pos_threshold: float = 0.6) -> List[Dict]:
    """按天汇总情感：每天的平均分 / 评论数 / 正向占比。

    需要评论表里有日期列和打好分的列。返回按日期升序的列表。
    """
    if comments_df is None or len(comments_df) == 0:
        raise ValueError("评论 DataFrame 为空")
    for c in (score_col, date_col):
        if c not in comments_df.columns:
            raise ValueError(f"缺 {c} 列")

    df = comments_df[[date_col, score_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, score_col])

    out = []
    for day, group in df.groupby(df[date_col].dt.date):
        scores = group[score_col]
        n = int(len(scores))
        out.append({
            "date": str(day),
            "n_comments": n,
            "mean_score": float(scores.mean()),
            "positive_pct": float((scores >= pos_threshold).mean() * 100) if n else 0.0,
        })
    out.sort(key=lambda r: r["date"])
    return out


def keyword_sentiment(comments_df: pd.DataFrame,
                      keywords: List[str],
                      text_col: str = "comment",
                      score_col: str = "sentiment_score",
                      pos_threshold: float = 0.6,
                      neg_threshold: float = 0.4) -> Dict[str, Dict]:
    """统计每个关键词命中的评论的情感表现。

    用于定位「哪些话题/产品点正向、哪些负向」。只返回有命中的关键词。
    """
    if comments_df is None or len(comments_df) == 0:
        raise ValueError("评论 DataFrame 为空")
    for c in (text_col, score_col):
        if c not in comments_df.columns:
            raise ValueError(f"缺 {c} 列")

    df = comments_df
    out: Dict[str, Dict] = {}
    for kw in keywords:
        if not kw:
            continue
        mask = df[text_col].astype(str).str.contains(kw, na=False, case=False, regex=False)
        hit = df.loc[mask, score_col].dropna()
        n = int(len(hit))
        if n == 0:
            continue
        out[kw] = {
            "n_comments": n,
            "mean_score": float(hit.mean()),
            "positive_pct": float((hit >= pos_threshold).mean() * 100),
            "negative_pct": float((hit <= neg_threshold).mean() * 100),
        }
    return out


def top_negative_comments(comments_df: pd.DataFrame,
                          text_col: str = "comment",
                          score_col: str = "sentiment_score",
                          neg_threshold: float = 0.4,
                          top_n: int = 10) -> List[Dict]:
    """挑出情感分最低的负面评论，供人工排查口碑风险。

    返回按分数升序（最差在前）的最多 top_n 条记录。
    """
    if comments_df is None or len(comments_df) == 0:
        raise ValueError("评论 DataFrame 为空")
    for c in (text_col, score_col):
        if c not in comments_df.columns:
            raise ValueError(f"缺 {c} 列")

    df = comments_df[[text_col, score_col]].copy()
    df = df.dropna(subset=[score_col])
    neg = df[df[score_col] <= neg_threshold].sort_values(score_col).head(top_n)
    return [
        {"comment": str(row[text_col]), "score": float(row[score_col])}
        for _, row in neg.iterrows()
    ]
