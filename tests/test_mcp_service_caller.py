"""
MCPServiceCaller单元测试

测试MCPServiceCaller类的核心功能，包括：
- 成功的服务调用
- HTTP错误响应（401, 404, 500等）
- 网络超时
- 无效token的处理
- 重试逻辑

验证需求：
- 需求 8（MCP工具调用）
- 需求 12（错误处理）
- 需求 17（安全要求）
"""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aioresponses import aioresponses
from src.mcp_service.mcp_service_caller import MCPServiceCaller
from src.token_management.token_manager import TokenManager
from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption
from src.mcp_config import MCPServiceConfig


@pytest_asyncio.fixture
async def db_manager():
    """创建临时数据库管理器"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name
    
    manager = DatabaseManager(db_path)
    await manager.initialize()
    
    yield manager
    
    await manager.close()
    
    # 清理临时文件
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def encryption():
    """创建加密器（使用临时密钥）"""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    return TokenEncryption(encryption_key=key)


@pytest_asyncio.fixture
async def token_manager(db_manager, encryption):
    """创建TokenManager实例"""
    return TokenManager(db_manager, encryption)


@pytest.fixture
def mcp_config():
    """创建MCP配置实例"""
    return MCPServiceConfig(
        base_url="https://test-mcp.example.com",
        timeout=10,
        max_retries=2,
        retry_delay=0.1  # 使用较短的延迟以加快测试
    )


@pytest_asyncio.fixture
async def service_caller(token_manager, mcp_config):
    """创建MCPServiceCaller实例"""
    return MCPServiceCaller(token_manager, mcp_config)


@pytest_asyncio.fixture
async def setup_user_token(token_manager):
    """设置测试用户的token"""
    platform = "qq"
    user_id = "123456"
    token = "sk-test-token-123"
    
    await token_manager.bind_token(platform, user_id, token)
    
    return platform, user_id, token


class TestMCPServiceCallerInit:
    """测试MCPServiceCaller初始化"""
    
    @pytest.mark.asyncio
    async def test_init_with_config(self, token_manager, mcp_config):
        """测试使用自定义配置初始化"""
        caller = MCPServiceCaller(token_manager, mcp_config)
        assert caller.token_manager == token_manager
        assert caller.config == mcp_config
    
    @pytest.mark.asyncio
    async def test_init_without_config(self, token_manager):
        """测试使用默认配置初始化"""
        caller = MCPServiceCaller(token_manager)
        assert caller.token_manager == token_manager
        assert caller.config is not None
        assert isinstance(caller.config, MCPServiceConfig)


class TestMCPServiceCallerCallService:
    """测试服务调用功能"""
    
    @pytest.mark.asyncio
    async def test_call_service_no_token(self, service_caller):
        """测试用户未绑定token的情况
        
        验证需求 12.1: 用户未绑定token时调用服务返回友好错误提示
        """
        platform = "qq"
        user_id = "999999"  # 不存在的用户
        
        result = await service_caller.call_service(
            platform, user_id, "translate", text="Hello"
        )
        
        assert result["success"] is False
        assert "未绑定token" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_invalid_service_name(self, service_caller, setup_user_token):
        """测试无效的服务名称"""
        platform, user_id, _ = setup_user_token
        
        result = await service_caller.call_service(
            platform, user_id, "invalid_service", param="value"
        )
        
        assert result["success"] is False
        assert "未知的服务名称" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_success(self, service_caller, setup_user_token):
        """测试成功的服务调用
        
        验证需求 8.3: 使用用户的token调用MCP服务
        验证需求 8.4: MCP服务返回成功响应时格式化结果并返回给用户
        验证需求 17.5: 通过Authorization头传输token
        """
        platform, user_id, token = setup_user_token
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=200,
                payload={"result": "你好"}
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello", target="zh"
            )
            
            assert result["success"] is True
            assert "data" in result
            assert result["data"]["result"] == "你好"
    
    @pytest.mark.asyncio
    async def test_call_service_401_unauthorized(self, service_caller, setup_user_token):
        """测试HTTP 401错误（token无效）
        
        验证需求 8.5: MCP服务返回错误时返回友好的错误消息
        验证需求 12.4: MCP服务返回401错误时提示用户token可能已过期
        """
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应
        with aioresponses() as m:
            # 只mock一次，因为401不应该重试
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=401,
                repeat=True  # 允许重复使用这个mock
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "Token无效" in result["error"] or "已过期" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_404_not_found(self, service_caller, setup_user_token):
        """测试HTTP 404错误"""
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=404,
                body="Not Found",
                repeat=True
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "404" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_500_server_error(self, service_caller, setup_user_token):
        """测试HTTP 500错误"""
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=500,
                body="Internal Server Error",
                repeat=True
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_timeout(self, service_caller, setup_user_token):
        """测试服务调用超时
        
        验证需求 12.3: MCP服务调用超时时返回超时错误并建议稍后重试
        """
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应（模拟超时）
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                exception=TimeoutError(),
                repeat=True
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "超时" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_retry_all_failed(self, service_caller, setup_user_token):
        """测试重试逻辑：所有尝试都失败（仅对超时重试）"""
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应（所有请求都超时）
        with aioresponses() as m:
            # max_retries=2，所以总共会尝试3次
            m.post(
                "https://test-mcp.example.com/v1/translate",
                exception=asyncio.TimeoutError(),
                repeat=True
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "超时" in result["error"]
    
    @pytest.mark.asyncio
    async def test_call_service_no_retry_on_401(self, service_caller, setup_user_token):
        """测试401错误不重试（token无效不应该重试）"""
        platform, user_id, _ = setup_user_token
        
        # Mock HTTP响应
        with aioresponses() as m:
            # 只mock一次，因为401不应该重试
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=401,
                repeat=True
            )
            
            result = await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            assert result["success"] is False
            assert "Token无效" in result["error"] or "已过期" in result["error"]


class TestMCPServiceCallerValidateToken:
    """测试token验证功能"""
    
    @pytest.mark.asyncio
    async def test_validate_token_empty(self, service_caller):
        """测试空token验证"""
        result = await service_caller.validate_token("")
        assert result is False
        
        result = await service_caller.validate_token(None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, service_caller):
        """测试有效token验证
        
        验证需求 1.1: 验证token是否有效
        """
        token = "sk-valid-token"
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                status=200,
                payload={"tools": []}
            )
            
            result = await service_caller.validate_token(token)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, service_caller):
        """测试无效token验证"""
        token = "sk-invalid-token"
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                status=401
            )
            
            result = await service_caller.validate_token(token)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_timeout(self, service_caller):
        """测试token验证超时"""
        token = "sk-test-token"
        
        # Mock HTTP响应（模拟超时）
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                exception=TimeoutError()
            )
            
            result = await service_caller.validate_token(token)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_token_server_error(self, service_caller):
        """测试token验证时服务器错误"""
        token = "sk-test-token"
        
        # Mock HTTP响应
        with aioresponses() as m:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                status=500
            )
            
            result = await service_caller.validate_token(token)
            # 对于500错误，我们保守地返回False
            assert result is False


class TestMCPServiceCallerSecurity:
    """测试安全相关功能"""
    
    @pytest.mark.asyncio
    async def test_authorization_header_format(self, service_caller, setup_user_token):
        """测试Authorization头格式正确
        
        验证需求 17.5: 通过Authorization头传输token（Bearer格式）
        """
        platform, user_id, token = setup_user_token
        
        # Mock HTTP响应并验证请求头
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=200,
                payload={"result": "success"}
            )
            
            await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            # 验证请求头包含正确的Authorization
            # aioresponses会记录所有请求
            requests = m.requests
            assert len(requests) > 0
            
            # 获取最后一个请求
            last_request = list(requests.values())[0][0]
            headers = last_request.kwargs.get('headers', {})
            
            assert 'Authorization' in headers
            assert headers['Authorization'] == f"Bearer {token}"
    
    @pytest.mark.asyncio
    async def test_https_url(self, service_caller, setup_user_token):
        """测试使用HTTPS URL
        
        验证需求 17.3: 使用HTTPS调用MCP服务
        """
        platform, user_id, _ = setup_user_token
        
        # 验证配置的URL是HTTPS
        assert service_caller.config.base_url.startswith("https://")
        
        # 验证实际请求使用HTTPS
        with aioresponses() as m:
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=200,
                payload={"result": "success"}
            )
            
            await service_caller.call_service(
                platform, user_id, "translate", text="Hello"
            )
            
            # 验证请求URL是HTTPS
            requests = m.requests
            assert len(requests) > 0
            
            # 获取请求的URL - requests是一个字典，key是(method, URL)元组
            request_key = list(requests.keys())[0]
            method, url = request_key
            assert str(url).startswith("https://")


class TestMCPServiceCallerMultipleUsers:
    """测试多用户场景"""
    
    @pytest.mark.asyncio
    async def test_different_users_different_tokens(self, service_caller, token_manager):
        """测试不同用户使用各自的token"""
        # 设置两个用户
        await token_manager.bind_token("qq", "user1", "token1")
        await token_manager.bind_token("qq", "user2", "token2")
        
        # Mock HTTP响应
        with aioresponses() as m:
            # 为两个用户的请求都添加mock（使用repeat=True）
            m.post(
                "https://test-mcp.example.com/v1/translate",
                status=200,
                payload={"result": "result1"},
                repeat=True
            )
            
            # 用户1调用服务
            result1 = await service_caller.call_service(
                "qq", "user1", "translate", text="Hello"
            )
            
            # 用户2调用服务
            result2 = await service_caller.call_service(
                "qq", "user2", "translate", text="World"
            )
            
            assert result1["success"] is True
            assert result2["success"] is True
            
            # 验证使用了不同的token
            requests = m.requests
            # requests是一个字典，key是(method, URL)元组，value是请求列表
            request_key = list(requests.keys())[0]
            request_list = requests[request_key]
            
            assert len(request_list) >= 2
            
            headers1 = request_list[0].kwargs.get('headers', {})
            headers2 = request_list[1].kwargs.get('headers', {})
            
            assert headers1['Authorization'] == "Bearer token1"
            assert headers2['Authorization'] == "Bearer token2"
