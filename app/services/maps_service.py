import googlemaps
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.settings import settings


class MapsService:
    """
    Service layer for Google Maps APIs.
    Provides high-level methods for geocoding, nearby search,
    distance calculations, and directions.
    """

    def __init__(self):
        if not settings.GOOGLE_MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY must be set")
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

    def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get latitude/longitude for an address.
        """
        try:
            results = self.client.geocode(address)
            return results[0] if results else None
        except Exception as e:
            raise RuntimeError(f"Geocoding failed: {e}")

    def reverse_geocode(
        self, location: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Get address from latitude/longitude.
        """
        try:
            results = self.client.reverse_geocode(location)
            return results[0] if results else None
        except Exception as e:
            raise RuntimeError(f"Reverse geocoding failed: {e}")

    def nearby_places(
        self,
        location: Tuple[float, float],
        radius: int = 5000,
        type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for nearby places.
        """
        try:
            results = self.client.places_nearby(
                location=location, radius=radius, type=type, keyword=keyword
            )
            return results.get("results", [])
        except Exception as e:
            raise RuntimeError(f"Nearby search failed: {e}")

    def get_distances(
        self,
        origin: Tuple[float, float],
        destinations: List[Tuple[float, float]],
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get travel time and distance between origin and multiple destinations.
        """
        try:
            response = self.client.distance_matrix(
                origins=[origin],
                destinations=destinations,
                mode=mode,
                departure_time=departure_time or datetime.now(),
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Distance matrix failed: {e}")

    def get_directions(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get directions between origin and destination.
        """
        try:
            response = self.client.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                departure_time=departure_time or datetime.now(),
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Directions failed: {e}")

    def place_details(self, place_id: str, fields: list[str] | None = None):
        """
        Get detailed information about a place.
        """
        try:
            response = self.client.place(place_id=place_id, fields=fields)
            return response
        except Exception as e:
            raise RuntimeError(f"Place details failed: {e}")
