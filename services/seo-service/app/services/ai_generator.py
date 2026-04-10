"""AI content generation — delegates to AI Service via HTTP."""
from __future__ import annotations

import structlog
import httpx

from app.config import settings

log = structlog.get_logger(__name__)

_TEMPLATE_KEY = "seo.page.generate"


async def generate_seo_content(
    city_name: str,
    district_name: str,
    service_name: str,
    service_description: str,
    base_price: int | None,
    landmarks: list[str],
    keywords: list[str],
) -> dict:
    """Call AI Service to generate SEO content. Returns parsed JSON dict.

    Args:
        base_price: Reference price in fen (1 yuan = 100 fen). Converted to yuan for display.
    """
    price_str = f"{base_price / 100:.0f}" if base_price else "面议"

    log.info("ai_generator.calling", city=city_name, district=district_name, service=service_name)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/complete/template",
            headers={"X-Service-Key": settings.AI_SERVICE_KEY},
            json={
                "template_key": _TEMPLATE_KEY,
                "variables": {
                    "city_name": city_name,
                    "district_name": district_name,
                    "service_name": service_name,
                    "service_description": service_description or service_name,
                    "base_price": price_str,
                    "landmarks": "、".join(landmarks) if landmarks else "无",
                    "keywords": "、".join(keywords) if keywords else "无",
                },
                "caller_service": "seo-service",
            },
        )
        resp.raise_for_status()

    result = resp.json()["content"]

    # Validate required keys
    required_keys = {"intro", "local_intro", "service_items", "cases", "faq", "cta"}
    if isinstance(result, dict):
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"AI response missing required keys: {missing}")

    log.info("ai_generator.success", city=city_name, district=district_name, service=service_name)
    return result

