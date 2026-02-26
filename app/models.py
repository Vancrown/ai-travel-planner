from pydantic import BaseModel, Field, model_validator
from datetime import date
from typing import List, Optional, Any


# -- Request --

class ItineraryRequest(BaseModel):
    city: str = Field(..., examples=["New York City"])
    start_date: date = Field(..., examples=["2026-03-01"])
    end_date: date = Field(..., examples=["2026-03-05"])
    budget: int = Field(..., ge=50, le=500_000, description="Total trip budget in USD (min $50, max $500,000)")
    preferences: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional user preferences, e.g. 'I love Thai food' or 'must visit teamLab'",
        examples=["I love ramen and want to visit teamLab Borderless"],
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "ItineraryRequest":
        today = date.today()
        if self.start_date < today:
            raise ValueError(f"start_date must be today ({today}) or a future date.")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


# ── Response building blocks ──────────────────────────────────────────────────

class GoogleMapInfo(BaseModel):
    model_config = {"populate_by_name": True}

    name: str
    address: str
    google_maps_url: str = Field("", alias="google_maps_url")
    rating: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            # Accept google_map_url (no 's') as alias
            if "google_map_url" in v and "google_maps_url" not in v:
                v["google_maps_url"] = v.pop("google_map_url")
            if "google_maps_url" not in v:
                v["google_maps_url"] = ""
        return v


class MealRecommendation(BaseModel):
    model_config = {"populate_by_name": True}

    google_map_info: GoogleMapInfo
    est_price: int = Field(0, description="Estimated price per person in USD")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            # Accept google_maps_info as alias
            for alt in ("google_maps_info", "map_info", "place"):
                if alt in v and "google_map_info" not in v:
                    v["google_map_info"] = v.pop(alt)
                    break
            if "est_price" not in v:
                for alt in ("estimated_price", "price", "cost"):
                    if alt in v:
                        v["est_price"] = v.pop(alt)
                        break
        return v


class SightseeingSpot(BaseModel):
    model_config = {"populate_by_name": True}

    time_range: str = Field("", examples=["12:00 ~ 15:00"])
    location: GoogleMapInfo
    est_price: int = Field(0, description="Estimated entrance / activity cost in USD")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            for alt in ("google_map_info", "google_maps_info", "place", "spot"):
                if alt in v and "location" not in v:
                    v["location"] = v.pop(alt)
                    break
            if "time_range" not in v:
                for alt in ("time", "hours", "schedule"):
                    if alt in v:
                        v["time_range"] = v.pop(alt)
                        break
            if "est_price" not in v:
                for alt in ("estimated_price", "price", "cost", "entrance_fee"):
                    if alt in v:
                        v["est_price"] = v.pop(alt)
                        break
        return v


class HotelRecommendation(BaseModel):
    model_config = {"populate_by_name": True}

    google_map_info: GoogleMapInfo
    est_price: int = Field(0, description="Estimated price per night in USD")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            for alt in ("google_maps_info", "map_info", "place"):
                if alt in v and "google_map_info" not in v:
                    v["google_map_info"] = v.pop(alt)
                    break
            if "est_price" not in v:
                for alt in ("estimated_price", "price", "cost", "price_per_night"):
                    if alt in v:
                        v["est_price"] = v.pop(alt)
                        break
        return v


class DayItinerary(BaseModel):
    model_config = {"populate_by_name": True}

    date: date
    hotel: HotelRecommendation
    breakfast: MealRecommendation
    lunch: MealRecommendation
    dinner: MealRecommendation
    sightseeing_spots: List[SightseeingSpot] = Field(default_factory=list)
    est_daily_price: int = Field(0, description="Estimated total cost for the day in USD")

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            for alt in ("sightseeing", "attractions", "activities", "spots"):
                if alt in v and "sightseeing_spots" not in v:
                    v["sightseeing_spots"] = v.pop(alt)
                    break
            if "est_daily_price" not in v:
                for alt in ("estimated_daily_price", "daily_cost", "total_cost", "daily_price", "est_price"):
                    if alt in v:
                        v["est_daily_price"] = v.pop(alt)
                        break
        return v


class ItineraryResponse(BaseModel):
    model_config = {"populate_by_name": True}

    city: str
    start_date: date
    end_date: date
    budget: int
    estimated_total_price: int = 0
    itinerary: List[DayItinerary]

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, v: Any) -> Any:
        if isinstance(v, dict):
            if "estimated_total_price" not in v:
                for alt in ("total_price", "total_cost", "est_total_price", "estimated_cost"):
                    if alt in v:
                        v["estimated_total_price"] = v.pop(alt)
                        break
        return v
