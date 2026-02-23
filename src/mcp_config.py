"""
MCP服务器配置文件
用于配置MCP服务的基础URL、端点映射和连接参数
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import os


@dataclass
class MCPServiceConfig:
    """MCP服务配置类"""
    
    # ============================================
    # 基础URL配置
    # ============================================
    # MCP服务器的基础URL
    # 可通过环境变量 MCP_BASE_URL 覆盖
    base_url: str = "https://api.mcp-service.example.com"
    
    # ============================================
    # 服务端点映射
    # ============================================
    # 服务名称到API端点路径的映射
    # 格式: {"服务名称": "/api/路径"}
    service_endpoints: Dict[str, str] = field(default_factory=lambda: {
        "translate": "/v1/translate",      # 翻译服务
        "summarize": "/v1/summarize",      # 摘要服务
        "analyze": "/v1/analyze",          # 分析服务
        "generate": "/v1/generate",        # 生成服务
        "chat": "/v1/chat",                # 对话服务
        "embedding": "/v1/embedding",      # 向量嵌入服务
    })
    
    # ============================================
    # 连接参数
    # ============================================
    # HTTP请求超时时间（秒）
    # 可通过环境变量 MCP_TIMEOUT 覆盖
    timeout: int = 30
    
    # 请求失败时的最大重试次数
    # 可通过环境变量 MCP_MAX_RETRIES 覆盖
    max_retries: int = 3
    
    # 重试之间的延迟时间（秒）
    retry_delay: float = 1.0
    
    # 是否验证SSL证书
    verify_ssl: bool = True
    
    # ============================================
    # 高级配置
    # ============================================
    # 连接池大小
    connection_pool_size: int = 10
    
    # 是否启用请求日志
    enable_request_logging: bool = True
    
    def __post_init__(self):
        """初始化后处理，支持环境变量覆盖"""
        # 从环境变量覆盖基础URL
        env_base_url = os.getenv("MCP_BASE_URL")
        if env_base_url:
            self.base_url = env_base_url
        
        # 从环境变量覆盖超时设置
        env_timeout = os.getenv("MCP_TIMEOUT")
        if env_timeout:
            try:
                self.timeout = int(env_timeout)
            except ValueError:
                pass  # 保持默认值
        
        # 从环境变量覆盖重试次数
        env_max_retries = os.getenv("MCP_MAX_RETRIES")
        if env_max_retries:
            try:
                self.max_retries = int(env_max_retries)
            except ValueError:
                pass  # 保持默认值
    
    def get_service_url(self, service_name: str) -> str:
        """
        获取完整的服务URL
        
        Args:
            service_name: 服务名称
            
        Returns:
            完整的服务URL
            
        Raises:
            ValueError: 如果服务名称未配置
        """
        endpoint = self.service_endpoints.get(service_name)
        if endpoint is None:
            raise ValueError(
                f"未知的服务名称: {service_name}. "
                f"可用服务: {', '.join(self.service_endpoints.keys())}"
            )
        return f"{self.base_url.rstrip('/')}{endpoint}"
    
    def add_service(self, service_name: str, endpoint: str) -> None:
        """
        动态添加新的服务端点
        
        Args:
            service_name: 服务名称
            endpoint: API端点路径
        """
        self.service_endpoints[service_name] = endpoint
    
    def validate(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        # 验证基础URL
        if not self.base_url:
            return False
        
        # 验证URL格式
        if not (self.base_url.startswith("http://") or 
                self.base_url.startswith("https://")):
            return False
        
        # 验证超时时间
        if self.timeout <= 0:
            return False
        
        # 验证重试次数
        if self.max_retries < 0:
            return False
        
        # 验证重试延迟
        if self.retry_delay < 0:
            return False
        
        # 验证服务端点
        if not self.service_endpoints:
            return False
        
        return True
    
    def get_config_summary(self) -> str:
        """
        获取配置摘要信息
        
        Returns:
            配置摘要字符串
        """
        return f"""
MCP服务配置摘要:
- 基础URL: {self.base_url}
- 超时时间: {self.timeout}秒
- 最大重试: {self.max_retries}次
- 重试延迟: {self.retry_delay}秒
- SSL验证: {'启用' if self.verify_ssl else '禁用'}
- 已配置服务: {len(self.service_endpoints)}个
  {', '.join(self.service_endpoints.keys())}
        """.strip()


# ============================================
# 默认配置实例
# ============================================
# 创建默认配置实例供直接导入使用
default_config = MCPServiceConfig()


# ============================================
# 环境变量说明
# ============================================
"""
支持的环境变量:

1. MCP_BASE_URL
   - 说明: MCP服务器的基础URL
   - 示例: export MCP_BASE_URL=https://prod-mcp.example.com
   - 默认: https://api.mcp-service.example.com

2. MCP_TIMEOUT
   - 说明: HTTP请求超时时间（秒）
   - 示例: export MCP_TIMEOUT=45
   - 默认: 30

3. MCP_MAX_RETRIES
   - 说明: 请求失败时的最大重试次数
   - 示例: export MCP_MAX_RETRIES=5
   - 默认: 3

使用示例:

# 方式1: 使用默认配置
from mcp_config import MCPServiceConfig
config = MCPServiceConfig()

# 方式2: 自定义配置
config = MCPServiceConfig(
    base_url="https://custom-mcp.example.com",
    timeout=60,
    max_retries=5
)

# 方式3: 从环境变量加载
import os
os.environ["MCP_BASE_URL"] = "https://prod-mcp.example.com"
config = MCPServiceConfig()  # 自动从环境变量覆盖

# 验证配置
if config.validate():
    print("✅ 配置有效")
else:
    print("❌ 配置无效")

# 获取服务URL
translate_url = config.get_service_url("translate")
print(f"翻译服务URL: {translate_url}")

# 动态添加新服务
config.add_service("custom_service", "/v1/custom")

# 查看配置摘要
print(config.get_config_summary())
"""
