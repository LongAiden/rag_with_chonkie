"""
LLM operations for the RAG application.
Handles LLM-based response generation with fallback mechanisms.
"""

import os
import logfire

from models.models import SimpleRAGResponse
from ingestion.processors.prompts import OLLAMA_RAG_PROMPT_TEMPLATE


class OllamaBackend:
    def __init__(self, model: str):
        self.model = model

    async def generate(self, query: str, context: str, results: list, _agent=None) -> SimpleRAGResponse:
        import httpx
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
        prompt = OLLAMA_RAG_PROMPT_TEMPLATE.format(context=context, query=query)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ollama_base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
            if resp.status_code != 200:
                body = resp.text
                print(f"Ollama error {resp.status_code}: {body}", flush=True)
                resp.raise_for_status()
            data = resp.json()
            answer = data["response"]
            input_tokens = data.get("prompt_eval_count")
            output_tokens = data.get("eval_count")
            total_tokens = (input_tokens or 0) + (output_tokens or 0) or None
        return SimpleRAGResponse(
            answer=answer,
            confidence=None,
            word_count=len(answer.split()),
            sources_used=len(results),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            metadata={"method": "ollama", "model": self.model}
        )


class GeminiBackend:
    def __init__(self, model: str):
        self.model = model
        self._agent = None  # lazy init

    async def generate(self, query: str, context: str, results: list, _agent=None) -> SimpleRAGResponse:
        import google.generativeai as genai

        sources_used = len(results)

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")

        genai.configure(api_key=api_key)

        # Build deduplicated context: one entry per unique (document, page).
        seen_pages: dict = {}
        for result in results:
            meta = result.get('metadata') or {}
            doc_id = result.get('document_id', '')
            page_num = meta.get('page_number')
            page_key = (doc_id, page_num if page_num is not None else 'full')
            if page_key in seen_pages:
                continue
            content = (meta.get('full_content') or '').strip()
            label = f"Page {page_num}" if page_num is not None else "Document"
            seen_pages[page_key] = (label, content)

        context_parts = [
            f"[{label}]:\n{content}"
            for label, content in seen_pages.values()
            if content
        ]
        rich_context = "\n\n---\n\n".join(context_parts) or context

        prompt = f"""You are a RAG assistant. Answer the question using ONLY the provided sources.
Cite sources and page numbers when available.

Context:
{rich_context}

Question: {query}

Answer:"""

        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            answer = response.text

            usage = response.usage_metadata
            input_tokens = getattr(usage, 'prompt_token_count', None)
            output_tokens = getattr(usage, 'candidates_token_count', None)
            total_tokens = getattr(usage, 'total_token_count', None)

            logfire.info("Gemini response generated",
                        model=self.model, input_tokens=input_tokens,
                        output_tokens=output_tokens, sources_used=sources_used)

            return SimpleRAGResponse(
                answer=answer,
                confidence=0.9,
                word_count=len(answer.split()),
                sources_used=sources_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                metadata={"method": "gemini", "model": self.model}
            )
        except Exception as llm_error:
            logfire.error("Gemini generation failed", error=str(llm_error), model=self.model)
            print(f"Gemini failed: {llm_error}", flush=True)
            raise


def _get_backend(model: str) -> OllamaBackend | GeminiBackend:
    if model.startswith("gemini-"):
        return GeminiBackend(model)
    return OllamaBackend(model)


async def generate_llm_response(
    query: str,
    context: str,
    results: list,
    agent,
    model: str = "gemini-2.5-flash",
) -> SimpleRAGResponse:
    backend = _get_backend(model)
    return await backend.generate(query, context, results, agent)
