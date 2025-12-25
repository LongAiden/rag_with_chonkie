"""
Celery task definitions for long-running jobs.
Currently supports offloading entity extraction so API requests stay responsive.
"""

import asyncio
import os
import uuid
from typing import Any, Dict, List
from pathlib import Path

from worker.celery_app import celery_app


async def _run_entity_extraction(document_id: str, table_name: str) -> Dict[str, Any]:
    # Import inside the task to avoid loading FastAPI app when the worker starts.
    from api.app import (
        run_entity_extraction_for_document,
    )

    return await run_entity_extraction_for_document(
        document_id=document_id,
        filename=None,
        table_name=table_name,
    )


@celery_app.task(name="worker.tasks.run_entity_extraction")
def run_entity_extraction_task(
    document_id: str, table_name: str | None = None
) -> Dict[str, Any]:
    """
    Extract graph entities/relationships for a document asynchronously.
    """
    target_table = table_name or os.getenv("DEFAULT_TABLE_NAME", "document_chunks")
    return asyncio.run(_run_entity_extraction(document_id, target_table))


async def _process_upload(
    temp_path: str,
    document_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    chunk_size: int,
    table_name: str,
) -> Dict[str, Any]:
    """
    Process an uploaded document end-to-end inside Celery:
    - validate file
    - embed chunks and store
    - run entity extraction inline
    """
    from api.app import (
        DEFAULT_CHUNKING_SIMILARITY,
        config,
        get_pipeline,
        run_entity_extraction_for_document,
        validate_upload_params,
    )

    validate_upload_params(chunk_size, content_type)
    validation_result = config.file_validator.validate_file(temp_path)
    if not validation_result.is_valid:
        return {
            "status": "error",
            "detail": f"File validation failed: {validation_result.error_message}",
        }

    pipeline = await get_pipeline(table_name)
    processed_id = await pipeline.process_document(
        file_path=temp_path,
        chunk_size=chunk_size,
        similarity_threshold=DEFAULT_CHUNKING_SIMILARITY,
        document_id=document_id,
        metadata={
            "filename": filename,
            "content_type": content_type,
            "file_size": file_size,
            "upload_timestamp": str(uuid.uuid1().time),
            "validation_passed": True,
        },
    )

    extraction_summary = await run_entity_extraction_for_document(
        document_id=processed_id,
        filename=filename,
        table_name=table_name,
    )

    # Cleanup temp file
    try:
        Path(temp_path).unlink(missing_ok=True)
    except Exception:
        pass

    return {
        "status": extraction_summary.get("status", "completed"),
        "document_id": processed_id,
        "entities_extracted": extraction_summary.get("entities_extracted", 0),
        "relationships_extracted": extraction_summary.get("relationships_extracted", 0),
        "task_id": None,
        "detail": "Upload and extraction completed",
    }


@celery_app.task(name="worker.tasks.process_upload")
def process_upload_task(
    temp_path: str,
    document_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    chunk_size: int,
    table_name: str,
) -> Dict[str, Any]:
    """Celery task wrapper for end-to-end upload processing."""
    return asyncio.run(
        _process_upload(
            temp_path=temp_path,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            chunk_size=chunk_size,
            table_name=table_name,
        )
    )


async def _process_upload_batch(file_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Batch processing helper for future multi-upload support.
    Each item in file_items should contain the same keys as process_upload_task kwargs.
    """
    results = []
    for item in file_items:
        result = await _process_upload(
            temp_path=item["temp_path"],
            document_id=item["document_id"],
            filename=item["filename"],
            content_type=item.get("content_type") or "application/octet-stream",
            file_size=item.get("file_size") or 0,
            chunk_size=item.get("chunk_size") or 512,
            table_name=item.get("table_name") or "document_chunks",
        )
        results.append(result)
    return results


@celery_app.task(name="worker.tasks.batch_process_uploads")
def batch_process_uploads_task(file_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Celery task for batch uploads (preparation for future multi-upload feature).
    Expects a list of dicts with the same fields as process_upload_task kwargs.
    """
    return asyncio.run(_process_upload_batch(file_items))


def enqueue_batch_uploads(file_items: List[Dict[str, Any]]):
    """
    Convenience wrapper to enqueue batch uploads from callers.
    Usage example:
        task = enqueue_batch_uploads(file_items)
    """
    return batch_process_uploads_task.apply_async(kwargs={"file_items": file_items})
