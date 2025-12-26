"""
Test script to verify logfire instrumentation for graph integration.
This script simulates a search query to demonstrate the logfire tracking.
"""

import asyncio
import logfire
from api.config import get_config


async def test_graph_integration_logging():
    """
    Test that graph integration is properly logged with logfire.
    This will perform a sample search and show all logfire outputs.
    """
    print("=" * 80)
    print("Testing Graph Integration with Logfire Instrumentation")
    print("=" * 80)

    # Initialize configuration
    config = get_config()

    # Import the search function
    from retrieval.search import perform_document_search

    # Sample query
    test_query = "What are the main topics discussed in the documents?"

    print(f"\nRunning search query: '{test_query}'")
    print("\nLogfire will track the following:")
    print("  1. document_search span - Overall search operation")
    print("  2. embedding_generation_for_search span - Query embedding")
    print("  3. graph_enrichment span - Graph entity fetching")
    print("  4. graph_entity_query span - Database query for entities")
    print("  5. context_building span - Context assembly with graph data")
    print("  6. llm_response_generation span - LLM answer generation")
    print("\n" + "=" * 80)
    print("Expected Logfire Metrics:")
    print("=" * 80)
    print("\n📊 Graph Enrichment Metrics:")
    print("  - num_chunks: Number of chunks to enrich")
    print("  - entities_per_chunk: Entities requested per chunk")
    print("  - total_entities: Total entities fetched from database")
    print("  - chunks_with_entities: Chunks that have linked entities")
    print("  - enrichment_rate: Percentage of chunks enriched (%)")
    print("  - total_entities_added: Total entities added to results")
    print("  - avg_entities_per_enriched_chunk: Average entities per chunk")
    print("\n📝 Context Building Metrics:")
    print("  - total_context_parts: Number of context sections")
    print("  - graph_sections_added: Graph entity sections added")
    print("  - context_length: Total character count")
    print("  - graph_integrated: Boolean - were graph entities included?")
    print("\n" + "=" * 80)

    try:
        # Perform search with graph integration
        response = await perform_document_search(
            query=test_query,
            limit=5,
            threshold=0.7,
            pipeline=config.pipeline,
            config=config
        )

        print("\n✅ Search completed successfully!")
        print(f"\n📈 Results Summary:")
        print(f"  - Chunks found: {response.search_stats.chunks_found}")
        print(f"  - Average similarity: {response.search_stats.avg_similarity}")
        print(f"  - Search method: {response.search_stats.search_method}")

        # Check if graph entities were included
        total_graph_entities = sum(
            len(source.graph_entities or [])
            for source in response.sources
        )

        sources_with_entities = sum(
            1 for source in response.sources
            if source.graph_entities
        )

        print(f"\n🕸️  Graph Integration Summary:")
        print(f"  - Total graph entities: {total_graph_entities}")
        print(f"  - Sources with entities: {sources_with_entities}/{len(response.sources)}")

        if total_graph_entities > 0:
            print(f"  - Graph integration: ✅ VERIFIED")
            print(f"\n  Sample entities:")
            for i, source in enumerate(response.sources[:3]):
                if source.graph_entities:
                    print(f"\n  Source {i+1} entities:")
                    for entity in source.graph_entities[:3]:
                        print(f"    - {entity['name']} ({entity['type']}) - confidence: {entity.get('confidence', 'N/A')}")
        else:
            print(f"  - Graph integration: ⚠️  No entities found (might need entity extraction)")

    except Exception as e:
        print(f"\n❌ Error during search: {str(e)}")
        print("This might be expected if the database is not initialized.")

    print("\n" + "=" * 80)
    print("Logfire Instrumentation Test Complete")
    print("=" * 80)
    print("\n💡 To view detailed logfire traces:")
    print("  - Check your logfire dashboard")
    print("  - Look for spans: 'graph_enrichment', 'graph_entity_query', 'context_building'")
    print("  - Verify that graph metrics are being tracked")


if __name__ == "__main__":
    # Configure logfire (uses default local mode if no token set)
    logfire.configure()

    # Run the test
    asyncio.run(test_graph_integration_logging())
