# Test Infrastructure Fixes for user-token-management

## Problem Summary

All command handler tests were failing due to:
1. **StopIteration errors**: Direct instantiation of `TokenManagementPlugin` caused errors with mocked AstrBot framework
2. **File system pollution**: Tests created real files and databases in the project directory that interfered with each other
3. **Missing test configuration**: No pytest configuration or shared fixtures

## Solutions Implemented

### 1. pytest.ini Configuration

Created `pytest.ini` with:
- **Async test support**: `asyncio_mode = auto` for automatic async test detection
- **Test discovery patterns**: Configured to find test files, classes, and functions
- **Output configuration**: Verbose mode with short tracebacks
- **Markers**: Defined markers for asyncio, integration, unit, and slow tests

### 2. Shared Test Fixtures (tests/conftest.py)

Created comprehensive shared fixtures:

#### Mock Classes
- **MockStar**: Proper mock of AstrBot's Star base class that doesn't cause StopIteration
- **MockFilter**: Mock decorator that preserves original functions instead of replacing them with MagicMocks
- **MockContext**: Minimal mock of AstrBot Context
- **MockAstrMessageEvent**: Complete mock of AstrBot message events

#### Fixtures
- **temp_db_path**: Provides isolated temporary database paths
- **temp_key_path**: Provides isolated temporary encryption key paths
- **temp_data_dir**: Provides isolated temporary data directories
- **mock_context**: Provides mocked AstrBot context
- **plugin_instance**: Provides fully initialized plugin with temporary paths
- **create_mock_event**: Factory for creating mock message events

#### Utility Functions
- **assert_success_message()**: Validates success messages
- **assert_error_message()**: Validates error messages
- **assert_warning_message()**: Validates warning messages

### 3. Updated Test Template (tests/test_bind_token_command.py)

Updated the bind_token command tests to:
- Use shared fixtures instead of creating mocks in each test
- Remove duplicate mock setup code
- Use temporary paths for all file operations
- Properly handle async generators from command handlers

## Key Technical Solutions

### Problem: Methods Became MagicMocks

**Root Cause**: The `@filter.command()` decorator from the mocked astrbot module was replacing methods with MagicMocks.

**Solution**: Created `MockFilter` class that implements decorator methods that return the original function unchanged:

```python
class MockFilter:
    @staticmethod
    def command(command_name):
        def decorator(func):
            return func  # Return function unchanged
        return decorator
```

### Problem: Plugin Initialization with Real Paths

**Root Cause**: Plugin `__init__` creates real directories and files.

**Solution**: After plugin initialization, override the component instances with new ones using temporary paths:

```python
plugin = TokenManagementPlugin(mock_context)
plugin.db_manager = DatabaseManager(str(temp_data_dir / "test_tokens.db"))
plugin.encryption = TokenEncryption(key_file_path=str(temp_data_dir / "test_encryption.key"))
# ... reinitialize dependent components
```

### Problem: Test Isolation

**Solution**: Each test gets its own temporary directory via pytest's `tmp_path` fixture, ensuring complete isolation.

## Test Results

All 8 tests in `test_bind_token_command.py` now pass:
- ✅ test_bind_token_success_with_tools
- ✅ test_bind_token_success_no_tools
- ✅ test_bind_token_missing_parameter
- ✅ test_bind_token_empty_token
- ✅ test_bind_token_database_failure
- ✅ test_bind_token_exception_handling
- ✅ test_bind_token_multiple_users
- ✅ test_bind_token_update_existing

## Usage for Other Tests

Other command handler tests can now use the same pattern:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_command(plugin_instance, create_mock_event):
    """Test description"""
    plugin = plugin_instance
    
    # Mock any external dependencies
    plugin.tool_registry.some_method = AsyncMock(return_value=True)
    
    # Create event
    event = create_mock_event("/my_command arg1 arg2")
    
    # Execute command
    results = []
    async for result in plugin.my_command(event):
        results.append(result)
    
    # Assert results
    assert len(results) == 1
    assert "expected text" in results[0]
```

## Files Created/Modified

### Created:
- `pytest.ini` - Pytest configuration
- `tests/conftest.py` - Shared fixtures and utilities
- `TEST_INFRASTRUCTURE_FIXES.md` - This document

### Modified:
- `tests/test_bind_token_command.py` - Updated to use new fixtures

## Next Steps

To fix the remaining command handler tests:
1. Update each test file to use the shared fixtures from `conftest.py`
2. Remove duplicate mock setup code
3. Use `plugin_instance` and `create_mock_event` fixtures
4. Follow the pattern established in `test_bind_token_command.py`
