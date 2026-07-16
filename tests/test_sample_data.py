"""自带样例及其生成脚本的数据质量回归测试。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def _assert_fan_stock_flow_conserved(df: pd.DataFrame) -> None:
    daily_net = df["new_fans"] - df["unfollows"]
    opening_fans = int(df["total_fans"].iloc[0] - daily_net.iloc[0])
    expected_stock = opening_fans + daily_net.cumsum()
    pd.testing.assert_series_equal(
        df["total_fans"].reset_index(drop=True),
        expected_stock.reset_index(drop=True),
        check_names=False,
    )


def test_checked_in_fan_sample_conserves_stock_flow():
    df = pd.read_csv(ROOT / "sample_data" / "fan_sample.csv",
                     encoding="utf-8-sig")
    _assert_fan_stock_flow_conserved(df)


def test_generated_fan_sample_conserves_stock_flow(tmp_path):
    (tmp_path / "sample_data").mkdir()
    subprocess.run(
        [sys.executable, str(ROOT / "generate_sample_data.py")],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    df = pd.read_csv(tmp_path / "sample_data" / "fan_sample.csv",
                     encoding="utf-8-sig")
    _assert_fan_stock_flow_conserved(df)


def test_dashboard_generated_fan_sample_conserves_stock_flow():
    from dashboard import generate_sample_data

    _, fan_df, _ = generate_sample_data()
    _assert_fan_stock_flow_conserved(fan_df)
