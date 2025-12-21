"""
LLM operations for the RAG application.
Handles LLM-based response generation with fallback mechanisms.
"""

import logfire
from typing import List

from document_processing.config import get_gemini_model
from models.models import SimpleRAGResponse


async def generate_llm_response(
    query: str,
    context: str,
    results: list,
    agent
) -> SimpleRAGResponse:
    """
    Generate LLM response using Pydantic AI Agent or fallback.

    Args:
        query: User's search query
        context: Concatenated context from retrieved chunks
        results: List of search results
        agent: Pydantic AI Agent instance (from config)

    Returns:
        SimpleRAGResponse with answer, confidence, word count, and metadata
    """
    # Calculate metadata
    sources_used = len(results)
    gemini_model = get_gemini_model()

    with logfire.span("llm_response_generation",
                     query=query[:100],  # Truncate long queries
                     sources_used=sources_used,
                     context_length=len(context)):

        logfire.info("Starting LLM response generation",
                    query_length=len(query),
                    context_length=len(context),
                    sources_used=sources_used)

        try:
            # Check if agent is configured
            if agent is None:
                raise Exception(
                    "Pydantic AI Agent is not configured - missing GOOGLE_API_KEY or configuration failed"
                )

            # Use Pydantic AI Agent for structured response with proper user message
            user_message = f"""Context from documents:
{context}

User Question: {query}

Sources used: {sources_used}"""

            response = await agent.run(user_message)

            # The agent now returns a structured SimpleRAGResponse directly
            if hasattr(response, 'output') and isinstance(response.output, SimpleRAGResponse):
                # Update sources_used if not set correctly by the model
                if response.output.sources_used != sources_used:
                    response.output.sources_used = sources_used

                logfire.info("LLM response generated successfully",
                            word_count=response.output.word_count,
                            confidence=response.output.confidence,
                            method="pydantic_ai_agent")

                return response.output
            else:
                # Fallback if response structure is unexpected
                answer_text = response.output if hasattr(response, 'output') else str(response)

                logfire.warn("Unexpected response structure, using fallback",
                            response_type=type(response).__name__)

                return SimpleRAGResponse(
                    answer=answer_text,
                    confidence=0.8,
                    word_count=len(answer_text.split()),
                    sources_used=sources_used,
                    metadata={"method": "pydantic_ai_agent_fallback", "model": gemini_model}
                )

        except Exception as llm_error:
            logfire.error("LLM generation failed, using fallback",
                         error=str(llm_error),
                         error_type=type(llm_error).__name__)

            print(f"Pydantic AI Agent failed: {llm_error}")
            # Fallback to basic structured response
            fallback_answer = f"LLM generation failed ({str(llm_error)}), but found {len(results)} relevant chunks:\n\n"
            for i, result in enumerate(results[:3]):
                fallback_answer += f"{i+1}. {result['text'][:300]}...\n\n"

            return SimpleRAGResponse(
                answer=fallback_answer,
                confidence=0.3,  # Low confidence due to fallback
                word_count=len(fallback_answer.split()),
                sources_used=sources_used,
                metadata={
                    "fallback_reason": str(llm_error),
                    "method": "pydantic_ai_fallback"
                }
            )
