"""
LLM service for itinerary generation with retry, timeout, fallback model,
and improved prompts (weather-aware, local gems, budget breakdown, day difficulty).
"""
import json
import logging
import time
from typing import Optional

from openai import OpenAI, APIConnectionError, APIStatusError
from dotenv import load_dotenv

from app.config import get_settings
from app.models import (
    ItineraryRequest,
    ItineraryResponse,
    RefineItineraryRequest,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert travel planner. When given a city, travel dates, and a budget,
you generate a detailed, realistic day-by-day itinerary in JSON format.

RULES:
- Respond ONLY with a valid JSON object — no markdown, no code fences, no extra text.
- All prices are in USD (integers).
- Use realistic establishment names, real street addresses (keep addresses short, e.g. "848 Washington St, NY"), and realistic ratings (1.0–5.0).
- For google_maps_url, generate a valid Google Maps search link:
  https://www.google.com/maps/search/?api=1&query=<URL-encoded+name>
- Keep the total cost of the itinerary within the provided budget.
- Spread the budget sensibly across accommodation, meals, and sightseeing.
- For multi-day trips, recommend the same hotel each night for simplicity.
- Keep place names concise (max 40 chars). Keep addresses concise (max 50 chars).
- Limit sightseeing_spots to maximum 3 per day to keep the response compact.
- Include at least one "local gem" or cultural experience per day when possible (hidden spots, local markets, workshops).
- Consider crowd avoidance: suggest visiting popular spots early morning or late afternoon when you know typical crowds.
- For each day set "day_difficulty" to one of: "easy", "moderate", "intense" based on how packed/active the day is.
- Add a short "tips" array (2-4 strings) with practical advice for this trip (e.g. "Book teamLab in advance", "Get a Suica card").
- Add "budget_breakdown" with accommodation, meals, activities (and total) summing to estimated_total_price.

OUTPUT JSON SCHEMA (strict):
{
  "city": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "budget": integer,
  "estimated_total_price": integer,
  "budget_breakdown": {
    "accommodation": integer,
    "meals": integer,
    "activities": integer,
    "total": integer
  },
  "tips": ["string", "string"],
  "itinerary": [
    {
      "date": "YYYY-MM-DD",
      "day_difficulty": "easy" | "moderate" | "intense",
      "hotel": {
        "google_map_info": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null },
        "est_price": integer
      },
      "breakfast": { "google_map_info": { ... }, "est_price": integer },
      "lunch": { "google_map_info": { ... }, "est_price": integer },
      "dinner": { "google_map_info": { ... }, "est_price": integer },
      "sightseeing_spots": [
        { "time_range": "HH:MM ~ HH:MM", "location": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null }, "est_price": integer }
      ],
      "est_daily_price": integer
    }
  ]
}
"""

REFINE_SYSTEM_PROMPT = """You are an expert travel planner. You will be given an existing itinerary and a user instruction to modify it.
Your job is to return a complete revised itinerary in the same JSON schema, incorporating the user's request (e.g. "make it cheaper", "add more cultural experiences", "less walking").
- Respond ONLY with a valid JSON object — no markdown, no code fences.
- Preserve city, start_date, end_date, budget. Recompute estimated_total_price and budget_breakdown.
- Keep the same structure: each day has hotel, breakfast, lunch, dinner, sightseeing_spots, est_daily_price, day_difficulty.
- All prices in USD (integers). Include google_maps_url for every place.
"""


def _build_user_prompt(req: ItineraryRequest) -> str:
    num_days = (req.end_date - req.start_date).days + 1
    lines = [
        f"Plan a {num_days}-day trip to {req.city}.",
        f"Travel dates: {req.start_date} to {req.end_date}.",
        f"Total budget: ${req.budget} USD.",
        "Consider typical weather for this season and suggest indoor alternatives if relevant.",
    ]
    if req.preferences and req.preferences.strip():
        lines.append(
            f"User preferences / special requests: {req.preferences.strip()}\n"
            "Please incorporate these into the itinerary — choose hotels, "
            "restaurants, and sightseeing that align with them."
        )
    lines.append("Generate a full itinerary following the JSON schema (include budget_breakdown, tips, day_difficulty for each day).")
    return "\n".join(lines)


def _build_refine_user_prompt(refine_req: RefineItineraryRequest) -> str:
    prev = refine_req.previous_itinerary
    import json as _json
    prev_json = prev.model_dump(mode="json")
    return (
        "Current itinerary (JSON):\n"
        + _json.dumps(prev_json, indent=2, default=str)
        + "\n\nUser instruction: "
        + refine_req.instruction
        + "\n\nReturn the revised full itinerary as a single JSON object in the same schema."
    )


def _parse_response(raw_text: str, context: str = "") -> dict:
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("LLM returned no content.")
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        for p in parts[1:]:
            p = p.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw_text = p
                break
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}\n\nSnippet: {raw_text[:500]}")


def _ensure_budget_breakdown(data: dict) -> None:
    itinerary = data.get("itinerary") or []
    if "budget_breakdown" in data and data["budget_breakdown"]:
        return
    acc = meals = activities = 0
    for day in itinerary:
        if isinstance(day, dict):
            h = day.get("hotel") or {}
            acc += int(h.get("est_price") or h.get("estimated_price") or 0)
            for key in ("breakfast", "lunch", "dinner"):
                m = day.get(key) or {}
                meals += int(m.get("est_price") or m.get("estimated_price") or 0)
            for s in day.get("sightseeing_spots") or []:
                activities += int(s.get("est_price") or s.get("estimated_price") or 0)
    data["budget_breakdown"] = {
        "accommodation": acc,
        "meals": meals,
        "activities": activities,
        "total": acc + meals + activities,
    }


def _call_llm(
    messages: list[dict],
    timeout_seconds: int,
    max_retries: int,
    model: str,
    fallback_model: Optional[str],
) -> str:
    settings = get_settings()
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=timeout_seconds,
    )
    last_error = None
    for attempt in range(max_retries + 1):
        use_model = fallback_model if (attempt > 0 and fallback_model) else model
        try:
            response = client.chat.completions.create(
                model=use_model,
                max_tokens=16000,
                response_format={"type": "json_object"},
                messages=messages,
            )
            choice = response.choices[0]
            if choice.finish_reason == "length":
                raise ValueError(
                    "Itinerary too long. Try fewer days or a shorter trip."
                )
            return (choice.message.content or "").strip()
        except (APIConnectionError, APIStatusError) as e:
            last_error = e
            logger.warning("LLM attempt %s failed: %s", attempt + 1, e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                raise
    if last_error:
        raise last_error
    raise RuntimeError("LLM call failed after retries")


def generate_itinerary(req: ItineraryRequest) -> ItineraryResponse:
    load_dotenv(override=True)
    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")
    model = settings.openai_model
    fallback = settings.openai_fallback_model
    timeout = settings.llm_timeout_seconds
    max_retries = settings.llm_max_retries

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(req)},
    ]
    raw = _call_llm(messages, timeout, max_retries, model, fallback)
    data = _parse_response(raw)
    _ensure_budget_breakdown(data)
    return ItineraryResponse(**data)


def refine_itinerary(refine_req: RefineItineraryRequest) -> ItineraryResponse:
    load_dotenv(override=True)
    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")
    model = settings.openai_model
    fallback = settings.openai_fallback_model
    timeout = settings.llm_timeout_seconds
    max_retries = settings.llm_max_retries

    messages = [
        {"role": "system", "content": REFINE_SYSTEM_PROMPT},
        {"role": "user", "content": _build_refine_user_prompt(refine_req)},
    ]
    raw = _call_llm(messages, timeout, max_retries, model, fallback)
    data = _parse_response(raw)
    _ensure_budget_breakdown(data)
    return ItineraryResponse(**data)
