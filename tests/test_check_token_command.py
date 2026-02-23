"""
测试check_token指令处理器

验证需求：需求 2（Token查询）
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
async def test_check_token_no_token_bound():
    """测试用户未绑定token的情况
    
    验证需求：需求 2.3 - 用户未绑定token时提示使用bind_token指令
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "还没有绑定token" in result_text
    assert "/bind_token" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_check_token_with_token_bound():
    """测试用户已绑定token的情况
    
    验证需求：需求 2.1, 2.2 - 返回token状态和部分信息（前4位和后4位）
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-abc123xyz456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1", "tool2", "tool3"])
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "Token已绑定" in result_text
    assert "sk-a...6456" in result_text  # 前4位和后4位
    assert "已注册工具: 3 个" in result_text
    
    # 验证不包含完整token
    assert "sk-abc123xyz456" not in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_check_token_short_token():
    """测试短token的显示（长度<=8）
    
    验证需求：需求 2.2, 2.4 - 不返回完整明文token
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定短token
    await plugin.token_manager.bind_token("qq", "123456", "short12")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=[])
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "shor..." in result_text
    assert "short12" not in result_text  # 不显示完整token
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_check_token_no_tools_registered():
    """测试已绑定token但未注册工具的情况
    
    验证需求：需求 2.1 - 返回token状态信息
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表为空
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=[])
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "Token已绑定" in result_text
    assert "已注册工具: 0 个" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_check_token_long_token_display():
    """测试长token的显示格式
    
    验证需求：需求 2.2 - 返回token的前4位和后4位
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定长token
    long_token = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
    await plugin.token_manager.bind_token("qq", "123456", long_token)
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1"])
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "sk-p...wxyz" in result_text
    assert "1234567890abcdefghijklmnopqrstuvwxyz" not in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_check_token_provides_helpful_commands():
    """测试返回消息包含有用的提示命令
    
    验证需求：需求 2 - 提供友好的用户体验
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1"])
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/check_token")
    
    # 执行
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "/list_tools" in result_text
    assert "/update_token" in result_text
    assert "/unbind_token" in result_text
    
    # 清理
    await plugin.db_manager.close()
