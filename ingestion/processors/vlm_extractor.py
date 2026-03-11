"""
Ollama VLM image extractor for PDF image blocks.
"""

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "Extract all text visible in this image. "
    "If the image contains a diagram, chart, or figure, describe its content and key data points. "
    "Be concise and factual."
)


class OllamaVLMExtractor:
    """Extracts content from images using a locally-hosted Ollama vision model."""

    def __init__(self, base_url: str, model_name: str = "llama3.2-vision:11b", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def describe_image(self, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": _DEFAULT_PROMPT,
                    "images": [b64],
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.warning(f"VLM image extraction failed: {e}")
            return "[IMAGE]"
