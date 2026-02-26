import json
import os

from openai import OpenAI
from dotenv import load_dotenv

from app.models import ItineraryRequest, ItineraryResponse

load_dotenv()

# NOTE: actual values are re-read inside generate_itinerary() with override=True
# so that .env changes are picked up without restarting the server.
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

OUTPUT JSON SCHEMA (strict):
{
  "city": "string",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "budget": integer,
  "estimated_total_price": integer,
  "itinerary": [
    {
      "date": "YYYY-MM-DD",
      "hotel": {
        "google_map_info": {
          "name": "string",
          "address": "string",
          "google_maps_url": "string",
          "rating": float | null
        },
        "est_price": integer
      },
      "breakfast": {
        "google_map_info": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null },
        "est_price": integer
      },
      "lunch": {
        "google_map_info": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null },
        "est_price": integer
      },
      "dinner": {
        "google_map_info": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null },
        "est_price": integer
      },
      "sightseeing_spots": [
        {
          "time_range": "HH:MM ~ HH:MM",
          "location": { "name": "string", "address": "string", "google_maps_url": "string", "rating": float | null },
          "est_price": integer
        }
      ],
      "est_daily_price": integer
    }
  ]
}
"""


def _build_user_prompt(req: ItineraryRequest) -> str:
    num_days = (req.end_date - req.start_date).days + 1
    lines = [
        f"Plan a {num_days}-day trip to {req.city}.",
        f"Travel dates: {req.start_date} to {req.end_date}.",
        f"Total budget: ${req.budget} USD.",
    ]
    if req.preferences and req.preferences.strip():
        lines.append(
            f"User preferences / special requests: {req.preferences.strip()}\n"
            f"Please incorporate these preferences into the itinerary — choose hotels, "
            f"restaurants, and sightseeing spots that align with them wherever possible."
        )
    lines.append("Generate a full itinerary following the JSON schema provided in the system prompt.")
    return "\n".join(lines)


def generate_itinerary(req: ItineraryRequest) -> ItineraryResponse:
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL") or None

    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        max_tokens=16000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(req)},
        ],
    )

    choice = response.choices[0]
    finish_reason = choice.finish_reason

    if finish_reason == "length":
        raise ValueError(
            "The itinerary is too long to generate in one response. "
            "Try a shorter trip (fewer days) or reduce the number of days."
        )

    raw_text = choice.message.content or ""
    raw_text = raw_text.strip()

    if not raw_text:
        raise ValueError("OpenAI returned no content in its response.")

    # Strip accidental markdown fences if any
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\n\nRaw response:\n{raw_text[:500]}")

    try:
        return ItineraryResponse(**data)
    except Exception as e:
        itinerary = data.get('itinerary') or []
        first_keys = list(itinerary[0].keys()) if itinerary and isinstance(itinerary[0], dict) else 'N/A'
        raise ValueError(f"Response schema mismatch: {e}\n\nKeys returned: {list(data.keys())}\nFirst itinerary item keys: {first_keys}")
