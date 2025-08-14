"""
Multi-step reasoning engine for GraphRAG.

This module provides sophisticated reasoning capabilities that can break down
complex questions into multiple steps, execute each step using the GraphRAG engine,
and chain the results together for comprehensive answers.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.core.reasoning_chain import ReasoningChain, ReasoningStep

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """Result of a multi-step reasoning process."""
    
    question: str
    reasoning_chain: ReasoningChain
    final_answer: str
    synthesis_reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_step_by_name(self, step_name: str) -> Optional[ReasoningStep]:
        """Get a specific step from the reasoning chain by name."""
        for step in self.reasoning_chain.steps:
            if step.name == step_name:
                return step
        return None
    
    def get_visualization(self) -> Dict[str, Any]:
        """Get a visualization-friendly representation of the reasoning process."""
        return {
            "question": self.question,
            "steps": [
                {
                    "name": step.name,
                    "description": step.description,
                    "status": step.status,
                    "query": step.query,
                    "answer": step.result.answer if step.result else None,
                    "reasoning": step.reasoning
                }
                for step in self.reasoning_chain.steps
            ],
            "final_answer": self.final_answer,
            "synthesis_reasoning": self.synthesis_reasoning,
            "summary": self.reasoning_chain.get_summary()
        }


class MultiStepReasoningEngine:
    """
    Engine for executing multi-step reasoning chains using GraphRAG.
    
    This engine can break down complex questions into reasoning steps,
    execute each step using the underlying GraphRAG engine, and chain
    the results together for sophisticated question answering.
    """
    
    def __init__(self, graph_rag_engine: SimpleGraphRAGEngine):
        """
        Initialize the reasoning engine.
        
        Args:
            graph_rag_engine: The underlying GraphRAG engine to use for individual steps
        """
        self.graph_rag_engine = graph_rag_engine
        logger.info(f"MultiStepReasoningEngine initialized with {type(graph_rag_engine).__name__}")
    
    async def reason(
        self,
        question: str,
        steps: Optional[List[Union[str, ReasoningStep]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        Execute multi-step reasoning for a complex question.
        
        Args:
            question: The complex question to answer
            steps: List of reasoning steps to execute, or None to auto-generate
            config: Configuration options for reasoning
            
        Returns:
            ReasoningResult with the complete reasoning process and final answer
        """
        logger.info(f"Starting multi-step reasoning for question: {question}")
        
        config = config or {}
        
        # Generate steps if not provided
        if steps is None:
            steps = await self._generate_steps_for_question(question, config)
        
        # Create reasoning chain
        reasoning_chain = ReasoningChain(question=question, steps=steps)
        
        # Execute each step in the chain
        await self._execute_reasoning_chain(reasoning_chain, config)
        
        # Synthesize final answer from all steps
        final_answer, synthesis_reasoning = await self._synthesize_final_answer(
            reasoning_chain, config
        )
        
        result = ReasoningResult(
            question=question,
            reasoning_chain=reasoning_chain,
            final_answer=final_answer,
            synthesis_reasoning=synthesis_reasoning,
            metadata={
                "total_steps": len(reasoning_chain.steps),
                "completed_steps": len(reasoning_chain.get_all_completed_steps()),
                "config": config
            }
        )
        
        logger.info(f"Multi-step reasoning completed with {len(reasoning_chain.steps)} steps")
        return result
    
    async def _generate_steps_for_question(
        self, 
        question: str, 
        config: Dict[str, Any]
    ) -> List[str]:
        """
        Automatically generate reasoning steps for a question.
        
        Args:
            question: The question to generate steps for
            config: Configuration options
            
        Returns:
            List of step names
        """
        # For now, provide a simple heuristic-based step generation
        # In a production system, this could use the LLM to generate steps
        
        question_lower = question.lower()
        
        # Default steps for different question types
        if any(keyword in question_lower for keyword in ["security", "vulnerability", "risk"]):
            return [
                "identify_security_components",
                "analyze_threat_vectors", 
                "assess_vulnerabilities",
                "recommend_mitigations"
            ]
        elif any(keyword in question_lower for keyword in ["architecture", "design", "system"]):
            return [
                "identify_system_components",
                "analyze_component_relationships",
                "evaluate_architecture_patterns"
            ]
        elif any(keyword in question_lower for keyword in ["performance", "scalability"]):
            return [
                "identify_performance_bottlenecks",
                "analyze_scaling_patterns",
                "recommend_optimizations"
            ]
        else:
            # Generic reasoning steps
            return [
                "gather_relevant_information",
                "analyze_key_concepts",
                "synthesize_insights"
            ]
    
    async def _execute_reasoning_chain(
        self, 
        reasoning_chain: ReasoningChain, 
        config: Dict[str, Any]
    ) -> None:
        """
        Execute all steps in a reasoning chain.
        
        Args:
            reasoning_chain: The chain to execute
            config: Configuration options
        """
        while not reasoning_chain.is_complete:
            current_step = reasoning_chain.get_current_step()
            if current_step is None:
                break
            
            logger.debug(f"Executing reasoning step: {current_step.name}")
            
            try:
                await self._execute_single_step(current_step, reasoning_chain, config)
                current_step.status = "completed"
            except Exception as e:
                logger.error(f"Step {current_step.name} failed: {e}", exc_info=True)
                current_step.status = "failed"
                current_step.reasoning = f"Step failed with error: {str(e)}"
            
            reasoning_chain.advance_to_next_step()
    
    async def _execute_single_step(
        self, 
        step: ReasoningStep, 
        reasoning_chain: ReasoningChain, 
        config: Dict[str, Any]
    ) -> None:
        """
        Execute a single reasoning step.
        
        Args:
            step: The step to execute
            reasoning_chain: The complete reasoning chain for context
            config: Configuration options
        """
        step.status = "running"
        
        # Build context from previous steps
        context = reasoning_chain.build_context_from_previous_steps()
        step.context_from_previous = context
        
        # Construct query for this step
        if context:
            step.query = f"{context}\n\nBased on the above context and focusing on {step.name.replace('_', ' ')}, {step.query or step.description}"
        else:
            step.query = f"Focusing on {step.name.replace('_', ' ')}, {step.query or step.description} for the question: {reasoning_chain.question}"
        
        # Execute the step using the GraphRAG engine
        step.result = await self.graph_rag_engine.query(step.query, config)
        
        # Add step-specific reasoning
        step.reasoning = self._generate_step_reasoning(step, reasoning_chain)
    
    def _generate_step_reasoning(
        self, 
        step: ReasoningStep, 
        reasoning_chain: ReasoningChain
    ) -> str:
        """
        Generate reasoning explanation for a step.
        
        Args:
            step: The executed step
            reasoning_chain: The complete reasoning chain
            
        Returns:
            Reasoning explanation string
        """
        if not step.result:
            return "Step execution failed"
        
        context_used = "with context from previous steps" if step.context_from_previous else "without previous context"
        return (
            f"Executed step '{step.name}' {context_used}. "
            f"Query processed: '{step.query[:100]}...' "
            f"Retrieved {len(step.result.relevant_chunks)} relevant chunks. "
            f"Answer: {step.result.answer[:200]}..."
        )
    
    async def _synthesize_final_answer(
        self, 
        reasoning_chain: ReasoningChain, 
        config: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Synthesize a final answer from all reasoning steps.
        
        Args:
            reasoning_chain: The completed reasoning chain
            config: Configuration options
            
        Returns:
            Tuple of (final_answer, synthesis_reasoning)
        """
        completed_steps = reasoning_chain.get_all_completed_steps()
        
        if not completed_steps:
            return "Unable to provide an answer - no reasoning steps completed successfully.", "No steps completed"
        
        # Collect all step results
        step_answers = []
        for step in completed_steps:
            if step.result and step.result.answer:
                step_answers.append(f"From {step.name}: {step.result.answer}")
        
        if not step_answers:
            return "Unable to provide an answer based on the completed steps.", "No valid step results"
        
        # Create synthesis query
        synthesis_context = "\n\n".join(step_answers)
        synthesis_query = (
            f"Based on the following step-by-step reasoning results, provide a comprehensive answer "
            f"to the original question: '{reasoning_chain.question}'\n\n"
            f"Reasoning steps and their results:\n{synthesis_context}\n\n"
            f"Final comprehensive answer:"
        )
        
        # Use the GraphRAG engine to synthesize the final answer
        try:
            synthesis_result = await self.graph_rag_engine.query(synthesis_query, config)
            final_answer = synthesis_result.answer
            synthesis_reasoning = (
                f"Synthesized answer from {len(completed_steps)} reasoning steps. "
                f"Combined insights from: {', '.join([step.name for step in completed_steps])}"
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Fallback to simple concatenation
            final_answer = "\n\n".join([
                f"{step.name}: {step.result.answer}" 
                for step in completed_steps 
                if step.result and step.result.answer
            ])
            synthesis_reasoning = f"Fallback synthesis due to error: {str(e)}"
        
        return final_answer, synthesis_reasoning