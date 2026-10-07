import logging
import httpx
from backend.errors import LLMUnavailableError

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str = "", model: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key
        self.model = model

    def health_check(self) -> bool:
        if not self.api_key or not self.api_key.strip():
            return False
        # Try checking configured model, or fallback model
        test_models = [self.model, "gemini-3.5-flash-lite", "gemini-3.5-flash"]
        seen = set()
        for m in test_models:
            if m in seen:
                continue
            seen.add(m)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}?key={self.api_key}"
                with httpx.Client(timeout=5.0) as client:
                    res = client.get(url)
                    if res.status_code == 200:
                        return True
            except Exception:
                continue
        return False

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024
    ) -> str:
        if not self.api_key or not self.api_key.strip():
            raise LLMUnavailableError("Gemini API key not set")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\nUser Request:\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        # Candidate models to try in case of 503 (high demand) or 404 (deprecated model)
        candidate_models = [self.model]
        for m in ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-pro"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_error = ""
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            continue
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(part.get("text", "") for part in parts)
                        if text:
                            return text
                    elif res.status_code in {503, 404, 429}:
                        logger.warning("Gemini model %s returned %d, trying fallback...", model_name, res.status_code)
                        last_error = f"HTTP {res.status_code}: {res.text[:120]}"
                        continue
                    else:
                        raise LLMUnavailableError(
                            f"Gemini API returned HTTP {res.status_code}: {res.text[:200]}"
                        )
            except LLMUnavailableError:
                raise
            except Exception as e:
                last_error = str(e)
                continue

        raise LLMUnavailableError(f"Gemini generation failure across available models: {last_error}")

