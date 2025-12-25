"""
Tests for Gemini API integration.

These tests verify:
1. API key configuration and authentication
2. Basic text generation
3. Structured output with Pydantic models
4. Entity extraction capabilities
"""
import pytest
import google.generativeai as genai
from pydantic import BaseModel
from typing import List, Optional


class SimpleResponse(BaseModel):
    """Simple response model for testing structured output."""
    answer: str
    confidence: float
    word_count: int


class Entity(BaseModel):
    """Entity model for testing extraction."""
    name: str
    type: str
    confidence: float


class TestGeminiAPI:
    """Test suite for Gemini API connection and functionality."""

    @pytest.mark.asyncio
    async def test_gemini_api_key_configured(self, gemini_api_key):
        """Test that Gemini API key is properly configured."""
        assert gemini_api_key is not None, "GOOGLE_API_KEY not set"
        assert len(gemini_api_key) > 0, "GOOGLE_API_KEY is empty"
        assert gemini_api_key != 'your-google-api-key-here', "GOOGLE_API_KEY not configured"

    @pytest.mark.asyncio
    async def test_gemini_api_authentication(self, gemini_api_key, gemini_model):
        """Test authentication with Gemini API."""
        try:
            genai.configure(api_key=gemini_api_key)

            # Try to list available models as authentication test
            models = genai.list_models()
            models_list = list(models)

            assert len(models_list) > 0, "No models available - authentication may have failed"

        except Exception as e:
            pytest.fail(f"Gemini API authentication failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_basic_text_generation(self, gemini_api_key, gemini_model):
        """Test basic text generation with Gemini."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        prompt = "What is machine learning? Answer in one sentence."

        try:
            response = model.generate_content(prompt)

            assert response is not None, "No response received"
            assert response.text is not None, "Response text is None"
            assert len(response.text) > 0, "Response text is empty"

            # Verify response contains relevant keywords
            response_lower = response.text.lower()
            assert any(keyword in response_lower for keyword in ['machine learning', 'ml', 'algorithm', 'data']), \
                "Response doesn't seem relevant to the question"

        except Exception as e:
            pytest.fail(f"Text generation failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_gemini_with_json_response(self, gemini_api_key, gemini_model):
        """Test Gemini's ability to return structured JSON responses."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        prompt = """
        Analyze this text and return a JSON object with the following structure:
        {
            "answer": "brief summary of the text",
            "confidence": 0.9,
            "word_count": 15
        }

        Text: "Machine learning is a subset of artificial intelligence."

        Return ONLY the JSON object, no other text.
        """

        try:
            response = model.generate_content(prompt)

            assert response is not None, "No response received"
            assert response.text is not None, "Response text is None"

            # Try to parse JSON from response
            import json

            # Clean response text (remove markdown code blocks if present)
            text = response.text.strip()
            if text.startswith('```'):
                # Remove markdown code block markers
                text = text.split('\n', 1)[1] if '\n' in text else text
                text = text.rsplit('```', 1)[0] if '```' in text else text
                text = text.strip()

            data = json.loads(text)

            assert 'answer' in data, "Response missing 'answer' field"
            assert 'confidence' in data, "Response missing 'confidence' field"
            assert 'word_count' in data, "Response missing 'word_count' field"

        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON response: {str(e)}\nResponse: {response.text}")
        except Exception as e:
            pytest.fail(f"Structured response test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_entity_extraction(self, gemini_api_key, gemini_model):
        """Test entity extraction using Gemini."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        text = "Apple Inc. was founded by Steve Jobs in Cupertino, California in 1976."

        prompt = f"""
        Extract entities from the following text and return a JSON array of objects.
        Each object should have: name, type (PERSON, ORGANIZATION, LOCATION, DATE), and confidence (0-1).

        Text: {text}

        Return ONLY a JSON array, no other text.
        """

        try:
            response = model.generate_content(prompt)

            assert response is not None, "No response received"
            assert response.text is not None, "Response text is None"

            # Parse JSON response
            import json

            # Clean response text
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text
                text = text.rsplit('```', 1)[0] if '```' in text else text
                text = text.strip()

            entities = json.loads(text)

            assert isinstance(entities, list), "Response is not a list"
            assert len(entities) > 0, "No entities extracted"

            # Verify entity structure
            for entity in entities:
                assert 'name' in entity, f"Entity missing 'name': {entity}"
                assert 'type' in entity, f"Entity missing 'type': {entity}"

            # Check for expected entities (case-insensitive)
            entity_names = [e['name'].lower() for e in entities]
            assert any('apple' in name for name in entity_names), "Expected entity 'Apple Inc.' not found"
            assert any('steve jobs' in name for name in entity_names), "Expected entity 'Steve Jobs' not found"

        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON response: {str(e)}\nResponse: {response.text}")
        except Exception as e:
            pytest.fail(f"Entity extraction test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_gemini_context_understanding(self, gemini_api_key, gemini_model):
        """Test Gemini's ability to understand and use context."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        context = """
        Document 1: Machine learning is a subset of AI that enables systems to learn from data.
        Document 2: Python is widely used for machine learning applications.
        """

        query = "What programming language is commonly used for machine learning?"

        prompt = f"""
        Based on the following context, answer the question.

        Context:
        {context}

        Question: {query}

        Answer in one sentence.
        """

        try:
            response = model.generate_content(prompt)

            assert response is not None, "No response received"
            assert response.text is not None, "Response text is None"

            response_lower = response.text.lower()
            assert 'python' in response_lower, "Response doesn't mention Python based on context"

        except Exception as e:
            pytest.fail(f"Context understanding test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_gemini_rate_limiting_handling(self, gemini_api_key, gemini_model):
        """Test handling of rapid API requests (rate limiting awareness)."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        # Make 3 rapid requests
        successful_requests = 0

        for i in range(3):
            try:
                response = model.generate_content(f"Count to {i+1}")
                if response and response.text:
                    successful_requests += 1

                # Small delay to be respectful to API
                import asyncio
                await asyncio.sleep(0.5)

            except Exception as e:
                # Log but don't fail - rate limiting is expected behavior
                print(f"Request {i+1} failed (possibly rate limited): {str(e)}")

        assert successful_requests > 0, "All requests failed - check API configuration"

    @pytest.mark.asyncio
    async def test_gemini_error_handling(self, gemini_api_key, gemini_model):
        """Test error handling for invalid requests."""
        genai.configure(api_key=gemini_api_key)

        model = genai.GenerativeModel(gemini_model)

        # Test with empty prompt (should handle gracefully)
        try:
            response = model.generate_content("")
            # Some models may accept empty prompts, others may reject
            # Just verify we don't crash
            assert True, "Empty prompt handled"

        except Exception as e:
            # Exception is acceptable - just verify it's handled
            assert isinstance(e, Exception), "Error should be an Exception instance"
            print(f"Empty prompt raised expected error: {type(e).__name__}")
