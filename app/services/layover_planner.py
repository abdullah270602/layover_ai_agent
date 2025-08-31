# app/services/layover_planner.py
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List

from app.schemas.itinerary import ItineraryRequest, LayoverPlan
from app.services.constants import AIRPORTS
from app.services.maps_service import MapsService
from app.services.llm_client import LLMClient


class LayoverPlanner:
    def __init__(
        self,
        leave_buffer_min: int = 45,
        return_buffer_min: int = 90,
        maps: Optional[MapsService] = None,
        llm: Optional[LLMClient] = None,
    ):
        self.maps = maps or MapsService()
        self.llm = llm or LLMClient()
        self.leave_buffer_min = leave_buffer_min
        self.return_buffer_min = return_buffer_min

    @staticmethod
    def _extract_city_name(geo: Dict[str, Any]) -> Optional[str]:
        comps = geo.get("address_components", [])
        for t in ("locality", "sublocality", "administrative_area_level_1"):
            for c in comps:
                if t in c.get("types", []):
                    return c.get("long_name")
        return None

    def _allowed_one_way_minutes(self, layover_minutes: int) -> int:
        total_hours = layover_minutes / 60.0
        usable = max(0, layover_minutes - self.leave_buffer_min - self.return_buffer_min)

        if total_hours < 3:
            bucket = 10
        elif total_hours < 5:
            bucket = 20
        elif total_hours < 7:
            bucket = 35
        elif total_hours < 9:
            bucket = 55
        elif total_hours < 12:
            bucket = 70
        elif total_hours < 14:
            bucket = 90
        else:
            bucket = 115

        hard_cap = int(usable * 0.45)
        if hard_cap <= 0:
            return 0
        return max(10, min(bucket, hard_cap))

    def _radius_from_one_way(self, one_way_min: int, avg_kmh: int = 40) -> int:
        """Convert allowed one-way minutes into a search radius (meters)."""
        meters = int(avg_kmh * (one_way_min / 60.0) * 1000)
        return max(3000, min(50000, meters))

    @staticmethod
    def _fmt_hm(minutes: int) -> str:
        h, m = divmod(max(0, minutes), 60)
        if h and m:
            return f"{h}h {m}m"
        if h:
            return f"{h}h 0m"
        return f"{m}m"

    def build_context(self, request: ItineraryRequest) -> Dict[str, Any]:
        airport_name = AIRPORTS.get(request.airport_code)
        if not airport_name:
            raise ValueError(f"Airport {request.airport_code} not found")

        airport_geo = self.maps.geocode(airport_name)
        if not airport_geo:
            raise ValueError(f"Could not geocode airport {request.airport_code}")

        airport_loc: Tuple[float, float] = (
            airport_geo["geometry"]["location"]["lat"],
            airport_geo["geometry"]["location"]["lng"],
        )
        city_hint = self._extract_city_name(airport_geo)

        layover_minutes = int((request.departure_time - request.arrival_time).total_seconds() // 60)
        usable_minutes = max(0, layover_minutes - self.leave_buffer_min - self.return_buffer_min)

        # Local-time strings (assumes datetimes already tz-aware for local zone if you want true local)
        earliest_exit_dt = request.arrival_time + timedelta(minutes=self.leave_buffer_min)
        latest_return_dt = request.departure_time - timedelta(minutes=self.return_buffer_min)

        earliest_exit_local = earliest_exit_dt.strftime("%H:%M")
        latest_return_local = latest_return_dt.strftime("%H:%M")

        max_one_way = self._allowed_one_way_minutes(layover_minutes)
        radius_m = self._radius_from_one_way(max_one_way, avg_kmh=40)

        raw_places = self.maps.discover_broad_places(
            location=airport_loc,
            radius_m=radius_m,
            city_hint=city_hint,
            open_now=None,
            max_results=80,
        )
        enriched = self.maps.attach_travel_times(origin=airport_loc, places=raw_places)

        filtered: List[Dict[str, Any]] = []
        for p in enriched:
            t = (p.get("_travel") or {}).get("duration_min")
            if t is None:
                continue
            if t <= max_one_way:
                filtered.append(p)

        def pri(p: Dict[str, Any]) -> tuple:
            rating = p.get("rating", 0)
            cnt = p.get("user_ratings_total", 0)
            dist = (p.get("_travel") or {}).get("duration_min") or 999
            return (rating, cnt, -dist)

        filtered.sort(key=pri, reverse=True)

        # strings used in metadata (we’ll force the LLM to copy them verbatim)
        layover_duration_str = self._fmt_hm(layover_minutes)
        safety_buffer_str = f"exit {self.leave_buffer_min}m, return {self.return_buffer_min}m"
        current_time_str = request.arrival_time.strftime("%H:%M")

        return {
            "airport": airport_geo.get("formatted_address"),
            "airport_code": request.airport_code,
            "arrival_time": request.arrival_time.isoformat(),
            "departure_time": request.departure_time.isoformat(),
            "layover_minutes": layover_minutes,
            "usable_minutes": usable_minutes,
            "nationality": request.nationality,
            "city_hint": city_hint,
            "max_one_way_minutes": max_one_way,
            "leave_buffer_min": self.leave_buffer_min,
            "return_buffer_min": self.return_buffer_min,
            "earliest_exit_local": earliest_exit_local,
            "latest_return_local": latest_return_local,
            "radius_m": radius_m,
            # precomputed strings for metadata (to avoid LLM inventing times)
            "meta_layover_duration": layover_duration_str,
            "meta_safety_buffer": safety_buffer_str,
            "meta_must_return_by": latest_return_local,
            "meta_current_time": current_time_str,
            "candidates": [
                {
                    "name": p.get("name"),
                    "address": p.get("vicinity") or p.get("formatted_address"),
                    "types": p.get("types"),
                    "rating": p.get("rating"),
                    "user_ratings_total": p.get("user_ratings_total"),
                    "travel": p.get("_travel"),
                    "place_id": p.get("place_id"),
                    "location": p.get("geometry", {}).get("location"),
                }
                for p in filtered[:30]
            ],
        }

    def generate_itinerary_plan(self, request: ItineraryRequest) -> LayoverPlan:
        ctx = self.build_context(request)
        model_class = LayoverPlan
        schema = model_class.model_json_schema()

        prompt = f"""
You are a JSON generator for a layover planner.

STRICT OUTPUT:
- Return **JSON only**, no code fences.
- Must conform exactly to the TARGET JSON SCHEMA.
- Fill ALL required fields.

HARD CONSTRAINTS (use these exact strings in metadata):
- metadata.airport = {ctx['airport_code']}
- metadata.layover_duration = "{ctx['meta_layover_duration']}"
- metadata.safety_buffer = "{ctx['meta_safety_buffer']}"
- metadata.must_return_by = "{ctx['meta_must_return_by']}"
- metadata.current_time = "{ctx['meta_current_time']}"

TIME RULES:
- Total layover = {ctx['layover_minutes']} minutes.
- Usable window (excluding buffers) = {ctx['usable_minutes']} minutes.
- Earliest exit = {ctx['earliest_exit_local']} (local).
- Latest return = {ctx['latest_return_local']} (local).
- Max ONE-WAY travel time to any stop = {ctx['max_one_way_minutes']} minutes.
- Assume exit buffer = {ctx['leave_buffer_min']} min, return buffer = {ctx['return_buffer_min']} min.

SELECTION RULES:
- Use ONLY from CANDIDATES; do not invent any name/address/place.
- Prefer off-airport options when time allows.
- 4–8 recommended_stops (fewer allowed if time is tight).
- Each stop: realistic "duration_range" (e.g., "45-90 min"), set "transport" to one of ["walk","metro","bus","taxi","rideshare"].
- Keep the total of durations + travel within the usable window. Avoid impossible stacks.

CANDIDATES:
{ctx['candidates']}

TARGET JSON SCHEMA:
{schema}
"""
        # Generate and validate against the Pydantic model
        raw_model = self.llm.generate_and_validate(prompt=prompt, model_class=model_class)
        return model_class.model_validate(raw_model)



planner = LayoverPlanner()