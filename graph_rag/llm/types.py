from typing import TypeVar, Dict, Any, List

# Type variable for LLM responses
LLM = TypeVar("LLM")

# Type aliases for common LLM-related data structures
EntityDict = Dict[str, Any]
RelationshipDict = Dict[str, Any]
MessageDict = Dict[str, str]
ConversationHistory = List[MessageDict]

# Type alias for embedding vectors
EmbeddingVector = List[float]

# Type alias for token usage statistics
TokenUsageStats = Dict[str, int] 