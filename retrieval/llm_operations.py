"""
LLM operations for the RAG application.
Handles LLM-based response generation with fallback mechanisms.
"""

import logfire

from models.models import SimpleRAGResponse
from ingestion.processors.prompts import OLLAMA_RAG_PROMPT_TEMPLATE


class OllamaBackend:
    def __init__(self, model: str):
        self.model = model

    async def generate(self, query: str, context: str, results: list, _agent=None) -> SimpleRAGResponse:
        import httpx
        prompt = OLLAMA_RAG_PROMPT_TEMPLATE.format(context=context, query=query)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
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

    async def generate(self, query: str, context: str, results: list, agent) -> SimpleRAGResponse:
        sources_used = len(results)

        with logfire.span("llm_response_generation",
                         query=query[:100],
                         sources_used=sources_used,
                         context_length=len(context)):

            logfire.info("Starting LLM response generation",
                        query_length=len(query),
                        context_length=len(context),
                        sources_used=sources_used)

            try:
                if agent is None:
                    raise Exception(
                        "Pydantic AI Agent is not configured - missing GOOGLE_API_KEY or configuration failed"
                    )

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

                user_message = f"""Context from documents:
{rich_context}

User Question: {query}

Sources used: {sources_used}"""

                response = await agent.run(user_message)

                usage = response.usage()
                input_tokens = usage.request_tokens
                output_tokens = usage.response_tokens
                total_tokens = usage.total_tokens

                if hasattr(response, 'output') and isinstance(response.output, SimpleRAGResponse):
                    if response.output.sources_used != sources_used:
                        response.output.sources_used = sources_used
                    response.output.input_tokens = input_tokens
                    response.output.output_tokens = output_tokens
                    response.output.total_tokens = total_tokens

                    logfire.info("LLM response generated successfully",
                                word_count=response.output.word_count,
                                confidence=response.output.confidence,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=total_tokens,
                                method="pydantic_ai_agent")
                    return response.output
                else:
                    answer_text = response.output if hasattr(response, 'output') else str(response)
                    logfire.warn("Unexpected response structure, using fallback",
                                response_type=type(response).__name__)
                    return SimpleRAGResponse(
                        answer=answer_text,
                        confidence=0.8,
                        word_count=len(answer_text.split()),
                        sources_used=sources_used,
                        metadata={"method": "pydantic_ai_agent_fallback", "model": self.model}
                    )

            except Exception as llm_error:
                logfire.error("LLM generation failed, using fallback",
                             error=str(llm_error),
                             error_type=type(llm_error).__name__)
                print(f"Pydantic AI Agent failed: {llm_error}")
                fallback_answer = f"LLM generation failed ({str(llm_error)}), but found {len(results)} relevant chunks:\n\n"
                for i, result in enumerate(results[:3]):
                    fallback_answer += f"{i+1}. {result['text'][:300]}...\n\n"
                return SimpleRAGResponse(
                    answer=fallback_answer,
                    confidence=0.3,
                    word_count=len(fallback_answer.split()),
                    sources_used=sources_used,
                    metadata={
                        "fallback_reason": str(llm_error),
                        "method": "pydantic_ai_fallback"
                    }
                )


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
