import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("applyforme.omniroute")


class OmniRouteService:
    @staticmethod
    async def call_chat_completion(
        messages: List[Dict[str, str]],
        temperature: float = 0.4,
        response_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Call OmniRoute LLM Gateway using OpenAI-compatible chat completion endpoint.
        Uses configured model (Gemini, OpenAI, Groq, etc.).
        """
        if not settings.OMNIROUTE_API_KEY or settings.OMNIROUTE_API_KEY.startswith("dev-"):
            logger.info("Using mock/local AI engine because OMNIROUTE_API_KEY is unset or dev default.")
            return None

        url = f"{settings.OMNIROUTE_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OMNIROUTE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload: Dict[str, Any] = {
            "model": settings.OMNIROUTE_MODEL,
            "messages": messages,
            "temperature": temperature
        }

        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if response_json:
                    return json.loads(content)
                return {"content": content}
        except Exception as e:
            logger.error(f"OmniRoute API request failed: {e}")
            return None

