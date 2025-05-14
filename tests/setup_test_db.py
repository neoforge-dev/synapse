import asyncio
import logging

from graph_rag.config import get_settings
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository

logger = logging.getLogger(__name__)

settings = get_settings()  # Get settings instance


async def setup_test_database():
    """Set up test database with clean state."""
    repo = MemgraphRepository(
        host="localhost",  # Use environment variables in real app
        port=7687,
    )

    try:
        # Clear existing data
        await repo.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Test database cleared successfully")

        # Create test indices if needed
        await repo.execute_query("""
            CREATE INDEX ON :Document(document_id);
            CREATE INDEX ON :Chunk(chunk_id);
        """)
        logger.info("Test database indices created")

    except Exception as e:
        logger.error(f"Error setting up test database: {e}")
        raise
    finally:
        await repo.close()


async def cleanup_test_database():
    """Clean up test database after tests."""
    repo = MemgraphRepository(
        host="localhost",  # Use environment variables in real app
        port=7687,
    )

    try:
        # Clear all data
        await repo.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Test database cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up test database: {e}")
        raise
    finally:
        await repo.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Run setup
    asyncio.run(setup_test_database())
