# social-pulse

中文社媒内容分析工具。喂进内容表现、粉丝增长、评论三类 CSV，产出四样东西：
内容表现盘点、粉丝画像、平台对比、运营洞察。评论用 SnowNLP 做中文情感打分，
不依赖任何在线服务，本地就能跑完整条链路。

适合需要把多平台运营数据落到结构化结论上的人：哪条内容是爆款、什么时段发互动最高、
粉丝从哪来、哪些话题口碑在掉、下一步该往哪使劲。

## 它解决什么

- **内容表现**：互动率、爆款识别（互动率前 20%）、按平台和内容类型拆解。
- **发布时段**：按小时和星期几统计平均互动率，找最优发布窗口；爆款 vs 普通内容的
  标题长度、发布时段、高频关键词对照。
- **粉丝画像**：新增 / 流失 / 净增 / 增长率，性别、年龄段、Top 城市分布。
- **中文情感**：SnowNLP 逐条打分，汇总正负中占比；支持按天趋势、按关键词拆情感、
  提取分数最低的负面评论做口碑排查。
- **运营洞察**：把上面的指标合成一份中文报告（整体概览 + 内容建议 + 平台建议 +
  风险关注）。默认走规则启发式，配了 LLM key 就走模型生成。

## 两种用法

工具有两层：一层是命令行（`__main__.py`，纯 pandas，能脚本化 / 进定时任务），
一层是 Streamlit 交互仪表板（`dashboard.py`，带图表和筛选）。指标算法两边一致，
要图形界面用仪表板，要自动化出报表用命令行。

## 安装

```bash
pip install -r requirements.txt
# 可选：运营洞察走 LLM 时才需要
pip install openai       # openai / deepseek 共用
pip install anthropic
```

依赖 Python 3.10+。情感分析需要 `snownlp`（已在 requirements 里）。

## 命令行

所有子命令默认读 `sample_data/` 下自带的示例数据，离线即可跑通。Windows 终端如遇
中文乱码，前面加 `set PYTHONIOENCODING=utf-8`（PowerShell：`$env:PYTHONIOENCODING="utf-8"`）。

```bash
# 内容表现：整体指标 + 平台分解 + 内容类型分解
python __main__.py content sample_data/content_sample.csv

# 发布时段 + 爆款特征
python __main__.py timing sample_data/content_sample.csv

# 粉丝增长 + 人口学画像
python __main__.py fan sample_data/fan_sample.csv

# 评论情感汇总（CSV 没有 sentiment_score 列时自动用 SnowNLP 现场打分）
python __main__.py sentiment sample_data/comment_sample.csv

# 情感 + 日趋势 + 关键词情感 + 最差 5 条负面评论
python __main__.py sentiment sample_data/comment_sample.csv \
    --trend --keywords "喜欢,失望,推荐" --top-negative 5

# 综合运营洞察（不带 key 走规则；带 --use-llm 且配了 key 走模型）
python __main__.py insights sample_data/content_sample.csv \
    --fan-csv sample_data/fan_sample.csv \
    --comment-csv sample_data/comment_sample.csv -o report.md

# 查看 LLM backend 配置状态
python __main__.py list-models
```

每个子命令都支持 `-o/--output` 把结果写文件（JSON，`insights` 可选 markdown）。

### 一个真实输出

```
$ python __main__.py insights sample_data/content_sample.csv \
    --fan-csv sample_data/fan_sample.csv \
    --comment-csv sample_data/comment_sample.csv

## 整体概览

发布 100 篇内容，总阅读 5,251,886，平均互动率 27.60%，粉丝净增 +6523（+80.3%），
评论情感正向 50% / 负向 36%。

## 内容运营建议

- 复盘爆款 "精彩48分享"（抖音） 找通用规律
- 高互动内容类型：视频 （203,864 互动），可增加产量

## 平台运营建议

- 主投放平台：小红书（1,825,015 阅读）
- 互动率最高：抖音（54.52%）

## 风险关注

- 流失率 18.0%，需排查内容方向 / 互动质量
- 评论负向占比 36%，关注客服 / 产品反馈
```

`sentiment` 子命令的关键词情感（示例数据）：`喜欢` 命中 13 条、平均分 0.95、全正向；
`失望` 命中 17 条、平均分 0.10、全负向。情感打分确实跑通了。

## 仪表板

```bash
streamlit run dashboard.py
```

浏览器打开 `http://localhost:8501`，默认加载示例数据，可切换平台筛选、查看图表、导出报告。

## 库调用

