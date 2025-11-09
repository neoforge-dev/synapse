#!/usr/bin/env python3
"""
Validation script to test entity extraction functionality.
This script verifies that entities are being extracted correctly from real text.
"""

import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.models import Chunk, Document


async def test_entity_extraction():
    """Test that SpacyEntityExtractor finds entities in real text"""
    print("Testing SpacyEntityExtractor...")

    # Initialize the extractor
    extractor = SpacyEntityExtractor()

    # Create test document with entity-rich content
    test_content = """
    Barack Obama was the 44th President of the United States from 2009 to 2017.
    He was born in Honolulu, Hawaii and later served as a senator from Illinois.
    Microsoft Corporation is a technology company founded by Bill Gates and Paul Allen.
    The company is headquartered in Redmond, Washington and has offices in San Francisco, California.
    Apple Inc. released the iPhone in 2007, revolutionizing the smartphone industry.
    """

    # Create chunks
    chunk1 = Chunk(
        id="chunk-1",
        document_id="test-entity-doc",
        text=test_content[:200],
        metadata={"chunk_index": 0}
    )
    chunk2 = Chunk(
        id="chunk-2",
        document_id="test-entity-doc",
        text=test_content[200:],
        metadata={"chunk_index": 1}
    )

    # Create document with chunks
    doc = Document(
        id="test-entity-doc",
        content=test_content,
        metadata={"title": "Test Entity Document", "source": "test"},
        chunks=[chunk1, chunk2]
    )

    # Extract entities
    result = await extractor.extract(doc)

    print(f"✓ Extracted {len(result.entities)} entities")
    print(f"✓ Extracted {len(result.relationships)} relationships")

    # Print entities for verification
    entity_types = {}
    for entity in result.entities:
        entity_type = entity.type
        if entity_type not in entity_types:
            entity_types[entity_type] = []
        entity_types[entity_type].append(entity.name)
        print(f"  - {entity.name} ({entity.type})")

    # Validate we found expected entities
    assert len(result.entities) > 0, "Should extract at least some entities"

    # Check for expected entity types
    expected_persons = ["Barack Obama", "Bill Gates", "Paul Allen"]
    expected_orgs = ["Microsoft Corporation", "Apple Inc."]
    expected_places = ["United States", "Honolulu", "Hawaii", "Illinois", "Redmond", "Washington", "San Francisco", "California"]

    found_persons = entity_types.get("PERSON", [])
    found_orgs = entity_types.get("ORG", [])
    found_places = entity_types.get("GPE", [])

    print(f"✓ Found PERSON entities: {found_persons}")
    print(f"✓ Found ORG entities: {found_orgs}")
    print(f"✓ Found GPE entities: {found_places}")

    # Verify we found at least some of each type
    assert any(person in found_persons for person in expected_persons), "Should find at least one expected person"
    assert any(org in found_orgs for org in expected_orgs), "Should find at least one expected organization"
    assert any(place in found_places for place in expected_places), "Should find at least one expected place"

    # Check relationships (MENTIONS) - SpaCy extractor may not generate these automatically
    mentions_count = sum(1 for rel in result.relationships if rel.type == "MENTIONS")
    print(f"✓ Found {mentions_count} MENTIONS relationships")
    # Note: SpaCy extractor focuses on entity extraction, relationships may be generated elsewhere

    print("🎉 All entity extraction tests passed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_entity_extraction())
