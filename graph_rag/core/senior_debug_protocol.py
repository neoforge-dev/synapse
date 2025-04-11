"""Senior Developer Debugging Protocol Implementation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import inspect
import traceback
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class TestFailure(BaseModel):
    __test__ = False # Prevent pytest collection
    """Represents a test failure with context."""
    error_message: str
    test_file: str
    test_function: str
    line_number: int
    expected_behavior: str
    actual_behavior: str
    test_code: str
    timestamp: datetime

class Investigation(BaseModel):
    """Represents a debugging investigation."""
    test_failure: TestFailure
    related_failures: List[TestFailure]
    execution_path: List[str]
    implementation_gaps: List[str]
    hypotheses: List[Dict[str, Any]]
    verification_steps: List[Dict[str, Any]]
    resolution: Optional[Dict[str, Any]] = None

class SeniorDebugProtocol:
    """Implements the Senior Developer Debugging Protocol."""

    def __init__(self, test_file: str, test_function: str):
        self.test_file = test_file
        self.test_function = test_function
        self.investigation = None

    def observe_failure(self, error: Exception) -> TestFailure:
        """Observe test failure without judgment."""
        tb = traceback.extract_tb(error.__traceback__)
        test_frame = next((frame for frame in tb if frame.filename.endswith(self.test_file)), None)
        
        if test_frame:
            line_number = test_frame.lineno
            test_code = test_frame.line
        else:
            line_number = 0
            test_code = ""

        return TestFailure(
            error_message=str(error),
            test_file=self.test_file,
            test_function=self.test_function,
            line_number=line_number,
            expected_behavior="",  # To be filled by analyze_test_case
            actual_behavior="",    # To be filled by analyze_test_case
            test_code=test_code,
            timestamp=datetime.utcnow()
        )

    def analyze_test_case(self, failure: TestFailure) -> TestFailure:
        """Analyze what the test is verifying and expected behavior."""
        # Get the test function's source code
        test_module = inspect.getmodule(inspect.currentframe())
        test_func = getattr(test_module, self.test_function)
        test_doc = inspect.getdoc(test_func) or ""
        
        # Extract expected behavior from docstring
        expected_behavior = test_doc.split("\n")[0] if test_doc else "Behavior not documented"
        
        # Update failure with analysis
        failure.expected_behavior = expected_behavior
        failure.actual_behavior = f"Failed with: {failure.error_message}"
        
        return failure

    def question_assumptions(self, failure: TestFailure) -> List[str]:
        """Question assumptions about the test and implementation."""
        assumptions = [
            "Is the test correctly verifying the intended behavior?",
            "Is the implementation incomplete?",
            "Is the implementation incorrect?",
            "Are all dependencies properly initialized?",
            "Is the test environment properly configured?",
            "Are there edge cases not considered?",
            "Is the error handling appropriate?"
        ]
        return assumptions

    def find_related_failures(self, failure: TestFailure) -> List[TestFailure]:
        """Find related failures in the same test file."""
        # This would typically involve running other tests in the same file
        # For now, return empty list as this requires test runner integration
        return []

    def trace_execution_path(self, failure: TestFailure) -> List[str]:
        """Trace the execution path from test to implementation."""
        path = []
        tb = traceback.extract_tb(failure.__traceback__)
        
        for frame in tb:
            if frame.filename.endswith('.py'):  # Only include Python files
                path.append(f"{frame.filename}:{frame.lineno} - {frame.name}")
        
        return path

    def identify_implementation_gaps(self, execution_path: List[str]) -> List[str]:
        """Identify gaps in the implementation based on execution path."""
        gaps = []
        for step in execution_path:
            if "test_" in step and "core/" not in step:
                gaps.append(f"Missing implementation for test step: {step}")
        return gaps

    def create_investigation(self, failure: TestFailure) -> Investigation:
        """Create a complete investigation for the failure."""
        related_failures = self.find_related_failures(failure)
        execution_path = self.trace_execution_path(failure)
        implementation_gaps = self.identify_implementation_gaps(execution_path)
        
        return Investigation(
            test_failure=failure,
            related_failures=related_failures,
            execution_path=execution_path,
            implementation_gaps=implementation_gaps,
            hypotheses=[],
            verification_steps=[],
            resolution=None
        )

    def generate_hypotheses(self, investigation: Investigation) -> List[Dict[str, Any]]:
        """Generate hypotheses about the root cause."""
        hypotheses = []
        
        # Hypothesis 1: Implementation Gap
        if investigation.implementation_gaps:
            hypotheses.append({
                "type": "implementation_gap",
                "description": "Missing implementation for required functionality",
                "confidence": 0.8,
                "verification_steps": [
                    "Check if all required methods are implemented",
                    "Verify method signatures match interfaces",
                    "Test with minimal implementation"
                ]
            })
        
        # Hypothesis 2: State Management
        hypotheses.append({
            "type": "state_management",
            "description": "Incorrect state management or transitions",
            "confidence": 0.6,
            "verification_steps": [
                "Log state at key points",
                "Verify state transitions",
                "Check for race conditions"
            ]
        })
        
        # Hypothesis 3: Edge Case
        hypotheses.append({
            "type": "edge_case",
            "description": "Unhandled edge case or boundary condition",
            "confidence": 0.5,
            "verification_steps": [
                "Test with boundary values",
                "Check input validation",
                "Verify error handling"
            ]
        })
        
        return hypotheses

    def verify_hypothesis(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Verify a hypothesis through systematic testing."""
        verification_steps = []
        
        for step in hypothesis["verification_steps"]:
            verification_steps.append({
                "step": step,
                "status": "pending",
                "result": None,
                "timestamp": datetime.utcnow()
            })
        
        return verification_steps

    def resolve_issue(self, investigation: Investigation, fix: Dict[str, Any]) -> Investigation:
        """Record the resolution of the issue."""
        investigation.resolution = {
            "fix": fix,
            "timestamp": datetime.utcnow(),
            "verified": False
        }
        return investigation

    def save_investigation(self, investigation: Investigation, path: Path) -> None:
        """Save the investigation to a file."""
        with open(path, 'w') as f:
            f.write(investigation.json(indent=2))

    def load_investigation(self, path: Path) -> Investigation:
        """Load an investigation from a file."""
        with open(path, 'r') as f:
            return Investigation.parse_raw(f.read())

    def handle_persistent_error(self, error: Exception, count: int) -> List[str]:
        """Handle errors that occur multiple times."""
        if count >= 2:
            reasoning = [
                "Component Architecture Analysis:\n"
                "Review the entire component's architecture, not just the specific function. "
                "Consider how data flows between components and where state is managed.",
                
                "Edge Cases and State Management:\n"
                "Consider edge cases that might not be immediately obvious. "
                "Review how state is managed across the component and potential race conditions.",
                
                "Dependency and Integration Analysis:\n"
                "Examine how this component integrates with others. "
                "Consider timing issues, resource contention, and dependency management."
            ]
            return reasoning
        return [] 