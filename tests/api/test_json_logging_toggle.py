"""Test JSON logging toggle functionality."""

import os
from unittest.mock import patch

from graph_rag.config import get_settings


def test_synapse_json_logs_alias():
    """Test that SYNAPSE_JSON_LOGS environment variable sets api_log_json."""
    # Test that SYNAPSE_JSON_LOGS=true sets api_log_json=True
    with patch.dict(os.environ, {"SYNAPSE_JSON_LOGS": "true"}, clear=False):
        settings = get_settings()
        assert settings.api_log_json is True

    # Test that SYNAPSE_JSON_LOGS=false sets api_log_json=False
    with patch.dict(os.environ, {"SYNAPSE_JSON_LOGS": "false"}, clear=False):
        settings = get_settings()
        assert settings.api_log_json is False

    # Test that SYNAPSE_JSON_LOGS=1 sets api_log_json=True
    with patch.dict(os.environ, {"SYNAPSE_JSON_LOGS": "1"}, clear=False):
        settings = get_settings()
        assert settings.api_log_json is True


def test_api_log_json_takes_precedence():
    """Test that SYNAPSE_API_LOG_JSON takes precedence over SYNAPSE_JSON_LOGS."""
    # When both are set, SYNAPSE_API_LOG_JSON should take precedence
    with patch.dict(os.environ, {
        "SYNAPSE_JSON_LOGS": "true",
        "SYNAPSE_API_LOG_JSON": "false"
    }, clear=False):
        settings = get_settings()
        assert settings.api_log_json is False


def test_json_logging_format_configuration():
    """Test that JSON logging format is properly configured in FastAPI lifespan."""
    from fastapi import FastAPI

    from graph_rag.api.main import lifespan

    # Mock settings with JSON logging enabled
    mock_settings = get_settings()
    mock_settings.api_log_json = True
    mock_settings.api_log_level = "INFO"

    app = FastAPI()

    # Capture logging configuration
    captured_config = {}

    def mock_basicConfig(**kwargs):
        captured_config.update(kwargs)
        # Don't actually call basicConfig to avoid interfering with test logging

    with patch('logging.basicConfig', mock_basicConfig):
        with patch('graph_rag.api.main.get_settings', return_value=mock_settings):
            # Test lifespan startup
            async def test_lifespan():
                async with lifespan(app):
                    pass

            import asyncio
            asyncio.run(test_lifespan())

    # Verify JSON format was configured
    assert 'format' in captured_config
    format_string = captured_config['format']
    # Should be JSON-like format
    assert '"time"' in format_string
    assert '"level"' in format_string
    assert '"name"' in format_string
    assert '"message"' in format_string
    assert captured_config['level'] == 'INFO'
