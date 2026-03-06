"""
Health check and demo helpers for hackathon/deployment.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/v1", tags=["Health & Demo"])


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check for load balancers and App Platform."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_configured=bool((settings.openai_api_key or "").strip()),
    )


DEMO_PROMPTS = [
    {
        "city": "Tokyo",
        "start_date": "2026-04-01",
        "end_date": "2026-04-03",
        "budget": 800,
        "preferences": "I love ramen and want to visit teamLab Borderless. Prefer boutique hotels.",
    },
    {
        "city": "Paris",
        "start_date": "2026-06-10",
        "end_date": "2026-06-12",
        "budget": 1200,
        "preferences": "Art museums, croissants, and a day trip to Versailles.",
    },
    {
        "city": "Bali",
        "start_date": "2026-07-01",
        "end_date": "2026-07-04",
        "budget": 600,
        "preferences": "Yoga, beaches, and local warungs. No party hostels.",
    },
]


class DemoPrompt(BaseModel):
    city: str
    start_date: str
    end_date: str
    budget: int
    preferences: str | None


class DemoPromptsResponse(BaseModel):
    prompts: list[DemoPrompt]


@router.get("/demo-prompts", response_model=DemoPromptsResponse)
async def demo_prompts():
    """Return example prompts for demo video and quick try."""
    return DemoPromptsResponse(
        prompts=[DemoPrompt(**p) for p in DEMO_PROMPTS]
    )
