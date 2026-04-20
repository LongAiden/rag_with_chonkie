"""
LLM interaction logger.

Persists every query/answer cycle to llm_interactions (asyncpg) and
optionally forwards a generation span to Langfuse.

Token counts are owned exclusively here — Logfire handles status/errors only.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class InteractionPayload:
    question: str
    answer: str
    model: str
    backend: str
    latency_ms: int
    sources_used: int
    table_name: str
    rerank_method: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Langfuse — optional singleton
# ---------------------------------------------------------------------------

_langfuse_client = None
_langfuse_attempted = False


def _get_langfuse():
    global _langfuse_client, _langfuse_attempted
    if _langfuse_attempted:
        return _langfuse_client
    _langfuse_attempted = True
    try:
        host = os.environ.get("LANGFUSE_HOST")
        pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
        sk = os.environ.get("LANGFUSE_SECRET_KEY")
        if not (host and pk and sk):
            return None
        from langfuse import Langfuse
        _langfuse_client = Langfuse(public_key=pk, secret_key=sk, host=host)
        logger.info("Langfuse client initialised at %s", host)
    except ImportError:
        logger.info("langfuse package not installed — skipping Langfuse integration")
    except Exception as exc:
        logger.warning("Langfuse init failed (non-fatal): %s", exc)
    return _langfuse_client


# ---------------------------------------------------------------------------
# Core logger — called via asyncio.create_task() from search.py
# ---------------------------------------------------------------------------

async def log_interaction(payload: InteractionPayload, connection_string: str) -> None:
    """
    Fire-and-forget coroutine.
    1. INSERT into llm_interactions via asyncpg.
    2. Flush Langfuse generation span (if configured).
    Errors are swallowed so the query path is never affected.
    """
    # 1. Local DB persistence
    try:
        conn = await asyncpg.connect(connection_string)
        try:
            await conn.execute(
                """
                INSERT INTO llm_interactions (
                    session_id, question, answer, model, backend,
                    input_tokens, output_tokens, total_tokens,
                    latency_ms, sources_used, table_name, rerank_method
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                payload.session_id,
                payload.question,
                payload.answer,
                payload.model,
                payload.backend,
                payload.input_tokens,
                payload.output_tokens,
                payload.total_tokens,
                payload.latency_ms,
                payload.sources_used,
                payload.table_name,
                payload.rerank_method,
            )
        finally:
            await conn.close()
    except Exception as db_err:
        logger.error("llm_logger: DB insert failed (non-fatal): %s", db_err)

    # 2. Langfuse span
    lf = _get_langfuse()
    if lf is None:
        return
    try:
        import asyncio
        trace = lf.trace(
            name="rag_query",
            input=payload.question,
            output=payload.answer,
            session_id=payload.session_id,
            metadata={
                "table_name": payload.table_name,
                "rerank_method": payload.rerank_method,
            },
        )
        trace.generation(
            name="llm_generate",
            model=payload.model,
            input=payload.question,
            output=payload.answer,
            usage={
                "input": payload.input_tokens,
                "output": payload.output_tokens,
                "total": payload.total_tokens,
            },
            metadata={"backend": payload.backend, "latency_ms": payload.latency_ms},
        )
        await asyncio.get_event_loop().run_in_executor(None, lf.flush)
    except Exception as lf_err:
        logger.warning("llm_logger: Langfuse flush failed (non-fatal): %s", lf_err)
