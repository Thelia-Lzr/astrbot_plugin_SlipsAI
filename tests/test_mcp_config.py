"""
MCPServiceConfig模块的单元测试

测试MCP服务配置管理功能。
**Validates: Requirements 14**
"""

import pytest
import os
from unittest.mock import patch

from src.mcp_config import MCPServiceConfig


class TestMCPServiceConfig:
    """MCPServiceConfig类的单元测试"""
    
    def test_default_configuration(self):
        """测试默认配置加载"""
        config = MCPServiceConfig()
        
        # 验证默认基础URL
        assert config.base_url == "https://api.mcp-service.example.com"
        
        # 验证默认超时时间
        assert config.timeout == 30
        
        # 验证默认重试次数
        assert config.max_retries == 3
        
        # 验证默认重试延迟
        assert config.retry_delay == 1.0
        
        # 验证默认SSL验证
        assert config.verify_ssl is True
        
        # 验证默认服务端点存在
        assert "translate" in config.service_endpoints
        assert "summarize" in config.service_endpoints
        assert "analyze" in config.service_endpoints
        assert "generate" in config.service_endpoints
    
    def test_custom_configuration(self):
        """测试自定义配置"""
        config = MCPServiceConfig(
            base_url="https://custom-mcp.example.com",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            verify_ssl=False
        )
        
        assert config.base_url == "https://custom-mcp.example.com"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.verify_ssl is False
    
    def test_environment_variable_override_base_url(self):
        """测试环境变量覆盖基础URL"""
        with patch.dict(os.environ, {"MCP_BASE_URL": "https://env-mcp.example.com"}):
            config = MCPServiceConfig()
            assert config.base_url == "https://env-mcp.example.com"
    
    def test_environment_variable_override_timeout(self):
        """测试环境变量覆盖超时时间"""
        with patch.dict(os.environ, {"MCP_TIMEOUT": "45"}):
            config = MCPServiceConfig()
            assert config.timeout == 45
    
    def test_environment_variable_override_max_retries(self):
        """测试环境变量覆盖最大重试次数"""
        with patch.dict(os.environ, {"MCP_MAX_RETRIES": "10"}):
            config = MCPServiceConfig()
            assert config.max_retries == 10
    
    def test_environment_variable_invalid_timeout(self):
        """测试环境变量提供无效超时时间时保持默认值"""
        with patch.dict(os.environ, {"MCP_TIMEOUT": "invalid"}):
            config = MCPServiceConfig()
            # 应该保持默认值
            assert config.timeout == 30
    
    def test_environment_variable_invalid_max_retries(self):
        """测试环境变量提供无效重试次数时保持默认值"""
        with patch.dict(os.environ, {"MCP_MAX_RETRIES": "not_a_number"}):
            config = MCPServiceConfig()
            # 应该保持默认值
            assert config.max_retries == 3
    
    def test_get_service_url_success(self):
        """测试成功获取服务URL"""
        config = MCPServiceConfig(base_url="https://api.example.com")
        
        # 测试获取翻译服务URL
        translate_url = config.get_service_url("translate")
        assert translate_url == "https://api.example.com/v1/translate"
        
        # 测试获取摘要服务URL
        summarize_url = config.get_service_url("summarize")
        assert summarize_url == "https://api.example.com/v1/summarize"
    
    def test_get_service_url_with_trailing_slash(self):
        """测试基础URL带有尾部斜杠时正确处理"""
        config = MCPServiceConfig(base_url="https://api.example.com/")
        
        translate_url = config.get_service_url("translate")
        # 不应该有双斜杠
        assert translate_url == "https://api.example.com/v1/translate"
        assert "//" not in translate_url.replace("https://", "")
    
    def test_get_service_url_unknown_service(self):
        """测试获取未知服务URL时抛出异常"""
        config = MCPServiceConfig()
        
        with pytest.raises(ValueError) as exc_info:
            config.get_service_url("unknown_service")
        
        # 验证错误消息包含服务名称
        assert "unknown_service" in str(exc_info.value)
        # 验证错误消息包含可用服务列表
        assert "translate" in str(exc_info.value)
    
    def test_add_service(self):
        """测试动态添加新服务端点"""
        config = MCPServiceConfig()
        
        # 添加新服务
        config.add_service("custom_service", "/v1/custom")
        
        # 验证服务已添加
        assert "custom_service" in config.service_endpoints
        assert config.service_endpoints["custom_service"] == "/v1/custom"
        
        # 验证可以获取新服务的URL
        custom_url = config.get_service_url("custom_service")
        assert custom_url.endswith("/v1/custom")
    
    def test_add_service_overwrites_existing(self):
        """测试添加已存在的服务会覆盖原有配置"""
        config = MCPServiceConfig()
        
        # 覆盖现有服务
        original_endpoint = config.service_endpoints["translate"]
        config.add_service("translate", "/v2/translate")
        
        # 验证端点已更新
        assert config.service_endpoints["translate"] == "/v2/translate"
        assert config.service_endpoints["translate"] != original_endpoint
    
    def test_validate_valid_configuration(self):
        """测试验证有效配置"""
        config = MCPServiceConfig(
            base_url="https://api.example.com",
            timeout=30,
            max_retries=3,
            retry_delay=1.0
        )
        
        assert config.validate() is True
    
    def test_validate_empty_base_url(self):
        """测试验证空基础URL"""
        config = MCPServiceConfig(base_url="")
        
        assert config.validate() is False
    
    def test_validate_invalid_url_scheme(self):
        """测试验证无效的URL协议"""
        config = MCPServiceConfig(base_url="ftp://api.example.com")
        
        assert config.validate() is False
    
    def test_validate_no_url_scheme(self):
        """测试验证缺少协议的URL"""
        config = MCPServiceConfig(base_url="api.example.com")
        
        assert config.validate() is False
    
    def test_validate_negative_timeout(self):
        """测试验证负数超时时间"""
        config = MCPServiceConfig(timeout=-1)
        
        assert config.validate() is False
    
    def test_validate_zero_timeout(self):
        """测试验证零超时时间"""
        config = MCPServiceConfig(timeout=0)
        
        assert config.validate() is False
    
    def test_validate_negative_max_retries(self):
        """测试验证负数重试次数"""
        config = MCPServiceConfig(max_retries=-1)
        
        assert config.validate() is False
    
    def test_validate_zero_max_retries(self):
        """测试验证零重试次数（应该有效）"""
        config = MCPServiceConfig(max_retries=0)
        
        # 零重试次数是有效的（表示不重试）
        assert config.validate() is True
    
    def test_validate_negative_retry_delay(self):
        """测试验证负数重试延迟"""
        config = MCPServiceConfig(retry_delay=-1.0)
        
        assert config.validate() is False
    
    def test_validate_empty_service_endpoints(self):
        """测试验证空服务端点"""
        config = MCPServiceConfig(service_endpoints={})
        
        assert config.validate() is False
    
    def test_get_config_summary(self):
        """测试获取配置摘要"""
        config = MCPServiceConfig(
            base_url="https://test.example.com",
            timeout=45,
            max_retries=5,
            retry_delay=2.0,
            verify_ssl=False
        )
        
        summary = config.get_config_summary()
        
        # 验证摘要包含关键信息
        assert "https://test.example.com" in summary
        assert "45秒" in summary
        assert "5次" in summary
        assert "2.0秒" in summary
        assert "禁用" in summary  # SSL验证禁用
        
        # 验证包含服务列表
        assert "translate" in summary
        assert "summarize" in summary
    
    def test_service_endpoints_default_values(self):
        """测试默认服务端点包含所有必需服务"""
        config = MCPServiceConfig()
        
        # 验证所有默认服务都存在
        expected_services = [
            "translate",
            "summarize",
            "analyze",
            "generate",
            "chat",
            "embedding"
        ]
        
        for service in expected_services:
            assert service in config.service_endpoints, \
                f"默认配置应包含服务: {service}"
            assert config.service_endpoints[service].startswith("/"), \
                f"服务端点应以/开头: {service}"
    
    def test_http_url_is_valid(self):
        """测试HTTP协议的URL也是有效的"""
        config = MCPServiceConfig(base_url="http://localhost:8080")
        
        assert config.validate() is True
    
    def test_https_url_is_valid(self):
        """测试HTTPS协议的URL是有效的"""
        config = MCPServiceConfig(base_url="https://api.example.com")
        
        assert config.validate() is True
    
    def test_multiple_environment_variables(self):
        """测试同时使用多个环境变量覆盖"""
        env_vars = {
            "MCP_BASE_URL": "https://multi-env.example.com",
            "MCP_TIMEOUT": "90",
            "MCP_MAX_RETRIES": "7"
        }
        
        with patch.dict(os.environ, env_vars):
            config = MCPServiceConfig()
            
            assert config.base_url == "https://multi-env.example.com"
            assert config.timeout == 90
            assert config.max_retries == 7
    
    def test_custom_service_endpoints(self):
        """测试自定义服务端点映射"""
        custom_endpoints = {
            "service1": "/api/v1/service1",
            "service2": "/api/v2/service2"
        }
        
        config = MCPServiceConfig(service_endpoints=custom_endpoints)
        
        assert config.service_endpoints == custom_endpoints
        assert "translate" not in config.service_endpoints  # 默认服务不存在
    
    def test_connection_pool_size_default(self):
        """测试连接池大小默认值"""
        config = MCPServiceConfig()
        
        assert config.connection_pool_size == 10
    
    def test_enable_request_logging_default(self):
        """测试请求日志默认启用"""
        config = MCPServiceConfig()
        
        assert config.enable_request_logging is True
    
    def test_get_service_url_with_multiple_services(self):
        """测试获取多个不同服务的URL"""
        config = MCPServiceConfig(base_url="https://api.example.com")
        
        services = ["translate", "summarize", "analyze", "generate"]
        urls = [config.get_service_url(service) for service in services]
        
        # 验证所有URL都不同
        assert len(urls) == len(set(urls))
        
        # 验证所有URL都包含基础URL
        for url in urls:
            assert url.startswith("https://api.example.com")
    
    def test_config_immutability_after_validation(self):
        """测试配置验证后仍可修改（配置不是不可变的）"""
        config = MCPServiceConfig()
        
        # 验证配置
        assert config.validate() is True
        
        # 修改配置
        config.timeout = 60
        
        # 验证修改生效
        assert config.timeout == 60
    
    def test_base_url_without_port(self):
        """测试不带端口的基础URL"""
        config = MCPServiceConfig(base_url="https://api.example.com")
        
        url = config.get_service_url("translate")
        assert url == "https://api.example.com/v1/translate"
    
    def test_base_url_with_port(self):
        """测试带端口的基础URL"""
        config = MCPServiceConfig(base_url="https://api.example.com:8443")
        
        url = config.get_service_url("translate")
        assert url == "https://api.example.com:8443/v1/translate"
    
    def test_base_url_with_path(self):
        """测试带路径的基础URL"""
        config = MCPServiceConfig(base_url="https://api.example.com/mcp")
        
        url = config.get_service_url("translate")
        assert url == "https://api.example.com/mcp/v1/translate"
    
    def test_endpoint_without_leading_slash(self):
        """测试端点路径不以斜杠开头的情况"""
        config = MCPServiceConfig()
        config.add_service("test", "v1/test")  # 没有前导斜杠
        
        url = config.get_service_url("test")
        # 应该正确拼接
        assert "v1/test" in url
