#!/usr/bin/env python3
"""
Automated import migration script for project reorganization.
Updates all imports from old document_processing structure to new ingestion/retrieval/api structure.
"""

import os
import re
from pathlib import Path

# Import mapping: old_import -> new_import
IMPORT_MAPPINGS = {
    # Processor imports
    'from document_processing.base_processor': 'from ingestion.processors.base_processor',
    'from document_processing.pdf_processor': 'from ingestion.processors.pdf_processor',
    'from document_processing.docx_processor': 'from ingestion.processors.docx_processor',
    'from document_processing.txt_processor': 'from ingestion.processors.txt_processor',
    'from document_processing.processor_factory': 'from ingestion.processors.processor_factory',

    # Chunking imports
    'from document_processing.chunk_pdf_with_chonkie': 'from ingestion.chunking.semantic_chunker',

    # Embedding imports
    'from document_processing.embed_chunks_to_db': 'from ingestion.embedding.vector_store',

    # Extraction imports
    'from document_processing.extraction_flow': 'from ingestion.extraction.extraction_flow',

    # Validation imports
    'from document_processing.file_validator': 'from ingestion.validation.file_validator',

    # Retrieval imports
    'from document_processing.retrieval': 'from retrieval.search',
    'from document_processing.reranker': 'from retrieval.reranking',
    'from document_processing.llm_operations': 'from retrieval.llm_operations',
    'from document_processing.utils': 'from retrieval.utils',

    # API imports
    'from document_processing.api_routes': 'from api.routes.document_routes',
    'from document_processing.full_pipeline_pgvector': 'from api.app',
    'from document_processing.config': 'from api.config',
    'from document_processing.validators': 'from api.validators',
    'from document_processing.templates': 'from api.templates',
}

# Relative import mappings for files within moved modules
RELATIVE_IMPORT_MAPPINGS = {
    # Within ingestion/processors/
    'from .chunk_pdf_with_chonkie': 'from ingestion.chunking.semantic_chunker',
    'from .processor_factory': 'from ingestion.processors.processor_factory',

    # Within ingestion/chunking/
    'from .processor_factory': 'from ingestion.processors.processor_factory',
}


def update_imports_in_file(file_path: Path) -> bool:
    """
    Update imports in a single file.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply import mappings
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)

        # Apply relative import mappings if file is in ingestion/
        if 'ingestion' in str(file_path):
            for old_import, new_import in RELATIVE_IMPORT_MAPPINGS.items():
                content = content.replace(old_import, new_import)

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in directory."""
    return list(directory.rglob('*.py'))


def main():
    """Main migration function."""
    print("🔄 Starting import migration...\n")

    # Directories to process
    directories_to_update = [
        Path('ingestion'),
        Path('retrieval'),
        Path('api'),
        Path('worker'),
        Path('graph_processing'),
    ]

    modified_files = []
    skipped_files = []

    for directory in directories_to_update:
        if not directory.exists():
            print(f"⚠️  Directory not found: {directory}")
            continue

        print(f"📁 Processing {directory}/...")

        python_files = find_python_files(directory)

        for file_path in python_files:
            if file_path.name == '__pycache__':
                continue

            was_modified = update_imports_in_file(file_path)

            if was_modified:
                modified_files.append(file_path)
                print(f"  ✅ Updated: {file_path}")
            else:
                skipped_files.append(file_path)
                print(f"  ⏭️  Skipped: {file_path} (no changes)")

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Migration Summary:")
    print(f"{'='*60}")
    print(f"✅ Modified files: {len(modified_files)}")
    print(f"⏭️  Skipped files: {len(skipped_files)}")
    print(f"{'='*60}\n")

    if modified_files:
        print("Modified files:")
        for file_path in modified_files:
            print(f"  - {file_path}")

    print("\n✨ Migration complete!")
    print("\n Next steps:")
    print("  1. Review the changes with: git diff")
    print("  2. Test imports: python3 -m py_compile ingestion/**/*.py retrieval/*.py api/**/*.py")
    print("  3. Run the application to verify everything works")


if __name__ == '__main__':
    main()
