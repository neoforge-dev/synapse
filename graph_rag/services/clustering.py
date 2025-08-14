"""Semantic clustering service for grouping similar content."""

import logging
import math
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

import numpy as np
from pydantic import BaseModel

from graph_rag.core.interfaces import SearchResultData, ChunkData

logger = logging.getLogger(__name__)


class ClusteringStrategy(Enum):
    """Available clustering strategies."""
    KMEANS = "kmeans"
    HIERARCHICAL = "hierarchical"
    TOPIC_BASED = "topic_based"
    SIMILARITY_THRESHOLD = "similarity_threshold"


@dataclass
class ClusterInfo:
    """Information about a cluster."""
    id: str
    centroid: Optional[List[float]]
    size: int
    representative_text: str
    avg_score: float
    diversity_score: float


class ClusterResult(BaseModel):
    """Result of clustering operation."""
    clusters: List[List[SearchResultData]]
    cluster_info: List[ClusterInfo]
    strategy: ClusteringStrategy
    total_clusters: int
    silhouette_score: Optional[float] = None
    
    @property
    def avg_cluster_size(self) -> float:
        if not self.clusters:
            return 0.0
        return sum(len(cluster) for cluster in self.clusters) / len(self.clusters)


class SemanticClusteringService:
    """Service for semantic clustering of search results."""
    
    def __init__(self, min_cluster_size: int = 2, max_clusters: int = 10):
        """Initialize clustering service.
        
        Args:
            min_cluster_size: Minimum number of items per cluster
            max_clusters: Maximum number of clusters to create
        """
        self.min_cluster_size = min_cluster_size
        self.max_clusters = max_clusters
    
    def cluster_results(
        self,
        results: List[SearchResultData],
        strategy: ClusteringStrategy = ClusteringStrategy.SIMILARITY_THRESHOLD,
        target_clusters: Optional[int] = None,
        similarity_threshold: float = 0.7
    ) -> ClusterResult:
        """Cluster search results using the specified strategy.
        
        Args:
            results: List of search results to cluster
            strategy: Clustering strategy to use
            target_clusters: Target number of clusters (for k-means)
            similarity_threshold: Similarity threshold for threshold-based clustering
            
        Returns:
            ClusterResult with clustered results and metadata
        """
        if not results:
            # Return empty result for no results
            return ClusterResult(
                clusters=[],
                cluster_info=[],
                strategy=strategy,
                total_clusters=0
            )
        
        if len(results) < self.min_cluster_size:
            # Return single cluster if not enough results
            cluster_info = self._create_cluster_info("cluster_0", results)
            return ClusterResult(
                clusters=[results],
                cluster_info=[cluster_info],
                strategy=strategy,
                total_clusters=1
            )
        
        if strategy == ClusteringStrategy.SIMILARITY_THRESHOLD:
            return self._threshold_clustering(results, similarity_threshold)
        elif strategy == ClusteringStrategy.KMEANS:
            k = target_clusters or min(self.max_clusters, len(results) // 2)
            return self._kmeans_clustering(results, k)
        elif strategy == ClusteringStrategy.TOPIC_BASED:
            return self._topic_based_clustering(results)
        else:
            # Default to threshold clustering
            return self._threshold_clustering(results, similarity_threshold)
    
    def _threshold_clustering(
        self, 
        results: List[SearchResultData], 
        threshold: float
    ) -> ClusterResult:
        """Cluster based on similarity threshold."""
        clusters = []
        used_indices = set()
        
        for i, result in enumerate(results):
            if i in used_indices:
                continue
                
            # Start new cluster with current result
            cluster = [result]
            used_indices.add(i)
            
            # Find similar results
            for j, other_result in enumerate(results):
                if j in used_indices or i == j:
                    continue
                    
                similarity = self._calculate_similarity(result, other_result)
                if similarity >= threshold:
                    cluster.append(other_result)
                    used_indices.add(j)
            
            if len(cluster) >= self.min_cluster_size:
                clusters.append(cluster)
        
        # Handle remaining unclustered results
        remaining = [results[i] for i in range(len(results)) if i not in used_indices]
        if remaining:
            if len(remaining) >= self.min_cluster_size:
                clusters.append(remaining)
            elif clusters:
                # Add to largest cluster
                largest_cluster = max(clusters, key=len)
                largest_cluster.extend(remaining)
            else:
                # Create cluster with remaining items
                clusters.append(remaining)
        
        # Create cluster info
        cluster_info = [
            self._create_cluster_info(f"cluster_{i}", cluster)
            for i, cluster in enumerate(clusters)
        ]
        
        return ClusterResult(
            clusters=clusters,
            cluster_info=cluster_info,
            strategy=ClusteringStrategy.SIMILARITY_THRESHOLD,
            total_clusters=len(clusters)
        )
    
    def _kmeans_clustering(
        self, 
        results: List[SearchResultData], 
        k: int
    ) -> ClusterResult:
        """Simple k-means clustering implementation."""
        # Extract embeddings
        embeddings = []
        valid_results = []
        
        for result in results:
            if result.chunk.embedding:
                embeddings.append(result.chunk.embedding)
                valid_results.append(result)
        
        if len(embeddings) < k or len(embeddings) < self.min_cluster_size:
            # Fall back to single cluster
            cluster_info = self._create_cluster_info("cluster_0", valid_results)
            return ClusterResult(
                clusters=[valid_results] if valid_results else [results],
                cluster_info=[cluster_info],
                strategy=ClusteringStrategy.KMEANS,
                total_clusters=1
            )
        
        try:
            # Convert to numpy arrays
            X = np.array(embeddings)
            
            # Initialize centroids randomly
            n_samples, n_features = X.shape
            centroids = X[np.random.choice(n_samples, k, replace=False)]
            
            # K-means iterations
            max_iters = 100
            tolerance = 1e-4
            
            for _ in range(max_iters):
                # Assign points to closest centroids
                distances = np.sqrt(((X - centroids[:, np.newaxis])**2).sum(axis=2))
                labels = np.argmin(distances, axis=0)
                
                # Update centroids
                new_centroids = np.array([X[labels == i].mean(axis=0) for i in range(k)])
                
                # Check convergence
                if np.allclose(centroids, new_centroids, atol=tolerance):
                    break
                    
                centroids = new_centroids
            
            # Group results by cluster
            clusters = [[] for _ in range(k)]
            for i, label in enumerate(labels):
                clusters[label].append(valid_results[i])
            
            # Remove empty clusters
            clusters = [cluster for cluster in clusters if len(cluster) >= self.min_cluster_size]
            
            # Create cluster info
            cluster_info = [
                self._create_cluster_info(f"cluster_{i}", cluster)
                for i, cluster in enumerate(clusters)
            ]
            
            return ClusterResult(
                clusters=clusters,
                cluster_info=cluster_info,
                strategy=ClusteringStrategy.KMEANS,
                total_clusters=len(clusters)
            )
            
        except Exception as e:
            logger.warning(f"K-means clustering failed: {e}, falling back to threshold clustering")
            return self._threshold_clustering(results, 0.7)
    
    def _topic_based_clustering(self, results: List[SearchResultData]) -> ClusterResult:
        """Cluster based on topic keywords and document metadata."""
        topic_clusters = defaultdict(list)
        
        # Extract topics from metadata
        for result in results:
            topics = self._extract_topics(result)
            if topics:
                # Use first topic as primary cluster
                primary_topic = topics[0]
                topic_clusters[primary_topic].append(result)
            else:
                # Default cluster for items without topics
                topic_clusters["general"].append(result)
        
        # Convert to list format
        clusters = [cluster for cluster in topic_clusters.values() 
                   if len(cluster) >= self.min_cluster_size]
        
        # Merge small clusters
        small_clusters = [cluster for cluster in topic_clusters.values() 
                         if len(cluster) < self.min_cluster_size]
        if small_clusters:
            misc_cluster = []
            for cluster in small_clusters:
                misc_cluster.extend(cluster)
            if misc_cluster:
                clusters.append(misc_cluster)
        
        # Create cluster info
        cluster_info = [
            self._create_cluster_info(f"cluster_{i}", cluster)
            for i, cluster in enumerate(clusters)
        ]
        
        return ClusterResult(
            clusters=clusters,
            cluster_info=cluster_info,
            strategy=ClusteringStrategy.TOPIC_BASED,
            total_clusters=len(clusters)
        )
    
    def _calculate_similarity(
        self, 
        result1: SearchResultData, 
        result2: SearchResultData
    ) -> float:
        """Calculate similarity between two search results."""
        # Try embedding-based similarity first
        if result1.chunk.embedding and result2.chunk.embedding:
            return self._cosine_similarity(result1.chunk.embedding, result2.chunk.embedding)
        
        # Fall back to text-based similarity
        return self._text_similarity(result1.chunk.text, result2.chunk.text)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(b * b for b in vec2))
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text-based similarity using Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_topics(self, result: SearchResultData) -> List[str]:
        """Extract topics from result metadata."""
        topics = []
        
        # Check chunk metadata
        if result.chunk.metadata:
            chunk_topics = result.chunk.metadata.get("topics", [])
            if isinstance(chunk_topics, list):
                topics.extend(chunk_topics)
            elif isinstance(chunk_topics, str):
                topics.append(chunk_topics)
        
        # Check document metadata if available
        if result.document and result.document.metadata:
            doc_topics = result.document.metadata.get("topics", [])
            if isinstance(doc_topics, list):
                topics.extend(doc_topics)
            elif isinstance(doc_topics, str):
                topics.append(doc_topics)
        
        # Extract keywords from text as fallback
        if not topics:
            topics = self._extract_keywords_from_text(result.chunk.text)
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Simple keyword extraction from text."""
        # Simple approach: find capitalized words and common technical terms
        words = text.split()
        keywords = []
        
        technical_terms = {
            "machine learning", "artificial intelligence", "neural networks",
            "deep learning", "data science", "python", "programming",
            "algorithm", "database", "api", "software", "technology"
        }
        
        text_lower = text.lower()
        for term in technical_terms:
            if term in text_lower:
                keywords.append(term.replace(" ", "_"))
        
        # Add capitalized words (potential proper nouns)
        for word in words:
            if len(word) > 3 and word[0].isupper() and word.isalpha():
                keywords.append(word.lower())
        
        return keywords[:3]  # Return top 3 keywords
    
    def _create_cluster_info(self, cluster_id: str, cluster: List[SearchResultData]) -> ClusterInfo:
        """Create cluster information."""
        if not cluster:
            return ClusterInfo(
                id=cluster_id,
                centroid=None,
                size=0,
                representative_text="",
                avg_score=0.0,
                diversity_score=0.0
            )
        
        # Calculate centroid if embeddings are available
        centroid = None
        embeddings = [result.chunk.embedding for result in cluster 
                     if result.chunk.embedding]
        if embeddings and len(embeddings) == len(cluster):
            try:
                centroid = np.mean(embeddings, axis=0).tolist()
            except Exception:
                centroid = None
        
        # Find representative text (highest scoring or longest)
        representative = max(cluster, key=lambda x: x.score)
        representative_text = representative.chunk.text[:200] + "..." if len(representative.chunk.text) > 200 else representative.chunk.text
        
        # Calculate average score
        avg_score = sum(result.score for result in cluster) / len(cluster)
        
        # Calculate diversity score (average pairwise similarity)
        diversity_score = self._calculate_cluster_diversity(cluster)
        
        return ClusterInfo(
            id=cluster_id,
            centroid=centroid,
            size=len(cluster),
            representative_text=representative_text,
            avg_score=avg_score,
            diversity_score=diversity_score
        )
    
    def _calculate_cluster_diversity(self, cluster: List[SearchResultData]) -> float:
        """Calculate diversity score for a cluster (lower is more diverse)."""
        if len(cluster) <= 1:
            return 0.0
        
        similarities = []
        for i in range(len(cluster)):
            for j in range(i + 1, len(cluster)):
                sim = self._calculate_similarity(cluster[i], cluster[j])
                similarities.append(sim)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def diversify_clusters(
        self, 
        cluster_result: ClusterResult, 
        max_per_cluster: int = 3
    ) -> ClusterResult:
        """Diversify clusters by selecting representative items from each cluster."""
        diversified_clusters = []
        diversified_info = []
        
        for i, cluster in enumerate(cluster_result.clusters):
            if len(cluster) <= max_per_cluster:
                diversified_clusters.append(cluster)
                diversified_info.append(cluster_result.cluster_info[i])
                continue
            
            # Select diverse representatives
            representatives = self._select_diverse_representatives(cluster, max_per_cluster)
            diversified_clusters.append(representatives)
            
            # Update cluster info
            updated_info = self._create_cluster_info(f"cluster_{i}", representatives)
            diversified_info.append(updated_info)
        
        return ClusterResult(
            clusters=diversified_clusters,
            cluster_info=diversified_info,
            strategy=cluster_result.strategy,
            total_clusters=len(diversified_clusters)
        )
    
    def _select_diverse_representatives(
        self, 
        cluster: List[SearchResultData], 
        max_items: int
    ) -> List[SearchResultData]:
        """Select diverse representatives from a cluster."""
        if len(cluster) <= max_items:
            return cluster
        
        # Start with highest scoring item
        selected = [max(cluster, key=lambda x: x.score)]
        remaining = [item for item in cluster if item != selected[0]]
        
        # Select items that are most different from already selected
        for _ in range(max_items - 1):
            if not remaining:
                break
            
            best_candidate = None
            best_min_similarity = -1
            
            for candidate in remaining:
                # Find minimum similarity to already selected items
                min_sim = min(
                    self._calculate_similarity(candidate, selected_item)
                    for selected_item in selected
                )
                
                if min_sim > best_min_similarity:
                    best_min_similarity = min_sim
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
        
        return selected