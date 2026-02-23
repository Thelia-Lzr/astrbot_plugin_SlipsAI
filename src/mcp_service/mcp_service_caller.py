"""
MCP服务调用模块

该模块使用用户token调用外部MCP服务。
实现HTTP请求、超时和重试逻辑、错误处理等功能。

职责：
- 获取用户的token并调用外部MCP服务
- 处理MCP服务调用的HTTP请求
- 处理token无效或过期的情况
- 返回格式化的服务响应
- 实现超时和重试逻辑

验证需求：
- 需求 8（MCP工具调用）
- 需求 17（安全要求）
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from src.token_management.token_manager import TokenManager
from src.mcp_config import MCPServiceConfig


logger = logging.getLogger(__name__)


class MCPServiceCaller:
    """MCP服务调用器
    
    使用用户token调用外部MCP服务，处理HTTP请求、超时、重试等逻辑。
    
    Attributes:
        token_manager: Token管理器实例
        config: MCP服务配置实例
    """
    
    def __init__(self, token_manager: TokenManager, config: Optional[MCPServiceConfig] = None):
        """初始化MCP服务调用器
        
        Args:
            token_manager: Token管理器实例
            config: MCP服务配置实例，如果为None则使用默认配置
        """
        self.token_manager = token_manager
        self.config = config if config is not None else MCPServiceConfig()
        logger.info("MCPServiceCaller initialized")
    
    async def call_service(
        self, 
        platform: str, 
        user_id: str, 
        service_name: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """使用用户token调用MCP服务
        
        获取用户token，构建HTTP请求，调用MCP服务，处理响应和错误。
        实现超时和重试逻辑（根据MCPConfig配置）。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
            service_name: 服务名称（如：translate, summarize等）
            **kwargs: 服务参数，将作为JSON body发送
            
        Returns:
            Dict[str, Any]: 服务响应字典
                成功时: {"success": True, "data": <响应数据>}
                失败时: {"success": False, "error": <错误消息>}
                
        验证需求：
        - 需求 8.3: 使用用户的token调用MCP服务
        - 需求 8.4: MCP服务返回成功响应时格式化结果并返回给用户
        - 需求 8.5: MCP服务返回错误时返回友好的错误消息
        - 需求 17.3: 使用HTTPS调用MCP服务
        - 需求 17.5: 通过Authorization头传输token（不在URL中）
        """
        # 步骤 1: 获取用户token
        token = await self.token_manager.get_user_token(platform, user_id)
        
        if token is None:
            logger.warning(f"User {platform}:{user_id} has no token")
            return {
                "success": False,
                "error": "用户未绑定token，请先使用 /bind_token 绑定"
            }
        
        # 步骤 2: 获取服务URL
        try:
            service_url = self.config.get_service_url(service_name)
        except ValueError as e:
            logger.error(f"Invalid service name: {service_name}")
            return {
                "success": False,
                "error": f"未知的服务名称: {service_name}"
            }
        
        # 步骤 3: 构建请求头
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 步骤 4: 调用MCP服务（带重试逻辑）
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self._make_request(
                    service_url, 
                    headers, 
                    kwargs,
                    attempt
                )
                
                # 如果成功，直接返回
                if result["success"]:
                    return result
                
                # 对于401错误（token无效），不重试
                if "Token无效" in result.get("error", "") or "已过期" in result.get("error", ""):
                    logger.info("Token invalid, not retrying")
                    return result
                
                # 对于404、500等HTTP错误，不重试（这些是服务端问题，重试无意义）
                if "HTTP" in result.get("error", ""):
                    logger.info(f"HTTP error, not retrying: {result.get('error')}")
                    return result
                
                # 如果是最后一次尝试，返回错误
                if attempt >= self.config.max_retries:
                    return result
                
                # 否则，记录错误并准备重试（仅对超时和网络错误重试）
                last_error = result.get("error", "Unknown error")
                logger.warning(
                    f"Service call failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {last_error}"
                )
                
                # 等待后重试
                await asyncio.sleep(self.config.retry_delay)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Exception during service call (attempt {attempt + 1}): {e}")
                
                # 如果是最后一次尝试，返回错误
                if attempt >= self.config.max_retries:
                    return {
                        "success": False,
                        "error": f"服务调用异常: {str(e)}"
                    }
                
                # 等待后重试
                await asyncio.sleep(self.config.retry_delay)
        
        # 理论上不应该到达这里，但作为保险
        return {
            "success": False,
            "error": f"服务调用失败: {last_error}"
        }
    
    async def _make_request(
        self,
        url: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """执行HTTP请求
        
        Args:
            url: 请求URL
            headers: 请求头
            data: 请求数据
            attempt: 当前尝试次数（用于日志）
            
        Returns:
            Dict[str, Any]: 响应字典
        """
        try:
            # 创建超时配置
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=timeout,
                    ssl=self.config.verify_ssl
                ) as response:
                    # 处理HTTP状态码
                    if response.status == 200:
                        # 成功
                        response_data = await response.json()
                        logger.info(f"Service call successful: {url}")
                        return {
                            "success": True,
                            "data": response_data
                        }
                    elif response.status == 401:
                        # Token无效
                        logger.warning(f"Token invalid for service: {url}")
                        return {
                            "success": False,
                            "error": "Token无效或已过期，请更新token"
                        }
                    else:
                        # 其他错误
                        error_text = await response.text()
                        logger.error(
                            f"Service call failed with status {response.status}: {error_text}"
                        )
                        return {
                            "success": False,
                            "error": f"服务调用失败: HTTP {response.status}",
                            "details": error_text
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"Service call timeout: {url}")
            return {
                "success": False,
                "error": "服务调用超时，请稍后重试"
            }
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {
                "success": False,
                "error": f"网络错误: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            return {
                "success": False,
                "error": f"请求异常: {str(e)}"
            }
    
    async def validate_token(self, token: str) -> bool:
        """验证token是否有效
        
        通过调用MCP服务的健康检查端点或工具列表端点来验证token。
        这是一个可选的辅助方法，用于在绑定token时验证其有效性。
        
        Args:
            token: 要验证的token字符串
            
        Returns:
            bool: token有效返回True，无效返回False
            
        验证需求：
        - 需求 1.1: 验证token是否有效
        """
        if not token:
            logger.warning("Empty token provided for validation")
            return False
        
        try:
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # 尝试调用工具列表端点（假设这是一个轻量级的验证端点）
            # 如果MCP服务有专门的验证端点，应该使用那个
            validation_url = f"{self.config.base_url.rstrip('/')}/v1/tools/list"
            
            timeout = aiohttp.ClientTimeout(total=10)  # 验证使用较短的超时
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    validation_url,
                    headers=headers,
                    timeout=timeout,
                    ssl=self.config.verify_ssl
                ) as response:
                    if response.status == 200:
                        logger.info("Token validation successful")
                        return True
                    elif response.status == 401:
                        logger.warning("Token validation failed: 401 Unauthorized")
                        return False
                    else:
                        logger.warning(f"Token validation returned status {response.status}")
                        # 对于其他状态码，我们不确定token是否有效
                        # 可以选择返回False或True，这里选择False以保守
                        return False
                        
        except asyncio.TimeoutError:
            logger.error("Token validation timeout")
            return False
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False