```python
import pandas as pd
from headless_analytics import (
    compute_content_metrics, compute_fan_growth,
    platform_breakdown, content_type_breakdown,
    posting_time_analysis, viral_features,
    summarize_sentiment, sentiment_trend,
    keyword_sentiment, top_negative_comments,
)
from llm_insights import generate_insights, LLMClient

content_df = pd.read_csv("content.csv", encoding="utf-8-sig")
fan_df = pd.read_csv("fans.csv", encoding="utf-8-sig")

content_m = compute_content_metrics(content_df)
fan_m = compute_fan_growth(fan_df)
platforms = platform_breakdown(content_df)
types = content_type_breakdown(content_df)
timing = posting_time_analysis(content_df)   # 最优发布时段

report = generate_insights(
    content_metrics=content_m.to_dict(),
    fan_metrics=fan_m.to_dict(),
    platforms=platforms,
    content_types=types,
)
print(report.to_markdown())
```

`headless_analytics.py` 里所有函数都是纯 pandas、无图表依赖，返回 dataclass 或
dict / list，方便接到任何下游。

## 数据格式

### 内容表现 CSV

| 列 | 类型 | 必需 | 说明 |
|---|---|---|---|
| content_id | int | 否 | |
| title | str | 否 | 影响爆款标题长度分析 |
| platform | str | 否 | 影响平台分解 |
| reads | int | **是** | 阅读量 |
| likes | int | **是** | 点赞 |
| comments | int | 否 | 评论数 |
| shares | int | 否 | 转发 |
| content_type | str | 否 | 图文 / 视频 / 直播等 |
| publish_time | datetime | 否 | 影响发布时段分析 |
| keywords | str | 否 | 逗号分隔，影响爆款关键词分析 |

### 粉丝增长 CSV

| 列 | 类型 | 必需 |
|---|---|---|
| date | 可解析日期 | **是** |
| new_fans | int | **是** |
| unfollows | int | **是** |
| total_fans | int | 否 |
| interactions | int | 否 |
| gender / age / city | str / int / str | 否 |

### 评论情感 CSV

| 列 | 类型 | 必需 | 说明 |
|---|---|---|---|
| comment | str | **是** | SnowNLP 据此打分 |
| date | datetime | 否 | 日趋势需要 |
| sentiment_score | float | 否 | 缺失时命令行自动用 SnowNLP 现场算 |

## 设计取舍

- **命令行与仪表板共存，指标算法同源**：仪表板那套分析器耦合 plotly，没法脚本化；
  `headless_analytics.py` 用纯 pandas 重算同样的指标，命令行和定时任务调它。
- **情感打分本地化**：用 SnowNLP，不调任何在线接口，离线可跑；代价是只支持中文。
- **运营洞察缺 key 不报错**：没配 LLM key 时退回规则启发式，仍覆盖高流失、负增长、
  负面情感、低互动、爆款复盘五类信号，保证拿得到基线建议。
- **编码兼容 BOM**：示例 CSV 以 BOM 开头，命令行先试 `utf-8-sig` 再退 `utf-8`。
- **进度提示走 stderr**：SnowNLP 批量打分的进度行打到 stderr，stdout 只留结构化 JSON，
  方便 `| jq` 或重定向。

## 测试

```bash
python -m pytest tests/ -q -o addopts=""
```

108 个测试，约 5 秒跑完。覆盖纯 pandas 分析函数、规则洞察（LLM 路径用 mock，无网络
依赖）、以及命令行每个子命令的端到端跑通（含此前损坏的情感回退分支回归用例）。

`pyproject.toml` 默认开了覆盖率（`--cov`），需要 `pytest-cov`；不想要覆盖率就用上面的
`-o addopts=""` 关掉。

## 项目结构

```
social-pulse/
├── __main__.py              # 命令行入口（6 个子命令）
├── headless_analytics.py    # 纯 pandas 分析函数（命令行 / 库调用共用）
├── llm_insights.py          # 运营洞察：规则 + 可选 LLM
├── dashboard.py             # Streamlit 交互仪表板
├── content_analyzer.py      # 内容分析（仪表板用，带 plotly）
├── fan_analyzer.py          # 粉丝分析（仪表板用）
├── sentiment_analyzer.py    # SnowNLP 中文情感
├── generate_sample_data.py  # 生成示例数据
├── sample_data/             # 自带示例：content / fan / comment
└── tests/                   # 108 个测试
```

## 已知限制

- 情感分析只支持中文（SnowNLP）；多语种需自行替换打分后端。
- `compute_fan_growth` 的流失率按整段累计流失 / 起始粉丝数算，不是逐日 churn。
- 运营洞察的建议条数有上限（内容 5 条、平台 3 条、风险 5 条），超出自动截断。

## 许可

MIT
