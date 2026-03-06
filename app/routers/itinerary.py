"""
Itinerary API: generate and refine travel itineraries.
Includes rate limiting, response caching, and structured error handling.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends

from app.config import get_settings
from app.models import ItineraryRequest, ItineraryResponse, RefineItineraryRequest
from app.services.llm_service import generate_itinerary, refine_itinerary
from app.services.cache import TTLCache
from app.services.rate_limit import InMemoryRateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/itinerary", tags=["Itinerary"])

_settings = get_settings()
_cache = TTLCache(ttl_seconds=_settings.cache_ttl_seconds)
_rate_limiter = InMemoryRateLimiter(
    requests_per_window=_settings.rate_limit_requests,
    window_seconds=_settings.rate_limit_window_seconds,
)


def _request_payload(req: ItineraryRequest) -> dict[str, Any]:
    return req.model_dump(mode="json")


@router.post("/", response_model=ItineraryResponse)
async def create_itinerary(request: Request, req: ItineraryRequest) -> ItineraryResponse:
    """
    Generate a day-by-day travel itinerary using AI.
    Rate limited and cached for identical requests.
    """
    num_days = (req.end_date - req.start_date).days + 1
    if num_days > 14:
        raise HTTPException(
            status_code=422,
            detail=f"Trip duration is {num_days} days. Maximum is 14 days.",
        )

    _rate_limiter.raise_if_exceeded(request)

    payload = _request_payload(req)
    cached = _cache.get(payload)
    if cached is not None:
        logger.info("Returning cached itinerary for %s", req.city)
        return ItineraryResponse(**cached)

    try:
        result = await asyncio.to_thread(generate_itinerary, req)
        _cache.set(payload, result.model_dump(mode="json"))
        return result
    except EnvironmentError as e:
        logger.error("Config error: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        logger.warning("LLM response error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error generating itinerary")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")


@router.post("/refine", response_model=ItineraryResponse)
async def refine_itinerary_endpoint(request: Request, req: RefineItineraryRequest) -> ItineraryResponse:
    """
    Refine an existing itinerary with a natural-language instruction.
    E.g. "make it cheaper", "add more cultural experiences", "less walking".
    """
    _rate_limiter.raise_if_exceeded(request)

    try:
        return await asyncio.to_thread(refine_itinerary, req)
    except EnvironmentError as e:
        logger.error("Config error: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        logger.warning("LLM refine error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error refining itinerary")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")
