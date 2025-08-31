from fastapi import APIRouter,HTTPException, Query
from pydantic import ValidationError

from app.schemas.itinerary import ItineraryRequest, LayoverPlan
from app.services.layover_planner import planner

router = APIRouter(prefix="/v1/layover", tags=["layover"])

@router.post("/plan", response_model=LayoverPlan, summary="Generate a layover plan")
def generate_layover_plan(
    payload: ItineraryRequest,
    include_debug: bool = Query(False, description="If true, returns { plan, debug_ctx }"),
):
    """
    Given arrival/departure and airport, returns a structured LayoverPlan.
    """
    try:
        if include_debug:
            ctx = planner.build_context(payload)
            plan = planner.generate_itinerary_plan(payload)
            return {"plan": plan, "debug_ctx": ctx}  # FastAPI will serialize LayoverPlan ok
        else:
            return planner.generate_itinerary_plan(payload)
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Planner error: {ex}")
