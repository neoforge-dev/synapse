"""
Reasoning chain implementation for multi-step reasoning in GraphRAG.

This module provides classes to track and manage complex reasoning processes
that break down questions into multiple interconnected steps.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from graph_rag.core.graph_rag_engine import QueryResult

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """Represents a single step in a reasoning chain."""
    
    name: str
    description: str = ""
    query: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[QueryResult] = None
    reasoning: Optional[str] = None
    context_from_previous: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize step-specific attributes after dataclass creation."""
        if not self.description:
            self.description = f"Execute reasoning step: {self.name}"
        
        if not self.query:
            self.query = f"Based on the context, {self.name.replace('_', ' ')}"


class ReasoningChain:
    """Manages a chain of reasoning steps for complex question answering."""
    
    def __init__(self, question: str, steps: List[Union[str, ReasoningStep]]):
        """
        Initialize a reasoning chain.
        
        Args:
            question: The original complex question to be answered
            steps: List of step names or ReasoningStep objects
        """
        self.question = question
        self.current_step_index = 0
        self.metadata: Dict[str, Any] = {}
        
        # Convert string steps to ReasoningStep objects
        self.steps: List[ReasoningStep] = []
        for step in steps:
            if isinstance(step, str):
                self.steps.append(ReasoningStep(name=step))
            elif isinstance(step, ReasoningStep):
                self.steps.append(step)
            else:
                raise ValueError(f"Step must be string or ReasoningStep, got {type(step)}")
        
        logger.info(f"Created reasoning chain with {len(self.steps)} steps for question: {question}")
    
    @property
    def is_complete(self) -> bool:
        """Check if all steps have been completed."""
        return self.current_step_index >= len(self.steps)
    
    def get_current_step(self) -> Optional[ReasoningStep]:
        """Get the current step in the chain."""
        if self.is_complete:
            return None
        return self.steps[self.current_step_index]
    
    def advance_to_next_step(self) -> bool:
        """
        Advance to the next step in the chain.
        
        Returns:
            True if advanced successfully, False if already at the end
        """
        if not self.is_complete:
            self.current_step_index += 1
            return True
        return False
    
    def get_previous_step_results(self, num_steps: int = 1) -> List[ReasoningStep]:
        """
        Get results from previous steps for context.
        
        Args:
            num_steps: Number of previous steps to include
            
        Returns:
            List of completed previous steps
        """
        if self.current_step_index == 0:
            return []
        
        start_idx = max(0, self.current_step_index - num_steps)
        return [
            step for step in self.steps[start_idx:self.current_step_index]
            if step.status == "completed" and step.result is not None
        ]
    
    def get_all_completed_steps(self) -> List[ReasoningStep]:
        """Get all completed steps in the chain."""
        return [step for step in self.steps if step.status == "completed"]
    
    def build_context_from_previous_steps(self, num_steps: int = 2) -> str:
        """
        Build context string from previous step results.
        
        Args:
            num_steps: Number of previous steps to include in context
            
        Returns:
            Formatted context string
        """
        previous_steps = self.get_previous_step_results(num_steps)
        if not previous_steps:
            return ""
        
        context_parts = []
        for step in previous_steps:
            if step.result and step.result.answer:
                context_parts.append(f"From {step.name}: {step.result.answer}")
        
        if not context_parts:
            return ""
        
        return "\n".join([
            "Context from previous reasoning steps:",
            *context_parts,
            ""
        ])
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the reasoning chain progress."""
        completed_count = sum(1 for step in self.steps if step.status == "completed")
        failed_count = sum(1 for step in self.steps if step.status == "failed")
        
        return {
            "question": self.question,
            "total_steps": len(self.steps),
            "completed_steps": completed_count,
            "failed_steps": failed_count,
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "step_names": [step.name for step in self.steps]
        }