"""CLI-specific error handling and user guidance utilities."""

import logging
import sys
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from graph_rag.api.errors import (
    ConfigurationError,
    EmbeddingServiceError,
    ErrorClassifier,
    GraphRAGError,
    IngestionError,
    MemgraphConnectionError,
    SearchError,
    ServiceUnavailableError,
    VectorStoreError,
)

logger = logging.getLogger(__name__)
console = Console()


class CLIErrorHandler:
    """Enhanced error handler for CLI commands with user-friendly guidance."""
    
    @staticmethod
    def handle_cli_error(error: Exception, command_context: Dict[str, Any] | None = None) -> None:
        """
        Handle CLI errors with appropriate user guidance and exit codes.
        
        Args:
            error: The exception that occurred
            command_context: Context about the command being executed
        """
        command_context = command_context or {}
        command_name = command_context.get("command", "unknown")
        
        # Classify the error if it's not already a GraphRAGError
        if isinstance(error, GraphRAGError):
            graph_error = error
        else:
            graph_error = ErrorClassifier.classify_error(error, command_context)
        
        # Display user-friendly error message
        CLIErrorHandler._display_error_message(graph_error, command_name)
        
        # Determine appropriate exit code
        exit_code = CLIErrorHandler._get_exit_code(graph_error)
        
        # Log technical details for debugging
        logger.error(
            f"CLI error in {command_name}: {error}",
            exc_info=True,
            extra={"command_context": command_context}
        )
        
        raise typer.Exit(exit_code)
    
    @staticmethod
    def _display_error_message(error: GraphRAGError, command_name: str) -> None:
        """Display a user-friendly error message with recovery suggestions."""
        
        # Error title with emoji for visual appeal
        if isinstance(error, MemgraphConnectionError):
            title = "🔌 Knowledge Graph Unavailable"
        elif isinstance(error, VectorStoreError):
            title = "🗂️ Vector Search Unavailable"
        elif isinstance(error, EmbeddingServiceError):
            title = "🧠 Embedding Service Unavailable"
        elif isinstance(error, IngestionError):
            title = "📄 Document Processing Failed"
        elif isinstance(error, SearchError):
            title = "🔍 Search Failed"
        elif isinstance(error, ConfigurationError):
            title = "⚙️ Configuration Issue"
        else:
            title = "❌ Operation Failed"
        
        # Create error panel
        error_text = Text()
        error_text.append(f"{error.message}\n\n", style="bold red")
        
        # Add recovery suggestions if available
        recovery_suggestions = getattr(error, 'details', {}).get('recovery_suggestions', [])
        if recovery_suggestions:
            error_text.append("💡 Try these solutions:\n", style="bold yellow")
            for i, suggestion in enumerate(recovery_suggestions, 1):
                error_text.append(f"  {i}. {suggestion}\n", style="cyan")
        
        # Add context-specific suggestions
        context_suggestions = CLIErrorHandler._get_context_suggestions(error, command_name)
        if context_suggestions:
            error_text.append("\n🛠️ Command-specific help:\n", style="bold blue")
            for suggestion in context_suggestions:
                error_text.append(f"  • {suggestion}\n", style="blue")
        
        # Add general help
        error_text.append(f"\n📚 Get help: synapse {command_name} --help", style="dim")
        error_text.append(f"\n🩺 System status: synapse admin health", style="dim")
        
        # Display the panel
        console.print(Panel(
            error_text,
            title=title,
            border_style="red",
            width=80
        ))
    
    @staticmethod
    def _get_context_suggestions(error: GraphRAGError, command_name: str) -> list[str]:
        """Get command-specific recovery suggestions."""
        suggestions = []
        
        if command_name == "ingest":
            if isinstance(error, MemgraphConnectionError):
                suggestions.extend([
                    "Start Memgraph: make run-memgraph",
                    "Try ingesting without graph: synapse ingest --no-graph <path>",
                    "Verify Memgraph is accessible: docker ps | grep memgraph"
                ])
            elif isinstance(error, EmbeddingServiceError):
                suggestions.extend([
                    "Ingest without embeddings: synapse ingest --no-embeddings <path>",
                    "Use mock embeddings: synapse ingest --mock-embeddings <path>"
                ])
            elif isinstance(error, IngestionError):
                suggestions.extend([
                    "Try with replace flag: synapse ingest --replace <path>",
                    "Check file format: synapse parse <path>",
                    "Ingest smaller batches: synapse ingest --batch-size 10 <path>"
                ])
        
        elif command_name == "search":
            if isinstance(error, MemgraphConnectionError):
                suggestions.extend([
                    "Use vector-only search: synapse search --vector-only '<query>'",
                    "Try keyword search: synapse search --keyword '<query>'"
                ])
            elif isinstance(error, VectorStoreError):
                suggestions.extend([
                    "Use graph-only search: synapse search --graph-only '<query>'",
                    "Rebuild vector index: synapse admin rebuild-vectors"
                ])
            elif isinstance(error, SearchError):
                suggestions.extend([
                    "Simplify your query: use fewer and simpler terms",
                    "Check available documents: synapse admin stats"
                ])
        
        elif command_name == "query":
            if isinstance(error, (MemgraphConnectionError, VectorStoreError)):
                suggestions.extend([
                    "Use simplified search: synapse search '<simplified query>'",
                    "Check if documents are ingested: synapse admin list-documents"
                ])
        
        elif command_name == "store":
            if isinstance(error, MemgraphConnectionError):
                suggestions.extend([
                    "Start Memgraph first: make run-memgraph",
                    "Store in vector-only mode: synapse store --vector-only <parsed-file>"
                ])
        
        return suggestions
    
    @staticmethod
    def _get_exit_code(error: GraphRAGError) -> int:
        """Determine appropriate exit code based on error type."""
        if isinstance(error, ConfigurationError):
            return 78  # EX_CONFIG
        elif isinstance(error, (MemgraphConnectionError, ServiceUnavailableError)):
            return 69  # EX_UNAVAIL
        elif isinstance(error, IngestionError):
            if error.details.get("recoverable", True):
                return 75  # EX_TEMPFAIL
            else:
                return 66  # EX_NOINPUT
        elif isinstance(error, (VectorStoreError, EmbeddingServiceError)):
            return 75  # EX_TEMPFAIL
        else:
            return 70  # EX_SOFTWARE


