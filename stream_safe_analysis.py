#!/usr/bin/env python3
"""
Search and Query System Evaluation for Business Intelligence.
"""

import json
import sys
import httpx
from typing import Dict, List, Any, Optional
import time

# Test queries for different business scenarios
BUSINESS_QUERIES = {
    "strategic": [
        "What are the key principles for building a successful startup?",
        "How do you grow a sustainable business?",
        "What are the most important product development strategies?",
        "How to scale a team effectively?",
    ],
    "operational": [
        "What are the best practices for MVP development?",
        "How to implement effective user feedback loops?", 
        "What are the key metrics for measuring product success?",
        "How to manage technical debt in a growing codebase?",
    ],
    "technical": [
        "How to choose the right technology stack?",
        "What are the best practices for API design?",
        "How to implement efficient data processing pipelines?",
        "What are the key considerations for system architecture?",
    ],
    "market": [
        "How to identify and validate market opportunities?",
        "What are effective customer acquisition strategies?",
        "How to price products competitively?",
        "What are the key factors in market positioning?",
    ]
}

API_BASE = "http://localhost:8000/api/v1"


class SearchSystemEvaluator:
    """Evaluates search and query system for business intelligence capabilities."""
    
    def test_search_accuracy(self, query: str, search_type: str = "vector", limit: int = 5) -> Dict[str, Any]:
        """Test search accuracy and relevance."""
        url = f"{API_BASE}/search/query"
        payload = {
            "query": query,
            "search_type": search_type, 
            "limit": limit
        }
        
        start_time = time.time()
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            duration = time.time() - start_time
            
            data = response.json()
            results = data.get("results", [])
            
            # Analyze results
            analysis = {
                "query": query,
                "search_type": search_type,
                "duration_ms": duration * 1000,
                "total_results": len(results),
                "avg_score": sum(r.get("score", 0) for r in results) / len(results) if results else 0,
                "max_score": max((r.get("score", 0) for r in results), default=0),
                "min_score": min((r.get("score", 0) for r in results), default=0),
                "has_relevant_content": any(len(r.get("chunk", {}).get("text", "")) > 50 for r in results),
                "content_diversity": len(set(r.get("chunk", {}).get("document_id") for r in results)),
                "results": results
            }
            
            return analysis
            
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }
    
    def test_query_types(self) -> Dict[str, List[Dict[str, Any]]]:
        """Test different types of business queries."""
        results = {}
        
        for category, queries in BUSINESS_QUERIES.items():
            print(f"\n=== Testing {category.upper()} queries ===", file=sys.stderr)
            category_results = []
            
            for query in queries:
                print(f"Testing: {query[:60]}...", file=sys.stderr)
                
                # Test vector search
                vector_result = self.test_search_accuracy(query, "vector", 3)
                
                # Test keyword search if available
                try:
                    keyword_result = self.test_search_accuracy(query, "keyword", 3)
                except:
                    keyword_result = {"error": "keyword search not available"}
                
                category_results.append({
                    "query": query,
                    "vector": vector_result,
                    "keyword": keyword_result
                })
                
            results[category] = category_results
            
        return results
    
    def test_response_quality(self, query: str) -> Dict[str, Any]:
        """Test query response quality and formatting."""
        url = f"{API_BASE}/query/ask"
        payload = {
            "text": query,
            "k": 5,
            "include_graph": True,
            "search_type": "vector"
        }
        
        start_time = time.time()
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            duration = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    "query": query,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "duration_ms": duration * 1000
                }
                
            data = response.json()
            
            analysis = {
                "query": query,
                "duration_ms": duration * 1000,
                "has_answer": bool(data.get("answer")),
                "answer_length": len(data.get("answer", "")),
                "has_citations": bool(data.get("citations")),
                "citation_count": len(data.get("citations", [])),
                "has_graph_context": bool(data.get("graph_context")),
                "chunk_count": len(data.get("relevant_chunks", [])),
                "answer_preview": data.get("answer", "")[:200],
                "response": data
            }
            
            return analysis
            
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze system performance characteristics."""
        print("\n=== Performance Analysis ===", file=sys.stderr)
        
        test_queries = [
            "business strategy",
            "product development", 
            "team management",
            "technical architecture",
            "market analysis"
        ]
        
        performance_data = []
        
        for query in test_queries:
            print(f"Performance test: {query}", file=sys.stderr)
            
            # Multiple runs for average
            durations = []
            for _ in range(3):
                result = self.test_search_accuracy(query, "vector", 5)
                if "duration_ms" in result:
                    durations.append(result["duration_ms"])
            
            if durations:
                performance_data.append({
                    "query": query,
                    "avg_duration_ms": sum(durations) / len(durations),
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                    "runs": len(durations)
                })
        
        return {
            "performance_tests": performance_data,
            "avg_response_time": sum(p["avg_duration_ms"] for p in performance_data) / len(performance_data) if performance_data else 0
        }


    def identify_improvements(self) -> List[Dict[str, Any]]:
        """Identify key areas for improvement based on testing."""
        improvements = []
        
        # Test a representative sample
        sample_queries = [
            "What are the key principles for building a successful startup?",
            "How to implement effective user feedback loops?",
            "What are the best practices for API design?"
        ]
        
        for query in sample_queries:
            print(f"Analyzing improvement opportunities for: {query[:50]}...", file=sys.stderr)
            
            search_result = self.test_search_accuracy(query, "vector", 5)
            query_result = self.test_response_quality(query)
            
            issues = []
            recommendations = []
            
            # Check search quality
            if search_result.get("avg_score", 0) < 0.3:
                issues.append("Low relevance scores")
                recommendations.append("Improve embedding model or add query expansion")
                
            if search_result.get("total_results", 0) < 3:
                issues.append("Insufficient results")
                recommendations.append("Expand knowledge base or improve chunking strategy")
                
            # Check response quality  
            if query_result.get("error"):
                issues.append(f"Query processing error: {query_result['error']}")
                recommendations.append("Fix query processing pipeline bugs")
                
            if not query_result.get("has_answer"):
                issues.append("No synthesized answer generated")
                recommendations.append("Improve LLM integration and prompt engineering")
                
            if query_result.get("duration_ms", 0) > 5000:
                issues.append("Slow response time")
                recommendations.append("Optimize search and LLM inference")
            
            improvements.append({
                "query": query,
                "issues": issues,
                "recommendations": recommendations,
                "search_metrics": search_result,
                "query_metrics": query_result
            })
        
        return improvements

    def run_evaluation(self):
        """Run comprehensive search and query system analysis."""
        print("Starting Search & Query System Analysis...", file=sys.stderr)
        
        analysis_results = {
            "timestamp": time.time(),
            "api_base": API_BASE
        }
        
        try:
            # Test query types
            print("\n1. Testing different query types...", file=sys.stderr)
            analysis_results["query_type_analysis"] = self.test_query_types()
            
            # Test performance
            print("\n2. Analyzing performance...", file=sys.stderr)
            analysis_results["performance_analysis"] = self.analyze_performance()
            
            # Identify improvements
            print("\n3. Identifying improvement opportunities...", file=sys.stderr)
            analysis_results["improvement_analysis"] = self.identify_improvements()
            
            # Output results as JSON
            print(json.dumps(analysis_results, indent=2))
            
        except KeyboardInterrupt:
            print("\nAnalysis interrupted by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\nAnalysis failed: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    evaluator = SearchSystemEvaluator()
    evaluator.run_evaluation()


if __name__ == "__main__":
    main()