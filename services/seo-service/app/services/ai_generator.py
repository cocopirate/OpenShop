"""AI content generation service using OpenAI."""
from __future__ import annotations

import json
import structlog
from openai import AsyncOpenAI

from app.config import settings

log = structlog.get_logger(__name__)

SYSTEM_MESSAGE = """你是本地SEO内容专家。用户会提供城市、区、服务信息，你需要生成一段本地化的服务页面内容。
要求：
1. 内容口语化，贴近本地用户
2. 自然融入地标名称，不要堆砌
3. 必须严格输出 JSON，不要有任何额外文字
4. JSON 结构严格遵守 schema，字段不可增删"""

USER_MESSAGE_TEMPLATE = """城市：{city_name}
区：{district_name}
服务：{service_name}（{service_description}）
参考价格：{base_price}元起
周边地标：{landmarks}
关键词：{keywords}"""

EXPECTED_SCHEMA = """{
  "intro": "150字以内的服务介绍，自然融入城市/区名",
  "local_intro": "100字以内，结合地标描述服务覆盖范围",
  "service_items": [
    {"name": "服务项目名", "desc": "一句话描述", "price_hint": "价格参考"}
  ],
  "cases": [
    {"title": "案例标题", "desc": "案例描述，80字以内"}
  ],
  "faq": [
    {"q": "常见问题", "a": "回答，60字以内"}
  ],
  "cta": "行动号召文案，30字以内"
}"""


def _build_user_message(
    city_name: str,
    district_name: str,
    service_name: str,
    service_description: str,
    base_price: int | None,
    landmarks: list[str],
    keywords: list[str],
) -> str:
    # base_price is stored in fen (Chinese cents, 1 yuan = 100 fen)
    price_str = f"{base_price / 100:.0f}" if base_price else "面议"
    return USER_MESSAGE_TEMPLATE.format(
        city_name=city_name,
        district_name=district_name,
        service_name=service_name,
        service_description=service_description or service_name,
        base_price=price_str,
        landmarks="、".join(landmarks) if landmarks else "无",
        keywords="、".join(keywords) if keywords else "无",
    )


async def generate_seo_content(
    city_name: str,
    district_name: str,
    service_name: str,
    service_description: str,
    base_price: int | None,
    landmarks: list[str],
    keywords: list[str],
) -> dict:
    """Call OpenAI to generate SEO content. Returns parsed JSON dict.

    Args:
        base_price: Reference price in fen (1 yuan = 100 fen). Converted to yuan for display.
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    user_message = _build_user_message(
        city_name=city_name,
        district_name=district_name,
        service_name=service_name,
        service_description=service_description,
        base_price=base_price,
        landmarks=landmarks,
        keywords=keywords,
    )

    log.info("ai_generator.calling", city=city_name, district=district_name, service=service_name)

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.8,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {
                "role": "user",
                "content": user_message + f"\n\n请严格按照以下 JSON schema 输出：\n{EXPECTED_SCHEMA}",
            },
        ],
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("OpenAI returned empty content")

    result = json.loads(raw)

    # Validate required keys
    required_keys = {"intro", "local_intro", "service_items", "cases", "faq", "cta"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"AI response missing required keys: {missing}")

    log.info("ai_generator.success", city=city_name, district=district_name, service=service_name)
    return result
