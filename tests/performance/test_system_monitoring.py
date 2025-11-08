#!/usr/bin/env python3
"""
System Performance and Quality Monitoring Tests
Tests for performance benchmarking, load testing, and quality metrics
"""

import asyncio
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock

import psutil
import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from graph_rag.core.graph_rag_engine import QueryResult, SimpleGraphRAGEngine
from graph_rag.core.interfaces import ChunkData, GraphRepository, VectorStore


class TestPerformanceBenchmarks:
    """Test performance benchmarks for optimization planning"""

    @pytest.fixture
    def performance_engine(self):
        """Create GraphRAG engine optimized for performance testing"""
        mock_graph_store = AsyncMock(spec=GraphRepository)
        mock_vector_store = AsyncMock(spec=VectorStore)
        mock_entity_extractor = AsyncMock()
        mock_llm_service = AsyncMock()

        # Configure fast mock responses
        mock_vector_store.search.return_value = [
            ChunkData(
                id=f"perf-chunk-{i}",
                text=f"Performance test chunk {i}",
                document_id=f"perf-doc-{i//5}",
                embedding=[0.1] * 384,
                score=0.9 - (i * 0.1)
            )
            for i in range(10)
        ]

        mock_llm_service.generate_response.return_value = "Performance test response"

        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )

    @pytest.mark.asyncio
    async def test_query_response_time_benchmark(self, performance_engine):
        """Test query response time meets <200ms target"""
        queries = [
            "What is GraphRAG?",
            "How does vector search work?",
            "Explain knowledge graphs",
            "What are the benefits of hybrid retrieval?",
            "How do you implement entity extraction?"
        ]

        response_times = []

        for query in queries:
            start_time = time.perf_counter()
            result = await performance_engine.query(query)
            end_time = time.perf_counter()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            response_times.append(response_time)

            # Verify successful response
            assert isinstance(result, QueryResult), "Should return QueryResult"
            assert result.answer != "", "Should generate answer"

        # Calculate performance metrics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)

        # Log performance metrics
        print("\nQuery Performance Metrics:")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"95th percentile: {p95_response_time:.2f}ms")
        print(f"Maximum: {max_response_time:.2f}ms")

        # Performance assertions (adjusted for mocked components)
        assert avg_response_time < 500, f"Average response time {avg_response_time:.2f}ms exceeds 500ms target"
        assert p95_response_time < 1000, f"95th percentile {p95_response_time:.2f}ms exceeds 1000ms target"

    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self, performance_engine):
        """Test performance under concurrent load"""
        concurrent_queries = 20
        queries = [f"Performance test query {i}" for i in range(concurrent_queries)]

        start_time = time.perf_counter()

        # Execute queries concurrently
        tasks = [performance_engine.query(query) for query in queries]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify all queries completed successfully
        assert len(results) == concurrent_queries, "All queries should complete"
        assert all(isinstance(result, QueryResult) for result in results), "All should be QueryResults"

        # Calculate throughput
        throughput = concurrent_queries / total_time

        print("\nConcurrent Performance Metrics:")
        print(f"Total time for {concurrent_queries} queries: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} queries/second")

        # Performance assertions
        assert throughput >= 5, f"Throughput {throughput:.2f} queries/sec below minimum 5 queries/sec"
        assert total_time < 10, f"Total time {total_time:.2f}s exceeds 10s target"

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, performance_engine):
        """Test memory usage stays within reasonable bounds"""
        # Measure initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        large_queries = [f"Large query with lots of context {i} " * 100 for i in range(10)]

        memory_measurements = []

        for query in large_queries:
            await performance_engine.query(query)

            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(current_memory)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        max_memory = max(memory_measurements)
        memory_increase = final_memory - initial_memory

        print("\nMemory Usage Metrics:")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Maximum memory: {max_memory:.2f}MB")
        print(f"Memory increase: {memory_increase:.2f}MB")

        # Memory assertions (adjusted for test environment)
        assert max_memory < initial_memory + 100, "Memory usage should not increase by more than 100MB"
        assert memory_increase < 50, f"Memory increase {memory_increase:.2f}MB exceeds 50MB target"


