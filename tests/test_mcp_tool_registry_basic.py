"""MCPToolRegistry基础功能测试

测试MCPToolRegistry类的核心功能，包括工具注册、查询和调用。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
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


class TestMCPToolRegistryInit:
    """测试MCPToolRegistry初始化"""
    
    def test_init_with_config(self, mock_token_manager, mcp_config):
        """测试使用配置初始化"""
        registry = MCPToolRegistry(mock_token_manager, mcp_config)
        
        assert registry.token_manager == mock_token_manager
        assert registry.mcp_config == mcp_config
        assert registry._registry == {}
    
    def test_init_without_config(self, mock_token_manager):
        """测试不提供配置时使用默认配置"""
        registry = MCPToolRegistry(mock_token_manager)
        
        assert registry.token_manager == mock_token_manager
        assert registry.mcp_config is not None
        assert isinstance(registry.mcp_config, MCPServiceConfig)
        assert registry._registry == {}


class TestUserKey:
    """测试用户标识生成"""
    
    def test_get_user_key(self, tool_registry):
        """测试生成用户唯一标识"""
        user_key = tool_registry._get_user_key("qq", "123456")
        assert user_key == "qq:123456"
        
        user_key2 = tool_registry._get_user_key("telegram", "789")
        assert user_key2 == "telegram:789"


class TestToolSchemaValidation:
    """测试工具schema验证"""
    
    def test_validate_valid_tool_schema(self, tool_registry):
        """测试有效的工具schema"""
        tool = {
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
        }
        
        assert tool_registry._validate_tool_schema(tool) is True
    
    def test_validate_missing_name(self, tool_registry):
        """测试缺少name字段"""
        tool = {
            "description": "翻译文本",
            "parameters": {},
            "endpoint": "/v1/translate"
        }
        
        assert tool_registry._validate_tool_schema(tool) is False
    
    def test_validate_missing_description(self, tool_registry):
        """测试缺少description字段"""
        tool = {
            "name": "translate",
            "parameters": {},
            "endpoint": "/v1/translate"
        }
        
        assert tool_registry._validate_tool_schema(tool) is False
    
    def test_validate_missing_parameters(self, tool_registry):
        """测试缺少parameters字段"""
        tool = {
            "name": "translate",
            "description": "翻译文本",
            "endpoint": "/v1/translate"
        }
        
        assert tool_registry._validate_tool_schema(tool) is False
    
    def test_validate_missing_endpoint(self, tool_registry):
        """测试缺少endpoint字段"""
        tool = {
            "name": "translate",
            "description": "翻译文本",
            "parameters": {}
        }
        
        assert tool_registry._validate_tool_schema(tool) is False
    
    def test_validate_empty_name(self, tool_registry):
        """测试空name"""
        tool = {
            "name": "",
            "description": "翻译文本",
            "parameters": {},
            "endpoint": "/v1/translate"
        }
        
        assert tool_registry._validate_tool_schema(tool) is False
    
    def test_validate_invalid_parameters_type(self, tool_registry):
        """测试parameters不是字典"""
        tool = {
            "name": "translate",
            "description": "翻译文本",
            "parameters": "invalid",
            "endpoint": "/v1/translate"
        }
        
        assert tool_registry._validate_tool_schema(tool) is False


@pytest.mark.asyncio
class TestListUserTools:
    """测试列出用户工具"""
    
    async def test_list_tools_no_registration(self, tool_registry):
        """测试用户未注册任何工具"""
        tools = await tool_registry.list_user_tools("qq", "123456")
        assert tools == []
    
    async def test_list_tools_with_registration(self, tool_registry):
        """测试用户已注册工具"""
        # 手动添加工具到注册表
        user_key = "qq:123456"
        tool1 = MCPTool(
            name="translate",
            description="翻译",
            parameters={},
            endpoint="/v1/translate"
        )
        tool2 = MCPTool(
            name="summarize",
            description="摘要",
            parameters={},
            endpoint="/v1/summarize"
        )
        
        tool_registry._registry[user_key] = {
            "translate": tool1,
            "summarize": tool2
        }
        
        tools = await tool_registry.list_user_tools("qq", "123456")
        assert len(tools) == 2
        assert "translate" in tools
        assert "summarize" in tools


class TestGetToolInfo:
    """测试获取工具信息"""
    
    def test_get_tool_info_not_registered(self, tool_registry):
        """测试获取未注册用户的工具信息"""
        info = tool_registry.get_tool_info("qq", "123456", "translate")
        assert info is None
    
    def test_get_tool_info_tool_not_found(self, tool_registry):
        """测试获取不存在的工具信息"""
        user_key = "qq:123456"
        tool_registry._registry[user_key] = {}
        
        info = tool_registry.get_tool_info("qq", "123456", "translate")
        assert info is None
    
    def test_get_tool_info_success(self, tool_registry):
        """测试成功获取工具信息"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译文本",
            parameters={
                "required": ["text", "target"],
                "properties": {
                    "text": {"type": "string"},
                    "target": {"type": "string"}
                }
            },
            endpoint="/v1/translate",
            method="POST"
        )
        
        tool_registry._registry[user_key] = {"translate": tool}
        
        info = tool_registry.get_tool_info("qq", "123456", "translate")
        
        assert info is not None
        assert info["name"] == "translate"
        assert info["description"] == "翻译文本"
        assert info["endpoint"] == "/v1/translate"
        assert info["method"] == "POST"
        assert "parameters" in info


@pytest.mark.asyncio
class TestUnregisterUserTools:
    """测试取消注册用户工具"""
    
    async def test_unregister_no_tools(self, tool_registry):
        """测试取消注册没有工具的用户"""
        result = await tool_registry.unregister_user_tools("qq", "123456")
        assert result is False
    
    async def test_unregister_with_tools(self, tool_registry):
        """测试取消注册有工具的用户"""
        user_key = "qq:123456"
        tool = MCPTool(
            name="translate",
            description="翻译",
            parameters={},
            endpoint="/v1/translate"
        )
        
        tool_registry._registry[user_key] = {"translate": tool}
        
        result = await tool_registry.unregister_user_tools("qq", "123456")
        assert result is True
        assert user_key not in tool_registry._registry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
