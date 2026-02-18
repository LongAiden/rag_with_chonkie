"""
API routes for the RAG application.
FastAPI endpoints for upload, query, stats, health checks, and table management.
"""

import uuid
import logfire
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Header
from fastapi.responses import HTMLResponse

from api.config import DEFAULT_TABLE_NAME, DEFAULT_CHUNKING_SIMILARITY
from api.validators import (
    validate_upload_params,
    require_access_password,
    celery_upload_enabled
)
from retrieval.search import perform_document_search
# Lazy import to avoid circular dependency - imported in upload_and_process function
from api.templates import (
    HOME_PAGE_HTML,
    SEARCH_RESULTS_HTML,
    SEARCH_ERROR_HTML,
    STATS_PAGE_HTML,
    STATS_ERROR_HTML,
    HEALTH_CHECK_HTML,
    HEALTH_ERROR_HTML
)
from models.models import QueryRequest, UploadResponse, RAGResponse

# Create router
router = APIRouter()


async def get_pipeline_for_routes(table_name: str, get_pipeline_func):
    """Helper to get pipeline instance."""
    return await get_pipeline_func(table_name)


@router.get("/", response_class=HTMLResponse)
async def home():
    """Home page with upload and search forms."""
    return HOME_PAGE_HTML


@router.post("/upload", response_model=UploadResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    chunk_size: int = Form(512),
    table_name: str = Form("document_chunks"),
    access_password: Optional[str] = Form(None),
    x_app_password: Optional[str] = Header(default=None),
    # Dependencies injected by main app
    config=None,
    get_pipeline=None
):
    """Upload and process document with comprehensive validation and pgvector storage."""
    require_access_password(access_password or x_app_password)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate parameters
    validate_upload_params(chunk_size, file.content_type)

    # Generate unique document ID
    document_id = str(uuid.uuid4())
    processed_id = document_id
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{document_id}_{file.filename}"
    cleanup_temp = True

    try:
        # Write temporary file for validation
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Comprehensive file validation
        validation_result = config.file_validator.validate_file(str(temp_path))
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {validation_result.error_message}"
            )

        # Process with pgvector pipeline using specified table
        pipeline = await get_pipeline(table_name)

        if celery_upload_enabled():
            try:
                from worker.tasks import process_upload_task

                async_task = process_upload_task.apply_async(
                    kwargs={
                        "temp_path": str(temp_path),
                        "document_id": document_id,
                        "filename": file.filename,
                        "content_type": file.content_type or "application/octet-stream",
                        "file_size": validation_result.file_size,
                        "chunk_size": chunk_size,
                        "table_name": table_name,
                    }
                )

                logfire.info(
                    "Upload queued for Celery worker",
                    document_id=document_id,
                    filename=file.filename,
                    task_id=async_task.id,
                    table_name=table_name,
                )

                cleanup_temp = False  # worker will remove the temp file

                return UploadResponse(
                    status="queued",
                    document_id=document_id,
                    filename=file.filename,
                    message=f"Upload queued for processing. Task {async_task.id}",
                    chunks_created=None,
                    task_id=async_task.id,
                )
            except Exception as celery_error:
                logfire.warning(
                    "Celery upload dispatch failed; running inline",
                    document_id=document_id,
                    filename=file.filename,
                    error=str(celery_error),
                    table_name=table_name,
                )

        with logfire.span("document_insertion",
                          document_id=document_id,
                          filename=file.filename,
                          chunk_size=chunk_size,
                          table_name=table_name):
            logfire.info("Starting document processing",
                         document_id=document_id,
                         filename=file.filename,
                         file_size=validation_result.file_size)

            processed_id = await pipeline.ingest_document(
                file_path=str(temp_path),
                chunk_size=chunk_size,
                similarity_threshold=DEFAULT_CHUNKING_SIMILARITY,
                document_id=document_id,
                metadata={
                    'filename': file.filename,
                    'content_type': file.content_type,
                    'file_size': validation_result.file_size,
                    'upload_timestamp': str(uuid.uuid1().time),
                    'validation_passed': True
                }
            )

            logfire.info("Document processing completed successfully",
                         document_id=processed_id,
                         filename=file.filename)

        logfire.info("Upload and processing pipeline completed",
                     document_id=processed_id,
                     filename=file.filename)

        return UploadResponse(
            status="success",
            document_id=processed_id,
            filename=file.filename,
            message="Document processed successfully.",
            chunks_created=None,
            task_id=None
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )
    finally:
        # Cleanup temporary file
        if cleanup_temp:
            temp_path.unlink(missing_ok=True)


