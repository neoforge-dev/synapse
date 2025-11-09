"""Knowledge-optimized prompt templates for Graph RAG synthesis."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PromptStyle(Enum):
    """Different styles of answer generation."""
    CONCISE = "concise"           # Brief, to-the-point answers
    ANALYTICAL = "analytical"     # In-depth analysis with reasoning
    TEACHING = "teaching"         # Educational, step-by-step explanations
    SCHOLARLY = "scholarly"       # Academic-style with formal language
    CONVERSATIONAL = "conversational"  # Natural, dialogue-style responses
    TECHNICAL = "technical"       # Detailed technical explanations
    EXECUTIVE = "executive"       # High-level summary for decision makers


class ContextType(Enum):
    """Types of context that can be provided."""
    DOCUMENT_CHUNKS = "document_chunks"
    GRAPH_ENTITIES = "graph_entities"
    GRAPH_RELATIONSHIPS = "graph_relationships"
    CONVERSATION_HISTORY = "conversation_history"
    MIXED = "mixed"


@dataclass
class PromptTemplate:
    """A prompt template with placeholders and formatting rules."""

    name: str
    style: PromptStyle
    context_types: list[ContextType]

    # Template components
    system_prompt: str
    instruction_template: str
    context_template: str
    query_template: str

    # Quality indicators
    confidence_instructions: str = ""
    citation_instructions: str = ""
    uncertainty_handling: str = ""

    # Constraints
    max_length_instruction: str = ""
    format_requirements: str = ""

    # Metadata
    description: str = ""
    use_cases: list[str] = field(default_factory=list)

    def format_prompt(
        self,
        query: str,
        context: str = "",
        conversation_history: str = "",
        additional_instructions: str = "",
        **kwargs
    ) -> str:
        """Format the complete prompt with provided context."""

        # Build system prompt
        system_section = self.system_prompt

        # Build instruction section
        instructions = self.instruction_template
        if additional_instructions:
            instructions += f"\n\nAdditional Instructions:\n{additional_instructions}"

        # Build context section
        context_section = ""
        if context:
            context_section = self.context_template.format(context=context)

        # Build conversation history section
        history_section = ""
        if conversation_history:
            history_section = f"\n\nConversation History:\n{conversation_history}"

        # Build query section
        query_section = self.query_template.format(query=query, **kwargs)

        # Combine all sections
        full_prompt = f"{system_section}\n\n{instructions}"

        if context_section:
            full_prompt += f"\n\n{context_section}"

        if history_section:
            full_prompt += history_section

        full_prompt += f"\n\n{query_section}"

        return full_prompt.strip()


class PromptOptimizer:
    """Service for optimizing prompts for knowledge work."""

    def __init__(self):
        self.templates = self._create_default_templates()

    def _create_default_templates(self) -> dict[str, PromptTemplate]:
        """Create the default set of knowledge-optimized prompt templates."""
        templates = {}

        # Concise Knowledge Extraction Template
        templates["concise_knowledge"] = PromptTemplate(
            name="concise_knowledge",
            style=PromptStyle.CONCISE,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.GRAPH_ENTITIES],
            system_prompt=(
                "You are a knowledge extraction assistant that provides precise, "
                "factual answers based on source material. Focus on accuracy and brevity."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Answer directly and concisely based only on the provided context\n"
                "2. If information is incomplete, state what is missing\n"
                "3. Use specific facts, numbers, and details from the sources\n"
                "4. Cite sources using [1], [2] format for factual claims\n"
                "5. If you cannot answer from the context, say so explicitly"
            ),
            context_template="Source Material:\n{context}",
            query_template="Query: {query}\n\nAnswer:",
            confidence_instructions="Indicate your confidence level (High/Medium/Low) if uncertain.",
            citation_instructions="Cite sources for all factual claims using [number] format.",
            uncertainty_handling="If information is unclear or missing, explicitly state limitations.",
            description="Optimized for quick, accurate fact retrieval from knowledge bases."
        )

        # Analytical Deep-Dive Template
        templates["analytical_deep"] = PromptTemplate(
            name="analytical_deep",
            style=PromptStyle.ANALYTICAL,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.GRAPH_RELATIONSHIPS],
            system_prompt=(
                "You are an analytical research assistant that provides comprehensive, "
                "well-reasoned analysis based on source material. Connect ideas and "
                "explain relationships between concepts."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Provide a thorough analysis that synthesizes information from multiple sources\n"
                "2. Explain the reasoning behind your conclusions\n"
                "3. Identify patterns, relationships, and connections between concepts\n"
                "4. Present evidence systematically and cite all sources\n"
                "5. Address potential counterarguments or limitations\n"
                "6. Structure your response with clear sections if needed"
            ),
            context_template="Research Materials:\n{context}",
            query_template="Research Question: {query}\n\nAnalysis:",
            confidence_instructions=(
                "Assess the strength of evidence for each claim. "
                "Distinguish between well-supported conclusions and tentative findings."
            ),
            citation_instructions=(
                "Provide detailed citations showing which sources support each point. "
                "Use [1], [2] format and reference specific sections when possible."
            ),
            uncertainty_handling=(
                "Explicitly discuss areas where evidence is limited, conflicting, or inconclusive. "
                "Suggest what additional information would strengthen the analysis."
            ),
            description="Designed for comprehensive research and analytical tasks."
        )

        # Teaching and Explanation Template
        templates["teaching_explanation"] = PromptTemplate(
            name="teaching_explanation",
            style=PromptStyle.TEACHING,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.CONVERSATION_HISTORY],
            system_prompt=(
                "You are an expert teacher who explains complex topics clearly and systematically. "
                "Break down information into digestible steps and provide context for understanding."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Start with a clear, simple overview of the topic\n"
                "2. Break complex concepts into step-by-step explanations\n"
                "3. Use examples and analogies to clarify difficult points\n"
                "4. Build from basic to advanced concepts progressively\n"
                "5. Anticipate and address common questions or misconceptions\n"
                "6. Provide practical applications or relevance where appropriate\n"
                "7. Cite sources to allow for further learning"
            ),
            context_template="Educational Materials:\n{context}",
            query_template="Question: {query}\n\nExplanation:",
            confidence_instructions=(
                "When explaining complex topics, clearly distinguish between "
                "well-established facts and areas of ongoing research or debate."
            ),
            citation_instructions=(
                "Reference sources that students can consult for deeper learning. "
                "Indicate which sources are more accessible for beginners."
            ),
            uncertainty_handling=(
                "When concepts are complex or disputed, explain different perspectives "
                "and help learners understand the current state of knowledge."
            ),
            max_length_instruction="Aim for comprehensive but accessible explanations.",
            description="Optimized for educational content and complex topic explanations."
        )

        # Technical Documentation Template
        templates["technical_docs"] = PromptTemplate(
            name="technical_docs",
            style=PromptStyle.TECHNICAL,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.GRAPH_ENTITIES],
            system_prompt=(
                "You are a technical documentation expert who provides precise, "
                "implementation-focused answers with proper technical detail."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Provide technically accurate and detailed information\n"
                "2. Include specific parameters, configurations, and requirements\n"
                "3. Mention prerequisites, dependencies, and constraints\n"
                "4. Provide code examples or implementation details when relevant\n"
                "5. Include troubleshooting information if available\n"
                "6. Reference official documentation and authoritative sources\n"
                "7. Be precise about versions, specifications, and technical details"
            ),
            context_template="Technical Documentation:\n{context}",
            query_template="Technical Query: {query}\n\nTechnical Response:",
            confidence_instructions=(
                "Indicate confidence levels for technical specifications. "
                "Distinguish between confirmed facts and implementation suggestions."
            ),
            citation_instructions=(
                "Cite official documentation, specifications, and authoritative technical sources. "
                "Include version numbers and specific section references when possible."
            ),
            uncertainty_handling=(
                "When technical details are unclear or version-dependent, "
                "explicitly state limitations and suggest verification steps."
            ),
            format_requirements="Use proper technical formatting with code blocks and structured information.",
            description="Designed for technical documentation and implementation guidance."
        )

        # Executive Summary Template
        templates["executive_summary"] = PromptTemplate(
            name="executive_summary",
            style=PromptStyle.EXECUTIVE,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.GRAPH_RELATIONSHIPS],
            system_prompt=(
                "You are an executive briefing specialist who distills complex information "
                "into clear, actionable insights for decision-makers."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Lead with the most important findings and implications\n"
                "2. Focus on business impact and strategic considerations\n"
                "3. Highlight key risks, opportunities, and trade-offs\n"
                "4. Provide clear recommendations where appropriate\n"
                "5. Quantify impacts with numbers and metrics when available\n"
                "6. Keep technical details minimal unless directly relevant\n"
                "7. Structure information for quick scanning and decision-making"
            ),
            context_template="Source Information:\n{context}",
            query_template="Executive Question: {query}\n\nExecutive Summary:",
            confidence_instructions=(
                "Clearly indicate the reliability of key findings and recommendations. "
                "Highlight areas requiring additional validation."
            ),
            citation_instructions=(
                "Reference sources that executives can review for detailed information. "
                "Prioritize the most credible and recent sources."
            ),
            uncertainty_handling=(
                "Explicitly identify key assumptions and areas of uncertainty that "
                "could impact business decisions."
            ),
            max_length_instruction="Keep response concise but comprehensive for executive consumption.",
            description="Optimized for executive briefings and strategic decision support."
        )

        # Scholarly Research Template
        templates["scholarly_research"] = PromptTemplate(
            name="scholarly_research",
            style=PromptStyle.SCHOLARLY,
            context_types=[ContextType.DOCUMENT_CHUNKS, ContextType.GRAPH_RELATIONSHIPS],
            system_prompt=(
                "You are a scholarly research assistant who provides academically rigorous "
                "responses with proper methodology and comprehensive source attribution."
            ),
            instruction_template=(
                "Instructions:\n"
                "1. Provide academically rigorous analysis with proper methodology\n"
                "2. Present multiple perspectives and acknowledge scholarly debate\n"
                "3. Distinguish between primary and secondary sources\n"
                "4. Discuss methodological considerations and limitations\n"
                "5. Use formal academic language and structure\n"
                "6. Provide comprehensive citations in academic format\n"
                "7. Acknowledge gaps in current research or knowledge"
            ),
            context_template="Academic Sources:\n{context}",
            query_template="Research Question: {query}\n\nScholarly Response:",
            confidence_instructions=(
                "Assess the methodological rigor and reliability of findings. "
                "Distinguish between well-established research and emerging studies."
            ),
            citation_instructions=(
                "Provide full academic citations with author, year, title, and publication details. "
                "Indicate the type and quality of each source."
            ),
            uncertainty_handling=(
                "Thoroughly discuss methodological limitations, conflicting findings, "
                "and areas requiring further research."
            ),
            format_requirements="Use academic formatting with proper structure and formal language.",
            description="Designed for academic research and scholarly inquiry."
        )

        return templates

    def get_template(self, style: PromptStyle, context_type: ContextType = None) -> PromptTemplate:
        """Get the best template for a given style and context type."""

        # Map styles to template names
        style_mapping = {
            PromptStyle.CONCISE: "concise_knowledge",
            PromptStyle.ANALYTICAL: "analytical_deep",
            PromptStyle.TEACHING: "teaching_explanation",
            PromptStyle.TECHNICAL: "technical_docs",
            PromptStyle.EXECUTIVE: "executive_summary",
            PromptStyle.SCHOLARLY: "scholarly_research",
            PromptStyle.CONVERSATIONAL: "concise_knowledge",  # Default to concise
        }

        template_name = style_mapping.get(style, "concise_knowledge")
        template = self.templates.get(template_name)

        if not template:
            logger.warning(f"Template {template_name} not found, using default")
            return self.templates["concise_knowledge"]

        return template

    def optimize_prompt_for_context(
        self,
        query: str,
        context: str,
        style: PromptStyle = PromptStyle.ANALYTICAL,
        conversation_history: str = "",
        confidence_scoring: bool = True,
        citation_required: bool = True,
        max_length: int | None = None,
        **kwargs
    ) -> str:
        """
        Create an optimized prompt for the given query and context.

        Args:
            query: The user's question
            context: Available context (chunks, entities, etc.)
            style: Desired response style
            conversation_history: Previous conversation context
            confidence_scoring: Whether to request confidence indicators
            citation_required: Whether to require source citations
            max_length: Maximum response length constraint

        Returns:
            Optimized prompt string
        """

        # Determine context type
        context_type = self._analyze_context_type(context)

        # Get appropriate template
        template = self.get_template(style, context_type)

        # Build additional instructions
        additional_instructions = []

        if confidence_scoring:
            additional_instructions.append(template.confidence_instructions)

        if citation_required:
            additional_instructions.append(template.citation_instructions)

        if max_length:
            additional_instructions.append(f"Keep response under {max_length} words.")

        # Add uncertainty handling if context is limited
        if len(context.strip()) < 200:  # Very limited context
            additional_instructions.append(template.uncertainty_handling)

        additional_instructions_str = "\n".join(filter(None, additional_instructions))

        # Format the complete prompt
        optimized_prompt = template.format_prompt(
            query=query,
            context=context,
            conversation_history=conversation_history,
            additional_instructions=additional_instructions_str,
            **kwargs
        )

        return optimized_prompt

    def _analyze_context_type(self, context: str) -> ContextType:
        """Analyze the context to determine its primary type."""

        if not context.strip():
            return ContextType.MIXED

        # Look for patterns that indicate context type
        entity_patterns = [r'Entity:', r'- \w+\s+\(\w+\)', r'entities:']
        relationship_patterns = [r'-\[', r'RELATED_TO', r'relationships:', r'→']
        chunk_patterns = [r'Chunk \d+:', r'Source:', r'Document:']

        entity_score = sum(1 for pattern in entity_patterns if re.search(pattern, context, re.IGNORECASE))
        relationship_score = sum(1 for pattern in relationship_patterns if re.search(pattern, context, re.IGNORECASE))
        chunk_score = sum(1 for pattern in chunk_patterns if re.search(pattern, context, re.IGNORECASE))

        # Determine dominant type
        if chunk_score > entity_score and chunk_score > relationship_score:
            return ContextType.DOCUMENT_CHUNKS
        elif entity_score > relationship_score:
            return ContextType.GRAPH_ENTITIES
        elif relationship_score > 0:
            return ContextType.GRAPH_RELATIONSHIPS
        else:
            return ContextType.MIXED

    def get_style_from_string(self, style_str: str) -> PromptStyle:
        """Convert string to PromptStyle enum."""
        # Handle None or empty string
        if not style_str:
            return PromptStyle.ANALYTICAL

        try:
            return PromptStyle(style_str.lower())
        except ValueError:
            logger.warning(f"Unknown style '{style_str}', defaulting to analytical")
            return PromptStyle.ANALYTICAL

    def list_available_templates(self) -> list[dict[str, Any]]:
        """List all available templates with their metadata."""
        return [
            {
                "name": template.name,
                "style": template.style.value,
                "context_types": [ct.value for ct in template.context_types],
                "description": template.description,
                "use_cases": template.use_cases,
            }
            for template in self.templates.values()
        ]

    def add_custom_template(self, template: PromptTemplate) -> None:
        """Add a custom template to the optimizer."""
        self.templates[template.name] = template
        logger.info(f"Added custom template: {template.name}")

    def customize_template(
        self,
        base_template_name: str,
        modifications: dict[str, str],
        new_name: str | None = None
    ) -> PromptTemplate:
        """
        Create a customized version of an existing template.

        Args:
            base_template_name: Name of template to customize
            modifications: Dict of field names to new values
            new_name: Name for the new template (optional)

        Returns:
            New customized template
        """

        base_template = self.templates.get(base_template_name)
        if not base_template:
            raise ValueError(f"Base template '{base_template_name}' not found")

        # Create a copy of the base template
        template_dict = {
            "name": new_name or f"{base_template_name}_custom",
            "style": base_template.style,
            "context_types": base_template.context_types.copy(),
            "system_prompt": base_template.system_prompt,
            "instruction_template": base_template.instruction_template,
            "context_template": base_template.context_template,
            "query_template": base_template.query_template,
            "confidence_instructions": base_template.confidence_instructions,
            "citation_instructions": base_template.citation_instructions,
            "uncertainty_handling": base_template.uncertainty_handling,
            "max_length_instruction": base_template.max_length_instruction,
            "format_requirements": base_template.format_requirements,
            "description": base_template.description,
            "use_cases": base_template.use_cases.copy(),
        }

        # Apply modifications
        for field_name, value in modifications.items():
            if field_name in template_dict:
                template_dict[field_name] = value
            else:
                logger.warning(f"Unknown field '{field_name}' in template customization")

        # Create new template
        custom_template = PromptTemplate(**template_dict)

        # Add to templates if it has a name
        if new_name:
            self.templates[new_name] = custom_template

        return custom_template
