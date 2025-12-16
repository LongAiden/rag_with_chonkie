#!/usr/bin/env python3
"""
Extract entities and relationships from ALL existing chunks in the database.

This is a one-time migration script for populating the knowledge graph
from documents that were uploaded before entity extraction was enabled.

Usage:
    python scripts/extract_existing_chunks.py [--limit 100] [--batch-size 10]
"""

import asyncio
import asyncpg
import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from graph_processing.extraction_service import create_extraction_service

# Load environment variables
env_path = project_root / 'deployment' / '.env'
load_dotenv(env_path)


async def get_db_pool() -> asyncpg.Pool:
    """Create database connection pool."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "rag_db")
        user = os.getenv("POSTGRES_USER", "admin")
        password = os.getenv("POSTGRES_PASSWORD", "admin")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    return await asyncpg.create_pool(db_url, min_size=2, max_size=10)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract entities from all existing chunks"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of chunks to process (for testing)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Process chunks in batches of this size"
    )

    args = parser.parse_args()

    # Create database pool
    pool = await get_db_pool()

    try:
        # Create extraction service
        print("Initializing extraction service...")
        extraction_service = await create_extraction_service(pool)

        # Get all chunk IDs
        print(f"Fetching chunk IDs from database...")
        async with pool.acquire() as conn:
            if args.limit:
                chunks = await conn.fetch(
                    "SELECT chunk_id FROM chunks LIMIT $1",
                    args.limit
                )
            else:
                chunks = await conn.fetch("SELECT chunk_id FROM chunks")

            chunk_ids = [row['chunk_id'] for row in chunks]

        if not chunk_ids:
            print("No chunks found in database.")
            return

        print(f"\nFound {len(chunk_ids)} chunks to process")
        print(f"Processing in batches of {args.batch_size}")
        print(f"{'='*70}\n")

        # Process in batches
        total_entities = 0
        total_relationships = 0
        total_successful = 0
        total_failed = 0

        for i in range(0, len(chunk_ids), args.batch_size):
            batch = chunk_ids[i:i + args.batch_size]
            batch_num = i // args.batch_size + 1
            total_batches = (len(chunk_ids) + args.batch_size - 1) // args.batch_size

            print(f"Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

            result = await extraction_service.extract_from_chunks(
                chunk_ids=batch,
                verbose=True
            )

            total_entities += result['total_entities']
            total_relationships += result['total_relationships']
            total_successful += result['successful']
            total_failed += result['failed']

            print(f"  ✓ Batch complete: {result['total_entities']} entities, "
                  f"{result['total_relationships']} relationships\n")

        # Final summary
        print(f"\n{'='*70}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'='*70}")
        print(f"Total chunks processed: {len(chunk_ids)}")
        print(f"Successful: {total_successful}")
        print(f"Failed: {total_failed}")
        print(f"Total entities extracted: {total_entities}")
        print(f"Total relationships extracted: {total_relationships}")
        print(f"{'='*70}\n")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
