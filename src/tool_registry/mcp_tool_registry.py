"""MCP工具注册表模块

该模块管理MCP工具的发现、注册和调用，实现工具的动态注册和用户隔离。

职责：
- 从MCP服务器发现可用工具列表
- 为每个用户维护独立的工具注册表
- 动态创建工具处理器并绑定到用户会话
- 调用工具时自动使用用户的token进行认证
- 确保工具隔离性（用户只能调用自己的工具）
- 管理工具的生命周期（注册、更新、注销）

验证需求：
- 需求 6（MCP工具自动发现）
- 需求 7（MCP工具注册）
- 需求 8（MCP工具调用）
- 需求 9（工具隔离性）
- 需求 10（工具生命周期管理）
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from src.token_management.token_manager import TokenManager
from src.mcp_config import MCPServiceConfig
from src.tool_registry.mcp_tool import MCPTool


logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """MCP工具注册表
    
    管理MCP工具的发现、注册和调用。为每个用户维护独立的工具注册表，
    确保工具隔离性和安全性。
    
    Attributes:
        token_manager: Token管理器实例
        mcp_config: MCP服务配置实例
        _registry: 工具注册表，格式为 {user_key: {tool_name: MCPTool}}
    """
    
    def __init__(self, token_manager: TokenManager, mcp_config: Optional[MCPServiceConfig] = None):
        """初始化MCP工具注册表
        
        Args:
            token_manager: Token管理器实例
            mcp_config: MCP服务配置实例，如果为None则使用默认配置
        """
        self.token_manager = token_manager
        self.mcp_config = mcp_config if mcp_config is not None else MCPServiceConfig()
        self._registry: Dict[str, Dict[str, MCPTool]] = {}
        logger.info("MCPToolRegistry initialized")
    
    def _get_user_key(self, platform: str, user_id: str) -> str:
        """生成用户唯一标识
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
            
        Returns:
            用户唯一标识字符串，格式为 "platform:user_id"
        """
        return f"{platform}:{user_id}"
    
    async def discover_tools(self, token: str) -> List[Dict[str, Any]]:
        """从MCP服务器发现可用工具
        
        调用MCP服务器的 /v1/tools/list 端点获取工具列表，
        并验证每个工具的schema格式。
        
        Args:
            token: 用户的MCP token
            
        Returns:
            工具列表，每个工具包含: name, description, parameters, endpoint
            如果发现失败则返回空列表
            
        验证需求：
        - 需求 6.1: 调用MCP服务器的工具列表API
        - 需求 6.2: 验证每个工具的schema格式
        """
        if not token:
            logger.warning("Empty token provided for tool discovery")
            return []
        
        try:
            # 构建工具发现请求
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            tools_endpoint = f"{self.mcp_config.base_url.rstrip('/')}/v1/tools/list"
            timeout = aiohttp.ClientTimeout(total=self.mcp_config.timeout)
            
            logger.debug(f"Discovering tools from: {tools_endpoint}")
            
            # 调用MCP服务器获取工具列表
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    tools_endpoint,
                    headers=headers,
                    timeout=timeout,
                    ssl=self.mcp_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        tools = data.get("tools", [])
                        
                        logger.info(f"Discovered {len(tools)} tools from MCP server")
                        
                        # 验证工具数据格式
                        validated_tools = []
                        for tool in tools:
                            if self._validate_tool_schema(tool):
                                validated_tools.append(tool)
                            else:
                                logger.warning(f"Tool schema validation failed: {tool.get('name', 'unknown')}")
                        
                        logger.info(f"Validated {len(validated_tools)} tools")
                        return validated_tools
                        
                    elif response.status == 401:
                        logger.error("Token invalid, cannot discover tools")
                        return []
                    else:
                        error_text = await response.text()
                        logger.error(f"Tool discovery failed: HTTP {response.status}, {error_text}")
                        return []
                        
        except asyncio.TimeoutError:
            logger.error("Tool discovery request timeout")
            return []
        except Exception as e:
            logger.error(f"Tool discovery exception: {e}")
            return []
    
    def _validate_tool_schema(self, tool: Dict[str, Any]) -> bool:
        """验证工具schema格式
        
        检查工具数据是否包含所有必需字段，并且格式正确。
        
        Args:
            tool: 工具数据字典
            
        Returns:
            schema有效返回True，否则返回False
        """
        # 检查必需字段
        required_fields = ["name", "description", "parameters", "endpoint"]
        for field in required_fields:
            if field not in tool:
                logger.warning(f"Tool missing required field: {field}")
                return False
        
        # 检查name是否为非空字符串
        if not isinstance(tool["name"], str) or not tool["name"]:
            logger.warning("Tool name is not a valid string")
            return False
        
        # 检查description是否为字符串
        if not isinstance(tool["description"], str):
            logger.warning("Tool description is not a string")
            return False
        
        # 检查parameters是否为字典
        if not isinstance(tool["parameters"], dict):
            logger.warning("Tool parameters is not a dict")
            return False
        
        # 检查endpoint是否为非空字符串
        if not isinstance(tool["endpoint"], str) or not tool["endpoint"]:
            logger.warning("Tool endpoint is not a valid string")
            return False
        
        return True
    
    async def register_user_tools(self, platform: str, user_id: str) -> bool:
        """为用户注册MCP工具到聊天会话
        
        获取用户token，调用discover_tools发现可用工具，
        将工具存储在注册表中（user_key: {tool_name: MCPTool}）。
        
        Args:
            platform: 用户平台
            user_id: 用户ID
            
        Returns:
            注册是否成功（至少注册了一个工具）
            
        验证需求：
        - 需求 7.2: 将工具信息存储在用户的工具注册表中
        - 需求 7.3: 为每个用户维护独立的工具注册表
        """
        user_key = self._get_user_key(platform, user_id)
        
        # 获取用户token
        token = await self.token_manager.get_user_token(platform, user_id)
        if token is None:
            logger.error(f"User {user_key} has no token")
            return False
        
        # 发现可用工具
        tools_data = await self.discover_tools(token)
        if not tools_data:
            logger.warning(f"No tools discovered for user {user_key}")
            return False
        
        # 为用户注册工具
        self._registry[user_key] = {}
        
        for tool_data in tools_data:
            try:
                tool = MCPTool.from_dict(tool_data)
                self._registry[user_key][tool.name] = tool
                logger.debug(f"Registered tool '{tool.name}' for user {user_key}")
            except Exception as e:
                logger.error(f"Failed to create MCPTool from data: {e}")
                continue
        
        tool_count = len(self._registry[user_key])
        logger.info(f"Registered {tool_count} tools for user {user_key}")
        
        return tool_count > 0
    
    async def unregister_user_tools(self, platform: str, user_id: str) -> bool:
        """取消注册用户的MCP工具
        
        从注册表中删除用户的所有工具。
        
        Args:
            platform: 用户平台
            user_id: 用户ID
            
        Returns:
            取消注册是否成功
            
        验证需求：
        - 需求 4.1: 取消注册该用户的所有MCP工具
        - 需求 10.3: token解绑后自动取消注册所有工具
        """
        user_key = self._get_user_key(platform, user_id)
        
        if user_key in self._registry:
            tool_count = len(self._registry[user_key])
            del self._registry[user_key]
            logger.info(f"Unregistered {tool_count} tools for user {user_key}")
            return True
        else:
            logger.debug(f"No tools to unregister for user {user_key}")
            return False
    
    async def call_tool(
        self, 
        platform: str, 
        user_id: str, 
        tool_name: str, 
        **params
    ) -> Dict[str, Any]:
        """调用用户的MCP工具
        
        验证工具是否已注册，验证参数schema，使用用户token调用MCP服务。
        
        Args:
            platform: 用户平台
            user_id: 用户ID
            tool_name: 工具名称
            **params: 工具参数
            
        Returns:
            工具执行结果字典
                成功时: {"success": True, "data": <结果>, "tool": <工具名>}
                失败时: {"success": False, "error": <错误消息>}
                
        验证需求：
        - 需求 8.1: 验证工具是否存在于用户的注册表中
        - 需求 8.2: 验证提供的参数是否符合工具的schema
        - 需求 8.3: 使用用户的token调用MCP服务
        - 需求 9.2: 调用工具时仅使用该用户的token进行认证
        """
        user_key = self._get_user_key(platform, user_id)
        
        # 步骤 1: 验证用户是否有此工具
        if user_key not in self._registry:
            logger.warning(f"User {user_key} has no registered tools")
            return {
                "success": False,
                "error": "用户未注册任何工具，请先绑定token"
            }
        
        tool = self._registry[user_key].get(tool_name)
        if tool is None:
            logger.warning(f"Tool '{tool_name}' not found for user {user_key}")
            return {
                "success": False,
                "error": f"工具 '{tool_name}' 不存在或未注册"
            }
        
        # 步骤 2: 验证参数
        if not tool.validate_params(params):
            logger.warning(f"Parameter validation failed for tool '{tool_name}'")
            return {
                "success": False,
                "error": "参数验证失败，请检查必需参数"
            }
        
        # 步骤 3: 获取用户token
        token = await self.token_manager.get_user_token(platform, user_id)
        if token is None:
            logger.error(f"User {user_key} token not found")
            return {
                "success": False,
                "error": "Token已失效，请重新绑定"
            }
        
        # 步骤 4: 构建工具调用请求
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        tool_url = f"{self.mcp_config.base_url.rstrip('/')}{tool.endpoint}"
        
        # 步骤 5: 调用MCP工具
        try:
            timeout = aiohttp.ClientTimeout(total=self.mcp_config.timeout)
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    tool.method,
                    tool_url,
                    headers=headers,
                    json=params,
                    timeout=timeout,
                    ssl=self.mcp_config.verify_ssl
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Tool '{tool_name}' called successfully for user {user_key}")
                        return {
                            "success": True,
                            "data": data,
                            "tool": tool_name
                        }
                    elif response.status == 401:
                        logger.warning(f"Token invalid for tool call: {tool_name}")
                        return {
                            "success": False,
                            "error": "Token无效或已过期"
                        }
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Tool call failed with status {response.status}: {error_text}"
                        )
                        return {
                            "success": False,
                            "error": f"工具调用失败: HTTP {response.status}",
                            "details": error_text
                        }
                        
        except asyncio.TimeoutError:
            logger.error(f"Tool call timeout: {tool_name}")
            return {
                "success": False,
                "error": "工具调用超时"
            }
        except Exception as e:
            logger.error(f"Tool call exception: {e}")
            return {
                "success": False,
                "error": f"调用异常: {str(e)}"
            }
    
    async def list_user_tools(self, platform: str, user_id: str) -> List[str]:
        """列出用户可用的MCP工具
        
        Args:
            platform: 用户平台
            user_id: 用户ID
            
        Returns:
            工具名称列表
            
        验证需求：
        - 需求 7.4: 用户查询工具列表时返回该用户已注册的所有工具名称
        - 需求 9.4: 用户查询工具列表时仅返回该用户已注册的工具
        """
        user_key = self._get_user_key(platform, user_id)
        
        if user_key not in self._registry:
            logger.debug(f"User {user_key} has no registered tools")
            return []
        
        tool_names = list(self._registry[user_key].keys())
        logger.debug(f"User {user_key} has {len(tool_names)} tools")
        
        return tool_names
    
    def get_tool_info(self, platform: str, user_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具的详细信息
        
        Args:
            platform: 用户平台
            user_id: 用户ID
            tool_name: 工具名称
            
        Returns:
            工具信息（包含描述、参数schema等），如果工具不存在则返回None
            
        验证需求：
        - 需求 7.5: 用户查询工具详情时返回工具的描述、参数schema和端点信息
        - 需求 19.1-19.5: 返回工具的完整信息
        """
        user_key = self._get_user_key(platform, user_id)
        
        if user_key not in self._registry:
            logger.debug(f"User {user_key} has no registered tools")
            return None
        
        tool = self._registry[user_key].get(tool_name)
        if tool is None:
            logger.debug(f"Tool '{tool_name}' not found for user {user_key}")
            return None
        
        return tool.to_dict()
