import asyncio
import os
import sys
import inspect
from uuid import uuid4

# Add project root to path
sys.path.append(os.getcwd())

async def main():
    print("=== Verifying Performance Improvements ===")

    # 1. Verify Semantic Chunker Caching
    print("\n1. Testing Semantic Chunker Caching...")
    try:
        from ingestion.chunking.chunker_factory import get_chunker
        
        # First call - should initialize
        print("   Requesting chunker 1...")
        chunker1 = get_chunker("semantic", chunk_size=512)
        
        # Second call - should specific same instance
        print("   Requesting chunker 2...")
        chunker2 = get_chunker("semantic", chunk_size=512)
        
        if chunker1 is chunker2:
            print("   ✅ SUCCESS: Chunker instance is cached!")
        else:
            print("   ❌ FAILURE: Chunker instances are different!")
            
    except Exception as e:
        print(f"   ❌ ERROR during chunker test: {e}")

    # 2. Verify Async Methods
    print("\n2. Testing Async Method Signatures...")
    try:
        from graph_processing.entity_extraction import EntityExtractor
        from graph_processing.relationship_extraction import RelationshipExtractor
        
        # Check EntityExtractor
        if inspect.iscoroutinefunction(EntityExtractor.extract_entities_from_chunk):
            print("   ✅ EntityExtractor.extract_entities_from_chunk is async")
        else:
            print("   ❌ EntityExtractor.extract_entities_from_chunk is NOT async")

        if inspect.iscoroutinefunction(EntityExtractor._call_gemini_with_retry):
             print("   ✅ EntityExtractor._call_gemini_with_retry is async")
        else:
             print("   ❌ EntityExtractor._call_gemini_with_retry is NOT async")

        # Check RelationshipExtractor
        if inspect.iscoroutinefunction(RelationshipExtractor.extract_relationships_from_chunk):
            print("   ✅ RelationshipExtractor.extract_relationships_from_chunk is async")
        else:
            print("   ❌ RelationshipExtractor.extract_relationships_from_chunk is NOT async")
            
        if inspect.iscoroutinefunction(RelationshipExtractor._call_gemini_with_retry):
             print("   ✅ RelationshipExtractor._call_gemini_with_retry is async")
        else:
             print("   ❌ RelationshipExtractor._call_gemini_with_retry is NOT async")

    except Exception as e:
        print(f"   ❌ ERROR during async signature test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