def handle_cli_error(command_name: str):
    """Decorator to handle CLI errors for specific commands."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, typer.Exit):
                    raise  # Don't interfere with intentional exits
                CLIErrorHandler.handle_cli_error(e, {"command": command_name})
        return wrapper
    return decorator


def safe_async_run(coro, command_name: str):
    """Safely run an async coroutine with error handling."""
    import asyncio
    
    try:
        return asyncio.run(coro)
    except Exception as e:
        CLIErrorHandler.handle_cli_error(e, {"command": command_name})


# Convenience functions for common error scenarios
def handle_connection_error(service_name: str, error: Exception, command_name: str) -> None:
    """Handle connection errors with service-specific guidance."""
    if "memgraph" in service_name.lower():
        raise MemgraphConnectionError(reason=str(error))
    else:
        raise ServiceUnavailableError(
            service_name,
            reason=str(error),
            recovery_suggestions=[
                f"Check if {service_name} is running and accessible",
                "Verify configuration settings",
                f"Try alternative approach if available for {command_name} command"
            ]
        )


def handle_file_error(file_path: str, error: Exception) -> None:
    """Handle file-related errors with specific guidance."""
    error_msg = str(error).lower()
    
    if "permission denied" in error_msg:
        raise ConfigurationError(
            config_key="file_permissions",
            reason=f"Cannot access file '{file_path}': Permission denied"
        )
    elif "not found" in error_msg:
        raise ConfigurationError(
            config_key="file_path",
            reason=f"File not found: '{file_path}'"
        )
    else:
        raise IngestionError(
            document_id=file_path,
            stage="file_access",
            reason=str(error),
            recoverable=True
        )


def suggest_alternative_workflow(primary_error: GraphRAGError, command_name: str) -> None:
    """Suggest alternative workflows when primary approach fails."""
    alternatives = []
    
    if isinstance(primary_error, MemgraphConnectionError):
        if command_name == "ingest":
            alternatives.append("synapse ingest --vector-only <path>  # Store in vector search only")
        elif command_name == "search":
            alternatives.append("synapse search --vector-only '<query>'  # Vector search only")
    
    elif isinstance(primary_error, VectorStoreError):
        if command_name == "search":
            alternatives.append("synapse search --graph-only '<query>'  # Graph search only")
    
    elif isinstance(primary_error, EmbeddingServiceError):
        if command_name == "ingest":
            alternatives.append("synapse ingest --no-embeddings <path>  # Skip embeddings")
    
    if alternatives:
        console.print("\n🔄 Alternative approaches:", style="bold green")
        for alt in alternatives:
            console.print(f"  {alt}", style="green")


def handle_ingestion_error(document_id: str, error: Exception) -> None:
    """Handle ingestion-specific errors with appropriate guidance."""
    error_msg = str(error).lower()
    
    if "embedding" in error_msg:
        raise EmbeddingServiceError(
            reason=str(error),
            recovery_suggestions=[
                "Try ingesting without embeddings: --no-embeddings",
                "Use mock embeddings: --mock-embeddings",
                "Check embedding service configuration"
            ]
        )
    elif "graph" in error_msg or "memgraph" in error_msg:
        raise MemgraphConnectionError(reason=str(error))
    else:
        raise IngestionError(
            document_id=document_id,
            stage="processing",
            reason=str(error),
            recoverable=True
        )