"""
Unit tests for the refactored AppConfig with pydantic-settings.

Tests the configuration classes and their behavior.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestDatabaseConfig:
    """Test the DatabaseConfig class."""

    def test_default_values(self):
        """Test that DatabaseConfig has correct default values."""
        with patch.dict(os.environ, {}, clear=True):
            from api.config import DatabaseConfig
            config = DatabaseConfig()

            assert config.host == 'localhost'
            assert config.port == '5432'
            assert config.dbname == 'rag_db'
            assert config.user == 'admin'
            assert config.password == 'admin'

    def test_to_dict(self):
        """Test that to_dict returns correct format."""
        with patch.dict(os.environ, {}, clear=True):
            from api.config import DatabaseConfig
            config = DatabaseConfig()
            result = config.to_dict()

            assert isinstance(result, dict)
            assert 'host' in result
            assert 'port' in result
            assert 'dbname' in result
            assert 'user' in result
            assert 'password' in result

    def test_loads_from_environment(self):
        """Test that DatabaseConfig loads from environment variables."""
        env_vars = {
            'POSTGRES_HOST': 'custom-host',
            'POSTGRES_PORT': '5433',
            'POSTGRES_DB': 'custom_db',
            'POSTGRES_USER': 'custom_user',
            'POSTGRES_PASSWORD': 'custom_pass'
        }
        with patch.dict(os.environ, env_vars, clear=True):
            from importlib import reload
            import api.config
            reload(api.config)
            from api.config import DatabaseConfig
            
            config = DatabaseConfig()

            assert config.host == 'custom-host'
            assert config.port == '5433'
            assert config.dbname == 'custom_db'
            assert config.user == 'custom_user'
            assert config.password == 'custom_pass'


class TestAppSettings:
    """Test the AppSettings class."""

    def test_default_gemini_model(self):
        """Test that AppSettings has correct default Gemini model."""
        with patch.dict(os.environ, {}, clear=True):
            from api.config import AppSettings
            settings = AppSettings()

            assert settings.gemini_model == 'gemini-1.5-flash'

    def test_loads_google_api_key(self):
        """Test that AppSettings loads Google API key from environment."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-api-key'}, clear=True):
            from api.config import AppSettings
            settings = AppSettings()

            assert settings.google_api_key == 'test-api-key'

    def test_loads_logfire_token(self):
        """Test that AppSettings loads Logfire token from environment."""
        with patch.dict(os.environ, {'LOGFIRE_WRITE_TOKEN': 'test-token'}, clear=True):
            from api.config import AppSettings
            settings = AppSettings()

            assert settings.logfire_write_token == 'test-token'


class TestGetGeminiModel:
    """Test the get_gemini_model function."""

    def test_returns_default_when_not_set(self):
        """Test that get_gemini_model returns default when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            from api.config import get_gemini_model
            result = get_gemini_model()

            assert result == 'gemini-1.5-flash'

    def test_returns_configured_value(self):
        """Test that get_gemini_model returns configured value."""
        with patch.dict(os.environ, {'GEMINI_MODEL': 'gemini-2.0-pro'}, clear=True):
            from api.config import get_gemini_model
            result = get_gemini_model()

            assert result == 'gemini-2.0-pro'
