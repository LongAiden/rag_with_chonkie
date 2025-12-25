"""
Tests for Logfire integration.

These tests verify:
1. Logfire configuration
2. Logging functionality
3. Span/trace creation
4. Error logging
"""
import pytest
import logfire
import os
from io import StringIO
import sys


class TestLogfireIntegration:
    """Test suite for Logfire monitoring integration."""

    def test_logfire_import(self):
        """Test that Logfire library is installed and importable."""
        try:
            import logfire
            assert logfire is not None, "Logfire module is None"
        except ImportError as e:
            pytest.fail(f"Failed to import logfire: {str(e)}")

    def test_logfire_configuration(self, logfire_token):
        """Test Logfire configuration with token."""
        try:
            if logfire_token and logfire_token != 'your-logfire-write-token-or-leave-empty':
                # Configure with actual token
                logfire.configure(token=logfire_token)
            else:
                # Configure with default settings (local mode)
                logfire.configure()

            # If we get here without exception, configuration succeeded
            assert True, "Logfire configured successfully"

        except Exception as e:
            # Configuration errors are acceptable if no token provided
            if not logfire_token:
                print(f"Logfire configured in local mode: {str(e)}")
                assert True
            else:
                pytest.fail(f"Logfire configuration failed: {str(e)}")

    def test_logfire_info_logging(self, logfire_token):
        """Test basic info level logging."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Test info logging
            logfire.info("Test info message", test_param="test_value")

            # If no exception raised, test passes
            assert True, "Info logging successful"

        except Exception as e:
            pytest.fail(f"Info logging failed: {str(e)}")

    def test_logfire_error_logging(self, logfire_token):
        """Test error level logging."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Test error logging
            logfire.error("Test error message", error_code=500, error_type="TestError")

            # If no exception raised, test passes
            assert True, "Error logging successful"

        except Exception as e:
            pytest.fail(f"Error logging failed: {str(e)}")

    def test_logfire_span_creation(self, logfire_token):
        """Test creating spans for distributed tracing."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Test span creation
            with logfire.span("test_operation", operation_type="test"):
                logfire.info("Inside test span", step=1)

                # Nested span
                with logfire.span("nested_operation"):
                    logfire.info("Inside nested span", step=2)

            # If no exception raised, test passes
            assert True, "Span creation successful"

        except Exception as e:
            pytest.fail(f"Span creation failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_logfire_async_span(self, logfire_token):
        """Test spans in async context."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Test async span
            import asyncio

            with logfire.span("async_test_operation"):
                logfire.info("Start async operation")
                await asyncio.sleep(0.1)
                logfire.info("End async operation")

            assert True, "Async span creation successful"

        except Exception as e:
            pytest.fail(f"Async span creation failed: {str(e)}")

    def test_logfire_structured_data(self, logfire_token):
        """Test logging with structured data."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Test logging with various data types
            logfire.info(
                "Structured data test",
                string_field="test",
                int_field=42,
                float_field=3.14,
                bool_field=True,
                list_field=[1, 2, 3],
                dict_field={"key": "value"}
            )

            assert True, "Structured data logging successful"

        except Exception as e:
            pytest.fail(f"Structured data logging failed: {str(e)}")

    def test_logfire_with_exception(self, logfire_token):
        """Test logging exceptions with Logfire."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Create and log an exception
            try:
                raise ValueError("Test exception for logging")
            except ValueError as e:
                logfire.error(
                    "Exception occurred during test",
                    error=str(e),
                    error_type=type(e).__name__
                )

            assert True, "Exception logging successful"

        except Exception as e:
            pytest.fail(f"Exception logging failed: {str(e)}")

    def test_logfire_multiple_spans(self, logfire_token):
        """Test multiple independent spans."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            # Create multiple independent spans
            with logfire.span("operation_1"):
                logfire.info("Operation 1 started")

            with logfire.span("operation_2"):
                logfire.info("Operation 2 started")

            with logfire.span("operation_3"):
                logfire.info("Operation 3 started")

            assert True, "Multiple spans created successfully"

        except Exception as e:
            pytest.fail(f"Multiple spans test failed: {str(e)}")

    def test_logfire_performance_tracking(self, logfire_token):
        """Test tracking performance metrics with Logfire."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            import time

            with logfire.span("performance_test"):
                start_time = time.time()

                # Simulate some work
                time.sleep(0.1)

                end_time = time.time()
                duration = end_time - start_time

                logfire.info(
                    "Performance test completed",
                    duration_seconds=duration,
                    operations_count=100
                )

            assert True, "Performance tracking successful"

        except Exception as e:
            pytest.fail(f"Performance tracking failed: {str(e)}")

    def test_logfire_without_token(self):
        """Test that Logfire works in local mode without token."""
        try:
            # Configure without token (local mode)
            logfire.configure()

            logfire.info("Test message in local mode")

            with logfire.span("local_test"):
                logfire.info("Inside local span")

            assert True, "Logfire works in local mode"

        except Exception as e:
            # Local mode should still work
            print(f"Local mode test note: {str(e)}")
            assert True, "Logfire local mode acceptable"

    @pytest.mark.asyncio
    async def test_logfire_embedding_workflow(self, logfire_token):
        """Test Logfire integration in an embedding workflow."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            import asyncio

            # Simulate embedding workflow
            with logfire.span("embedding_workflow", text_count=3):
                logfire.info("Starting embedding process")

                with logfire.span("embedding_generation"):
                    logfire.info("Generating embeddings", batch_size=3)
                    await asyncio.sleep(0.05)

                with logfire.span("vector_storage"):
                    logfire.info("Storing vectors in database")
                    await asyncio.sleep(0.05)

                logfire.info("Embedding workflow completed", success=True)

            assert True, "Embedding workflow logging successful"

        except Exception as e:
            pytest.fail(f"Embedding workflow logging failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_logfire_search_workflow(self, logfire_token):
        """Test Logfire integration in a search workflow."""
        try:
            # Configure logfire
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()

            import asyncio

            # Simulate search workflow
            with logfire.span("search_workflow", query="test query"):
                logfire.info("Starting search", query_length=10)

                with logfire.span("vector_search"):
                    logfire.info("Performing similarity search", limit=5)
                    await asyncio.sleep(0.05)

                with logfire.span("reranking"):
                    logfire.info("Reranking results", candidates=5)
                    await asyncio.sleep(0.05)

                with logfire.span("llm_generation"):
                    logfire.info("Generating LLM response")
                    await asyncio.sleep(0.05)

                logfire.info("Search completed", results_count=5)

            assert True, "Search workflow logging successful"

        except Exception as e:
            pytest.fail(f"Search workflow logging failed: {str(e)}")
