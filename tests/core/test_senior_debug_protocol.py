"""Tests for the Senior Developer Debugging Protocol."""

import pytest
from datetime import datetime
from pathlib import Path
import inspect
from typing import Dict, Any

from graph_rag.core.senior_debug_protocol import (
    SeniorDebugProtocol,
    TestFailure,
    Investigation
)

@pytest.fixture
def debug_protocol():
    """Fixture for SeniorDebugProtocol instance."""
    return SeniorDebugProtocol(
        test_file="test_senior_debug_protocol.py",
        test_function="test_observe_failure"
    )

@pytest.fixture
def sample_error():
    """Fixture for a sample error to test with."""
    try:
        raise ValueError("Test error message")
    except ValueError as e:
        return e

def test_observe_failure(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test observing a test failure."""
    failure = debug_protocol.observe_failure(sample_error)
    
    assert isinstance(failure, TestFailure)
    assert failure.error_message == "Test error message"
    assert failure.test_file == "test_senior_debug_protocol.py"
    assert failure.test_function == "test_observe_failure"
    assert failure.timestamp <= datetime.utcnow()

def test_analyze_test_case(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test analyzing a test case."""
    failure = debug_protocol.observe_failure(sample_error)
    analyzed = debug_protocol.analyze_test_case(failure)
    
    assert analyzed.expected_behavior != ""
    assert analyzed.actual_behavior.startswith("Failed with:")

def test_question_assumptions(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test questioning assumptions."""
    failure = debug_protocol.observe_failure(sample_error)
    assumptions = debug_protocol.question_assumptions(failure)
    
    assert len(assumptions) > 0
    assert any("implementation" in a.lower() for a in assumptions)
    assert any("test" in a.lower() for a in assumptions)

def test_trace_execution_path(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test tracing execution path."""
    failure = debug_protocol.observe_failure(sample_error)
    path = debug_protocol.trace_execution_path(failure)
    
    assert isinstance(path, list)
    assert all(isinstance(step, str) for step in path)
    assert any("test_senior_debug_protocol.py" in step for step in path)

def test_identify_implementation_gaps(debug_protocol: SeniorDebugProtocol):
    """Test identifying implementation gaps."""
    execution_path = [
        "test_file.py:10 - test_function",
        "core/implementation.py:20 - some_method"
    ]
    gaps = debug_protocol.identify_implementation_gaps(execution_path)
    
    assert isinstance(gaps, list)
    assert len(gaps) > 0

def test_create_investigation(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test creating a complete investigation."""
    failure = debug_protocol.observe_failure(sample_error)
    investigation = debug_protocol.create_investigation(failure)
    
    assert isinstance(investigation, Investigation)
    assert investigation.test_failure == failure
    assert isinstance(investigation.related_failures, list)
    assert isinstance(investigation.execution_path, list)
    assert isinstance(investigation.implementation_gaps, list)

def test_generate_hypotheses(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test generating hypotheses."""
    failure = debug_protocol.observe_failure(sample_error)
    investigation = debug_protocol.create_investigation(failure)
    hypotheses = debug_protocol.generate_hypotheses(investigation)
    
    assert isinstance(hypotheses, list)
    assert len(hypotheses) > 0
    assert all("type" in h for h in hypotheses)
    assert all("description" in h for h in hypotheses)
    assert all("confidence" in h for h in hypotheses)
    assert all("verification_steps" in h for h in hypotheses)

def test_verify_hypothesis(debug_protocol: SeniorDebugProtocol):
    """Test verifying a hypothesis."""
    hypothesis = {
        "type": "implementation_gap",
        "description": "Test hypothesis",
        "confidence": 0.8,
        "verification_steps": ["Step 1", "Step 2"]
    }
    verification_steps = debug_protocol.verify_hypothesis(hypothesis)
    
    assert isinstance(verification_steps, list)
    assert len(verification_steps) == 2
    assert all("status" in step for step in verification_steps)
    assert all(step["status"] == "pending" for step in verification_steps)

def test_resolve_issue(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test resolving an issue."""
    failure = debug_protocol.observe_failure(sample_error)
    investigation = debug_protocol.create_investigation(failure)
    fix = {"description": "Test fix", "changes": ["Change 1", "Change 2"]}
    
    resolved = debug_protocol.resolve_issue(investigation, fix)
    
    assert resolved.resolution is not None
    assert resolved.resolution["fix"] == fix
    assert not resolved.resolution["verified"]

def test_save_and_load_investigation(
    debug_protocol: SeniorDebugProtocol,
    sample_error,
    tmp_path: Path
):
    """Test saving and loading an investigation."""
    failure = debug_protocol.observe_failure(sample_error)
    investigation = debug_protocol.create_investigation(failure)
    
    # Save investigation
    save_path = tmp_path / "investigation.json"
    debug_protocol.save_investigation(investigation, save_path)
    
    # Load investigation
    loaded = debug_protocol.load_investigation(save_path)
    
    assert isinstance(loaded, Investigation)
    assert loaded.test_failure.error_message == investigation.test_failure.error_message
    assert loaded.test_failure.test_file == investigation.test_failure.test_file

def test_handle_persistent_error(debug_protocol: SeniorDebugProtocol, sample_error):
    """Test handling persistent errors."""
    # First occurrence
    reasoning1 = debug_protocol.handle_persistent_error(sample_error, 1)
    assert len(reasoning1) == 0
    
    # Second occurrence
    reasoning2 = debug_protocol.handle_persistent_error(sample_error, 2)
    assert len(reasoning2) == 3
    assert all(isinstance(r, str) for r in reasoning2)
    assert any("Component Architecture" in r for r in reasoning2)
    assert any("Edge Cases" in r for r in reasoning2)
    assert any("Dependency" in r for r in reasoning2) 