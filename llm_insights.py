"""LLM 驱动的社媒分析洞察。

把数字指标（content / fan / sentiment）喂入 LLM，生成可执行的内容运营
建议：标题优化 / 发布时段建议 / 内容类型方向 / 风险点。

LLM 缺 key 时退化为规则启发式，仍能给出基线建议。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


LLMBackend = Literal["openai", "anthropic", "deepseek"]


class LLMNotAvailable(RuntimeError):
    pass


@dataclass
class InsightReport:
    overview: str
    content_recommendations: List[str]
    platform_recommendations: List[str]
    risks: List[str]
    backend: str
    fallback_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "overview": self.overview,
            "content_recommendations": self.content_recommendations,
            "platform_recommendations": self.platform_recommendations,
            "risks": self.risks,
            "backend": self.backend,
            "fallback_reason": self.fallback_reason,
        }

    def to_markdown(self) -> str:
        lines = ["## 整体概览", "", self.overview, ""]
        if self.content_recommendations:
            lines += ["## 内容运营建议", ""] + [f"- {r}" for r in self.content_recommendations] + [""]
        if self.platform_recommendations:
            lines += ["## 平台运营建议", ""] + [f"- {r}" for r in self.platform_recommendations] + [""]
        if self.risks:
            lines += ["## 风险关注", ""] + [f"- {r}" for r in self.risks]
        if self.fallback_reason:
            lines += ["", f"> 生成方式：规则回退（{self.fallback_reason}）"]
        return "\n".join(lines)


class LLMClient:
    def __init__(self, backend: LLMBackend = "deepseek",
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = 60.0):
        if backend not in {"openai", "anthropic", "deepseek"}:
            raise ValueError(f"不支持的 LLM backend：{backend}")
        self.backend = backend
        self.timeout = timeout
        self.api_key = api_key or self._default_key(backend)
        self.base_url = base_url or self._default_base_url(backend)
        self.model = model or self._default_model(backend)

    @staticmethod
    def _default_key(backend):
        return {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        }.get(backend)

    @staticmethod
    def _default_base_url(backend):
        return {"deepseek": "https://api.deepseek.com/v1"}.get(backend)

    @staticmethod
    def _default_model(backend):
        return {"openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-haiku-20241022",
                "deepseek": "deepseek-chat"}.get(backend, "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        if not self.is_available():
            raise LLMNotAvailable(
                f"{self.backend} backend 缺 API key（环境变量 "
                f"{self.backend.upper()}_API_KEY）"
            )
        if self.backend == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key, timeout=self.timeout)
            resp = client.messages.create(
                model=self.model, max_tokens=2048, temperature=temperature,
                system=system, messages=[{"role": "user", "content": user}])
            return resp.content[0].text if resp.content else ""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url,
                        timeout=self.timeout)
        resp = client.chat.completions.create(
            model=self.model, temperature=temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return resp.choices[0].message.content or ""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


# --- 规则 fallback ---------------------------------------------------------

def _heuristic_insights(content: Dict, fan: Dict, sentiment: Optional[Dict],
                        platforms: Dict, content_types: Dict,
                        fallback_reason: Optional[str] = None) -> InsightReport:
    n_posts = content.get("n_posts", 0)
    total_reads = content.get("total_reads", 0)
    avg_rate = content.get("avg_engagement_rate", 0)
    top_platform = content.get("top_platform")
    top_post = content.get("top_post", {})

    growth = fan.get("growth_pct", 0) if fan else 0
    churn = fan.get("churn_rate", 0) if fan else 0

    overview_parts = []
    overview_parts.append(f"发布 {n_posts} 篇内容，总阅读 {total_reads:,}")
    overview_parts.append(f"平均互动率 {avg_rate:.2%}")
    if fan:
        overview_parts.append(
            f"粉丝净增 {fan.get('net_growth', 0):+}（{growth:+.1f}%）"
        )
    if sentiment:
        overview_parts.append(
            f"评论情感正向 {sentiment.get('positive_pct', 0):.0f}% / "
            f"负向 {sentiment.get('negative_pct', 0):.0f}%"
        )
    overview = "，".join(overview_parts) + "。"

    content_recs = []
    if top_post and top_post.get("title"):
        content_recs.append(
            f"复盘爆款 \"{top_post['title']}\"（{top_post.get('platform', '')}） "
            f"找通用规律"
        )
    if content_types:
        best_type = max(content_types.items(),
                        key=lambda x: x[1].get("total_engagement", 0))
        content_recs.append(
            f"高互动内容类型：{best_type[0]} "
            f"（{best_type[1]['total_engagement']:,} 互动），可增加产量"
        )
    if avg_rate < 0.01:
        content_recs.append("平均互动率偏低，建议加强标题打磨 / 选题更新")

    platform_recs = []
    if top_platform:
        platform_recs.append(
            f"主投放平台：{top_platform}（{content.get('top_platform_reads', 0):,} 阅读）"
        )
    if platforms:
        # 找互动率最高的平台（不一定是阅读量最高）
        best_eng_plat = max(platforms.items(),
                            key=lambda x: x[1].get("avg_engagement_rate", 0))
        platform_recs.append(
            f"互动率最高：{best_eng_plat[0]}（{best_eng_plat[1]['avg_engagement_rate']:.2%}）"
        )

    risks = []
    if churn > 10:
        risks.append(f"流失率 {churn:.1f}%，需排查内容方向 / 互动质量")
    if growth < 0:
        risks.append(f"粉丝净增长为负 ({growth:+.1f}%)")
    if sentiment and sentiment.get("negative_pct", 0) > 25:
        risks.append(
            f"评论负向占比 {sentiment.get('negative_pct'):.0f}%，关注客服 / 产品反馈"
        )
    if fan and fan.get("stock_flow_check_available") and not fan.get(
            "stock_flow_consistent", True):
        risks.append(
            "粉丝存量与新增/取关流量不守恒：期末差额 "
            f"{fan.get('stock_flow_gap', 0):+}，最大日差额 "
            f"{fan.get('max_abs_stock_flow_gap', 0)}"
        )
    if avg_rate < 0.005:
        risks.append("互动率极低，账号活跃度堪忧")
    if not risks:
        risks.append("当前未发现明显风险点")

    return InsightReport(
        overview=overview,
        content_recommendations=content_recs[:5],
        platform_recommendations=platform_recs[:3],
        risks=risks[:5],
        backend="heuristic",
        fallback_reason=fallback_reason,
    )


# --- 主入口 -----------------------------------------------------------------

def generate_insights(
    content_metrics: Dict,
    fan_metrics: Optional[Dict] = None,
    sentiment_summary: Optional[Dict] = None,
    platforms: Optional[Dict] = None,
    content_types: Optional[Dict] = None,
    llm_client: Optional[LLMClient] = None,
    backend: Optional[str] = None,
) -> InsightReport:
    fan_metrics = fan_metrics or {}
    sentiment_summary = sentiment_summary or {}
    platforms = platforms or {}
    content_types = content_types or {}

    client = llm_client
    if client is None and backend:
        client = LLMClient(backend=backend)

    fallback_reason = None
    if client:
        if not client.is_available():
            fallback_reason = f"{client.backend} 未配置 API key"
        else:
            try:
                return _llm_insights(content_metrics, fan_metrics,
                                     sentiment_summary, platforms, content_types,
                                     client)
            except Exception as exc:
                # SDK 异常类型不统一；只披露类型，避免把响应或凭据带入报告。
                fallback_reason = (
                    f"{client.backend} 调用失败：{type(exc).__name__}"
                )

    return _heuristic_insights(content_metrics, fan_metrics, sentiment_summary,
                               platforms, content_types,
                               fallback_reason=fallback_reason)


def _llm_insights(content, fan, sentiment, platforms, content_types,
                  client: LLMClient) -> InsightReport:
    system = (
        "你是社交媒体运营顾问。基于给定的数据指标，写中文洞察报告："
        "整体概览（≤120 字）+ 3-5 条内容运营建议 + 2-3 条平台运营建议 + "
        "0-3 条风险关注。只输出 JSON，字段：overview (str), "
        "content_recommendations (list[str]), platform_recommendations "
        "(list[str]), risks (list[str])。"
    )
    payload = {
        "content_metrics": content,
        "fan_metrics": fan,
        "sentiment_summary": sentiment,
        "platforms_top5": dict(list(platforms.items())[:5]),
        "content_types_top5": dict(list(content_types.items())[:5]),
    }
    user = ("社媒数据：\n" + json.dumps(payload, ensure_ascii=False, indent=2)
            + "\n\n按 system 要求输出 JSON。")
    raw = _strip_fences(client.chat(system, user, temperature=0.3))
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("LLM 响应必须是 JSON object")

    overview = data.get("overview", "")
    if not isinstance(overview, str):
        raise ValueError("overview 必须是字符串")

    def _string_list(field: str) -> List[str]:
        value = data.get(field, [])
        if not isinstance(value, list):
            raise ValueError(f"{field} 必须是字符串列表")
        return [item for item in value if isinstance(item, str) and item]

    return InsightReport(
        overview=overview,
        content_recommendations=_string_list("content_recommendations"),
        platform_recommendations=_string_list("platform_recommendations"),
        risks=_string_list("risks"),
        backend=f"llm:{client.backend}",
    )
