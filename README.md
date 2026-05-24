# Social-Media-Analytics

社交媒体数据分析：Streamlit 仪表板（v1）+ headless CLI + LLM 运营洞察（v2）。

v1 提供 Streamlit 仪表板（图表 / 筛选 / 报告）+ 内容 / 粉丝 / 评论情感分析 + 32 个
测试。v2 在不动 v1 代码的前提下补：

1. **Headless 分析模块** — v1 的 analyzer 都强依赖 Streamlit + plotly。v2 加
   `headless_analytics.py` 纯 pandas 实现同样指标，让脚本 / CI / 报表 cron 能跑。
2. **CLI 入口** — `__main__.py` 5 个子命令脚本化生成日报。
3. **LLM 运营洞察** — 喂入指标 → LLM 生成 overview / 内容建议 / 平台建议 /
   风险四段报告。缺 API key 时退化为规则启发式（基于流失率 / 互动率 / 情感分布
   的分支逻辑）。

## v2 新增

| 文件 | 干什么 |
|---|---|
| `headless_analytics.py` | `compute_content_metrics` + `compute_fan_growth` + `summarize_sentiment` + `platform_breakdown` + `content_type_breakdown` + `demographic_breakdown` |
| `llm_insights.py` | `generate_insights(content, fan, sentiment, ...)` → `InsightReport`（overview / 内容建议 / 平台建议 / 风险）+ markdown 渲染 |
| `__main__.py` | CLI 5 子命令 content / fan / sentiment / insights / list-models |
| `tests/test_headless_analytics.py` | 27 测试 |
| `tests/test_llm_insights.py` | 20 测试：规则覆盖各种场景 + LLM mock |

总 79 个测试通过（32 v1 + 47 v2），2 秒跑完。

## v1 仍保留

| 模块 | 干什么 |
|---|---|
| `dashboard.py` | Streamlit 交互式主界面 |
| `content_analyzer.py` | 内容表现 + plotly 图表 |
| `fan_analyzer.py` | 粉丝增长 + plotly 可视化 |
| `sentiment_analyzer.py` | SnowNLP 评论情感 + 词云 |
| `generate_sample_data.py` | 合成示例数据 |
| `sample_data/{content,comment,fan}_sample.csv` | 示例数据集 |

## 安装

```bash
pip install -r requirements.txt
# 可选：v2 LLM 洞察
pip install openai      # openai / deepseek
pip install anthropic
```

## 快速开始

### v2 headless CLI

```bash
# 内容表现统计 + 平台 / 内容类型分解
python __main__.py content sample_data/content_sample.csv

# 粉丝增长 + 人口学分布
python __main__.py fan sample_data/fan_sample.csv

# 评论情感汇总（自动调 v1 SnowNLP 算 score，如果 CSV 没有 sentiment_score 列）
python __main__.py sentiment sample_data/comment_sample.csv

# 综合 LLM 洞察报告
python __main__.py insights sample_data/content_sample.csv \
    --fan-csv sample_data/fan_sample.csv \
    --comment-csv sample_data/comment_sample.csv \
    --use-llm --backend deepseek -o report.md

# LLM backend 配置
python __main__.py list-models
```

### v1 Streamlit 仪表板

```bash
streamlit run dashboard.py
```

### 库调用

```python
import pandas as pd
from headless_analytics import (
    compute_content_metrics, compute_fan_growth,
    platform_breakdown, content_type_breakdown,
)
from llm_insights import generate_insights, LLMClient

content_df = pd.read_csv("content.csv", encoding="utf-8-sig")
fan_df = pd.read_csv("fans.csv", encoding="utf-8-sig")

content_m = compute_content_metrics(content_df)
fan_m = compute_fan_growth(fan_df)
platforms = platform_breakdown(content_df)
types = content_type_breakdown(content_df)

report = generate_insights(
    content_metrics=content_m.to_dict(),
    fan_metrics=fan_m.to_dict(),
    platforms=platforms,
    content_types=types,
    llm_client=LLMClient(backend="deepseek"),
)
print(report.to_markdown())
```

