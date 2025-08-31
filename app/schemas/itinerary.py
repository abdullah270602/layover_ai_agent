from typing import List, Optional, Literal, Annotated
from pydantic import BaseModel, Field, computed_field, constr

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


class ItineraryRequest(BaseModel):
    airport_code: str = Field(
        ...,
        description="IATA code of the arrival airport (3 uppercase letters)",
        min_length=3,
        max_length=3,
        example="RUH"
    )
    arrival_time: datetime = Field(
        ...,
        description="Arrival time in ISO 8601 format (UTC recommended)",
    )
    departure_time: datetime = Field(
        ...,
        description="Departure time in ISO 8601 format (UTC recommended)"
    )
    nationality: str = Field(
        ...,
        description="Nationality of the traveler (ISO 3166 country code recommended)",
        min_length=2,
        max_length=64,
    )

    # Validate airport code format
    @field_validator("airport_code")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("Airport code must be exactly 3 uppercase letters (IATA code)")
        return v

    # Validate that departure is later than arrival
    @field_validator("departure_time")
    @classmethod
    def validate_times(cls, v: datetime, info) -> datetime:
        arrival = info.data.get("arrival_time")
        if arrival and v <= arrival:
            raise ValueError("Departure time must be later than arrival time")
        return v

    @computed_field  #  makes it appear in dumps & schema
    @property
    def layover_hours(self) -> int:
        """Layover duration in hours (rounded down)."""
        return int((self.departure_time - self.arrival_time).total_seconds() // 3600)

    @computed_field
    @property
    def layover_minutes(self) -> int:
        """Layover duration in minutes."""
        return int((self.departure_time - self.arrival_time).total_seconds() // 60)


class RecommendedStop(BaseModel):
    """
    Represents a recommended activity or place to visit during a layover.
    """

    id: int = Field(1, description="Unique identifier for the stop", ge=1)
    title: Annotated[str, constr(min_length=3, max_length=100)] = Field(
        "Sample Stop", description="Name of the stop"
    )
    description: Annotated[str, constr(min_length=10, max_length=500)] = Field(
        "A short description of the recommended stop.",
        description="Brief description of the stop",
    )
    tags: Annotated[List[str], Field(min_length=1)] = Field(
        default_factory=lambda: ["sightseeing"],
        description="List of categories/tags e.g. ['food', 'sightseeing']",
    )
    opening_hours: Optional[str] = Field(
        "09:00-21:00", description="Opening hours in HH:MM-HH:MM format"
    )
    duration_range: Optional[str] = Field(
        ..., description="Estimated visit duration e.g. '30-60 min'"
    )
    cost: Optional[str] = Field(
        ..., description="Approximate cost e.g. 'Free', '$10-20'"
    )
    transport: Optional[Literal["walk", "metro", "bus", "taxi", "rideshare"]] = Field(
        ..., description="Primary mode of transport to reach the stop"
    )
    options: List[str] = Field(
        default_factory=lambda: ["Alternative option"],
        description="Alternative choices for the stop",
    )
    notes: Optional[str] = Field(
        "Best visited in the evening.", description="Extra notes, tips, or warnings"
    )


class BaggageStorage(BaseModel):
    """
    Information about baggage storage options at or near the airport.
    """

    title: str = Field("Airport Storage", description="Name of the storage service")
    location: str = Field(
        ..., description="Where it is located"
    )
    rate: str = Field(
        ..., description="Pricing info e.g. '$5/hour', '50 SAR/day'"
    )
    availability: str = Field(
        ..., description="Availability details e.g. '24/7', '06:00-22:00'"
    )


class LocalInsight(BaseModel):
    """
    Represents helpful cultural or practical information about the layover city.
    """

    title: str = Field("Cultural Tips", description="Title of the insight")
    content: List[str] = Field(
        default_factory=lambda: [
            "Dress modestly in public areas.",
            "Shops may close during prayer times.",
        ],
        description="List of insight points or cultural notes",
    )


class LayoverMetadata(BaseModel):
    """
    Metadata about the layover itself.
    """

    airport: str = Field("RUH", description="IATA code of the airport e.g. 'RUH'")
    layover_duration: str = Field(
        ..., description="Total layover time e.g. '8h 30m' or '12h'"
    )
    safety_buffer: str = Field(
        ..., description="Buffer time to return to airport e.g. '2h'"
    )
    must_return_by: str = Field(
        ..., description="Time by which passenger must return, in HH:MM"
    )
    current_time: str = Field(..., description="Current local time in HH:MM")


class LayoverPlan(BaseModel):
    """
    Full layover plan including stops, baggage, and cultural insights.
    """

    metadata: LayoverMetadata = Field(
        default_factory=LayoverMetadata,
        description="Layover metadata such as airport and timings",
    )
    recommended_stops: List[RecommendedStop] = Field(
        default_factory=lambda: [RecommendedStop()],
        description="List of recommended stops during layover",
    )
    baggage_storage: List[BaggageStorage] = Field(
        default_factory=lambda: [BaggageStorage()],
        description="Available baggage storage options",
    )
    local_insights: List[LocalInsight] = Field(
        default_factory=lambda: [LocalInsight()],
        description="Cultural tips or local insights",
    )
