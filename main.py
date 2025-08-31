import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.routes.layover import router as layover_router

log = logging.getLogger()

ALLOWED_ORIGINS = [
    "https://uboorly-frontend.vercel.app/",
    "https://uboorly.com",
    "http://localhost:3000",
    "http://localhost:8000",
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Layover Planner API",
        version="1.0.0",
        description="Generates structured layover plans using Google Maps + Gemini."
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    app.include_router(layover_router)

    @app.get("/", tags=["meta"])
    def health():
        return {"ok": True}

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(_: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app

app = create_app()