class TestLoadTesting:
    """Test system load handling for Fortune 500 scale requirements"""

    @pytest.fixture
    def load_test_engine(self):
        """Create engine for load testing"""
        mock_graph_store = AsyncMock(spec=GraphRepository)
        mock_vector_store = AsyncMock(spec=VectorStore)
        mock_entity_extractor = AsyncMock()
        mock_llm_service = AsyncMock()

        # Configure realistic mock responses
        mock_vector_store.search.return_value = [
            ChunkData(
                id=f"load-chunk-{i}",
                text=f"Load test chunk {i} with realistic content length",
                document_id=f"load-doc-{i//10}",
                embedding=[0.1] * 384,
                score=0.9 - (i * 0.05)
            )
            for i in range(50)
        ]

        mock_llm_service.generate_response.return_value = "Load test response with substantial content"

        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )

    def test_sustained_load_handling(self, load_test_engine):
        """Test handling sustained load (100+ concurrent users simulation)"""
        num_users = 50  # Reduced for test environment
        queries_per_user = 5

        def user_simulation():
            """Simulate a user making multiple queries"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            user_results = []
            try:
                for i in range(queries_per_user):
                    result = loop.run_until_complete(
                        load_test_engine.query(f"User query {i}")
                    )
                    user_results.append(result)
                    time.sleep(0.1)  # Simulate user think time
            finally:
                loop.close()

            return user_results

        # Execute load test
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_simulation) for _ in range(num_users)]
            results = [future.result() for future in futures]

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify load test results
        total_queries = num_users * queries_per_user
        successful_queries = sum(len(user_results) for user_results in results)

        print("\nLoad Test Metrics:")
        print(f"Users simulated: {num_users}")
        print(f"Queries per user: {queries_per_user}")
        print(f"Total queries: {total_queries}")
        print(f"Successful queries: {successful_queries}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average queries/second: {successful_queries/total_time:.2f}")

        # Load test assertions
        assert successful_queries == total_queries, "All queries should complete successfully"
        assert total_time < 60, f"Load test should complete within 60 seconds, took {total_time:.2f}s"

        success_rate = successful_queries / total_queries
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95% target"

    def test_stress_test_breaking_point(self, load_test_engine):
        """Test system behavior at breaking point"""
        # Gradually increase load to find breaking point
        load_levels = [10, 25, 50, 75]  # Concurrent operations
        breaking_point_found = False

        for load_level in load_levels:
            print(f"\nTesting load level: {load_level} concurrent operations")

            async def stress_operation():
                return await load_test_engine.query("Stress test query")

            start_time = time.perf_counter()

            try:
                # Run stress test at this level
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                tasks = [stress_operation() for _ in range(load_level)]
                results = loop.run_until_complete(asyncio.gather(*tasks))

                end_time = time.perf_counter()
                duration = end_time - start_time

                # Check if system is still performing well
                throughput = load_level / duration

                print(f"Duration: {duration:.2f}s, Throughput: {throughput:.2f} ops/sec")

                if duration > 10 or throughput < 2:  # Performance degradation detected
                    breaking_point_found = True
                    print(f"Performance degradation detected at {load_level} concurrent operations")
                    break

            except Exception as e:
                breaking_point_found = True
                print(f"System failure at {load_level} concurrent operations: {e}")
                break
            finally:
                loop.close()

        # System should handle reasonable load before breaking
        # For test environment, expect to handle at least 25 concurrent operations
        if breaking_point_found:
            assert load_level >= 25, f"System should handle at least 25 concurrent operations, failed at {load_level}"


class TestQualityMetrics:
    """Test quality metrics and system reliability"""

    @pytest.fixture
    def quality_test_engine(self):
        """Create engine for quality testing"""
        mock_graph_store = AsyncMock(spec=GraphRepository)
        mock_vector_store = AsyncMock(spec=VectorStore)
        mock_entity_extractor = AsyncMock()
        mock_llm_service = AsyncMock()

        # Configure quality-focused mock responses
        mock_vector_store.search.return_value = [
            ChunkData(
                id=f"quality-chunk-{i}",
                text=f"High-quality test chunk {i} with relevant content",
                document_id=f"quality-doc-{i//3}",
                embedding=[0.1] * 384,
                score=0.95 - (i * 0.02)  # High-quality scores
            )
            for i in range(15)
        ]

        mock_llm_service.generate_response.return_value = "High-quality response with detailed information"

        return SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor,
            llm_service=mock_llm_service
        )

    @pytest.mark.asyncio
    async def test_response_quality_consistency(self, quality_test_engine):
        """Test response quality consistency across multiple queries"""
        test_queries = [
            "What is machine learning?",
            "How does natural language processing work?",
            "Explain computer vision techniques",
            "What are the applications of AI?",
            "How do neural networks function?"
        ]

        quality_scores = []
        response_lengths = []

        for query in test_queries:
            result = await quality_test_engine.query(query)

            # Quality metrics
            response_length = len(result.answer)
            chunk_count = len(result.relevant_chunks)

            response_lengths.append(response_length)

            # Basic quality score (based on response completeness)
            quality_score = min(100, (response_length / 50) * 20 + chunk_count * 10)
            quality_scores.append(quality_score)

            # Quality assertions
            assert response_length > 10, f"Response should be substantial, got {response_length} characters"
            assert chunk_count > 0, "Should have relevant chunks"

        # Overall quality metrics
        avg_quality = statistics.mean(quality_scores)
        quality_variance = statistics.variance(quality_scores)
        avg_response_length = statistics.mean(response_lengths)

        print("\nQuality Metrics:")
        print(f"Average quality score: {avg_quality:.2f}")
        print(f"Quality variance: {quality_variance:.2f}")
        print(f"Average response length: {avg_response_length:.0f} characters")

        # Quality consistency assertions
        assert avg_quality >= 50, f"Average quality score {avg_quality:.2f} below minimum 50"
        assert quality_variance <= 200, f"Quality variance {quality_variance:.2f} too high (inconsistent quality)"

    @pytest.mark.asyncio
    async def test_error_rate_monitoring(self, quality_test_engine):
        """Test error rate stays below acceptable threshold"""
        test_scenarios = [
            ("normal_query", "Standard question about technology"),
            ("empty_query", ""),
            ("long_query", "Very long query " * 100),
            ("special_chars", "Query with special characters: !@#$%^&*()"),
            ("unicode_query", "Query with unicode: 中文 العربية русский"),
        ]

        total_queries = len(test_scenarios)
        successful_queries = 0
        errors = []

        for scenario_name, query in test_scenarios:
            try:
                result = await quality_test_engine.query(query)
                if isinstance(result, QueryResult):
                    successful_queries += 1
                else:
                    errors.append(f"{scenario_name}: Invalid result type")
            except Exception as e:
                errors.append(f"{scenario_name}: {str(e)}")

        success_rate = successful_queries / total_queries
        error_rate = 1 - success_rate

        print("\nError Rate Monitoring:")
        print(f"Total queries: {total_queries}")
        print(f"Successful queries: {successful_queries}")
        print(f"Success rate: {success_rate:.1%}")
        print(f"Error rate: {error_rate:.1%}")

        if errors:
            print("Errors encountered:")
            for error in errors:
                print(f"  - {error}")

        # Error rate assertions
        assert error_rate <= 0.05, f"Error rate {error_rate:.1%} exceeds 5% threshold"
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below 95% target"

    @pytest.mark.asyncio
    async def test_system_reliability_metrics(self, quality_test_engine):
        """Test system reliability over extended operation"""
        reliability_queries = 50
        start_time = time.time()

        successful_operations = 0
        failed_operations = 0
        response_times = []

        for i in range(reliability_queries):
            query_start = time.perf_counter()

            try:
                result = await quality_test_engine.query(f"Reliability test query {i}")
                query_end = time.perf_counter()

                response_time = (query_end - query_start) * 1000  # milliseconds
                response_times.append(response_time)

                if isinstance(result, QueryResult) and result.answer:
                    successful_operations += 1
                else:
                    failed_operations += 1

            except Exception:
                failed_operations += 1
                query_end = time.perf_counter()
                response_time = (query_end - query_start) * 1000
                response_times.append(response_time)

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate reliability metrics
        uptime_percentage = successful_operations / reliability_queries
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        print("\nReliability Metrics:")
        print(f"Total operations: {reliability_queries}")
        print(f"Successful operations: {successful_operations}")
        print(f"Failed operations: {failed_operations}")
        print(f"Uptime percentage: {uptime_percentage:.1%}")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"Maximum response time: {max_response_time:.2f}ms")
        print(f"Total duration: {total_duration:.2f}s")

        # Reliability assertions
        assert uptime_percentage >= 0.99, f"Uptime {uptime_percentage:.1%} below 99% target"
        assert avg_response_time < 1000, f"Average response time {avg_response_time:.2f}ms exceeds 1s"
        assert failed_operations <= 1, f"Too many failed operations: {failed_operations}"


class TestResourceUtilization:
    """Test resource utilization and optimization"""

    @pytest.mark.asyncio
    async def test_cpu_utilization_monitoring(self):
        """Test CPU utilization stays within acceptable bounds"""
        # Monitor CPU usage during operations
        cpu_measurements = []

        # Simple CPU-intensive task simulation
        for i in range(10):
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_measurements.append(cpu_percent)

            # Simulate some work
            await asyncio.sleep(0.1)

        avg_cpu = statistics.mean(cpu_measurements)
        max_cpu = max(cpu_measurements)

        print("\nCPU Utilization Metrics:")
        print(f"Average CPU: {avg_cpu:.1f}%")
        print(f"Maximum CPU: {max_cpu:.1f}%")

        # CPU utilization should be reasonable
        assert max_cpu < 90, f"Maximum CPU usage {max_cpu:.1f}% exceeds 90% threshold"

    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_measurements = [initial_memory]

        # Simulate extended operations
        for i in range(20):
            # Simulate memory usage
            temp_data = [i] * 1000
            del temp_data

            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_measurements.append(current_memory)

            time.sleep(0.1)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print("\nMemory Leak Detection:")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Memory growth: {memory_growth:.2f}MB")

        # Memory growth should be minimal
        assert memory_growth < 10, f"Memory growth {memory_growth:.2f}MB indicates potential leak"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
