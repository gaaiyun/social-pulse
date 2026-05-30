"""CLI（__main__.py）端到端测试：在自带 sample_data 上真跑每个子命令。

覆盖此前损坏的 sentiment 回退分支（CSV 无评分列时现场用 SnowNLP 打分）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample_data"
sys.path.insert(0, str(ROOT))


def _load_main():
    """__main__.py 不是合法的模块名，按路径手动加载。"""
    spec = importlib.util.spec_from_file_location("smm_cli", ROOT / "__main__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cli = _load_main()


def _run(argv, capsys):
    rc = cli.main(argv)
    out = capsys.readouterr().out
    return rc, out


def test_content_subcommand(capsys):
    rc, out = _run(["content", str(SAMPLE / "content_sample.csv")], capsys)
    assert rc == 0
    payload = json.loads(out)
    assert payload["metrics"]["n_posts"] == 100
    assert payload["platform_breakdown"]          # 非空
    assert payload["content_type_breakdown"]


def test_timing_subcommand(capsys):
    rc, out = _run(["timing", str(SAMPLE / "content_sample.csv")], capsys)
    assert rc == 0
    payload = json.loads(out)
    assert 0 <= payload["posting_time"]["best_hour"] <= 23
    assert payload["viral_features"]["n_viral"] >= 1


def test_fan_subcommand(capsys):
    rc, out = _run(["fan", str(SAMPLE / "fan_sample.csv")], capsys)
    assert rc == 0
    payload = json.loads(out)
    assert payload["growth"]["n_days"] == 30
    assert "gender" in payload["demographics"]


def test_sentiment_subcommand_with_score_col(capsys):
    """评论表已有 sentiment_score 列时直接汇总，不触发 SnowNLP。"""
    import pandas as pd
    tmp = SAMPLE / "_scored_tmp.csv"
    df = pd.read_csv(SAMPLE / "comment_sample.csv", encoding="utf-8-sig")
    df["sentiment_score"] = [0.9, 0.1] * (len(df) // 2) + [0.5] * (len(df) % 2)
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    try:
        rc, out = _run(["sentiment", str(tmp)], capsys)
        assert rc == 0
        payload = json.loads(out)
        assert payload["summary"]["n_comments"] == len(df)
    finally:
        tmp.unlink(missing_ok=True)


def test_sentiment_subcommand_fallback_snownlp(capsys):
    """回归此前的 bug：CSV 没有 sentiment_score 列时现场算（analyze_batch）。"""
    rc, out = _run(["sentiment", str(SAMPLE / "comment_sample.csv")], capsys)
    assert rc == 0
    payload = json.loads(out)
    s = payload["summary"]
    assert s["n_comments"] > 0
    assert s["n_positive"] + s["n_neutral"] + s["n_negative"] == s["n_comments"]


def test_sentiment_subcommand_extras(capsys):
    """趋势 / 关键词 / 负面提取的附加输出。"""
    rc, out = _run([
        "sentiment", str(SAMPLE / "comment_sample.csv"),
        "--trend", "--keywords", "喜欢,失望", "--top-negative", "5",
    ], capsys)
    assert rc == 0
    payload = json.loads(out)
    assert "daily_trend" in payload
    assert "keyword_sentiment" in payload
    assert "top_negative" in payload
    assert len(payload["top_negative"]) <= 5


def test_insights_subcommand_markdown(capsys):
    rc, out = _run([
        "insights", str(SAMPLE / "content_sample.csv"),
        "--fan-csv", str(SAMPLE / "fan_sample.csv"),
    ], capsys)
    assert rc == 0
    assert "## 整体概览" in out


def test_insights_subcommand_json(capsys):
    rc, out = _run([
        "insights", str(SAMPLE / "content_sample.csv"),
        "--format", "json",
    ], capsys)
    assert rc == 0
    payload = json.loads(out)
    assert payload["backend"] == "heuristic"
    assert "overview" in payload


def test_insights_with_comment_sentiment(capsys):
    """带 --comment-csv 时，洞察概览应纳入情感（回归 analyze_batch 修复）。"""
    rc, out = _run([
        "insights", str(SAMPLE / "content_sample.csv"),
        "--comment-csv", str(SAMPLE / "comment_sample.csv"),
    ], capsys)
    assert rc == 0
    assert "情感" in out


def test_list_models_subcommand(capsys):
    rc, out = _run(["list-models"], capsys)
    assert rc == 0
    assert "backend" in out
    assert "deepseek" in out
