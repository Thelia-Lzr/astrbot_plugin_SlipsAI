"""
测试update_token指令处理器

验证需求：
- 需求 3（Token更新）
- 需求 10（工具生命周期管理）
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.fixture
def mock_context():
    """创建模拟的AstrBot上下文"""
    return MockContext()


@pytest.mark.asyncio
async def test_update_token_success_with_tools():
    """测试成功更新token并重新注册工具"""
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定一个token
    await plugin.token_manager.bind_token("qq", "123456", "sk-old-token")
    
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=True)
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate", "summarize"])
    
    # 创建事件
    event = MockAstrMessageEvent("/update_token sk-new-token-123")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证调用顺序和参数
    plugin.tool_registry.unregister_user_tools.assert_called_once_with("qq", "123456")
    plugin.tool_registry.register_user_tools.assert_called_once_with("qq", "123456")
    plugin.tool_registry.list_user_tools.assert_called_once_with("qq", "123456")
    
    # 验证返回消息
    assert len(results) == 1
    result_text = results[0]
    assert "✅ Token更新成功" in result_text
    assert "已重新注册 2 个MCP工具" in result_text
    assert "translate" in result_text
    assert "summarize" in result_text
    
    # 验证token已更新
    token = await plugin.token_manager.get_user_token("qq", "123456")
    assert token == "sk-new-token-123"
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_update_token_success_no_tools():
    """测试成功更新token但未发现工具"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定一个token
    await plugin.token_manager.bind_token("qq", "123456", "sk-old-token")
    
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    plugin.tool_registry.register_user_tools = AsyncMock(return_value=False)
    
    # 创建事件
    event = MockAstrMessageEvent("/update_token sk-new-token-456")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证调用
    plugin.tool_registry.unregister_user_tools.assert_called_once_with("qq", "123456")
    plugin.tool_registry.register_user_tools.assert_called_once_with("qq", "123456")
    
    # 验证返回消息
    assert len(results) == 1
    result_text = results[0]
    assert "✅ Token更新成功" in result_text
    assert "⚠️ 未发现可用的MCP工具" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_update_token_no_existing_token():
    """测试用户未绑定token时尝试更新"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 不绑定token，直接尝试更新
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    plugin.tool_registry.register_user_tools = AsyncMock()
    
    # 创建事件
    event = MockAstrMessageEvent("/update_token sk-new-token-789")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证没有执行更新
    plugin.tool_registry.unregister_user_tools.assert_not_called()
    plugin.tool_registry.register_user_tools.assert_not_called()
    
    # 验证返回错误消息
    assert len(results) == 1
    result_text = results[0]
    assert "❌ 您还没有绑定token" in result_text
    assert "/bind_token" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_update_token_missing_parameter():
    """测试缺少token参数"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    plugin.tool_registry.register_user_tools = AsyncMock()
    
    # 创建事件（缺少token参数）
    event = MockAstrMessageEvent("/update_token")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证没有调用任何组件方法
    plugin.tool_registry.unregister_user_tools.assert_not_called()
    plugin.tool_registry.register_user_tools.assert_not_called()
    
    # 验证返回用法提示
    assert len(results) == 1
    result_text = results[0]
    assert "❌ 用法错误" in result_text
    assert "/update_token <new_token>" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_update_token_empty_parameter():
    """测试token参数为空"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # Mock工具注册表的方法
    plugin.tool_registry.unregister_user_tools = AsyncMock()
    plugin.tool_registry.register_user_tools = AsyncMock()
    
    # 创建事件（token为空）
    event = MockAstrMessageEvent("/update_token   ")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证没有调用任何组件方法
    plugin.tool_registry.unregister_user_tools.assert_not_called()
    plugin.tool_registry.register_user_tools.assert_not_called()
    
    # 验证返回错误消息
    assert len(results) == 1
    result_text = results[0]
    assert "❌ Token不能为空" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_update_token_workflow_order():
    """测试更新token的工作流程顺序"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定一个token
    await plugin.token_manager.bind_token("qq", "123456", "sk-old-token")
    
    # 记录调用顺序
    call_order = []
    
    async def track_unregister(*args):
        call_order.append("unregister")
    
    async def track_register(*args):
        call_order.append("register")
        return True
    
    async def track_list_tools(*args):
        call_order.append("list_tools")
        return ["tool1"]
    
    plugin.tool_registry.unregister_user_tools = AsyncMock(side_effect=track_unregister)
    plugin.tool_registry.register_user_tools = AsyncMock(side_effect=track_register)
    plugin.tool_registry.list_user_tools = AsyncMock(side_effect=track_list_tools)
    
    # 创建事件
    event = MockAstrMessageEvent("/update_token sk-workflow-test")
    
    # 执行指令
    results = []
    async for result in plugin.update_token_command(event):
        results.append(result)
    
    # 验证调用顺序：取消注册 -> 重新注册 -> 列出工具
    assert call_order == ["unregister", "register", "list_tools"]
    
    # 清理
    await plugin.db_manager.close()
