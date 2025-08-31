# app/services/llm_client.py
from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError
from google import genai
from google.genai import types
from app.settings import settings


class LLMClient:
    def __init__(self):
        api_key = settings.GOOGLE_GENAI_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_GENAI_API_KEY is not set")
        self.client = genai.Client(api_key=api_key)

    def generate_json(
        self,
        *,
        prompt: str,
        schema: Dict[str, Any] | Type[BaseModel],
        model: str = "gemini-2.5-flash",
    ) -> str:
        """
        Ask Gemini for JSON by providing a schema. Returns raw JSON text.
        `schema` can be a JSON Schema dict (model.model_json_schema()) or a Pydantic model class.
        """
        resp = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        # With response_schema, Gemini returns JSON in `resp.text`
        return resp.text

    def generate_and_validate(
        self,
        *,
        prompt: str,
        model_class: Type[BaseModel],
        model: str = "gemini-2.5-flash",
    ) -> BaseModel:
        """
        Validate the raw JSON text returned by the LLM.
        """
        raw = self.generate_json(
            prompt=prompt,
            schema=model_class.model_json_schema(),
            model=model,
        )
        try:
            return model_class.model_validate_json(raw)
        except ValidationError:
            cleaned = raw.strip().strip("`")
            return model_class.model_validate_json(cleaned)
