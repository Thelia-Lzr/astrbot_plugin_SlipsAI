"""
测试bind_token指令处理器

验证bind_token指令的参数解析、token绑定和工具注册功能。

验证需求：
- 需求 1（Token绑定管理）
- 需求 6（MCP工具自动发现）
- 需求 7（MCP工具注册）
- 需求 13（指令接口）
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_bind_token_success_with_tools(plugin_instance, create_mock_event):
    """测试成功绑定token并注册工具"""
    plugin = plugin_instance
    
    # Mock工具注册表的方法
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=True)
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate", "summarize"])
    
    # 创建模拟事件
    event = create_mock_event("/bind_token sk-test-token-123")
    
    # 调用bind_token指令
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    # 验证结果
    assert len(results) == 1
    result_text = results[0]
    assert "✅" in result_text or "成功" in result_text
    assert "Token绑定成功" in result_text
    assert "已自动注册 2 个MCP工具" in result_text
    assert "translate" in result_text
    assert "summarize" in result_text
    
    # 验证token已保存
    token = await plugin.token_manager.get_user_token("qq", "123456")
    assert token == "sk-test-token-123"


@pytest.mark.asyncio
async def test_bind_token_success_no_tools(plugin_instance, create_mock_event):
    """测试成功绑定token但未发现工具"""
    plugin = plugin_instance
    
    # Mock工具注册表返回失败
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=False)
    
    event = create_mock_event("/bind_token sk-test-token-456")
    
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "✅" in result_text or "成功" in result_text
    assert "Token绑定成功" in result_text
    assert "⚠️" in result_text or "警告" in result_text
    assert "未发现可用的MCP工具" in result_text
    
    # 验证token已保存
    token = await plugin.token_manager.get_user_token("qq", "123456")
    assert token == "sk-test-token-456"


@pytest.mark.asyncio
async def test_bind_token_missing_parameter(plugin_instance, create_mock_event):
    """测试缺少token参数"""
    plugin = plugin_instance
    
    event = create_mock_event("/bind_token")
    
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌" in result_text or "错误" in result_text or "失败" in result_text
    assert "用法错误" in result_text
    assert "/bind_token <your_token>" in result_text


@pytest.mark.asyncio
async def test_bind_token_empty_token(plugin_instance, create_mock_event):
    """测试空token参数"""
    plugin = plugin_instance
    
    # When message is "/bind_token   " (only spaces), split() treats it as missing parameter
    event = create_mock_event("/bind_token   ")
    
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌" in result_text or "错误" in result_text or "失败" in result_text
    # The command treats spaces-only as missing parameter
    assert "用法错误" in result_text


@pytest.mark.asyncio
async def test_bind_token_database_failure(plugin_instance, create_mock_event):
    """测试数据库操作失败"""
    plugin = plugin_instance
    
    # Mock token_manager.bind_token返回失败
    plugin.token_manager.bind_token = AsyncMock(return_value=False)
    
    event = create_mock_event("/bind_token sk-test-token-789")
    
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌" in result_text or "错误" in result_text or "失败" in result_text
    assert "Token绑定失败" in result_text


@pytest.mark.asyncio
async def test_bind_token_exception_handling(plugin_instance, create_mock_event):
    """测试异常处理"""
    plugin = plugin_instance
    
    # Mock token_manager.bind_token抛出异常
    plugin.token_manager.bind_token = AsyncMock(side_effect=Exception("Database error"))
    
    event = create_mock_event("/bind_token sk-test-token-error")
    
    results = []
    async for result in plugin.bind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌" in result_text or "错误" in result_text or "失败" in result_text
    assert "发生未知错误" in result_text


@pytest.mark.asyncio
async def test_bind_token_multiple_users(plugin_instance, create_mock_event):
    """测试多个用户绑定不同token"""
    plugin = plugin_instance
    
    # Mock工具注册
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=True)
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1"])
    
    # 用户1绑定token
    event1 = create_mock_event("/bind_token token-user1", "qq", "user001")
    results1 = []
    async for result in plugin.bind_token_command(event1):
        results1.append(result)
    
    # 用户2绑定token
    event2 = create_mock_event("/bind_token token-user2", "telegram", "user002")
    results2 = []
    async for result in plugin.bind_token_command(event2):
        results2.append(result)
    
    # 验证两个用户都成功绑定
    assert "✅" in results1[0] or "成功" in results1[0]
    assert "Token绑定成功" in results1[0]
    assert "✅" in results2[0] or "成功" in results2[0]
    assert "Token绑定成功" in results2[0]
    
    # 验证token隔离
    token1 = await plugin.token_manager.get_user_token("qq", "user001")
    token2 = await plugin.token_manager.get_user_token("telegram", "user002")
    assert token1 == "token-user1"
    assert token2 == "token-user2"
    assert token1 != token2


@pytest.mark.asyncio
async def test_bind_token_update_existing(plugin_instance, create_mock_event):
    """测试更新已存在的token"""
    plugin = plugin_instance
    
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=True)
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1"])
    
    # 第一次绑定
    event1 = create_mock_event("/bind_token old-token", "qq", "user123")
    async for _ in plugin.bind_token_command(event1):
        pass
    
    # 第二次绑定（更新）
    event2 = create_mock_event("/bind_token new-token", "qq", "user123")
    results = []
    async for result in plugin.bind_token_command(event2):
        results.append(result)
    
    # 验证更新成功
    assert "✅" in results[0] or "成功" in results[0]
    assert "Token绑定成功" in results[0]
    
    # 验证token已更新
    token = await plugin.token_manager.get_user_token("qq", "user123")
    assert token == "new-token"