@router.post("/query", response_model=RAGResponse)
async def query_documents(
    request: QueryRequest,
    x_app_password: Optional[str] = Header(default=None),
    # Dependencies injected by main app
    config=None,
    get_pipeline=None
):
    """Query documents using pgvector similarity search + LLM generation with optional reranking."""
    require_access_password(x_app_password)
    try:
        pipeline = await get_pipeline(DEFAULT_TABLE_NAME)
        result = await perform_document_search(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
            pipeline=pipeline,
            config=config,
            document_ids=request.document_ids,
            table_name=DEFAULT_TABLE_NAME
        )
        # Return the structured RAGResponse directly
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/query-form", response_class=HTMLResponse)
async def query_documents_form(
    query: str = Form(...),
    limit: int = Form(5),
    threshold: float = Form(0.7),
    table_name: str = Form(DEFAULT_TABLE_NAME),
    access_password: Optional[str] = Form(None),
    # Dependencies injected by main app
    config=None,
    get_pipeline=None
):
    """Query documents using form data (for HTML form submission) with optional reranking."""
    require_access_password(access_password)
    try:
        pipeline = await get_pipeline(table_name)
        result = await perform_document_search(
            query=query,
            limit=limit,
            threshold=threshold,
            pipeline=pipeline,
            config=config,
            document_ids=None,
            table_name=table_name
        )

        # Build sources HTML with optional BM25 rerank scores
        sources_html = ''.join([f"""
        <div class="source-item">
            <strong>Source {i+1}</strong> (Similarity: {source.similarity:.1%}{"" if source.rerank_score is None else f", BM25: {source.rerank_score:.3f}"})<br>
            <em>Document: {source.document_id[:8]}... | Page: {source.page_number or 'N/A'}</em><br><br>
            <div style="white-space: pre-wrap; word-wrap: break-word;">{source.text}</div>
        </div>
        """ for i, source in enumerate(result.sources)])

        # Use template with substitutions
        html_content = SEARCH_RESULTS_HTML.format(
            query=query,
            answer=result.answer,
            source_count=len(result.sources),
            sources_html=sources_html,
            chunks_found=result.search_stats.chunks_found,
            avg_similarity=f"{result.search_stats.avg_similarity:.1%}",
            search_method=result.search_stats.search_method,
            table_used=result.table_used,
            threshold_used=f"{result.search_stats.threshold_used:.1%}",
            confidence=f"{result.search_stats.confidence:.1%}" if result.search_stats.confidence else "N/A",
            word_count=result.search_stats.word_count or 0,
            graph_enriched="Yes" if result.search_stats.graph_enriched else "No"
        )

        return html_content

    except Exception as e:
        # Check if it's a rate limit error and provide helpful message
        error_msg = str(e)
        if any(indicator in error_msg.lower() for indicator in ["rate limit", "quota exceeded", "429", "resource exhausted"]):
            error_msg = (
                f"⚠️ API Rate Limit Reached\n\n"
                f"The Gemini API rate limit has been exceeded. This typically happens during entity extraction.\n\n"
                f"Please try again in a minute or two.\n\n"
                f"Technical details: {error_msg}"
            )

        # Return error page using template
        return SEARCH_ERROR_HTML.format(error_message=error_msg)


