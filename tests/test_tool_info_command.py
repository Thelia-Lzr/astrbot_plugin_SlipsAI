"""
测试tool_info指令处理器

验证需求：需求 19（工具信息查询）
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
async def test_tool_info_missing_parameter():
    """测试缺少工具名称参数的情况
    
    验证需求：需求 19 - 参数缺失时返回用法提示
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建模拟事件（没有工具名称参数）
    event = MockAstrMessageEvent("/tool_info")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "用法错误" in result_text
    assert "/tool_info <tool_name>" in result_text
    assert "/list_tools" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_empty_tool_name():
    """测试工具名称为空的情况
    
    验证需求：需求 19 - 工具名称为空时返回错误提示
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建模拟事件（工具名称为空）
    event = MockAstrMessageEvent("/tool_info ")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "工具名称不能为空" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_no_token_bound():
    """测试用户未绑定token的情况
    
    验证需求：需求 19 - 用户未绑定token时返回友好提示
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info translate")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "还没有绑定token" in result_text
    assert "/bind_token" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_tool_not_found():
    """测试工具不存在的情况
    
    验证需求：需求 19.6 - 工具不存在时返回错误提示
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具信息返回None（工具不存在）
    plugin.tool_registry.get_tool_info = MagicMock(return_value=None)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info nonexistent_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "不存在或未注册" in result_text
    assert "nonexistent_tool" in result_text
    assert "/list_tools" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_complete_information():
    """测试获取完整工具信息的情况
    
    验证需求：
    - 需求 19.1 - 返回工具的名称和描述
    - 需求 19.2 - 返回工具的参数列表
    - 需求 19.3 - 标识哪些参数是必需的
    - 需求 19.4 - 返回每个参数的类型和描述
    - 需求 19.5 - 返回工具的API端点和HTTP方法
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息
    mock_tool_info = {
        "name": "translate",
        "description": "翻译文本到目标语言",
        "parameters": {
            "required": ["text", "target"],
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要翻译的文本"
                },
                "target": {
                    "type": "string",
                    "description": "目标语言代码"
                },
                "source": {
                    "type": "string",
                    "description": "源语言代码（可选）"
                }
            }
        },
        "endpoint": "/v1/translate",
        "method": "POST"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info translate")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    
    # 验证工具名称和描述
    assert "工具信息: translate" in result_text
    assert "翻译文本到目标语言" in result_text
    
    # 验证参数信息
    assert "参数:" in result_text
    assert "text" in result_text
    assert "string, 必需" in result_text
    assert "要翻译的文本" in result_text
    
    assert "target" in result_text
    assert "string, 必需" in result_text
    assert "目标语言代码" in result_text
    
    assert "source" in result_text
    assert "string, 可选" in result_text
    assert "源语言代码（可选）" in result_text
    
    # 验证端点和方法
    assert "端点: /v1/translate" in result_text
    assert "方法: POST" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_no_parameters():
    """测试工具没有参数的情况
    
    验证需求：需求 19 - 正确处理无参数的工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（没有参数）
    mock_tool_info = {
        "name": "status",
        "description": "获取系统状态",
        "parameters": {},
        "endpoint": "/v1/status",
        "method": "GET"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info status")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "工具信息: status" in result_text
    assert "获取系统状态" in result_text
    assert "参数: 无参数" in result_text
    assert "端点: /v1/status" in result_text
    assert "方法: GET" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_missing_description():
    """测试工具缺少描述字段的情况
    
    验证需求：需求 19.1 - 处理缺少描述的工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（没有description字段）
    mock_tool_info = {
        "name": "mystery_tool",
        "parameters": {},
        "endpoint": "/v1/mystery",
        "method": "POST"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info mystery_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "工具信息: mystery_tool" in result_text
    assert "描述: 无描述" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_missing_endpoint():
    """测试工具缺少端点信息的情况
    
    验证需求：需求 19.5 - 处理缺少端点的工具
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（没有endpoint字段）
    mock_tool_info = {
        "name": "test_tool",
        "description": "测试工具",
        "parameters": {}
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info test_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "端点: 未知" in result_text
    assert "方法: POST" in result_text  # 默认方法
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_parameter_without_description():
    """测试参数缺少描述的情况
    
    验证需求：需求 19.4 - 处理缺少描述的参数
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（参数没有description字段）
    mock_tool_info = {
        "name": "test_tool",
        "description": "测试工具",
        "parameters": {
            "required": ["param1"],
            "properties": {
                "param1": {
                    "type": "string"
                    # 没有description字段
                }
            }
        },
        "endpoint": "/v1/test",
        "method": "POST"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info test_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "param1" in result_text
    assert "string, 必需" in result_text
    assert "无描述" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_parameter_without_type():
    """测试参数缺少类型的情况
    
    验证需求：需求 19.4 - 处理缺少类型的参数
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（参数没有type字段）
    mock_tool_info = {
        "name": "test_tool",
        "description": "测试工具",
        "parameters": {
            "required": ["param1"],
            "properties": {
                "param1": {
                    "description": "参数1"
                    # 没有type字段
                }
            }
        },
        "endpoint": "/v1/test",
        "method": "POST"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info test_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "param1" in result_text
    assert "any, 必需" in result_text  # 默认类型为any
    assert "参数1" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_all_optional_parameters():
    """测试所有参数都是可选的情况
    
    验证需求：需求 19.3 - 正确标识可选参数
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（所有参数都是可选的）
    mock_tool_info = {
        "name": "search",
        "description": "搜索工具",
        "parameters": {
            "required": [],  # 没有必需参数
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "limit": {
                    "type": "integer",
                    "description": "结果数量限制"
                }
            }
        },
        "endpoint": "/v1/search",
        "method": "GET"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info search")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    assert "query" in result_text
    assert "string, 可选" in result_text
    assert "limit" in result_text
    assert "integer, 可选" in result_text
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_different_users():
    """测试不同用户查询工具信息的隔离性
    
    验证需求：需求 9.4 - 用户只能查询自己注册的工具信息
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 用户1绑定token
    await plugin.token_manager.bind_token("qq", "user1", "sk-token1")
    
    # 用户2绑定token
    await plugin.token_manager.bind_token("qq", "user2", "sk-token2")
    
    # Mock工具信息（根据用户返回不同结果）
    def mock_get_tool_info(platform, user_id, tool_name):
        if user_id == "user1" and tool_name == "tool_a":
            return {
                "name": "tool_a",
                "description": "用户1的工具A",
                "parameters": {},
                "endpoint": "/v1/tool_a",
                "method": "POST"
            }
        elif user_id == "user2" and tool_name == "tool_b":
            return {
                "name": "tool_b",
                "description": "用户2的工具B",
                "parameters": {},
                "endpoint": "/v1/tool_b",
                "method": "GET"
            }
        return None
    
    plugin.tool_registry.get_tool_info = mock_get_tool_info
    
    # 用户1查询tool_a
    event1 = MockAstrMessageEvent("/tool_info tool_a", platform="qq", user_id="user1")
    results1 = []
    async for result in plugin.tool_info_command(event1):
        results1.append(result)
    
    # 验证用户1可以查询tool_a
    assert len(results1) == 1
    result_text1 = results1[0]
    assert "tool_a" in result_text1
    assert "用户1的工具A" in result_text1
    
    # 用户1查询tool_b（应该失败）
    event2 = MockAstrMessageEvent("/tool_info tool_b", platform="qq", user_id="user1")
    results2 = []
    async for result in plugin.tool_info_command(event2):
        results2.append(result)
    
    # 验证用户1无法查询tool_b
    assert len(results2) == 1
    result_text2 = results2[0]
    assert "不存在或未注册" in result_text2
    
    # 用户2查询tool_b
    event3 = MockAstrMessageEvent("/tool_info tool_b", platform="qq", user_id="user2")
    results3 = []
    async for result in plugin.tool_info_command(event3):
        results3.append(result)
    
    # 验证用户2可以查询tool_b
    assert len(results3) == 1
    result_text3 = results3[0]
    assert "tool_b" in result_text3
    assert "用户2的工具B" in result_text3
    
    # 清理
    await plugin.db_manager.close()


@pytest.mark.asyncio
async def test_tool_info_with_complex_parameters():
    """测试具有复杂参数的工具
    
    验证需求：需求 19.2, 19.3, 19.4 - 正确显示复杂参数信息
    """
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定token
    await plugin.token_manager.bind_token("qq", "123456", "sk-test123456")
    
    # Mock工具详细信息（复杂参数）
    mock_tool_info = {
        "name": "complex_tool",
        "description": "具有复杂参数的工具",
        "parameters": {
            "required": ["input", "config"],
            "properties": {
                "input": {
                    "type": "string",
                    "description": "输入文本"
                },
                "config": {
                    "type": "object",
                    "description": "配置对象"
                },
                "options": {
                    "type": "array",
                    "description": "选项数组"
                },
                "timeout": {
                    "type": "number",
                    "description": "超时时间（秒）"
                },
                "verbose": {
                    "type": "boolean",
                    "description": "是否输出详细信息"
                }
            }
        },
        "endpoint": "/v1/complex",
        "method": "POST"
    }
    
    plugin.tool_registry.get_tool_info = MagicMock(return_value=mock_tool_info)
    
    # 创建模拟事件
    event = MockAstrMessageEvent("/tool_info complex_tool")
    
    # 执行
    results = []
    async for result in plugin.tool_info_command(event):
        results.append(result)
    
    # 验证
    assert len(results) == 1
    result_text = results[0]
    
    # 验证必需参数
    assert "input" in result_text
    assert "string, 必需" in result_text
    assert "config" in result_text
    assert "object, 必需" in result_text
    
    # 验证可选参数
    assert "options" in result_text
    assert "array, 可选" in result_text
    assert "timeout" in result_text
    assert "number, 可选" in result_text
    assert "verbose" in result_text
    assert "boolean, 可选" in result_text
    
    # 清理
    await plugin.db_manager.close()
