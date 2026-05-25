"""OpenAI 中文总结封装。

如果没有 OPENAI_API_KEY，函数会返回 None，让主程序生成基础模板。
这样 GitHub Actions 或本地环境即使没配置 key，也不会失败。
"""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def has_openai_key() -> bool:
    """检查是否配置 OpenAI API key。"""

    return bool(os.getenv("OPENAI_API_KEY"))


def summarize_with_openai(prompt: str, max_tokens: int = 2200) -> str | None:
    """调用 OpenAI 生成中文总结。失败时返回 None。"""

    if not has_openai_key():
        return None

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是中文投资研究助手。请用清晰、谨慎、适合复盘的中文输出。"
                        "不要编造事实；如果信息不足，请明确说需要继续验证。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or None
    except Exception as exc:  # OpenAI SDK 异常类型可能随版本变化，保持宽容处理。
        print(f"[WARN] OpenAI 总结失败，改用基础模板: {exc}")
        return None


def compact_news_for_prompt(news: list[Any], limit: int = 25) -> str:
    """把新闻列表压缩成适合 LLM 读取的文本。"""

    lines: list[str] = []
    for idx, item in enumerate(news[:limit], start=1):
        lines.append(
            f"{idx}. 标题: {item.title}\n"
            f"   来源: {item.source}\n"
            f"   日期: {item.published or '未知'}\n"
            f"   摘要: {item.summary or '无'}\n"
            f"   正文: {getattr(item, 'article_text', '') or '未抓取到正文'}\n"
            f"   链接: {item.link}"
        )
    return "\n".join(lines)
