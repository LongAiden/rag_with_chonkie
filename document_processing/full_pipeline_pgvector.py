"""
Main FastAPI application for RAG (Retrieval-Augmented Generation) system.
Integrates vector search, knowledge graphs, and LLM generation.

This module serves as the entry point and orchestrator for the entire RAG pipeline.
Core functionality is distributed across specialized modules:
- config.py: Configuration and environment management
- validators.py: Request validation and authentication
- retrieval.py: Document search and graph enrichment
- llm_operations.py: LLM-based response generation
- extraction_flow.py: Entity extraction orchestration
- api_routes.py: FastAPI endpoint definitions
- utils.py: BM25 reranking and utilities
"""

from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, Header
from fastapi.responses import HTMLResponse

from document_processing.config import AppConfig, DEFAULT_TABLE_NAME, DEFAULT_EMBEDDING_MODEL
from document_processing.embed_chunks_to_db import ChunkEmbeddingPipeline
from models.models import QueryRequest, UploadResponse, RAGResponse

# Initialize FastAPI application
app = FastAPI(title="pgvector RAG API", version="1.0.0")

# Register graph routes
from api.graph_routes import router as graph_router
app.include_router(graph_router)

# Global configuration
config = AppConfig()


async def get_pipeline(table_name: str = DEFAULT_TABLE_NAME):
    """
    Get or create ChunkEmbeddingPipeline for the specified table.
    Implements lazy initialization pattern for performance.

    Args:
        table_name: Database table name for chunk storage

    Returns:
        ChunkEmbeddingPipeline instance
    """
    if config.pipeline is None or config.pipeline.vector_store.table_name != table_name:
        config.pipeline = ChunkEmbeddingPipeline(
            db_params=config.db_params,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            table_name=table_name
        )
        # Initialize the database for the new pipeline
        await config.pipeline.vector_store._initialize_database()
    return config.pipeline


# Import route handlers from api_routes module
from document_processing.api_routes import (
    home,
    upload_and_process,
    query_documents,
    query_documents_form,
    get_database_stats,
    health_check,
    get_supported_types,
    delete_table
)


# Re-register routes with dependency injection
@app.get("/", response_class=HTMLResponse)
async def home_route():
    return await home()


@app.post("/upload", response_model=UploadResponse)
async def upload_route(
    file: UploadFile = File(...),
    chunk_size: int = Form(512),
    table_name: str = Form("document_chunks"),
    access_password: Optional[str] = Form(None),
    x_app_password: Optional[str] = Header(default=None),
):
    return await upload_and_process(
        file=file,
        chunk_size=chunk_size,
        table_name=table_name,
        access_password=access_password,
        x_app_password=x_app_password,
        config=config,
        get_pipeline=get_pipeline
    )


@app.post("/query", response_model=RAGResponse)
async def query_route(
    request: QueryRequest,
    x_app_password: Optional[str] = Header(default=None),
):
    return await query_documents(
        request=request,
        x_app_password=x_app_password,
        config=config,
        get_pipeline=get_pipeline
    )


@app.post("/query-form", response_class=HTMLResponse)
async def query_form_route(
    query: str = Form(...),
    limit: int = Form(5),
    threshold: float = Form(0.7),
    table_name: str = Form(DEFAULT_TABLE_NAME),
    access_password: Optional[str] = Form(None),
):
    return await query_documents_form(
        query=query,
        limit=limit,
        threshold=threshold,
        table_name=table_name,
        access_password=access_password,
        config=config,
        get_pipeline=get_pipeline
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats_route():
    return await get_database_stats(get_pipeline=get_pipeline)


@app.get("/health", response_class=HTMLResponse)
async def health_route():
    return await health_check(get_pipeline=get_pipeline)


@app.get("/supported-types")
async def supported_types_route():
    return await get_supported_types(config=config)


@app.delete("/table/{table_name}")
async def delete_table_route(table_name: str):
    return await delete_table(
        table_name=table_name,
        config=config,
        get_pipeline=get_pipeline
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
