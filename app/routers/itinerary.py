import asyncio

from fastapi import APIRouter, HTTPException
from app.models import ItineraryRequest, ItineraryResponse
from app.services.llm_service import generate_itinerary

router = APIRouter(prefix="/itinerary", tags=["Itinerary"])


@router.post("/", response_model=ItineraryResponse, summary="Generate a travel itinerary")
async def create_itinerary(req: ItineraryRequest) -> ItineraryResponse:
    """
    Generate a day-by-day travel itinerary using an LLM.

    - **city**: Destination city (e.g. "New York City")
    - **start_date**: First day of the trip
    - **end_date**: Last day of the trip
    - **budget**: Total budget in USD (min 50, max 500000)
    """
    num_days = (req.end_date - req.start_date).days + 1
    if num_days > 14:
        raise HTTPException(
            status_code=422,
            detail=f"Trip duration is {num_days} days. Maximum supported is 14 days to ensure a complete itinerary.",
        )

    try:
        # Run the synchronous (blocking) LLM call in a thread pool so the
        # event loop is not blocked during the ~30-second API call.
        return await asyncio.to_thread(generate_itinerary, req)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned an unexpected response format: {e}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
