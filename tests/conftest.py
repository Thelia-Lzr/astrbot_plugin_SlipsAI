"""
Pytest configuration and shared fixtures for user-token-management tests

This module provides:
- Temporary database paths for isolated test environments
- Mocked plugin instances with proper AstrBot framework mocks
- Shared test utilities and fixtures
"""

import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, Mock
from typing import AsyncGenerator

# Mock astrbot module before any imports
# This prevents StopIteration errors from the real AstrBot framework
class MockStar:
    """Mock Star base class that does nothing"""
    def __init__(self, context):
        pass

class MockFilter:
    """Mock filter decorator that preserves the original function"""
    @staticmethod
    def command(command_name):
        """Decorator that returns the function unchanged"""
        def decorator(func):
            return func
        return decorator
    
    @staticmethod
    def message_type(*types):
        """Decorator that returns the function unchanged"""
        def decorator(func):
            return func
        return decorator

sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.star'] = MagicMock()
sys.modules['astrbot.api.star'].Star = MockStar
sys.modules['astrbot.api.event'] = MagicMock()
sys.modules['astrbot.api.event'].filter = MockFilter()


class MockContext:
    """Mock AstrBot Context object
    
    Provides a minimal mock of the AstrBot Context that prevents
    StopIteration errors during plugin initialization.
    """
    
    def __init__(self):
        self.config = {}
        self.data_dir = None
    
    def get_config(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value):
        """Set configuration value"""
        self.config[key] = value


class MockAstrMessageEvent:
    """Mock AstrBot message event object
    
    Simulates the AstrBot message event interface for testing
    command handlers.
    """
    
    def __init__(self, message_str: str, platform: str = "qq", user_id: str = "123456"):
        self.message_str = message_str
        self._platform = platform
        self._user_id = user_id
        self._results = []
    
    def get_platform_name(self) -> str:
        """Get platform name"""
        return self._platform
    
    def get_sender_id(self) -> str:
        """Get sender user ID"""
        return self._user_id
    
    def plain_result(self, text: str):
        """Mock returning plain text result"""
        self._results.append(text)
        return text


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for isolated testing
    
    Each test gets its own temporary database file that is automatically
    cleaned up after the test completes.
    
    Args:
        tmp_path: Pytest's temporary directory fixture
        
    Returns:
        str: Path to temporary database file
    """
    db_file = tmp_path / "test_tokens.db"
    return str(db_file)


@pytest.fixture
def temp_key_path(tmp_path: Path) -> str:
    """Provide a temporary encryption key path for isolated testing
    
    Each test gets its own temporary encryption key file that is
    automatically cleaned up after the test completes.
    
    Args:
        tmp_path: Pytest's temporary directory fixture
        
    Returns:
        str: Path to temporary encryption key file
    """
    key_file = tmp_path / "test_encryption.key"
    return str(key_file)


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory for isolated testing
    
    Each test gets its own temporary data directory that is
    automatically cleaned up after the test completes.
    
    Args:
        tmp_path: Pytest's temporary directory fixture
        
    Returns:
        Path: Temporary data directory path
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def mock_context() -> MockContext:
    """Provide a mocked AstrBot Context
    
    Returns:
        MockContext: Mocked context object
    """
    return MockContext()


@pytest.fixture
async def plugin_instance(mock_context: MockContext, temp_data_dir: Path):
    """Provide a properly initialized plugin instance for testing
    
    This fixture:
    - Creates a plugin with mocked AstrBot context
    - Uses temporary database and key files
    - Initializes the database
    - Cleans up after the test
    
    Args:
        mock_context: Mocked AstrBot context
        temp_data_dir: Temporary data directory
        
    Yields:
        TokenManagementPlugin: Initialized plugin instance
    """
    # Import here to avoid issues with mocking
    from src.plugin import TokenManagementPlugin
    from src.database.database_manager import DatabaseManager
    from src.encryption.token_encryption import TokenEncryption
    from src.token_management.token_manager import TokenManager
    
    # Create plugin instance - it will try to use real paths
    plugin = TokenManagementPlugin(mock_context)
    
    # Override the components to use temp paths
    db_path = str(temp_data_dir / "test_tokens.db")
    key_path = str(temp_data_dir / "test_encryption.key")
    
    plugin.db_manager = DatabaseManager(db_path)
    plugin.encryption = TokenEncryption(key_file_path=key_path)
    plugin.token_manager = TokenManager(plugin.db_manager, plugin.encryption)
    
    # Re-initialize dependent components
    from src.mcp_service.mcp_service_caller import MCPServiceCaller
    from src.tool_registry.mcp_tool_registry import MCPToolRegistry
    
    plugin.mcp_caller = MCPServiceCaller(plugin.token_manager, plugin.mcp_config)
    plugin.tool_registry = MCPToolRegistry(plugin.token_manager, plugin.mcp_config)
    
    # Initialize database
    await plugin.db_manager.initialize()
    
    # Yield plugin for test use
    yield plugin
    
    # Cleanup
    await plugin.db_manager.close()


@pytest.fixture
def mock_message_event() -> MockAstrMessageEvent:
    """Provide a mock message event with default values
    
    Returns:
        MockAstrMessageEvent: Mock message event
    """
    return MockAstrMessageEvent("/test_command", platform="qq", user_id="test_user")


@pytest.fixture
def create_mock_event():
    """Factory fixture for creating mock message events
    
    Returns:
        Callable: Function to create mock events with custom parameters
    """
    def _create_event(message_str: str, platform: str = "qq", user_id: str = "123456") -> MockAstrMessageEvent:
        return MockAstrMessageEvent(message_str, platform, user_id)
    
    return _create_event


# Utility functions for tests

def assert_success_message(result_text: str, *expected_phrases: str):
    """Assert that a result contains success indicators and expected phrases
    
    Args:
        result_text: The result text to check
        *expected_phrases: Phrases that should be in the result
    """
    assert "✅" in result_text or "成功" in result_text
    for phrase in expected_phrases:
        assert phrase in result_text


def assert_error_message(result_text: str, *expected_phrases: str):
    """Assert that a result contains error indicators and expected phrases
    
    Args:
        result_text: The result text to check
        *expected_phrases: Phrases that should be in the result
    """
    assert "❌" in result_text or "错误" in result_text or "失败" in result_text
    for phrase in expected_phrases:
        assert phrase in result_text


def assert_warning_message(result_text: str, *expected_phrases: str):
    """Assert that a result contains warning indicators and expected phrases
    
    Args:
        result_text: The result text to check
        *expected_phrases: Phrases that should be in the result
    """
    assert "⚠️" in result_text or "警告" in result_text
    for phrase in expected_phrases:
        assert phrase in result_text
