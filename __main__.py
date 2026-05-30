"""social-pulse 命令行入口。

中文社媒内容分析：内容表现 / 平台对比 / 粉丝画像 / 中文情感（SnowNLP）/ 运营洞察。

子命令：
    content     内容表现统计 + 平台 / 内容类型分解
    timing      发布时段分析 + 爆款特征拆解
    fan         粉丝增长 + 人口学画像
    sentiment   评论情感汇总（含日趋势 / 关键词情感 / 负面反馈提取）
    insights    规则或 LLM 综合运营洞察报告
    list-models 列出可用的 LLM backend
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from headless_analytics import (
    compute_content_metrics, compute_fan_growth,
    content_type_breakdown, demographic_breakdown,
    keyword_sentiment, platform_breakdown, posting_time_analysis,
    sentiment_trend, summarize_sentiment, top_negative_comments,
    viral_features,
)
from llm_insights import LLMClient, generate_insights


def _emit(payload, output: str) -> None:
    """统一输出：打到 stdout，并按需写文件。"""
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")


def _load_csv(path: str) -> pd.DataFrame:
    # 自动尝试 utf-8 / utf-8-sig（v1 sample 是 BOM 开头）
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8")


def cmd_content(args) -> int:
    df = _load_csv(args.csv)
    payload = {
        "metrics": compute_content_metrics(df).to_dict(),
        "platform_breakdown": platform_breakdown(df),
        "content_type_breakdown": content_type_breakdown(df),
    }
    _emit(payload, args.output)
    return 0


def cmd_timing(args) -> int:
    df = _load_csv(args.csv)
    payload = {
        "posting_time": posting_time_analysis(df),
        "viral_features": viral_features(df, top_percent=args.top_percent),
    }
    _emit(payload, args.output)
    return 0


def cmd_fan(args) -> int:
    df = _load_csv(args.csv)
    payload = {
        "growth": compute_fan_growth(df).to_dict(),
        "demographics": demographic_breakdown(df),
    }
    _emit(payload, args.output)
    return 0


def cmd_sentiment(args) -> int:
    df = _load_csv(args.csv)
    if args.score_col not in df.columns:
        # CSV 没有打好分的列，用 SnowNLP 现场批量打分。
        # analyze_batch 才是返回 DataFrame 的批量接口；analyze_sentiment 只接受单条文本。
        sys.stderr.write(
            f"[info] CSV 没有 {args.score_col} 列；用 SnowNLP 现场逐条算\n"
        )
        try:
            from sentiment_analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer(df)
            df = analyzer.analyze_batch(comment_col=args.text_col)
            # analyze_batch 固定写入 sentiment_score 列；若用户指定了别的列名，做一次别名。
            if args.score_col != "sentiment_score" and "sentiment_score" in df.columns:
                df[args.score_col] = df["sentiment_score"]
        except Exception as e:
            sys.stderr.write(f"[error] 现场算失败：{e}\n")
            return 2

    summary = summarize_sentiment(df, score_col=args.score_col,
                                  pos_threshold=args.pos_threshold,
                                  neg_threshold=args.neg_threshold)
    payload = {"summary": summary.to_dict()}

    if args.trend:
        try:
            payload["daily_trend"] = sentiment_trend(
                df, score_col=args.score_col, date_col=args.date_col,
                pos_threshold=args.pos_threshold)
        except ValueError as e:
            sys.stderr.write(f"[warn] 日趋势跳过：{e}\n")

    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        payload["keyword_sentiment"] = keyword_sentiment(
            df, kws, text_col=args.text_col, score_col=args.score_col,
            pos_threshold=args.pos_threshold, neg_threshold=args.neg_threshold)

    if args.top_negative > 0:
        try:
            payload["top_negative"] = top_negative_comments(
                df, text_col=args.text_col, score_col=args.score_col,
                neg_threshold=args.neg_threshold, top_n=args.top_negative)
        except ValueError as e:
            sys.stderr.write(f"[warn] 负面评论提取跳过：{e}\n")

    _emit(payload, args.output)
    return 0


def cmd_insights(args) -> int:
    content_df = _load_csv(args.content_csv)
    content_m = compute_content_metrics(content_df)
    platforms = platform_breakdown(content_df)
    types = content_type_breakdown(content_df)

    fan_m = None
    if args.fan_csv:
        fan_m = compute_fan_growth(_load_csv(args.fan_csv)).to_dict()

    sent_m = None
    if args.comment_csv:
        cdf = _load_csv(args.comment_csv)
        if "sentiment_score" not in cdf.columns:
            try:
                from sentiment_analyzer import SentimentAnalyzer
                # analyze_batch 才会写出 sentiment_score 列；analyze_sentiment 只算单条。
                cdf = SentimentAnalyzer(cdf).analyze_batch()
            except Exception as e:
                sys.stderr.write(f"[warn] 评论情感现场算失败，洞察将不含情感：{e}\n")
        if "sentiment_score" in cdf.columns:
            sent_m = summarize_sentiment(cdf).to_dict()

    client = LLMClient(backend=args.backend) if args.use_llm else None
    if args.use_llm and client and not client.is_available():
        sys.stderr.write(
            f"[warn] --use-llm 但 {args.backend.upper()}_API_KEY 未配，退化规则\n"
        )

    report = generate_insights(
        content_metrics=content_m.to_dict(),
        fan_metrics=fan_m, sentiment_summary=sent_m,
        platforms=platforms, content_types=types,
        llm_client=client,
    )

    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.to_markdown())

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
                   if args.format == "json" else report.to_markdown())
        Path(args.output).write_text(content, encoding="utf-8")
    return 0


def cmd_list_models(args) -> int:
    import os
    rows = [
        ("openai", "gpt-4o-mini", "OPENAI_API_KEY"),
        ("anthropic", "claude-3-5-haiku-20241022", "ANTHROPIC_API_KEY"),
        ("deepseek", "deepseek-chat", "DEEPSEEK_API_KEY"),
    ]
    print(f"{'backend':<12} {'default model':<32} configured")
    print("-" * 60)
    for b, m, e in rows:
        print(f"{b:<12} {m:<32} {'yes' if os.getenv(e) else 'no'}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="social-pulse",
        description="中文社媒内容分析：内容表现 / 平台对比 / 粉丝画像 / 中文情感 / 运营洞察",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("content", help="内容表现统计 + 平台 / 内容类型分解")
    sp.add_argument("csv")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_content)

    sp = sub.add_parser("timing", help="发布时段分析 + 爆款特征拆解")
    sp.add_argument("csv")
    sp.add_argument("--top-percent", type=float, default=0.2,
                    help="爆款判定：互动率前百分之多少（默认 0.2）")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_timing)

    sp = sub.add_parser("fan", help="粉丝增长 + 人口学画像")
    sp.add_argument("csv")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_fan)

    sp = sub.add_parser("sentiment", help="评论情感汇总 + 日趋势 / 关键词 / 负面提取")
    sp.add_argument("csv")
    sp.add_argument("--score-col", default="sentiment_score")
    sp.add_argument("--text-col", default="comment")
    sp.add_argument("--date-col", default="date")
    sp.add_argument("--pos-threshold", type=float, default=0.6)
    sp.add_argument("--neg-threshold", type=float, default=0.4)
    sp.add_argument("--trend", action="store_true", help="附带按天情感趋势")
    sp.add_argument("--keywords", help="逗号分隔的关键词，统计各自情感")
    sp.add_argument("--top-negative", type=int, default=0,
                    help="附带情感最低的 N 条负面评论（默认 0=不输出）")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_sentiment)

    sp = sub.add_parser("insights", help="LLM / 规则综合洞察")
    sp.add_argument("content_csv", help="内容表现 CSV")
    sp.add_argument("--fan-csv", help="粉丝增长 CSV")
    sp.add_argument("--comment-csv", help="评论 CSV")
    sp.add_argument("--use-llm", action="store_true")
    sp.add_argument("--backend", default="deepseek",
                    choices=["openai", "anthropic", "deepseek"])
    sp.add_argument("--format", default="markdown", choices=["markdown", "json"])
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_insights)

    sp = sub.add_parser("list-models", help="列 LLM backend")
    sp.set_defaults(func=cmd_list_models)
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