@router.get("/stats", response_class=HTMLResponse)
async def get_database_stats(get_pipeline=None):
    """Get database statistics from ALL chunk tables."""
    try:
        # Get default pipeline for connection
        pipeline = await get_pipeline(DEFAULT_TABLE_NAME)
        conn = await pipeline.vector_store._get_connection()

        try:
            # Find all tables with chunk structure (id, document_id, text, embedding columns)
            tables = await conn.fetch("""
                SELECT DISTINCT t1.table_name
                FROM information_schema.columns t1
                WHERE t1.table_schema = 'public'
                AND t1.column_name = 'document_id'
                AND EXISTS (
                    SELECT 1 FROM information_schema.columns t2
                    WHERE t2.table_name = t1.table_name
                    AND t2.table_schema = 'public'
                    AND t2.column_name = 'embedding'
                )
                AND t1.table_name NOT IN ('entities', 'relationships', 'entity_nodes', 'entity_edges')
                ORDER BY t1.table_name
            """)

            table_names = [row['table_name'] for row in tables]

            print(
                f"\n📊 Found chunk tables: {', '.join(table_names) if table_names else 'none'}")

            if not table_names:
                # No chunk tables found, use default
                stats = await pipeline.get_stats()
                table_display = pipeline.vector_store.table_name
            else:
                # Aggregate stats from all chunk tables
                total_docs = 0
                total_chunks = 0
                total_text_length = 0
                earliest = None
                latest = None

                for table_name in table_names:
                    result = await conn.fetchrow(f"""
                        SELECT
                            COUNT(DISTINCT document_id) as docs,
                            COUNT(*) as chunks,
                            COALESCE(SUM(LENGTH(text)), 0) as total_length,
                            MIN(created_at) as earliest,
                            MAX(created_at) as latest
                        FROM {table_name}
                    """)

                    total_docs += result['docs'] or 0
                    total_chunks += result['chunks'] or 0
                    total_text_length += result['total_length'] or 0

                    print(
                        f"  {table_name}: {result['docs']} docs, {result['chunks']} chunks")

                    if result['earliest'] and (earliest is None or result['earliest'] < earliest):
                        earliest = result['earliest']
                    if result['latest'] and (latest is None or result['latest'] > latest):
                        latest = result['latest']

                stats = {
                    'total_documents': total_docs,
                    'total_chunks': total_chunks,
                    'avg_text_length': total_text_length / total_chunks if total_chunks > 0 else 0,
                    'earliest_chunk': earliest,
                    'latest_chunk': latest
                }

                table_display = f"ALL TABLES ({len(table_names)} tables)"
                print(
                    f"📊 TOTAL: {total_docs} documents, {total_chunks} chunks\n")

            # Use template with substitutions
            return STATS_PAGE_HTML.format(
                total_documents=f"{stats['total_documents']:,}",
                total_chunks=f"{stats['total_chunks']:,}",
                avg_text_length=f"{stats['avg_text_length']:.0f}",
                avg_chunks_per_doc=f"{stats['total_chunks'] // max(stats['total_documents'], 1):.0f}",
                embedding_model=pipeline.embedding_generator.model_name,
                embedding_dim=pipeline.embedding_generator.embedding_dim,
                table_name=table_display,
                earliest_chunk=str(
                    stats['earliest_chunk']) if stats['earliest_chunk'] else 'No documents yet',
                latest_chunk=str(
                    stats['latest_chunk']) if stats['latest_chunk'] else 'No documents yet'
            )

        finally:
            await conn.close()

    except Exception as e:
        print(f"❌ Stats error: {str(e)}")
        import traceback
        traceback.print_exc()
        return STATS_ERROR_HTML.format(error_message=str(e))


@router.get("/health", response_class=HTMLResponse)
async def health_check(get_pipeline=None):
    """Health check endpoint to verify system status."""
    try:
        pipeline = await get_pipeline(DEFAULT_TABLE_NAME)
        stats = await pipeline.get_stats()

        # Check database connection
        db_status = "healthy" if stats['total_chunks'] >= 0 else "error"
        status_icon = "✅" if db_status == "healthy" else "❌"
        status_color = "#28a745" if db_status == "healthy" else "#dc3545"

        html_content = HEALTH_CHECK_HTML.format(
            status_color=status_color,
            status_icon=status_icon,
            db_status_upper=db_status.upper(),
            embedding_model=pipeline.embedding_generator.model_name,
            table_name=pipeline.vector_store.table_name,
            total_documents=f"{stats['total_documents']:,}",
            total_chunks=f"{stats['total_chunks']:,}",
            embedding_dim=pipeline.embedding_generator.embedding_dim,
            avg_text_length=f"{stats['avg_text_length']:.0f}",
            timestamp=str(uuid.uuid1().time)
        )
        return html_content

    except Exception as e:
        return HEALTH_ERROR_HTML.format(error_message=str(e))


