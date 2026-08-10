import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class AIProvider:
    def __init__(self):
        self.provider = getattr(settings, "AI_PROVIDER", "groq").lower()
        self.api_key = getattr(settings, "AI_API_KEY", "")
        self.model = getattr(settings, "AI_MODEL", "openai/gpt-oss-20b")
        self.base_url = getattr(settings, "AI_BASE_URL", "https://api.groq.com/openai/v1").rstrip('/')

    def generate_response(self, messages, tools=None):
        if not self.api_key:
            logger.error("AI_API_KEY is not configured.")
            return {"error": "AI configuration error. Please contact support."}
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return {"error": "AI service is currently unavailable."}
