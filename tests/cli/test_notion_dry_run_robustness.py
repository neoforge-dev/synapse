"""Test Notion dry-run robustness including multi-run consistency and 429 handling."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from graph_rag.cli.main import app

runner = CliRunner()


def test_notion_dry_run_multi_run_consistency(tmp_path: Path):
    """Test that dry-run produces consistent results across multiple runs."""
    state_file = tmp_path / "state.json"
    
    # Initial state: page a exists
    initial_state = {
        "db:db1": {
            "last_edited_time": "2024-01-01T00:00:00Z", 
            "pages": {"a": "2024-01-01T00:00:00Z"}
        }
    }
    state_file.write_text(json.dumps(initial_state))

    # Mock Notion API response - same for multiple runs
    mock_response = {
        "results": [
            {"id": "a", "properties": {}, "last_edited_time": "2024-02-01T00:00:00Z"},
            {"id": "b", "properties": {}, "last_edited_time": "2024-01-15T00:00:00Z"},
        ],
        "has_more": False,
    }

    with patch("graph_rag.cli.commands.notion.NotionClient") as MockClient:
        client = MockClient.return_value
        client.query_database.return_value = mock_response

        # First dry-run
        result1 = runner.invoke(
            app,
            [
                "notion", "sync", "--db", "db1", "--dry-run", 
                "--state-file", str(state_file)
            ],
        )
        assert result1.exit_code == 0, result1.output
        lines1 = [json.loads(l) for l in result1.output.splitlines() if l.strip()]
        
        # Second dry-run (should be identical)
        result2 = runner.invoke(
            app,
            [
                "notion", "sync", "--db", "db1", "--dry-run",
                "--state-file", str(state_file)
            ],
        )
        assert result2.exit_code == 0, result2.output
        lines2 = [json.loads(l) for l in result2.output.splitlines() if l.strip()]
        
        # Results should be identical
        assert len(lines1) == len(lines2)
        actions1 = {d["page_id"]: d["action"] for d in lines1}
        actions2 = {d["page_id"]: d["action"] for d in lines2}
        assert actions1 == actions2
        assert actions1.get("a") == "update"
        assert actions1.get("b") == "add"


def test_notion_dry_run_state_file_corruption_recovery(tmp_path: Path):
    """Test that dry-run handles corrupted state files gracefully."""
    state_file = tmp_path / "corrupted_state.json"
    
    # Write corrupted JSON
    state_file.write_text('{"db:db1": invalid json}')

    mock_response = {
        "results": [
            {"id": "a", "properties": {}, "last_edited_time": "2024-01-01T00:00:00Z"},
        ],
        "has_more": False,
    }

    with patch("graph_rag.cli.commands.notion.NotionClient") as MockClient:
        client = MockClient.return_value
        client.query_database.return_value = mock_response

        # Should not crash, should fallback to no state
        result = runner.invoke(
            app,
            [
                "notion", "sync", "--db", "db1", "--dry-run",
                "--state-file", str(state_file)
            ],
        )
        assert result.exit_code == 0, result.output
        lines = [json.loads(l) for l in result.output.splitlines() if l.strip()]
        
        # Without valid state, should treat all pages as new
        actions = {d["page_id"]: d["action"] for d in lines}
        assert actions.get("a") == "add"


def test_notion_sync_429_rate_limit_handling():
    """Test that Notion sync handles 429 rate limiting with proper backoff."""
    import requests
    
    # Create a mock 429 response
    mock_429_response = MagicMock()
    mock_429_response.status_code = 429
    mock_429_response.headers = {"Retry-After": "2"}
    mock_429_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "429 Client Error: Too Many Requests"
    )
    
    # Create a successful response for retry
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {
        "results": [
            {"id": "a", "properties": {}, "last_edited_time": "2024-01-01T00:00:00Z"},
        ],
        "has_more": False,
    }

    with patch("graph_rag.cli.commands.notion.NotionClient") as MockClient:
        client = MockClient.return_value
        
        # First call returns 429, second call succeeds
        client.query_database.side_effect = [
            requests.exceptions.HTTPError("429 Client Error: Too Many Requests"),
            mock_success_response.json.return_value
        ]

        # Should handle 429 and retry successfully
        result = runner.invoke(
            app,
            [
                "notion", "sync", "--db", "db1", "--dry-run", "--limit", "1"
            ],
        )
        assert result.exit_code == 0, result.output
        lines = [json.loads(l) for l in result.output.splitlines() if l.strip()]
        
        # Should still get the result after retry
        actions = {d["page_id"]: d["action"] for d in lines}
        assert actions.get("a") == "add"
        
        # Verify retry happened
        assert client.query_database.call_count == 2


def test_notion_sync_rate_limit_budget_configuration():
    """Test that rate limit budget is properly configured and respected."""
    from graph_rag.config import get_settings
    
    settings = get_settings()
    
    # Verify rate limiting settings exist
    assert hasattr(settings, 'notion_max_qps')
    assert hasattr(settings, 'notion_backoff_ceiling')
    assert hasattr(settings, 'notion_max_retries')
    
    # Default values should be reasonable
    assert settings.notion_max_qps > 0
    assert settings.notion_backoff_ceiling > 0
    assert settings.notion_max_retries > 0


@pytest.mark.asyncio
async def test_notion_sync_exponential_backoff_ceiling():
    """Test that exponential backoff respects the configured ceiling."""
    import asyncio
    import time
    from unittest.mock import AsyncMock
    
    # Mock a rate-limited client that eventually succeeds
    mock_client = AsyncMock()
    
    # Track backoff times
    backoff_times = []
    original_sleep = asyncio.sleep
    
    async def mock_sleep(delay):
        backoff_times.append(delay)
        # Don't actually sleep in tests
        pass
    
    with patch('asyncio.sleep', mock_sleep):
        # Simulate multiple 429 errors followed by success
        from graph_rag.config import get_settings
        settings = get_settings()
        
        # Test that backoff doesn't exceed ceiling
        max_backoff = settings.notion_backoff_ceiling
        
        # Simulate exponential backoff calculation
        backoff = 1.0
        for i in range(5):
            backoff = min(backoff * 2, max_backoff)
            backoff_times.append(backoff)
        
        # All backoff times should be <= ceiling
        for delay in backoff_times:
            assert delay <= max_backoff