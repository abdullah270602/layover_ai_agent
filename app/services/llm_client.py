# llm_client.py
import os
from google import genai
from app.settings import settings



class LLMClient:
    def __init__(self):
        api_key = settings.GOOGLE_GENAI_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in environment variables")
        self.client = genai.Client(api_key=api_key)

    def chat(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
