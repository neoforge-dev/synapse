import pytest
import os
from pydantic_settings import SettingsConfigDict

# Adjust import path based on your project structure
from graph_rag.config.settings import Settings, SettingsConfigDict

# Define the path to a temporary test .env file relative to this test file
TEST_ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), '.env.test')

@pytest.fixture(scope="function")
def create_test_env_file():
    """Fixture to create a temporary .env file for testing."""
    env_content = """
    # Test overrides
    APP_NAME=TestGraphRAG
    DEBUG=True
    MEMGRAPH_HOST=testhost
    MEMGRAPH_PORT=1234
    EMBEDDING_MODEL_NAME=test-model
    VECTOR_SEARCH_SIMILARITY_THRESHOLD=0.9
    # Test extra variable (should be ignored)
    EXTRA_VAR=ignore_me 
    """
    with open(TEST_ENV_FILE_PATH, "w") as f:
        f.write(env_content)
    yield TEST_ENV_FILE_PATH # Provide the path to the test
    # Teardown: remove the file after the test function runs
    os.remove(TEST_ENV_FILE_PATH)

@pytest.fixture(scope="module")
def settings_with_test_env(tmp_path_factory):
    """Fixture to create a temporary .env file and load settings from it."""
    # ... (env file creation remains the same)
    env_path = tmp_path_factory.mktemp("config_test") / ".env.test"
    env_content = """
    APP_NAME="TestGraphRAG"
    DEBUG=True
    MEMGRAPH_HOST="testhost"
    MEMGRAPH_PORT=1234
    MEMGRAPH_USERNAME="testuser"
    #MEMGRAPH_PASSWORD="testpass"
    VECTOR_STORE_TYPE="chroma"
    """
    env_path.write_text(env_content)

    # Force Pydantic to load from this specific file
    original_config = Settings.model_config
    Settings.model_config = SettingsConfigDict(
        env_file=str(env_path), env_file_encoding='utf-8', extra='ignore'
    )
    settings = Settings()
    Settings.model_config = original_config # Restore
    return settings

def test_settings_load_defaults():
    """Test loading settings without any .env file (using defaults)."""
    # Temporarily override config to ensure no .env is loaded
    original_config = Settings.model_config
    Settings.model_config = SettingsConfigDict(
        env_file='.env.nonexistent', env_file_encoding='utf-8', extra='ignore'
    )
    settings = Settings()
    Settings.model_config = original_config # Restore

    assert settings.APP_NAME == "graph-rag-mcp" # Corrected expected default
    assert settings.DEBUG is False
    assert settings.MEMGRAPH_HOST == "localhost"
    assert settings.MEMGRAPH_PORT == 7687
    assert settings.get_memgraph_uri() == "bolt://localhost:7687"

def test_settings_load_from_env_file(settings_with_test_env):
    """Test loading settings from the temporary .env.test file."""
    settings = settings_with_test_env

    assert settings.APP_NAME == "TestGraphRAG"
    assert settings.DEBUG is True
    assert settings.MEMGRAPH_HOST == "testhost"
    assert settings.MEMGRAPH_PORT == 1234
    assert settings.get_memgraph_uri() == "bolt://testhost:1234" # Check constructed URI
    assert settings.MEMGRAPH_USERNAME == "testuser"
    assert settings.MEMGRAPH_PASSWORD is None # Password was commented out
    assert settings.VECTOR_STORE_TYPE == "chroma"

def test_settings_memgraph_uri_override():
    """Test that MEMGRAPH_URI overrides host/port if provided."""
    # Simulate setting MEMGRAPH_URI via environment variable
    os.environ["MEMGRAPH_URI"] = "bolt://override-host:9999"
    settings = Settings()
    del os.environ["MEMGRAPH_URI"] # Clean up env var
    
    assert settings.MEMGRAPH_HOST == "localhost" # Default host is still loaded
    assert settings.MEMGRAPH_PORT == 7687       # Default port is still loaded
    assert settings.MEMGRAPH_URI == "bolt://override-host:9999" # URI is loaded
    assert settings.get_memgraph_uri() == "bolt://override-host:9999" # Method returns override 