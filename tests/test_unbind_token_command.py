"""
测试unbind_token指令处理器

验证unbind_token指令的token解绑和工具取消注册功能。

验证需求：
- 需求 4（Token解绑）
- 需求 10（工具生命周期管理）
- 需求 13（指令接口）
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

# Mock astrbot module before importing plugin
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.star'] = MagicMock()
sys.modules['astrbot.api.event'] = MagicMock()

from src.plugin import TokenManagementPlugin


class MockContext:
    """模拟AstrBot Context对象"""
    pass


class MockAstrMessageEvent:
    """模拟AstrBot消息事件对象"""
    
    def __init__(self, message_str: str, platform: str = "qq", user_id: str = "123456"):
        self.message_str = message_str
        self._platform = platform
        self._user_id = user_id
        self._results = []
    
    def get_platform_name(self) -> str:
        return self._platform
    
    def get_sender_id(self) -> str:
        return self._user_id
    
    def plain_result(self, text: str):
        """模拟返回纯文本结果"""
        self._results.append(text)
        return text


@pytest.mark.asyncio
async def test_unbind_token_success():
    """测试成功解绑token"""
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 初始化数据库
    await plugin.db_manager.initialize()
    
    # 先绑定一个token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test-token-123")
    
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/unbind_token")
    
    # 调用unbind_token指令
    results = []
    async for result in plugin.unbind_token_command(event):
        results.append(result)
    
    # 验证结果
    assert len(results) == 1
    result_text = results[0]
    assert "✅ Token已解绑" in result_text
    assert "🔧 所有MCP工具已取消注册" in result_text
    
    # 验证token已删除
    has_token = await plugin.token_manager.has_token("qq", "123456")
    assert has_token is False
    
    # 验证unregister_user_tools被调用
    plugin.tool_registry.unregister_user_tools.assert_called_once_with("qq", "123456")
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_no_token_bound():
    """测试用户未绑定token时尝试解绑"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 不绑定token，直接尝试解绑
    event = MockAstrMessageEvent("/unbind_token")
    
    results = []
    async for result in plugin.unbind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌ 您还没有绑定token" in result_text
    assert "/bind_token <token>" in result_text
    assert "/check_token" in result_text
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_database_failure():
    """测试数据库操作失败"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test-token-456")
    
    # Mock工具取消注册
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    
    # Mock token_manager.unbind_token返回失败
    plugin.token_manager.unbind_token = AsyncMock(return_value=False)
    
    event = MockAstrMessageEvent("/unbind_token")
    
    results = []
    async for result in plugin.unbind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌ Token解绑失败" in result_text
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_exception_handling():
    """测试异常处理"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test-token-789")
    
    # Mock unregister_user_tools抛出异常
    plugin.tool_registry.unregister_user_tools = AsyncMock(side_effect=Exception("Registry error"))
    
    event = MockAstrMessageEvent("/unbind_token")
    
    results = []
    async for result in plugin.unbind_token_command(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌ 发生未知错误" in result_text
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_multiple_users():
    """测试多个用户独立解绑token"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # Mock工具取消注册
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    
    # 两个用户绑定token
    await plugin.token_manager.bind_token("qq", "user001", "token-user1")
    await plugin.token_manager.bind_token("telegram", "user002", "token-user2")
    
    # 用户1解绑token
    event1 = MockAstrMessageEvent("/unbind_token", "qq", "user001")
    results1 = []
    async for result in plugin.unbind_token_command(event1):
        results1.append(result)
    
    # 验证用户1解绑成功
    assert "✅ Token已解绑" in results1[0]
    has_token1 = await plugin.token_manager.has_token("qq", "user001")
    assert has_token1 is False
    
    # 验证用户2的token仍然存在
    has_token2 = await plugin.token_manager.has_token("telegram", "user002")
    assert has_token2 is True
    token2 = await plugin.token_manager.get_user_token("telegram", "user002")
    assert token2 == "token-user2"
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_lifecycle():
    """测试完整的token生命周期：绑定 -> 解绑 -> 重新绑定"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # Mock工具注册和取消注册
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=True)
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1"])
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    
    # 1. 绑定token
    event_bind = MockAstrMessageEvent("/bind_token first-token", "qq", "user123")
    async for _ in plugin.bind_token_command(event_bind):
        pass
    
    has_token = await plugin.token_manager.has_token("qq", "user123")
    assert has_token is True
    
    # 2. 解绑token
    event_unbind = MockAstrMessageEvent("/unbind_token", "qq", "user123")
    results_unbind = []
    async for result in plugin.unbind_token_command(event_unbind):
        results_unbind.append(result)
    
    assert "✅ Token已解绑" in results_unbind[0]
    has_token = await plugin.token_manager.has_token("qq", "user123")
    assert has_token is False
    
    # 3. 重新绑定token
    event_rebind = MockAstrMessageEvent("/bind_token second-token", "qq", "user123")
    results_rebind = []
    async for result in plugin.bind_token_command(event_rebind):
        results_rebind.append(result)
    
    assert "✅ Token绑定成功" in results_rebind[0]
    token = await plugin.token_manager.get_user_token("qq", "user123")
    assert token == "second-token"
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_tools_unregistered_before_deletion():
    """测试工具在token删除前被取消注册"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test-token")
    
    # 记录调用顺序
    call_order = []
    
    async def mock_unregister(*args):
        call_order.append("unregister")
    
    async def mock_unbind(*args):
        call_order.append("unbind")
        return True
    
    plugin.tool_registry.unregister_user_tools = AsyncMock(side_effect=mock_unregister)
    plugin.token_manager.unbind_token = AsyncMock(side_effect=mock_unbind)
    
    event = MockAstrMessageEvent("/unbind_token")
    async for _ in plugin.unbind_token_command(event):
        pass
    
    # 验证调用顺序：先取消注册工具，再删除token
    assert call_order == ["unregister", "unbind"]
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_unbind_token_different_platforms():
    """测试不同平台的用户独立解绑"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    
    # 同一用户ID在不同平台绑定token
    await plugin.token_manager.bind_token("qq", "user123", "qq-token")
    await plugin.token_manager.bind_token("telegram", "user123", "telegram-token")
    
    # QQ平台用户解绑
    event_qq = MockAstrMessageEvent("/unbind_token", "qq", "user123")
    async for _ in plugin.unbind_token_command(event_qq):
        pass
    
    # 验证QQ平台token已删除
    has_qq_token = await plugin.token_manager.has_token("qq", "user123")
    assert has_qq_token is False
    
    # 验证Telegram平台token仍然存在
    has_telegram_token = await plugin.token_manager.has_token("telegram", "user123")
    assert has_telegram_token is True
    telegram_token = await plugin.token_manager.get_user_token("telegram", "user123")
    assert telegram_token == "telegram-token"
    
    await plugin.db_manager.close()
