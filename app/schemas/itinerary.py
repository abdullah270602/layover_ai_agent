from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
import re


from datetime import datetime
from pydantic import BaseModel, Field, field_validator
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
        example="2025-09-01T10:00:00Z"
    )
    departure_time: datetime = Field(
        ...,
        description="Departure time in ISO 8601 format (UTC recommended)",
        example="2025-09-01T18:00:00Z"
    )
    nationality: str = Field(
        ...,
        description="Nationality of the traveler (ISO 3166 country code recommended)",
        min_length=2,
        max_length=64,
        example="Pakistani"
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
        arrival = info.data.get("arrival_time")  # ✅ use info.data in Pydantic v2
        if arrival and v <= arrival:
            raise ValueError("Departure time must be later than arrival time")
        return v

    @property
    def layover_hours(self) -> int:
        return int((self.departure_time - self.arrival_time).total_seconds() // 3600)