@router.get("/supported-types")
async def get_supported_types(config=None):
    """Get information about supported file types and validation config (using processor registry)."""
    from ingestion.processors.page_utils import get_page_number_for_position, get_supported_file_types, list_available_processors

    # Get supported types from processor registry (dynamic based on registered processors)
    supported_extensions = get_supported_file_types()
    processors = list_available_processors()

    return {
        "supported_extensions": supported_extensions,
        "max_file_size_mb": config.file_validator.config.max_file_size_mb,
        "supported_types": [ext.replace('.', '') for ext in supported_extensions],
        "registered_processors": [str(processor) for processor in processors],
        "vector_store_info": {
            "embedding_model": "all-MiniLM-L6-v2",
            "database_backend": "PostgreSQL + pgvector",
            "chunking_method": "semantic_chunking_with_chonkie",
            "processor_pattern": "Abstract Method + Factory Method"
        }
    }


@router.delete("/table/{table_name}")
async def delete_table(table_name: str, config=None, get_pipeline=None):
    """Delete a specific table from the database (optimized for speed)."""
    with logfire.span("table_deletion", table_name=table_name):
        logfire.info("Starting table deletion", table_name=table_name)

        try:
            pipeline_instance = await get_pipeline(table_name)

            # Get connection and delete table quickly
            conn = await pipeline_instance.vector_store._get_connection()
            row_count = 0

            with logfire.span("table_existence_check"):
                # Check if table exists and get approximate row count in one query
                result = await conn.fetchrow("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = $1
                    ) as table_exists,
                    COALESCE((
                        SELECT reltuples::bigint
                        FROM pg_catalog.pg_class
                        WHERE relname = $1
                    ), 0) as estimated_rows;
                """, table_name)

                table_exists = result['table_exists']
                # Approximate count (much faster)
                row_count = result['estimated_rows']

                logfire.info("Table existence check completed",
                             table_exists=table_exists,
                             estimated_rows=row_count)

            if not table_exists:
                await conn.close()
                logfire.warn("Table deletion failed - table does not exist",
                             table_name=table_name)
                raise HTTPException(
                    status_code=404,
                    detail=f"Table '{table_name}' does not exist"
                )

            with logfire.span("table_data_deletion"):
                # Two-step ultra-fast deletion: TRUNCATE then DROP
                # Step 1: Instant data removal (no WAL overhead)
                await conn.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
                logfire.info("Table data truncated successfully",
                             table_name=table_name,
                             rows_deleted=row_count)

            with logfire.span("table_schema_deletion"):
                # Step 2: Clean schema removal
                await conn.execute(f"DROP TABLE {table_name} CASCADE;")
                logfire.info("Table schema dropped successfully",
                             table_name=table_name)

            await conn.close()

            # Reset pipeline if we deleted the current table
            if table_name == pipeline_instance.vector_store.table_name:
                config.pipeline = None
                logfire.info("Pipeline reset due to current table deletion",
                             table_name=table_name)

            logfire.info("Table deletion completed successfully",
                         table_name=table_name,
                         estimated_rows_deleted=row_count)

            return {
                "status": "success",
                "message": f"Table '{table_name}' deleted successfully",
                "table_name": table_name,
                "estimated_rows_deleted": row_count,
                "timestamp": str(uuid.uuid1().time)
            }

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logfire.error("Table deletion failed with unexpected error",
                          table_name=table_name,
                          error=str(e),
                          error_type=type(e).__name__)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete table '{table_name}': {str(e)}"
            )
