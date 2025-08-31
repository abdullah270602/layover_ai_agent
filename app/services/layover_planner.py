# layover_planner.py
from typing import Dict, Any
from app.schemas.itinerary import ItineraryRequest
from app.services.constants import AIRPORTS
from app.services.maps_service import MapsService
from app.services.llm_client import LLMClient


class LayoverPlanner:
    def __init__(self):
        self.maps = MapsService()
        self.llm = LLMClient()

    def build_context(self, request: ItineraryRequest) -> Dict[str, Any]:
        """
        Fetch maps data around the airport and prepare context for the LLM.
        """
        # Step 1: Geocode airport
        airport_name = AIRPORTS.get(request.airport_code)
        if not airport_name:
            raise ValueError(f"Airport {request.airport_code} not found")
        
        airport_geo = self.maps.geocode(airport_name)
        if not airport_geo:
            raise ValueError(f"Could not geocode airport {request.airport_code}")
        airport_location = (
            airport_geo["geometry"]["location"]["lat"],
            airport_geo["geometry"]["location"]["lng"],
        )

        # Step 2: Find nearby attractions and restaurants
        attractions = self.maps.nearby_places(
            location=airport_location, radius=10000, type="tourist_attraction"
        )
        restaurants = self.maps.nearby_places(
            location=airport_location, radius=5000, type="restaurant"
        )

        # Step 3: Return structured context
        return {
            "airport": airport_geo.get("formatted_address"),
            "airport_code": request.airport_code,
            "arrival_time": request.arrival_time.isoformat(),
            "departure_time": request.departure_time.isoformat(),
            "layover_hours": request.layover_hours,
            "nationality": request.nationality,
            "nearby_attractions": [
                {"name": p["name"], "address": p.get("vicinity"), "rating": p.get("rating")}
                for p in attractions[:5]
            ],
            "nearby_restaurants": [
                {"name": p["name"], "address": p.get("vicinity"), "rating": p.get("rating")}
                for p in restaurants[:5]
            ],
        }

    def generate_itinerary(self, request: ItineraryRequest) -> str:
        """
        Build context and use the LLM to generate a natural-language itinerary.
        """
        context = self.build_context(request)

        prompt = f"""
        You are a smart layover trip planner. 
        The traveler has a {context['layover_hours']} hour layover at {context['airport']} ({context['airport_code']}).
        - Arrival: {context['arrival_time']}
        - Departure: {context['departure_time']}
        - Traveler nationality: {context['nationality']}

        Nearby attractions:
        {context['nearby_attractions']}

        Nearby restaurants:
        {context['nearby_restaurants']}

        Please create a detailed layover itinerary that fits within the layover window.
        Include transit time, recommended activities, meals, and when to return to the airport.
        """
        return self.llm.chat(prompt)
