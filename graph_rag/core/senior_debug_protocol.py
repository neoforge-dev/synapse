"""Senior Developer Debugging Protocol Implementation."""

import importlib.util
import inspect
import logging
import sys  # Import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TestFailure(BaseModel):
    __test__ = False  # Prevent pytest collection
    """Represents a test failure with context."""
    error_message: str
    test_file: str
    test_function: str
    test_parameters: Optional[dict[str, Any]] = None  # Parameters used in the test
    test_code: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    traceback_str: Optional[str] = None  # Store traceback as string
    expected_behavior: Optional[str] = None  # Added field
    actual_behavior: Optional[str] = None  # Added field
    # traceback: Optional[Any] = None # Store raw traceback object


class Investigation(BaseModel):
    """Represents a debugging investigation."""

    test_failure: TestFailure
    related_failures: list[TestFailure]
    execution_path: list[dict[str, Any]]
    implementation_gaps: list[str]
    hypotheses: list[dict[str, Any]]
    verification_steps: list[dict[str, Any]]
    resolution: Optional[dict[str, Any]] = None


class SeniorDebugProtocol:
    """Implements the Senior Developer Debugging Protocol."""

    def __init__(self, test_file: str, test_function: str):
        self.test_file = test_file
        self.test_function = test_function
        self.investigation = None

    def observe_failure(self, error: Exception) -> TestFailure:
        """Observe a test failure and capture context."""
        exc_type, exc_value, exc_tb = sys.exc_info()  # Get exception info
        # frame = inspect.currentframe().f_back # Get the caller frame (the test function)
        # test_function_name = frame.f_code.co_name
        # test_file = inspect.getfile(frame)
        test_function_name = self.test_function  # Use name from instance
        test_file = self.test_file  # Use file from instance

        # Capture test code snippet (adjust lines before/after as needed)
        try:
            # Need the frame where the error actually happened, not the caller of observe_failure
            # This part is tricky without direct traceback access or runner integration
            # Let's try to get it from the traceback if available
            if exc_tb:
                frame = exc_tb.tb_frame
                lines, lineno = inspect.getsourcelines(frame)
                start = max(0, frame.f_lineno - 1 - 2)  # Use frame lineno (1-based)
                end = min(len(lines), frame.f_lineno - 1 + 3)
                test_code = "".join(lines[start:end])
            else:
                test_code = "Could not retrieve test source code (no traceback frame)."
        except Exception as e:
            logger.warning(f"Error retrieving source code: {e}")
            test_code = "Could not retrieve test source code."

        # Capture traceback as string
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        failure_data = TestFailure(
            error_message=str(error),
            test_file=test_file,  # Use relative path from instance
            test_function=test_function_name,
            test_code=test_code,
            traceback_str=tb_str,  # Store string traceback
            # traceback=exc_tb, # Store raw traceback object
            # TODO: Capture test parameters if possible (might require pytest hooks or fixture inspection)
        )
        # We should store failures per test case, perhaps in a dict keyed by test name
        # self.failures.append(failure_data)
        logger.info(f"Observed failure in {test_function_name}: {error}")
        return failure_data

    def analyze_test_case(self, failure: TestFailure) -> TestFailure:
        """Analyze what the test is verifying and expected behavior."""
        # Get the test function's source code
        try:
            # Attempt to load the module from the file path in the failure object
            spec = importlib.util.spec_from_file_location(
                "test_module_to_analyze", failure.test_file
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            test_func = getattr(test_module, failure.test_function)
            test_doc = inspect.getdoc(test_func) or ""
        except (FileNotFoundError, AttributeError, ImportError) as e:
            logger.warning(
                f"Could not load test function {failure.test_function} from {failure.test_file}: {e}"
            )
            test_doc = ""

        # Extract expected behavior from docstring
        expected_behavior = (
            test_doc.split("\n")[0] if test_doc else "Behavior not documented"
        )

        # Update failure with analysis (assuming these fields exist or are added to TestFailure model)
        failure.expected_behavior = expected_behavior
        failure.actual_behavior = f"Failed with: {failure.error_message}"
        logger.debug(
            f"Analyzed test {failure.test_function}: Expected: '{expected_behavior}'"
        )

        return failure  # Return modified failure object

    def question_assumptions(self, failure: TestFailure) -> list[str]:
        """Question assumptions about the test and implementation."""
        assumptions = [
            "Is the test correctly verifying the intended behavior?",
            "Is the implementation incomplete?",
            "Is the implementation incorrect?",
            "Are all dependencies properly initialized?",
            "Is the test environment properly configured?",
            "Are there edge cases not considered?",
            "Is the error handling appropriate?",
        ]
        return assumptions

    def find_related_failures(self, failure: TestFailure) -> list[TestFailure]:
        """Find related failures in the same test file."""
        # This would typically involve running other tests in the same file
        # For now, return empty list as this requires test runner integration
        return []

    def trace_execution_path(self, failure: TestFailure) -> list[dict[str, Any]]:
        """Trace the execution path leading to the failure using stored traceback string."""
        if not failure.traceback_str:
            return [{"error": "No traceback available."}]

        # Parse the traceback string (simple parsing, might need refinement)
        path = []
        lines = failure.traceback_str.strip().split("\n")
        # Heuristic: traceback lines often start with "  File ..."
        for line in lines:
            line = line.strip()
            if line.startswith("File"):
                parts = line.split(",")
                file_path = parts[0].replace('File "', "").replace('"', "").strip()
                line_no = (
                    parts[1].replace("line ", "").strip() if len(parts) > 1 else "N/A"
                )
                func_name = (
                    parts[2].replace("in ", "").strip() if len(parts) > 2 else "N/A"
                )
                path.append({"file": file_path, "line": line_no, "function": func_name})
            elif not line.startswith(("Traceback", "During handling")):
                # Append code snippet lines associated with the frame
                if path:  # Ensure we have a frame to associate with
                    path[-1]["code"] = path[-1].get("code", "") + line + "\n"
        return path

    def identify_implementation_gaps(self, execution_path: list[str]) -> list[str]:
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
            resolution=None,
        )

    def generate_hypotheses(self, investigation: Investigation) -> list[dict[str, Any]]:
        """Generate hypotheses about the root cause."""
        hypotheses = []

        # Hypothesis 1: Implementation Gap
        if investigation.implementation_gaps:
            hypotheses.append(
                {
                    "type": "implementation_gap",
                    "description": "Missing implementation for required functionality",
                    "confidence": 0.8,
                    "verification_steps": [
                        "Check if all required methods are implemented",
                        "Verify method signatures match interfaces",
                        "Test with minimal implementation",
                    ],
                }
            )

        # Hypothesis 2: State Management
        hypotheses.append(
            {
                "type": "state_management",
                "description": "Incorrect state management or transitions",
                "confidence": 0.6,
                "verification_steps": [
                    "Log state at key points",
                    "Verify state transitions",
                    "Check for race conditions",
                ],
            }
        )

        # Hypothesis 3: Edge Case
        hypotheses.append(
            {
                "type": "edge_case",
                "description": "Unhandled edge case or boundary condition",
                "confidence": 0.5,
                "verification_steps": [
                    "Test with boundary values",
                    "Check input validation",
                    "Verify error handling",
                ],
            }
        )

        return hypotheses

    def verify_hypothesis(self, hypothesis: dict[str, Any]) -> list[dict[str, Any]]:
        """Verify a hypothesis through systematic testing."""
        verification_steps = []

        for step in hypothesis["verification_steps"]:
            verification_steps.append(
                {
                    "step": step,
                    "status": "pending",
                    "result": None,
                    "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            )

        return verification_steps

    def resolve_issue(
        self, investigation: Investigation, fix: dict[str, Any]
    ) -> Investigation:
        """Record the resolution of the issue."""
        investigation.resolution = {
            "fix": fix,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
            "verified": False,
        }
        return investigation

    def save_investigation(self, investigation: Investigation, path: Path) -> None:
        """Save the investigation to a file."""
        with open(path, "w") as f:
            f.write(investigation.model_dump_json(indent=2))

    def load_investigation(self, path: Path) -> Investigation:
        """Load an investigation from a file."""
        with open(path) as f:
            return Investigation.parse_raw(f.read())

    def handle_persistent_error(self, error: Exception, count: int) -> list[str]:
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
                "Consider timing issues, resource contention, and dependency management.",
            ]
            return reasoning
        return []
