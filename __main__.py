"""Social-Media-Analytics CLI（v2）。

子命令：
    content     内容表现统计 + 平台 / 内容类型分解
    fan         粉丝增长 + 人口学分布
    sentiment   评论情感汇总（需要先用 v1 SentimentAnalyzer 算 sentiment_score）
    insights    LLM 或规则综合洞察报告
    list-models 列 LLM backend
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
    platform_breakdown, summarize_sentiment,
)
from llm_insights import LLMClient, generate_insights


def _load_csv(path: str) -> pd.DataFrame:
    # 自动尝试 utf-8 / utf-8-sig（v1 sample 是 BOM 开头）
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8")


def cmd_content(args) -> int:
    df = _load_csv(args.csv)
    metrics = compute_content_metrics(df)
    platforms = platform_breakdown(df)
    types = content_type_breakdown(df)
    payload = {
        "metrics": metrics.to_dict(),
        "platform_breakdown": platforms,
        "content_type_breakdown": types,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def cmd_fan(args) -> int:
    df = _load_csv(args.csv)
    growth = compute_fan_growth(df)
    demo = demographic_breakdown(df)
    payload = {"growth": growth.to_dict(), "demographics": demo}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def cmd_sentiment(args) -> int:
    df = _load_csv(args.csv)
    if args.score_col not in df.columns:
        # 需要先用 v1 SentimentAnalyzer 算
        sys.stderr.write(
            f"[info] CSV 没有 {args.score_col} 列；用 v1 SentimentAnalyzer 现场算\n"
        )
        try:
            from sentiment_analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer(df)
            df = analyzer.analyze_sentiment(text_col=args.text_col)
        except Exception as e:
            sys.stderr.write(f"[error] 现场算失败：{e}\n")
            return 2

    summary = summarize_sentiment(df, score_col=args.score_col,
                                  pos_threshold=args.pos_threshold,
                                  neg_threshold=args.neg_threshold)
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
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
                cdf = SentimentAnalyzer(cdf).analyze_sentiment()
            except Exception:
                pass
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
        prog="smm", description="社媒数据 headless 分析 + LLM 洞察"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("content", help="内容表现统计")
    sp.add_argument("csv")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_content)

    sp = sub.add_parser("fan", help="粉丝增长 + 人口学")
    sp.add_argument("csv")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_fan)

    sp = sub.add_parser("sentiment", help="评论情感汇总")
    sp.add_argument("csv")
    sp.add_argument("--score-col", default="sentiment_score")
    sp.add_argument("--text-col", default="comment")
    sp.add_argument("--pos-threshold", type=float, default=0.6)
    sp.add_argument("--neg-threshold", type=float, default=0.4)
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
