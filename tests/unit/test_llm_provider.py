"""
Unit tests for the LLM Provider abstraction.

Tests the LLMProvider interface and GeminiLLMProvider implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from graph_processing.llm_provider import LLMProvider
from graph_processing.gemini_provider import GeminiLLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self):
        self.generate_calls = []
        self.mock_response = "Mock response text"

    async def generate_content(self, prompt: str):
        self.generate_calls.append(prompt)
        response = MagicMock()
        response.text = self.mock_response
        return response

    def extract_text_from_response(self, response):
        return response.text

    def get_provider_name(self):
        return "mock"


class TestLLMProviderInterface:
    """Test the LLMProvider abstract interface."""

    def test_mock_provider_implements_interface(self):
        """Test that MockLLMProvider correctly implements LLMProvider."""
        provider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)
        assert provider.get_provider_name() == "mock"

    @pytest.mark.asyncio
    async def test_mock_provider_generate_content(self):
        """Test that MockLLMProvider can generate content."""
        provider = MockLLMProvider()
        provider.mock_response = "Test response"

        response = await provider.generate_content("Test prompt")
        text = provider.extract_text_from_response(response)

        assert text == "Test response"
        assert len(provider.generate_calls) == 1
        assert provider.generate_calls[0] == "Test prompt"

    @pytest.mark.asyncio
    async def test_mock_provider_tracks_multiple_calls(self):
        """Test that MockLLMProvider tracks multiple calls."""
        provider = MockLLMProvider()

        await provider.generate_content("Prompt 1")
        await provider.generate_content("Prompt 2")
        await provider.generate_content("Prompt 3")

        assert len(provider.generate_calls) == 3
        assert provider.generate_calls == ["Prompt 1", "Prompt 2", "Prompt 3"]


class TestGeminiLLMProvider:
    """Test the GeminiLLMProvider implementation."""

    def test_provider_name(self):
        """Test that GeminiLLMProvider returns correct provider name."""
        with patch('graph_processing.gemini_provider.genai'):
            provider = GeminiLLMProvider(api_key="test-key", model_name="gemini-2.5-flash")
            assert provider.get_provider_name() == "gemini"

    def test_extract_text_from_response(self):
        """Test text extraction from Gemini response."""
        with patch('graph_processing.gemini_provider.genai'):
            provider = GeminiLLMProvider(api_key="test-key", model_name="gemini-2.5-flash")

            mock_response = MagicMock()
            mock_response.text = "Extracted text content"

            result = provider.extract_text_from_response(mock_response)
            assert result == "Extracted text content"

    @pytest.mark.asyncio
    async def test_generate_content_calls_model(self):
        """Test that generate_content calls the underlying model."""
        with patch('graph_processing.gemini_provider.genai') as mock_genai:
            # Setup mock
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Generated response"
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            mock_genai.GenerativeModel.return_value = mock_model

            provider = GeminiLLMProvider(api_key="test-key", model_name="gemini-2.5-flash")

            response = await provider.generate_content("Test prompt")

            assert response == mock_response
            mock_model.generate_content_async.assert_called_once_with("Test prompt")
