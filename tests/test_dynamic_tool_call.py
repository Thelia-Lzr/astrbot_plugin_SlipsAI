"""
测试动态工具调用处理器

验证动态工具调用的消息解析、参数提取和工具执行功能。

验证需求：
- 需求 8（MCP工具调用）
- 需求 18（工具参数验证）
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
async def test_dynamic_tool_call_success():
    """测试成功调用工具"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    # Mock工具注册表
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate"])
    plugin.tool_registry.call_tool = AsyncMock(return_value={
        "success": True,
        "data": {"result": "你好", "source": "Hello"}
    })
    
    # 创建工具调用消息
    event = MockAstrMessageEvent('translate text="Hello" target="zh"')
    
    # 调用处理器
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    # 验证结果
    assert len(results) == 1
    result_text = results[0]
    assert "✅ 工具 'translate' 执行成功" in result_text
    assert "result: 你好" in result_text
    
    # 验证call_tool被正确调用
    plugin.tool_registry.call_tool.assert_called_once()
    call_args = plugin.tool_registry.call_tool.call_args
    assert call_args[0] == ("qq", "123456", "translate")
    assert call_args[1] == {"text": "Hello", "target": "zh"}
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_no_params():
    """测试调用无参数工具"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["status"])
    plugin.tool_registry.call_tool = AsyncMock(return_value={
        "success": True,
        "data": {"status": "online"}
    })
    
    event = MockAstrMessageEvent('status')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    assert len(results) == 1
    assert "✅ 工具 'status' 执行成功" in results[0]
    
    # 验证调用时没有参数
    call_args = plugin.tool_registry.call_tool.call_args
    assert call_args[1] == {}
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_failure():
    """测试工具调用失败"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate"])
    plugin.tool_registry.call_tool = AsyncMock(return_value={
        "success": False,
        "error": "参数验证失败，缺少必需参数: text"
    })
    
    event = MockAstrMessageEvent('translate target="zh"')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    assert len(results) == 1
    result_text = results[0]
    assert "❌ 工具执行失败" in result_text
    assert "参数验证失败" in result_text
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_not_a_tool():
    """测试普通消息不被处理"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate"])
    
    # 发送不是工具名称的消息
    event = MockAstrMessageEvent('hello world')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    # 不应该有任何结果（不是工具调用）
    assert len(results) == 0
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_command_ignored():
    """测试指令消息被忽略"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    # 发送指令消息（以/开头）
    event = MockAstrMessageEvent('/list_tools')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    # 不应该有任何结果（指令由其他处理器处理）
    assert len(results) == 0
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_no_token():
    """测试未绑定token的用户"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 不绑定token
    event = MockAstrMessageEvent('translate text="Hello"')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    # 不应该有任何结果（用户未绑定token）
    assert len(results) == 0
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_parse_tool_params_simple():
    """测试简单参数解析"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 测试简单的key=value格式
    params = plugin._parse_tool_params('text="Hello" target="zh"')
    assert params == {"text": "Hello", "target": "zh"}
    
    # 测试单引号
    params = plugin._parse_tool_params("text='Hello' target='zh'")
    assert params == {"text": "Hello", "target": "zh"}
    
    # 测试无引号
    params = plugin._parse_tool_params('count=5 enabled=true')
    assert params == {"count": 5, "enabled": True}


@pytest.mark.asyncio
async def test_parse_tool_params_types():
    """测试参数类型转换"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 测试整数
    params = plugin._parse_tool_params('count=10')
    assert params["count"] == 10
    assert isinstance(params["count"], int)
    
    # 测试浮点数
    params = plugin._parse_tool_params('rate=3.14')
    assert params["rate"] == 3.14
    assert isinstance(params["rate"], float)
    
    # 测试布尔值
    params = plugin._parse_tool_params('enabled=true disabled=false')
    assert params["enabled"] is True
    assert params["disabled"] is False
    
    # 测试字符串
    params = plugin._parse_tool_params('name="test"')
    assert params["name"] == "test"
    assert isinstance(params["name"], str)


@pytest.mark.asyncio
async def test_parse_tool_params_complex():
    """测试复杂参数解析"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 测试包含空格的字符串
    params = plugin._parse_tool_params('text="Hello World" target="zh-CN"')
    assert params["text"] == "Hello World"
    assert params["target"] == "zh-CN"
    
    # 测试混合类型
    params = plugin._parse_tool_params('text="Test" count=5 enabled=true rate=2.5')
    assert params == {
        "text": "Test",
        "count": 5,
        "enabled": True,
        "rate": 2.5
    }


@pytest.mark.asyncio
async def test_format_tool_result_simple():
    """测试简单结果格式化"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 测试简单字典
    result = plugin._format_tool_result({"result": "你好", "source": "Hello"})
    assert "result: 你好" in result
    assert "source: Hello" in result
    
    # 测试空数据
    result = plugin._format_tool_result({})
    assert result == "无返回数据"


@pytest.mark.asyncio
async def test_format_tool_result_complex():
    """测试复杂结果格式化"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    
    # 测试嵌套字典
    data = {
        "result": "success",
        "details": {"count": 5, "items": ["a", "b", "c"]}
    }
    result = plugin._format_tool_result(data)
    assert "result: success" in result
    assert "details:" in result
    assert '"count": 5' in result


@pytest.mark.asyncio
async def test_dynamic_tool_call_multiple_users():
    """测试多用户工具调用隔离"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 用户1绑定token
    await plugin.token_manager.bind_token("qq", "user001", "token1")
    # 用户2绑定token
    await plugin.token_manager.bind_token("qq", "user002", "token2")
    
    # Mock工具注册表
    async def mock_list_tools(platform, user_id):
        return ["translate"]
    
    async def mock_call_tool(platform, user_id, tool_name, **params):
        # 根据用户返回不同结果
        if user_id == "user001":
            return {"success": True, "data": {"result": "Result for user1"}}
        else:
            return {"success": True, "data": {"result": "Result for user2"}}
    
    plugin.tool_registry.list_user_tools = mock_list_tools
    plugin.tool_registry.call_tool = mock_call_tool
    
    # 用户1调用工具
    event1 = MockAstrMessageEvent('translate text="Hello"', "qq", "user001")
    results1 = []
    async for result in plugin.handle_dynamic_tool_call(event1):
        results1.append(result)
    
    # 用户2调用工具
    event2 = MockAstrMessageEvent('translate text="Hello"', "qq", "user002")
    results2 = []
    async for result in plugin.handle_dynamic_tool_call(event2):
        results2.append(result)
    
    # 验证结果隔离
    assert "Result for user1" in results1[0]
    assert "Result for user2" in results2[0]
    
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_dynamic_tool_call_exception_handling():
    """测试异常处理"""
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    await plugin.token_manager.bind_token("qq", "123456", "test-token")
    
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate"])
    plugin.tool_registry.call_tool = AsyncMock(side_effect=Exception("Network error"))
    
    event = MockAstrMessageEvent('translate text="Hello"')
    
    results = []
    async for result in plugin.handle_dynamic_tool_call(event):
        results.append(result)
    
    # 异常应该被捕获，不返回错误消息（因为可能不是工具调用）
    assert len(results) == 0
    
    await plugin.db_manager.close()
