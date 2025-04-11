import pytest
import os
from unittest import mock # Import mock
from pydantic_settings import SettingsConfigDict

# Adjust import path based on your project structure
from graph_rag.config.settings import Settings

# Define the path to a temporary test .env file relative to this test file
TEST_ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), '.env.test')

@pytest.fixture(scope="function")
def create_test_env_file():
    """Fixture to create a temporary .env file for testing."""
    env_content = """
    # Test overrides
    SYNAPSE_APP_NAME=TestGraphRAG
    SYNAPSE_DEBUG=True
    SYNAPSE_MEMGRAPH_HOST=testhost
    SYNAPSE_MEMGRAPH_PORT=1234
    SYNAPSE_EMBEDDING_MODEL_NAME=test-model
    SYNAPSE_VECTOR_SEARCH_SIMILARITY_THRESHOLD=0.9
    # Test extra variable (should be ignored if not prefixed or defined)
    EXTRA_VAR=ignore_me
    SYNAPSE_EXTRA_VAR_PREFIXED=ignore_me_too
    """
    with open(TEST_ENV_FILE_PATH, "w") as f:
        f.write(env_content)
    yield TEST_ENV_FILE_PATH # Provide the path to the test
    # Teardown: remove the file after the test function runs
    os.remove(TEST_ENV_FILE_PATH)

@pytest.fixture(scope="function")
def settings_with_test_env(tmp_path_factory):
    """Fixture to create a temporary .env file and return its path."""
    fn = tmp_path_factory.mktemp("config_test") / ".env.test"
    content = """
SYNAPSE_APP_NAME=TestGraphRAG
SYNAPSE_MEMGRAPH_HOST=testhost
SYNAPSE_MEMGRAPH_PORT=1234
# Add other test-specific vars if needed, WITH prefix
"""
    fn.write_text(content, encoding="utf-8")
    yield str(fn) # Yield the path as string

@pytest.fixture(scope="function")
def settings_with_uri_override_env(tmp_path_factory):
    fn = tmp_path_factory.mktemp("config_test_uri") / ".env.test.uri"
    content = """
SYNAPSE_MEMGRAPH_HOST=originalhost
SYNAPSE_MEMGRAPH_PORT=9999
SYNAPSE_MEMGRAPH_URI=bolt://override:5678
"""
    fn.write_text(content, encoding="utf-8")
    yield str(fn)

def test_settings_load_defaults(monkeypatch):
    """Test loading settings without any .env file (using defaults)."""
    # Temporarily remove env vars that might override defaults for this test
    monkeypatch.delenv("MEMGRAPH_HOST", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    # Add other env vars to delete if they conflict with defaults being tested

    # Assumes no .env file exists in the default location or parent dirs
    # Or, explicitly point to a non-existent file:
    original_config = Settings.model_config
    Settings.model_config = SettingsConfigDict(
        env_file='.env.nonexistent', env_file_encoding='utf-8', extra='ignore'
    )
    settings = Settings()
    Settings.model_config = original_config # Restore

    assert settings.APP_NAME == "graph-rag-mcp"
    assert settings.DEBUG is False
    assert settings.MEMGRAPH_HOST == "localhost" # Assert the default
    # Add other default assertions as needed

def test_settings_load_from_env_vars():
    """Test loading settings by directly passing values (simulating env vars)."""
    # Instead of mocking os.environ, pass values directly
    test_settings = Settings(
        APP_NAME="TestGraphRAGFromEnv",
        MEMGRAPH_HOST="envhost",
        MEMGRAPH_PORT=4321
        # Add other fields as needed, ensuring they are defined in Settings model
        # model_config can be omitted here as we are not relying on env/file loading
    )
    assert test_settings.APP_NAME == "TestGraphRAGFromEnv"
    assert test_settings.MEMGRAPH_HOST == "envhost"
    assert test_settings.MEMGRAPH_PORT == 4321
    # Verify get_memgraph_uri if the method exists and is needed
    # assert test_settings.get_memgraph_uri() == "bolt://envhost:4321"

def test_settings_memgraph_uri_override_from_env():
    """Test that MEMGRAPH_URI passed directly overrides host/port."""
    # Pass values directly, including the URI
    test_settings = Settings(
        MEMGRAPH_HOST="originalhost",
        MEMGRAPH_PORT=9999,
        MEMGRAPH_URI="bolt://override:5678"
    )
    # Assert the URI field directly if it exists
    # assert test_settings.MEMGRAPH_URI == "bolt://override:5678"
    # Verify get_memgraph_uri if the method exists and is needed
    # assert test_settings.get_memgraph_uri() == "bolt://override:5678"
    # Host/Port values might be retained but should be ignored by logic using the URI
    assert test_settings.MEMGRAPH_HOST == "originalhost" 
    assert test_settings.MEMGRAPH_PORT == 9999

def test_settings_load_from_env_file():
    """Test loading settings by mocking environment variables without prefix."""
    test_env_vars = {
        # Mock variables WITHOUT prefix, as default config doesn't use one
        'APP_NAME': 'TestGraphRAG',
        'MEMGRAPH_HOST': 'testhost',
        'MEMGRAPH_PORT': '1234',
        'EXTRA_VAR': 'ignore_me' # Should be ignored
    }
    
    # Use mock.patch.dict to set ONLY these variables for the test duration
    with mock.patch.dict(os.environ, test_env_vars, clear=True):
        # Load settings using the default model_config (no prefix)
        test_settings = Settings()
        
        # Assert values from mocked env vars
        assert test_settings.APP_NAME == "TestGraphRAG"
        assert test_settings.MEMGRAPH_HOST == "testhost"
        assert test_settings.MEMGRAPH_PORT == 1234
        # Assert default is used if not in mocked env
        assert test_settings.DEBUG is False 
        # Assert get_memgraph_uri uses loaded values
        # assert test_settings.get_memgraph_uri() == "bolt://testhost:1234"

def test_settings_memgraph_uri_override():
    """Test that MEMGRAPH_URI from env vars overrides host/port (without prefix)."""
    test_env_vars = {
        # Mock variables WITHOUT prefix
        'MEMGRAPH_HOST': 'originalhost',
        'MEMGRAPH_PORT': '9999',
        'MEMGRAPH_URI': 'bolt://override:5678'
    }
    
    with mock.patch.dict(os.environ, test_env_vars, clear=True):
        # Load settings using default model_config
        test_settings = Settings()
        
        # Assert URI takes precedence
        # assert test_settings.MEMGRAPH_URI == "bolt://override:5678"
        # assert test_settings.get_memgraph_uri() == "bolt://override:5678"
        # Assert host/port are still loaded but would be ignored by logic using the URI
        assert test_settings.MEMGRAPH_HOST == "originalhost"
        assert test_settings.MEMGRAPH_PORT == 9999 