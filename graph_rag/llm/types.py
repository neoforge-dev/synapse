from typing import Any, TypeVar

# Type variable for LLM responses
LLM = TypeVar("LLM")

# Type aliases for common LLM-related data structures
EntityDict = dict[str, Any]
RelationshipDict = dict[str, Any]
MessageDict = dict[str, str]
ConversationHistory = list[MessageDict]

# Type alias for embedding vectors
EmbeddingVector = list[float]

# Type alias for token usage statistics
TokenUsageStats = dict[str, int]
