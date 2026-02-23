"""MCPToolRegistry异步功能测试

测试MCPToolRegistry的异步方法，包括工具发现、注册和调用。
使用aioresponses模拟HTTP请求。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aioresponses import aioresponses
from src.tool_registry.mcp_tool_registry import MCPToolRegistry
from src.token_management.token_manager import TokenManager
from src.mcp_config import MCPServiceConfig
from src.tool_registry.mcp_tool import MCPTool


@pytest.fixture
def mock_token_manager():
    """创建mock的TokenManager"""
    manager = AsyncMock(spec=TokenManager)
    return manager


@pytest.fixture
def mcp_config():
    """创建测试用的MCP配置"""
    return MCPServiceConfig(
        base_url="https://test-mcp.example.com",
        timeout=10
    )


@pytest.fixture
def tool_registry(mock_token_manager, mcp_config):
    """创建MCPToolRegistry实例"""
    return MCPToolRegistry(mock_token_manager, mcp_config)


@pytest.mark.asyncio
class TestDiscoverTools:
    """测试工具发现功能"""
    
    async def test_discover_tools_empty_token(self, tool_registry):
        """测试空token"""
        tools = await tool_registry.discover_tools("")
        assert tools == []
    
    async def test_discover_tools_success(self, tool_registry):
        """测试成功发现工具"""
        with aioresponses() as m:
            # Mock MCP服务器响应
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                payload={
                    "tools": [
                        {
                            "name": "translate",
                            "description": "翻译文本",
                            "parameters": {
                                "required": ["text", "target"],
                                "properties": {
                                    "text": {"type": "string"},
                                    "target": {"type": "string"}
                                }
                            },
                            "endpoint": "/v1/translate",
                            "method": "POST"
                        },
                        {
                            "name": "summarize",
                            "description": "摘要文本",
                            "parameters": {
                                "required": ["text"],
                                "properties": {
                                    "text": {"type": "string"}
                                }
                            },
                            "endpoint": "/v1/summarize",
                            "method": "POST"
                        }
                    ]
                },
                status=200
            )
            
            tools = await tool_registry.discover_tools("test-token")
            
            assert len(tools) == 2
            assert tools[0]["name"] == "translate"
            assert tools[1]["name"] == "summarize"
    
    async def test_discover_tools_invalid_token(self, tool_registry):
        """测试无效token（401响应）"""
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                status=401
            )
            
            tools = await tool_registry.discover_tools("invalid-token")
            assert tools == []
    
    async def test_discover_tools_server_error(self, tool_registry):
        """测试服务器错误（500响应）"""
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                status=500,
                body="Internal Server Error"
            )
            
            tools = await tool_registry.discover_tools("test-token")
            assert tools == []
    
    async def test_discover_tools_timeout(self, tool_registry):
        """测试请求超时"""
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                exception=asyncio.TimeoutError()
            )
            
            tools = await tool_registry.discover_tools("test-token")
            assert tools == []
    
    async def test_discover_tools_invalid_schema(self, tool_registry):
        """测试工具schema验证失败"""
        with aioresponses() as m:
            # Mock返回包含无效工具的响应
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                payload={
                    "tools": [
                        {
                            "name": "valid_tool",
                            "description": "有效工具",
                            "parameters": {},
                            "endpoint": "/v1/valid"
                        },
                        {
                            "name": "",  # 无效：空name
                            "description": "无效工具",
                            "parameters": {},
                            "endpoint": "/v1/invalid"
                        },
                        {
                            # 无效：缺少endpoint
                            "name": "invalid_tool2",
                            "description": "无效工具2",
                            "parameters": {}
                        }
                    ]
                },
                status=200
            )
            
            tools = await tool_registry.discover_tools("test-token")
            
            # 只有有效的工具被返回
            assert len(tools) == 1
            assert tools[0]["name"] == "valid_tool"


@pytest.mark.asyncio
class TestRegisterUserTools:
    """测试用户工具注册"""
    
    async def test_register_no_token(self, tool_registry, mock_token_manager):
        """测试用户没有token"""
        mock_token_manager.get_user_token.return_value = None
        
        result = await tool_registry.register_user_tools("qq", "123456")
        assert result is False
    
    async def test_register_no_tools_discovered(self, tool_registry, mock_token_manager):
        """测试没有发现工具"""
        mock_token_manager.get_user_token.return_value = "test-token"
        
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                payload={"tools": []},
                status=200
            )
            
            result = await tool_registry.register_user_tools("qq", "123456")
            assert result is False
    
    async def test_register_success(self, tool_registry, mock_token_manager):
        """测试成功注册工具"""
        mock_token_manager.get_user_token.return_value = "test-token"
        
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                payload={
                    "tools": [
                        {
                            "name": "translate",
                            "description": "翻译文本",
                            "parameters": {"required": ["text"]},
                            "endpoint": "/v1/translate"
                        }
                    ]
                },
                status=200
            )
            
            result = await tool_registry.register_user_tools("qq", "123456")
            
            assert result is True
            
            # 验证工具已注册
            tools = await tool_registry.list_user_tools("qq", "123456")
            assert len(tools) == 1
            assert "translate" in tools


@pytest.mark.asyncio
class TestCallTool:
    """测试工具调用"""
    
    async def test_call_tool_no_registration(self, tool_registry):
        """测试调用未注册用户的工具"""
        result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
        
        assert result["success"] is False
        assert "未注册任何工具" in result["error"]
    
    async def test_call_tool_not_found(self, tool_registry):
        """测试调用不存在的工具"""
        # 注册一个工具
        user_key = "qq:123456"
        tool_registry._registry[user_key] = {}
        
        result = await tool_registry.call_tool("qq", "123456", "nonexistent", text="Hello")
        
        assert result["success"] is False
        assert "不存在或未注册" in result["error"]
    
    async def test_call_tool_invalid_params(self, tool_registry):
        """测试参数验证失败"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text", "target"]},
            endpoint="/v1/translate"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        # 缺少必需参数target
        result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
        
        assert result["success"] is False
        assert "参数验证失败" in result["error"]
    
    async def test_call_tool_no_token(self, tool_registry, mock_token_manager):
        """测试用户token不存在"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text"]},
            endpoint="/v1/translate"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        mock_token_manager.get_user_token.return_value = None
        
        result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
        
        assert result["success"] is False
        assert "Token已失效" in result["error"]
    
    async def test_call_tool_success(self, tool_registry, mock_token_manager):
        """测试成功调用工具"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text", "target"]},
            endpoint="/v1/translate",
            method="POST"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        mock_token_manager.get_user_token.return_value = "test-token"
        
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                payload={"result": "你好"},
                status=200
            )
            
            result = await tool_registry.call_tool(
                "qq", "123456", "translate",
                text="Hello", target="zh"
            )
            
            assert result["success"] is True
            assert result["data"]["result"] == "你好"
            assert result["tool"] == "translate"
    
    async def test_call_tool_invalid_token(self, tool_registry, mock_token_manager):
        """测试token无效（401响应）"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text"]},
            endpoint="/v1/translate"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        mock_token_manager.get_user_token.return_value = "invalid-token"
        
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=401
            )
            
            result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
            
            assert result["success"] is False
            assert "Token无效" in result["error"]
    
    async def test_call_tool_server_error(self, tool_registry, mock_token_manager):
        """测试服务器错误"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text"]},
            endpoint="/v1/translate"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        mock_token_manager.get_user_token.return_value = "test-token"
        
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=500,
                body="Internal Server Error"
            )
            
            result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
            
            assert result["success"] is False
            assert "工具调用失败" in result["error"]
    
    async def test_call_tool_timeout(self, tool_registry, mock_token_manager):
        """测试工具调用超时"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={"required": ["text"]},
            endpoint="/v1/translate"
        )
        tool_registry._registry[user_key] = {"translate": tool}
        
        mock_token_manager.get_user_token.return_value = "test-token"
        
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                exception=asyncio.TimeoutError()
            )
            
            result = await tool_registry.call_tool("qq", "123456", "translate", text="Hello")
            
            assert result["success"] is False
            assert "超时" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