## 一个真实输出（heuristic 路径）

```
$ python __main__.py insights sample_data/content_sample.csv \
    --fan-csv sample_data/fan_sample.csv

## 整体概览

发布 100 篇内容，总阅读 5,251,886，平均互动率 27.60%，粉丝净增 +6523（+80.3%）。

## 内容运营建议

- 复盘爆款 "精彩 48 分享"（抖音） 找通用规律
- 高互动内容类型：视频 （203,864 互动），可增加产量

## 平台运营建议

- 主投放平台：小红书（1,825,015 阅读）
- 互动率最高：抖音（54.52%）

## 风险关注

- 流失率 18.0%，需排查内容方向 / 互动质量
```

## 数据 schema

### 内容表现 CSV
| 列 | 类型 | 必需 |
|---|---|---|
| content_id | int | 否 |
| title | str | 否 |
| platform | str | 否（影响 platform_breakdown）|
| reads | int | **是** |
| likes | int | **是** |
| comments | int | 否 |
| shares | int | 否 |
| content_type | str | 否 |
| publish_time | datetime | 否 |
| keywords | str | 否 |

### 粉丝增长 CSV
| 列 | 类型 | 必需 |
|---|---|---|
| date | datetime-parseable | **是** |
| new_fans | int | **是** |
| unfollows | int | **是** |
| total_fans | int | 否 |
| interactions | int | 否 |
| gender | str | 否 |
| age | int | 否 |
| city | str | 否 |

### 评论情感 CSV
| 列 | 类型 | 必需 |
|---|---|---|
| comment | str | **是**（用于 SnowNLP 现场算）|
| date | datetime | 否 |
| sentiment_score | float | 否（CSV 没有时 CLI 自动调 SnowNLP）|

## 设计取舍

- **headless_analytics 与 v1 analyzer 共存**：v1 的 plotly 图表 + Streamlit
  UI 没动；v2 另起一个纯 pandas 模块算指标。要 UI 用 v1，要脚本化 / CI 用 v2。
- **LLM insights 缺 key 退规则不抛错**：规则启发式覆盖 5 种关键风险信号（高流失、
  负增长、负面情感、低互动、爆款复盘），用户没 LLM 也能拿到基线建议。
- **encoding="utf-8-sig"**：v1 sample_data CSV 以 BOM 开头，CLI 默认尝试
  `utf-8-sig`，失败再退到 `utf-8`，兼容两种写法。
- **CLI sentiment 命令现场调 SnowNLP**：如果传入 CSV 还没有 `sentiment_score`
  列，自动用 v1 `SentimentAnalyzer.analyze_sentiment` 现算。

## 项目结构

```
Social-Media-Analytics/
├── __main__.py                  # v2 CLI
├── headless_analytics.py        # v2 纯 pandas 分析
├── llm_insights.py              # v2 LLM 洞察
├── dashboard.py                 # v1 Streamlit
├── content_analyzer.py          # v1 内容分析（带 plotly）
├── fan_analyzer.py              # v1 粉丝分析
├── sentiment_analyzer.py        # v1 SnowNLP 评论情感
├── generate_sample_data.py
├── verify.py
├── tests/                       # 79 测试
│   ├── test_content.py
│   ├── test_fan.py
│   ├── test_sentiment.py
│   ├── test_headless_analytics.py   # v2 新增
│   └── test_llm_insights.py         # v2 新增
├── sample_data/{content,comment,fan}_sample.csv
└── requirements.txt
```

## 测试

```bash
pytest tests/ --no-cov
```

79 个测试，2 秒跑完。LLM mock，无网络 / 无 API key 依赖。SnowNLP 需要安装：
`pip install snownlp`。

## 已知限制

- 情感分析依赖 v1 的 SnowNLP，只支持中文；多语种需自己换 backend。
- `compute_fan_growth` 的 churn_rate 用整段累计流失 / 起始粉丝数算，不是日 churn；
  日粒度需要外部循环。
- LLM `insights` 输出最多 5 条建议 + 3 条平台建议 + 5 条风险，超出自动裁。

## 许可

MIT
