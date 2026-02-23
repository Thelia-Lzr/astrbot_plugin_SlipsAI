"""
测试list_tools指令处理器

验证需求：需求 7（MCP工具注册）、需求 19（工具信息查询）
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
async def test_list_tools_no_token_bound():
    """测试用户未绑定token的情况
    
    验证需求：需求 7, 19 - 用户未绑定token时返回友好提示
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "还没有绑定token" in result_text
    assert "/bind_token" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_no_tools_registered():
    """测试用户已绑定token但无工具的情况
    
    验证需求：需求 7, 19 - 无工具时返回友好提示
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
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "还没有可用的MCP工具" in result_text
    assert "/update_token" in result_text
    assert "/check_token" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_with_tools():
    """测试用户有工具的情况
    
    验证需求：需求 7.4, 19.1, 19.2 - 返回工具列表，包含名称和描述
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate", "summarize", "analyze"])
    
    # Mock工具详细信息
    def mock_get_tool_info(platform, user_id, tool_name):
        tool_info_map = {
            "translate": {"name": "translate", "description": "翻译文本到目标语言"},
            "summarize": {"name": "summarize", "description": "生成文本摘要"},
            "analyze": {"name": "analyze", "description": "分析文本内容"}
        }
        return tool_info_map.get(tool_name)
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "您的MCP工具列表（共 3 个）" in result_text
    assert "translate" in result_text
    assert "翻译文本到目标语言" in result_text
    assert "summarize" in result_text
    assert "生成文本摘要" in result_text
    assert "analyze" in result_text
    assert "分析文本内容" in result_text
    assert "/tool_info" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_with_missing_tool_info():
    """测试部分工具无法获取详细信息的情况
    
    验证需求：需求 7.4, 19 - 即使无法获取详细信息也应显示工具名称
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1", "tool2"])
    
    # Mock工具详细信息（tool2返回None）
    def mock_get_tool_info(platform, user_id, tool_name):
        if tool_name == "tool1":
            return {"name": "tool1", "description": "工具1描述"}
        return None  # tool2无法获取信息
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "您的MCP工具列表（共 2 个）" in result_text
    assert "tool1" in result_text
    assert "工具1描述" in result_text
    assert "tool2" in result_text  # 即使没有描述也应显示名称
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_with_no_description():
    """测试工具没有描述字段的情况
    
    验证需求：需求 19.1, 19.2 - 处理缺少描述的工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool_no_desc"])
    
    # Mock工具详细信息（没有description字段）
    def mock_get_tool_info(platform, user_id, tool_name):
        return {"name": "tool_no_desc"}  # 没有description字段
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "tool_no_desc" in result_text
    assert "无描述" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_single_tool():
    """测试只有一个工具的情况
    
    验证需求：需求 7.4, 19 - 正确显示单个工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具列表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["single_tool"])
    
    # Mock工具详细信息
    def mock_get_tool_info(platform, user_id, tool_name):
        return {"name": "single_tool", "description": "唯一的工具"}
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/list_tools")
    
    # 执行
    results = []
    async for result in plugin.list_tools_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "您的MCP工具列表（共 1 个）" in result_text
    assert "single_tool" in result_text
    assert "唯一的工具" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_list_tools_different_users():
    """测试不同用户的工具隔离性
    
    验证需求：需求 9.4 - 用户查询工具列表时仅返回该用户已注册的工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 用户1绑定token
    await plugin.token_manager.bind_token("qq", "user1", "sk-token1")
    
    # 用户2绑定token
    await plugin.token_manager.bind_token("qq", "user2", "sk-token2")
    
    # Mock工具列表（根据用户返回不同工具）
    async def mock_list_user_tools(platform, user_id):
        if user_id == "user1":
            return ["tool_a", "tool_b"]
        elif user_id == "user2":
            return ["tool_c"]
        return []
    
    plugin.tool_registry.list_user_tools = mock_list_user_tools
    
    # Mock工具详细信息
    def mock_get_tool_info(platform, user_id, tool_name):
        return {"name": tool_name, "description": f"{tool_name}的描述"}
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 用户1查询工具列表
    event1 = MockAstrMessageEvent("/list_tools", platform="qq", user_id="user1")
    results1 = []
    async for result in plugin.list_tools_command(event1):
        results1.append(result)
    
    # 验证用户1的结果
    assert len(results1) == 1
    result_text1 = results1[0]
    assert "共 2 个" in result_text1
    assert "tool_a" in result_text1
    assert "tool_b" in result_text1
    assert "tool_c" not in result_text1
    
    # 用户2查询工具列表
    event2 = MockAstrMessageEvent("/list_tools", platform="qq", user_id="user2")
    results2 = []
    async for result in plugin.list_tools_command(event2):
        results2.append(result)
    
    # 验证用户2的结果
    assert len(results2) == 1
    result_text2 = results2[0]
    assert "共 1 个" in result_text2
    assert "tool_c" in result_text2
    assert "tool_a" not in result_text2
    assert "tool_b" not in result_text2
    
    # 清理
    await plugin.db_manager.close()
