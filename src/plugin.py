"""
TokenManagementPlugin - AstrBot插件主类

该模块实现AstrBot插件的主类，继承自Star基类。
负责初始化所有组件并提供插件生命周期管理。

职责：
- 初始化所有核心组件（DatabaseManager、TokenEncryption、TokenManager等）
- 管理插件生命周期（启动、关闭）
- 提供组件访问接口供指令处理器使用

验证需求：需求 13（指令接口）
"""

import logging
from pathlib import Path
from astrbot.api.star import Context, Star
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption
from src.token_management.token_manager import TokenManager
from src.mcp_config import MCPServiceConfig
from src.mcp_service.mcp_service_caller import MCPServiceCaller
from src.tool_registry.mcp_tool_registry import MCPToolRegistry
from src.utils.logging_config import configure_default_logging


logger = logging.getLogger(__name__)


class TokenManagementPlugin(Star):
    """Token管理插件主类
    
    继承AstrBot的Star基类，实现用户token管理和MCP工具注册功能。
    初始化所有核心组件，并提供插件生命周期管理。
    
    Attributes:
        context: AstrBot上下文对象
        db_manager: 数据库管理器实例
        encryption: Token加密器实例
        token_manager: Token管理器实例
        mcp_config: MCP服务配置实例
        mcp_caller: MCP服务调用器实例
        tool_registry: MCP工具注册表实例
    """
    
    def __init__(self, context: Context):
        """初始化插件
        
        创建并初始化所有核心组件：
        - DatabaseManager: 数据库管理
        - TokenEncryption: Token加密
        - TokenManager: Token管理协调
        - MCPServiceConfig: MCP服务配置
        - MCPServiceCaller: MCP服务调用
        - MCPToolRegistry: MCP工具注册表
        
        Args:
            context: AstrBot上下文对象
        """
        super().__init__(context)
        
        # 获取数据目录路径
        # 使用AstrBot的数据目录，如果不存在则使用默认路径
        data_dir = Path("/AstrBot/data")
        if not data_dir.exists():
            # 如果默认路径不存在，使用当前目录下的data文件夹
            data_dir = Path("./data")
        
        # 确保数据目录存在
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志系统（在初始化其他组件之前）
        configure_default_logging(data_dir)
        
        logger.info("Initializing TokenManagementPlugin...")
        logger.info(f"Data directory: {data_dir}")
        
        # 初始化数据库管理器
        db_path = str(data_dir / "user_tokens.db")
        self.db_manager = DatabaseManager(db_path)
        logger.info(f"DatabaseManager initialized with path: {db_path}")
        
        # 初始化Token加密器
        key_file_path = str(data_dir / "encryption.key")
        self.encryption = TokenEncryption(key_file_path=key_file_path)
        logger.info(f"TokenEncryption initialized with key file: {key_file_path}")
        
        # 初始化Token管理器
        self.token_manager = TokenManager(self.db_manager, self.encryption)
        logger.info("TokenManager initialized")
        
        # 初始化MCP服务配置
        self.mcp_config = MCPServiceConfig()
        logger.info("MCPServiceConfig initialized")
        logger.debug(f"MCP Config: {self.mcp_config.get_config_summary()}")
        
        # 初始化MCP服务调用器
        self.mcp_caller = MCPServiceCaller(self.token_manager, self.mcp_config)
        logger.info("MCPServiceCaller initialized")
        
        # 初始化MCP工具注册表
        self.tool_registry = MCPToolRegistry(self.token_manager, self.mcp_config)
        logger.info("MCPToolRegistry initialized")
        
        logger.info("TokenManagementPlugin initialization complete")
    
    async def on_load(self):
        """插件加载时的回调
        
        在插件加载时执行初始化操作，主要是初始化数据库表结构。
        这个方法会在插件启动时由AstrBot框架自动调用。
        """
        try:
            logger.info("TokenManagementPlugin loading...")
            
            # 初始化数据库表结构
            await self.db_manager.initialize()
            logger.info("Database initialized successfully")
            
            logger.info("TokenManagementPlugin loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load TokenManagementPlugin: {e}")
            raise
    
    async def on_unload(self):
        """插件卸载时的回调
        
        在插件卸载时执行清理操作，主要是关闭数据库连接。
        这个方法会在插件关闭时由AstrBot框架自动调用。
        """
        try:
            logger.info("TokenManagementPlugin unloading...")
            
            # 关闭数据库连接
            await self.db_manager.close()
            logger.info("Database connection closed")
            
            logger.info("TokenManagementPlugin unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error during TokenManagementPlugin unload: {e}")
            # 不抛出异常，避免影响其他插件的卸载

    @filter.command("bind_token")
    async def bind_token_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """绑定token指令处理器

        处理用户的token绑定请求，执行以下操作：
        1. 解析指令参数，提取token
        2. 验证参数格式（token非空）
        3. 调用TokenManager.bind_token绑定token
        4. 调用MCPToolRegistry.register_user_tools自动注册工具
        5. 返回成功消息和已注册工具列表

        指令格式: /bind_token <token>

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含操作结果的消息

        验证需求：
        - 需求 1（Token绑定管理）
        - 需求 6（MCP工具自动发现）
        - 需求 7（MCP工具注册）
        """
        try:
            # 解析指令参数
            message_parts = event.message_str.split(maxsplit=1)

            # 验证参数格式
            if len(message_parts) < 2:
                logger.debug(f"bind_token command called without token parameter")
                yield event.plain_result(
                    "❌ 用法错误\n\n"
                    "正确用法: /bind_token <your_token>\n\n"
                    "示例: /bind_token sk-abc123xyz456"
                )
                return

            token = message_parts[1].strip()

            # 验证token非空
            if not token:
                logger.debug("bind_token command called with empty token")
                yield event.plain_result(
                    "❌ Token不能为空\n\n"
                    "请提供有效的token"
                )
                return

            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} attempting to bind token")
            logger.debug(f"Token prefix: {token[:4]}...")

            # 绑定token
            success = await self.token_manager.bind_token(platform, user_id, token)

            if not success:
                logger.error(f"Failed to bind token for user {platform}:{user_id}")
                yield event.plain_result(
                    "❌ Token绑定失败\n\n"
                    "请稍后重试或联系管理员"
                )
                return

            logger.info(f"Token bound successfully for user {platform}:{user_id}")

            # 自动注册MCP工具
            logger.info(f"Attempting to register MCP tools for user {platform}:{user_id}")
            tools_registered = await self.tool_registry.register_user_tools(platform, user_id)

            if tools_registered:
                # 获取已注册工具列表
                tool_names = await self.tool_registry.list_user_tools(platform, user_id)
                logger.info(f"Registered {len(tool_names)} tools for user {platform}:{user_id}")

                # 格式化工具列表
                tools_list = "\n".join([f"  • {name}" for name in tool_names])

                yield event.plain_result(
                    f"✅ Token绑定成功！\n\n"
                    f"🔧 已自动注册 {len(tool_names)} 个MCP工具：\n{tools_list}\n\n"
                    f"💡 提示：\n"
                    f"  • 使用 /list_tools 查看工具列表\n"
                    f"  • 使用 /tool_info <工具名> 查看工具详情"
                )
            else:
                logger.warning(f"Token bound but no tools discovered for user {platform}:{user_id}")
                yield event.plain_result(
                    "✅ Token绑定成功！\n\n"
                    "⚠️ 未发现可用的MCP工具\n\n"
                    "可能的原因：\n"
                    "  • Token无效或已过期\n"
                    "  • MCP服务暂时不可用\n"
                    "  • 您的账户没有可用工具\n\n"
                    "💡 您可以稍后使用 /list_tools 重试"
                )

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in bind_token_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )
    @filter.command("unbind_token")
    async def unbind_token_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """解绑token指令处理器

        处理用户的token解绑请求，执行以下操作：
        1. 获取用户信息（platform和user_id）
        2. 检查用户是否已绑定token
        3. 调用MCPToolRegistry.unregister_user_tools取消注册所有MCP工具
        4. 调用TokenManager.unbind_token删除token
        5. 返回成功消息确认工具已取消注册

        指令格式: /unbind_token

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含操作结果的消息

        验证需求：
        - 需求 4（Token解绑）
        - 需求 10（工具生命周期管理）
        """
        try:
            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} attempting to unbind token")

            # 检查用户是否已绑定token
            has_token = await self.token_manager.has_token(platform, user_id)

            if not has_token:
                logger.debug(f"User {platform}:{user_id} has no token to unbind")
                yield event.plain_result(
                    "❌ 您还没有绑定token\n\n"
                    "💡 提示：\n"
                    "  • 使用 /bind_token <token> 绑定token\n"
                    "  • 使用 /check_token 查看token状态"
                )
                return

            # 先取消注册所有MCP工具
            logger.info(f"Unregistering MCP tools for user {platform}:{user_id}")
            await self.tool_registry.unregister_user_tools(platform, user_id)
            logger.info(f"Tools unregistered successfully for user {platform}:{user_id}")

            # 删除token
            logger.info(f"Deleting token for user {platform}:{user_id}")
            success = await self.token_manager.unbind_token(platform, user_id)

            if success:
                logger.info(f"Token unbound successfully for user {platform}:{user_id}")
                yield event.plain_result(
                    "✅ Token已解绑\n\n"
                    "🔧 所有MCP工具已取消注册\n\n"
                    "💡 提示：\n"
                    "  • 如需继续使用，请使用 /bind_token <token> 重新绑定"
                )
            else:
                logger.error(f"Failed to unbind token for user {platform}:{user_id}")
                yield event.plain_result(
                    "❌ Token解绑失败\n\n"
                    "请稍后重试或联系管理员"
                )

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in unbind_token_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )

    @filter.command("check_token")
    async def check_token_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """检查token状态指令处理器

        处理用户的token状态查询请求，执行以下操作：
        1. 获取用户信息（platform和user_id）
        2. 调用TokenManager.has_token检查token状态
        3. 如果已绑定，获取token并返回部分信息（前4位和后4位）
        4. 如果未绑定，提示用户使用bind_token指令

        指令格式: /check_token

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含token状态信息的消息

        验证需求：
        - 需求 2（Token查询）
        """
        try:
            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} checking token status")

            # 检查用户是否已绑定token
            has_token = await self.token_manager.has_token(platform, user_id)

            if not has_token:
                logger.debug(f"User {platform}:{user_id} has no token bound")
                yield event.plain_result(
                    "❌ 您还没有绑定token\n\n"
                    "💡 提示：\n"
                    "  • 使用 /bind_token <token> 绑定您的token\n"
                    "  • 绑定后即可使用MCP工具"
                )
                return

            # 获取用户token（解密后）
            token = await self.token_manager.get_user_token(platform, user_id)

            if token is None:
                # 理论上不应该发生（has_token返回True但get_user_token返回None）
                logger.error(f"Token exists but cannot be retrieved for user {platform}:{user_id}")
                yield event.plain_result(
                    "❌ Token状态异常\n\n"
                    "建议使用 /update_token <new_token> 重新绑定"
                )
                return

            # 返回token的部分信息（前4位和后4位）
            # 确保token长度足够
            if len(token) <= 8:
                # 如果token太短，只显示前4位
                token_display = f"{token[:4]}..."
            else:
                # 显示前4位和后4位
                token_display = f"{token[:4]}...{token[-4:]}"

            logger.info(f"Token status checked for user {platform}:{user_id}, display: {token_display}")

            # 获取已注册工具数量
            tool_names = await self.tool_registry.list_user_tools(platform, user_id)
            tools_count = len(tool_names)

            yield event.plain_result(
                f"✅ Token已绑定\n\n"
                f"🔑 Token信息: {token_display}\n"
                f"🔧 已注册工具: {tools_count} 个\n\n"
                f"💡 提示：\n"
                f"  • 使用 /list_tools 查看工具列表\n"
                f"  • 使用 /update_token <new_token> 更新token\n"
                f"  • 使用 /unbind_token 解绑token"
            )

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in check_token_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )


    @filter.command("update_token")
    async def update_token_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """更新token指令处理器

        处理用户的token更新请求，执行以下操作：
        1. 解析指令参数，提取新token
        2. 验证参数格式（token非空）
        3. 检查用户是否已绑定token
        4. 调用MCPToolRegistry.unregister_user_tools取消注册旧工具
        5. 调用TokenManager.update_token更新token
        6. 调用MCPToolRegistry.register_user_tools重新注册工具
        7. 返回成功消息和重新注册的工具列表

        指令格式: /update_token <new_token>

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含操作结果的消息

        验证需求：
        - 需求 3（Token更新）
        - 需求 10（工具生命周期管理）
        """
        try:
            # 解析指令参数
            message_parts = event.message_str.split(maxsplit=1)

            # 验证参数格式
            if len(message_parts) < 2:
                logger.debug("update_token command called without token parameter")
                yield event.plain_result(
                    "❌ 用法错误\n\n"
                    "正确用法: /update_token <new_token>\n\n"
                    "示例: /update_token sk-new123xyz456"
                )
                return

            new_token = message_parts[1].strip()

            # 验证token非空
            if not new_token:
                logger.debug("update_token command called with empty token")
                yield event.plain_result(
                    "❌ Token不能为空\n\n"
                    "请提供有效的token"
                )
                return

            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} attempting to update token")
            logger.debug(f"New token prefix: {new_token[:4]}...")

            # 检查用户是否已绑定token
            has_token = await self.token_manager.has_token(platform, user_id)

            if not has_token:
                logger.debug(f"User {platform}:{user_id} has no token to update")
                yield event.plain_result(
                    "❌ 您还没有绑定token\n\n"
                    "💡 提示：\n"
                    "  • 使用 /bind_token <token> 先绑定token\n"
                    "  • 使用 /check_token 查看token状态"
                )
                return

            # 先取消注册旧工具
            logger.info(f"Unregistering old tools for user {platform}:{user_id}")
            await self.tool_registry.unregister_user_tools(platform, user_id)
            logger.info(f"Old tools unregistered successfully for user {platform}:{user_id}")

            # 更新token
            logger.info(f"Updating token for user {platform}:{user_id}")
            success = await self.token_manager.update_token(platform, user_id, new_token)

            if not success:
                logger.error(f"Failed to update token for user {platform}:{user_id}")
                yield event.plain_result(
                    "❌ Token更新失败\n\n"
                    "请稍后重试或联系管理员"
                )
                return

            logger.info(f"Token updated successfully for user {platform}:{user_id}")

            # 重新注册工具
            logger.info(f"Attempting to register MCP tools with new token for user {platform}:{user_id}")
            tools_registered = await self.tool_registry.register_user_tools(platform, user_id)

            if tools_registered:
                # 获取已注册工具列表
                tool_names = await self.tool_registry.list_user_tools(platform, user_id)
                logger.info(f"Re-registered {len(tool_names)} tools for user {platform}:{user_id}")

                # 格式化工具列表
                tools_list = "\n".join([f"  • {name}" for name in tool_names])

                yield event.plain_result(
                    f"✅ Token更新成功！\n\n"
                    f"🔧 已重新注册 {len(tool_names)} 个MCP工具：\n{tools_list}\n\n"
                    f"💡 提示：\n"
                    f"  • 使用 /list_tools 查看工具列表\n"
                    f"  • 使用 /tool_info <工具名> 查看工具详情"
                )
            else:
                logger.warning(f"Token updated but no tools discovered for user {platform}:{user_id}")
                yield event.plain_result(
                    "✅ Token更新成功！\n\n"
                    "⚠️ 未发现可用的MCP工具\n\n"
                    "可能的原因：\n"
                    "  • 新Token无效或已过期\n"
                    "  • MCP服务暂时不可用\n"
                    "  • 您的账户没有可用工具\n\n"
                    "💡 您可以稍后使用 /list_tools 重试"
                )

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in update_token_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )

    @filter.command("list_tools")
    async def list_tools_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """列出MCP工具指令处理器

        处理用户的工具列表查询请求，执行以下操作：
        1. 获取用户信息（platform和user_id）
        2. 调用MCPToolRegistry.list_user_tools获取工具列表
        3. 格式化工具列表，包含工具名称和描述
        4. 如果用户未绑定token或无工具，返回友好提示

        指令格式: /list_tools

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含工具列表信息的消息

        验证需求：
        - 需求 7（MCP工具注册）
        - 需求 19（工具信息查询）
        """
        try:
            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} requesting tool list")

            # 检查用户是否已绑定token
            has_token = await self.token_manager.has_token(platform, user_id)

            if not has_token:
                logger.debug(f"User {platform}:{user_id} has no token bound")
                yield event.plain_result(
                    "❌ 您还没有绑定token\n\n"
                    "💡 提示：\n"
                    "  • 使用 /bind_token <token> 绑定您的token\n"
                    "  • 绑定后即可自动注册MCP工具"
                )
                return

            # 获取用户工具列表
            tool_names = await self.tool_registry.list_user_tools(platform, user_id)

            if not tool_names:
                logger.debug(f"User {platform}:{user_id} has no tools registered")
                yield event.plain_result(
                    "❌ 您还没有可用的MCP工具\n\n"
                    "可能的原因：\n"
                    "  • Token无效或已过期\n"
                    "  • MCP服务暂时不可用\n"
                    "  • 您的账户没有可用工具\n\n"
                    "💡 提示：\n"
                    "  • 使用 /update_token <new_token> 更新token\n"
                    "  • 使用 /check_token 查看token状态"
                )
                return

            logger.info(f"User {platform}:{user_id} has {len(tool_names)} tools registered")

            # 格式化工具列表，包含工具名称和描述
            tools_info = []
            for tool_name in tool_names:
                tool = self.tool_registry.get_tool_info(platform, user_id, tool_name)
                if tool:
                    description = tool.get('description', '无描述')
                    tools_info.append(f"🔧 {tool_name}\n   {description}")
                else:
                    # 如果无法获取工具详细信息，只显示名称
                    tools_info.append(f"🔧 {tool_name}")

            # 构建响应消息
            result = f"📋 您的MCP工具列表（共 {len(tool_names)} 个）：\n\n"
            result += "\n\n".join(tools_info)
            result += "\n\n💡 提示：\n"
            result += "  • 使用 /tool_info <工具名> 查看详细信息"

            yield event.plain_result(result)

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in list_tools_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )

    @filter.command("tool_info")
    async def tool_info_command(self, event: AstrMessageEvent) -> MessageEventResult:
        """查看工具详细信息指令处理器

        处理用户的工具详细信息查询请求，执行以下操作：
        1. 解析指令参数，提取工具名称
        2. 验证参数格式（工具名称非空）
        3. 调用MCPToolRegistry.get_tool_info获取工具详细信息
        4. 格式化工具信息：名称、描述、参数schema、端点、HTTP方法
        5. 标识必需参数和可选参数
        6. 处理错误情况：参数缺失、工具不存在

        指令格式: /tool_info <tool_name>

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含工具详细信息的消息

        验证需求：
        - 需求 19（工具信息查询）
        """
        try:
            # 解析指令参数
            message_parts = event.message_str.split(maxsplit=1)

            # 验证参数格式
            if len(message_parts) < 2:
                logger.debug("tool_info command called without tool_name parameter")
                yield event.plain_result(
                    "❌ 用法错误\n\n"
                    "正确用法: /tool_info <tool_name>\n\n"
                    "示例: /tool_info translate\n\n"
                    "💡 提示：\n"
                    "  • 使用 /list_tools 查看可用工具列表"
                )
                return

            tool_name = message_parts[1].strip()

            # 验证工具名称非空
            if not tool_name:
                logger.debug("tool_info command called with empty tool_name")
                yield event.plain_result(
                    "❌ 工具名称不能为空\n\n"
                    "请提供有效的工具名称"
                )
                return

            # 获取用户信息
            platform = event.get_platform_name()
            user_id = event.get_sender_id()

            logger.info(f"User {platform}:{user_id} requesting info for tool: {tool_name}")

            # 检查用户是否已绑定token
            has_token = await self.token_manager.has_token(platform, user_id)

            if not has_token:
                logger.debug(f"User {platform}:{user_id} has no token bound")
                yield event.plain_result(
                    "❌ 您还没有绑定token\n\n"
                    "💡 提示：\n"
                    "  • 使用 /bind_token <token> 绑定您的token\n"
                    "  • 绑定后即可查看工具信息"
                )
                return

            # 获取工具信息
            tool_info = self.tool_registry.get_tool_info(platform, user_id, tool_name)

            if not tool_info:
                logger.debug(f"Tool '{tool_name}' not found for user {platform}:{user_id}")
                yield event.plain_result(
                    f"❌ 工具 '{tool_name}' 不存在或未注册\n\n"
                    f"💡 提示：\n"
                    f"  • 使用 /list_tools 查看可用工具列表\n"
                    f"  • 确认工具名称拼写正确"
                )
                return

            logger.info(f"Tool info retrieved for '{tool_name}' for user {platform}:{user_id}")

            # 格式化工具信息
            result = f"🔧 工具信息: {tool_name}\n\n"
            result += f"📝 描述: {tool_info.get('description', '无描述')}\n\n"

            # 格式化参数信息
            params = tool_info.get("parameters", {})
            required = params.get("required", [])
            properties = params.get("properties", {})

            if properties:
                result += "📌 参数:\n"
                params_info = []
                for param_name, param_schema in properties.items():
                    is_required = "必需" if param_name in required else "可选"
                    param_type = param_schema.get("type", "any")
                    param_desc = param_schema.get("description", "无描述")
                    params_info.append(f"  • {param_name} ({param_type}, {is_required}): {param_desc}")
                result += "\n".join(params_info)
            else:
                result += "📌 参数: 无参数"

            # 添加端点和方法信息
            result += f"\n\n🌐 端点: {tool_info.get('endpoint', '未知')}"
            result += f"\n📡 方法: {tool_info.get('method', 'POST')}"

            yield event.plain_result(result)

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in tool_info_command: {e}", exc_info=True)
            yield event.plain_result(
                "❌ 发生未知错误\n\n"
                "请稍后重试或联系管理员"
            )

    @filter.message_type("GroupMessage", "FriendMessage")
    async def handle_dynamic_tool_call(self, event: AstrMessageEvent) -> MessageEventResult:
        """处理动态工具调用

        当用户发送的消息不是指令（不以/开头）时，检查是否匹配已注册的工具名称。
        如果匹配，则解析参数并调用对应的MCP工具。

        消息格式: tool_name param1=value1 param2=value2
        示例: translate text="Hello" target="zh"

        Args:
            event: AstrBot消息事件对象

        Yields:
            MessageEventResult: 包含工具执行结果的消息，如果不是工具调用则不返回任何内容

        验证需求：
        - 需求 8（MCP工具调用）
        - 需求 18（工具参数验证）
        """
        message = event.message_str.strip()

        # 如果消息为空或以/开头（是指令），则不处理
        if not message or message.startswith('/'):
            return

        # 获取用户信息
        platform = event.get_platform_name()
        user_id = event.get_sender_id()

        # 检查用户是否已绑定token
        has_token = await self.token_manager.has_token(platform, user_id)
        if not has_token:
            # 用户未绑定token，不处理（可能是普通消息）
            return

        # 解析消息：第一个词是潜在的工具名称
        parts = message.split(maxsplit=1)
        if len(parts) < 1:
            return

        potential_tool_name = parts[0]

        # 检查用户是否有此工具
        tool_names = await self.tool_registry.list_user_tools(platform, user_id)
        if potential_tool_name not in tool_names:
            # 不是工具调用，交给其他处理器
            return

        try:

            logger.info(f"User {platform}:{user_id} calling tool: {potential_tool_name}")

            # 解析参数（支持 key=value 格式）
            params = {}
            if len(parts) > 1:
                params = self._parse_tool_params(parts[1])
                logger.debug(f"Parsed parameters: {params}")

            # 调用工具
            result = await self.tool_registry.call_tool(
                platform, user_id, potential_tool_name, **params
            )

            # 格式化并返回结果
            if result.get("success"):
                logger.info(f"Tool '{potential_tool_name}' executed successfully for user {platform}:{user_id}")
                
                # 格式化工具执行结果
                tool_data = result.get("data", {})
                formatted_result = self._format_tool_result(tool_data)
                
                yield event.plain_result(
                    f"✅ 工具 '{potential_tool_name}' 执行成功\n\n"
                    f"📊 结果：\n{formatted_result}"
                )
            else:
                error_msg = result.get("error", "未知错误")
                logger.warning(f"Tool '{potential_tool_name}' execution failed for user {platform}:{user_id}: {error_msg}")
                
                yield event.plain_result(
                    f"❌ 工具执行失败\n\n"
                    f"错误信息: {error_msg}\n\n"
                    f"💡 提示：\n"
                    f"  • 使用 /tool_info {potential_tool_name} 查看参数要求\n"
                    f"  • 检查参数格式是否正确"
                )

        except Exception as e:
            # 处理未预期的错误
            logger.error(f"Unexpected error in handle_dynamic_tool_call: {e}", exc_info=True)
            # 不返回错误消息，因为可能不是工具调用

    def _parse_tool_params(self, params_str: str) -> dict:
        """解析工具参数字符串

        支持 key=value 格式的参数解析。
        示例: text="Hello World" target="zh" count=5

        Args:
            params_str: 参数字符串

        Returns:
            解析后的参数字典

        注意：
        - 支持带引号的字符串值（单引号或双引号）
        - 支持数字类型（整数和浮点数）
        - 支持布尔类型（true/false）
        """
        params = {}
        
        # 简单的参数解析逻辑
        # 使用正则表达式匹配 key=value 格式
        import re
        
        # 匹配 key="value" 或 key='value' 或 key=value
        pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
        matches = re.findall(pattern, params_str)
        
        for match in matches:
            key = match[0]
            # 获取值（可能在不同的捕获组中）
            value = match[1] or match[2] or match[3]
            
            # 尝试转换类型
            if value.lower() == 'true':
                params[key] = True
            elif value.lower() == 'false':
                params[key] = False
            elif value.isdigit():
                params[key] = int(value)
            else:
                try:
                    params[key] = float(value)
                except ValueError:
                    params[key] = value
        
        return params

    def _format_tool_result(self, data: dict) -> str:
        """格式化工具执行结果

        将工具返回的数据格式化为易读的字符串。

        Args:
            data: 工具返回的数据字典

        Returns:
            格式化后的结果字符串
        """
        if not data:
            return "无返回数据"
        
        # 如果数据是简单的字典，格式化为键值对
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    # 复杂类型，使用JSON格式
                    import json
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                    lines.append(f"{key}:\n{value_str}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            # 其他类型，直接转换为字符串
            return str(data)


