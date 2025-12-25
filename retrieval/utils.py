"""
Utility functions for the RAG application.
Includes BM25 reranking and other helper functions.
"""

import os
import numpy as np
from typing import List, Dict
from rank_bm25 import BM25Okapi

from retrieval.reranking import Reranker


def rerank_bm25(query: str, sources: List[Dict], top_k: int) -> List[Dict]:
    """
    Use BM25 to return top k sources from the inputs.

    Args:
        query: Search query string
        sources: List of sources from PostgreSQL
            Format: {
                'chunk_id': '6250bf1e-e76e-4bb9-b33b-d05eb07aa77c',
                'text': 'abc',
                'metadata': {},
                ...
            }
        top_k: Number of top results to return

    Returns:
        List of top k sources with BM25 scores added
    """
    # Tokenize the text (simple word splitting)
    tokenized_corpus = [doc['text'].lower().split() for doc in sources]

    # Create BM25 index
    bm25 = BM25Okapi(tokenized_corpus)

    # Search with BM25
    tokenized_query = query.lower().split()

    # Get BM25 scores for all documents
    bm25_scores = bm25.get_scores(tokenized_query)

    # Get top k results
    top_indices = np.argsort(bm25_scores)[::-1][:top_k]

    # Retrieve top documents
    bm25_results = []
    for idx in top_indices:
        result = sources[idx].copy()
        result['bm25_score'] = float(bm25_scores[idx])
        bm25_results.append(result)

    return bm25_results


def get_reranker(config) -> Reranker:
    """
    Get or initialize the reranker (lazy initialization).

    Args:
        config: Application configuration object

    Returns:
        Reranker instance
    """
    if config.reranker is None:
        # Get model from environment or use default
        rerank_model = os.getenv('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        config.reranker = Reranker(model_name=rerank_model)
        print(f"✓ Reranker initialized with model: {rerank_model}")
    return config.reranker
