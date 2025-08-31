# app/services/maps_service.py
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import googlemaps
from app.settings import settings


class MapsService:
    """
    High-level wrapper over googlemaps with:
      - pagination (Nearby & Text search)
      - broader discovery utilities
      - DM batching
      - safe param handling (rankby vs radius)
      - optional language/region filter
    """

    MAX_RADIUS_M = 50_000
    DM_CHUNK = 25

    def __init__(self) -> None:
        if not settings.GOOGLE_MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY must be set")
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

    def geocode(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            res = self.client.geocode(address, language=language, region=region)
            return res[0] if res else None
        except Exception as e:
            raise RuntimeError(f"Geocoding failed: {e}")

    def reverse_geocode(
        self,
        location: Tuple[float, float],
        *,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            res = self.client.reverse_geocode(location, language=language, region=region)
            return res[0] if res else None
        except Exception as e:
            raise RuntimeError(f"Reverse geocoding failed: {e}")

    def _paginate_places(
        self,
        api_callable,
        *,
        max_results: int = 60,
        page_sleep_s: float = 2.0,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generic paginator for places_nearby / places (Text Search).
        Google requires ~2s delay before next_page_token becomes active.
        """
        out: List[Dict[str, Any]] = []
        next_token: Optional[str] = None

        while True:
            if next_token:
                kwargs["page_token"] = next_token
                time.sleep(page_sleep_s)  # required by API

            resp = api_callable(**kwargs)
            out.extend(resp.get("results", []))

            next_token = resp.get("next_page_token")
            if not next_token or len(out) >= max_results:
                break

        # Trim to requested max
        return out[:max_results]

    @staticmethod
    def _dedupe_by_place_id(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen, out = set(), []
        for it in items:
            pid = it.get("place_id") or it.get("place", {}).get("place_id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            out.append(it)
        return out

    @staticmethod
    def _normalize_place_lite(p: Dict[str, Any]) -> Dict[str, Any]:
        loc = ((p.get("geometry") or {}).get("location") or {})
        return {
            "place_id": p.get("place_id"),
            "name": p.get("name"),
            "vicinity": p.get("vicinity") or p.get("formatted_address"),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("user_ratings_total"),
            "price_level": p.get("price_level"),
            "types": p.get("types") or [],
            "location": {"lat": loc.get("lat"), "lng": loc.get("lng")},
        }

    def nearby_places(
        self,
        *,
        location: Tuple[float, float],
        place_type: Optional[str] = None,
        keyword: Optional[str] = None,
        radius: Optional[int] = None,
        rankby: Optional[str] = None,       # 'prominence' (default) or 'distance'
        open_now: Optional[bool] = None,
        language: Optional[str] = None,
        region: Optional[str] = None,
        max_results: int = 60,
        normalize: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Paginated Nearby Search. If rankby='distance', radius must be omitted.
        One of (place_type, keyword, name) is required when rankby='distance'.
        """
        try:
            kwargs: Dict[str, Any] = dict(location=location, language=language)
            if region:
                kwargs["region"] = region
            if rankby:
                kwargs["rankby"] = rankby
            if radius is not None and not rankby:
                # enforce API max
                kwargs["radius"] = min(radius, self.MAX_RADIUS_M)
            if place_type:
                kwargs["type"] = place_type
            if keyword:
                kwargs["keyword"] = keyword
            if open_now is not None:
                kwargs["open_now"] = open_now

            results = self._paginate_places(
                self.client.places_nearby,
                max_results=max_results,
                **kwargs,
            )
            return [self._normalize_place_lite(r) for r in results] if normalize else results
        except Exception as e:
            raise RuntimeError(f"Nearby search failed: {e}")

    def text_search(
        self,
        *,
        query: str,
        location: Tuple[float, float],
        radius: int = 5000,
        open_now: Optional[bool] = None,
        language: Optional[str] = None,
        region: Optional[str] = None,
        max_results: int = 60,
        normalize: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Paginated Text Search (aka 'places' in googlemaps).
        """
        try:
            kwargs = dict(
                query=query,
                location=location,
                radius=min(radius, self.MAX_RADIUS_M),
                language=language,
            )
            if region:
                kwargs["region"] = region
            if open_now is not None:
                kwargs["open_now"] = open_now

            results = self._paginate_places(
                self.client.places,
                max_results=max_results,
                **kwargs,
            )
            return [self._normalize_place_lite(r) for r in results] if normalize else results
        except Exception as e:
            raise RuntimeError(f"Text search failed: {e}")

    def place_details(
        self,
        place_id: str,
        fields: Optional[List[str]] = None,
        *,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Places Details. If no fields specified, returns a rich default set.
        """
        try:
            fields = fields or [
                "place_id",
                "name",
                "formatted_address",
                "geometry/location",
                "rating",
                "user_ratings_total",
                "price_level",
                "opening_hours/open_now",
                "types",
                "url",
                "website",
                "international_phone_number",
            ]
            return self.client.place(place_id=place_id, fields=fields, language=language)
        except Exception as e:
            raise RuntimeError(f"Place details failed: {e}")

    def discover_broad_places(
        self,
        *,
        location: Tuple[float, float],
        radius_m: int,
        city_hint: Optional[str] = None,
        open_now: Optional[bool] = None,
        language: Optional[str] = None,
        region: Optional[str] = None,
        max_results: int = 60,
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None,
        normalize: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Broaden results by:
          - multiple Nearby queries by type (rankby=distance)
          - multiple Text searches by keyword (anchored with city name if provided)
          - merge + dedupe + sort by (rating, reviews)
        """
        nearby_types = [
            "shopping_mall",
            "park",
            "museum",
            "tourist_attraction",
            "art_gallery",
            "amusement_park",
            "zoo",
            "cafe",
            "restaurant",
        ]

        all_results: List[Dict[str, Any]] = []

        # Nearby ‘rankby=distance’ for quick breadth
        for t in nearby_types:
            try:
                res = self.nearby_places(
                    location=location,
                    place_type=t,
                    rankby="distance",
                    open_now=open_now,
                    language=language,
                    region=region,
                    max_results=max_results // 2,  # split budget
                    normalize=False,
                )
                all_results.extend(res)
            except Exception:
                # continue on partial errors
                pass

        # Text queries anchored to city label if provided
        city_term = f" in {city_hint}" if city_hint else ""
        text_queries = [
            f"boulevard{city_term}",
            f"front{city_term}",
            f"mall{city_term}",
            f"market{city_term}",
            f"souq{city_term}",
            f"heritage{city_term}",
            f"museum{city_term}",
            f"park{city_term}",
            f"family entertainment{city_term}",
            f"theme park{city_term}",
            f"food court{city_term}",
            f"coffee{city_term}",
            f"shawarma{city_term}",
        ]

        for q in text_queries:
            try:
                res = self.text_search(
                    query=q,
                    location=location,
                    radius=radius_m,
                    open_now=open_now,
                    language=language,
                    region=region,
                    max_results=max_results // 2,
                    normalize=False,
                )
                all_results.extend(res)
            except Exception:
                pass

        merged = self._dedupe_by_place_id(all_results)

        # filter by quality if requested
        if min_rating is not None or min_reviews is not None:
            tmp = []
            for r in merged:
                rating_ok = (r.get("rating") or 0) >= (min_rating or 0)
                reviews_ok = (r.get("user_ratings_total") or 0) >= (min_reviews or 0)
                if rating_ok and reviews_ok:
                    tmp.append(r)
            merged = tmp

        # sort by rating & review count
        merged.sort(
            key=lambda r: (r.get("rating", 0) or 0, r.get("user_ratings_total", 0) or 0),
            reverse=True,
        )

        results = merged[:max_results]
        return [self._normalize_place_lite(r) for r in results] if normalize else results

    def get_distances(
        self,
        *,
        origin: Tuple[float, float],
        destinations: List[Tuple[float, float]],
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return self.client.distance_matrix(
                origins=[origin],
                destinations=destinations,
                mode=mode,
                language=language,
                departure_time=departure_time or datetime.now(),
            )
        except Exception as e:
            raise RuntimeError(f"Distance matrix failed: {e}")

    def attach_travel_times(
        self,
        *,
        origin: Tuple[float, float],
        places: List[Dict[str, Any]],
        mode: str = "driving",
        departure_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Adds per-place _travel = {duration_min, distance_km} using DM in 25-destination batches.
        """
        for i in range(0, len(places), self.DM_CHUNK):
            batch = places[i : i + self.DM_CHUNK]

            dests: List[Tuple[float, float]] = []
            idx_map: List[int] = []
            for j, p in enumerate(batch):
                loc = ((p.get("geometry") or {}).get("location")) or (p.get("location"))
                if not loc:
                    continue
                lat, lng = loc.get("lat"), loc.get("lng")
                if lat is None or lng is None:
                    continue
                dests.append((lat, lng))
                idx_map.append(j)

            if not dests:
                continue

            dm = self.get_distances(
                origin=origin,
                destinations=dests,
                mode=mode,
                departure_time=departure_time,
            )
            elements = (dm.get("rows", [{}])[0] or {}).get("elements", [])

            for k, el in enumerate(elements):
                if el.get("status") != "OK":
                    continue
                dur = el.get("duration_in_traffic") or el.get("duration")
                dist = el.get("distance")
                travel = {
                    "duration_min": int(round((dur["value"] / 60))) if dur else None,
                    "distance_km": round((dist["value"] / 1000), 1) if dist else None,
                }
                batch_idx = idx_map[k]
                batch[batch_idx]["_travel"] = travel

        return places
