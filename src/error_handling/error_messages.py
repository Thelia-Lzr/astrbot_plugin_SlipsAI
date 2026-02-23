"""
错误处理和消息模块

该模块提供统一的错误处理机制和友好的错误消息。
确保错误消息不暴露系统内部实现细节，同时为用户提供清晰的错误提示。

验证需求：需求 12（错误处理）
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举
    
    定义系统中可能出现的10种错误场景。
    """
    # 错误场景 1: 用户未绑定token
    USER_NO_TOKEN = "user_no_token"
    
    # 错误场景 2: Token解密失败
    TOKEN_DECRYPTION_FAILED = "token_decryption_failed"
    
    # 错误场景 3: MCP服务调用失败
    MCP_SERVICE_FAILED = "mcp_service_failed"
    
    # 错误场景 4: 数据库连接失败
    DATABASE_ERROR = "database_error"
    
    # 错误场景 5: 无效的指令参数
    INVALID_COMMAND_PARAMS = "invalid_command_params"
    
    # 错误场景 6: 工具发现失败
    TOOL_DISCOVERY_FAILED = "tool_discovery_failed"
    
    # 错误场景 7: 工具不存在
    TOOL_NOT_FOUND = "tool_not_found"
    
    # 错误场景 8: 工具参数验证失败
    TOOL_PARAM_VALIDATION_FAILED = "tool_param_validation_failed"
    
    # 错误场景 9: 工具调用超时
    TOOL_CALL_TIMEOUT = "tool_call_timeout"
    
    # 错误场景 10: 工具调用时token失效
    TOKEN_INVALID_DURING_CALL = "token_invalid_during_call"


class ErrorMessages:
    """错误消息类
    
    提供友好的、不暴露内部细节的错误消息。
    所有错误消息都经过精心设计，确保用户友好且安全。
    
    验证需求：
    - 需求 12.5: 数据库操作失败时返回通用错误消息不暴露内部细节
    - 需求 12.7: 不在用户错误消息中暴露系统内部实现细节
    """
    
    # 错误场景 1: 用户未绑定token
    USER_NO_TOKEN = {
        "message": "用户未绑定token，请先使用 /bind_token 绑定",
        "suggestions": [
            "使用 /bind_token <token> 绑定您的token",
            "绑定后即可使用MCP服务"
        ]
    }
    
    # 错误场景 2: Token解密失败
    TOKEN_DECRYPTION_FAILED = {
        "message": "Token解密失败，请重新绑定token",
        "suggestions": [
            "使用 /update_token <new_token> 重新绑定",
            "如果问题持续，请联系管理员"
        ]
    }
    
    # 错误场景 3: MCP服务调用失败
    MCP_SERVICE_FAILED = {
        "message": "服务调用失败",
        "suggestions": [
            "请稍后重试",
            "如果问题持续，请检查网络连接"
        ]
    }
    
    # 错误场景 3.1: MCP服务返回401错误
    TOKEN_INVALID = {
        "message": "Token无效或已过期，请更新token",
        "suggestions": [
            "使用 /update_token <new_token> 更新token",
            "确认您的token仍然有效"
        ]
    }
    
    # 错误场景 3.2: MCP服务调用超时
    SERVICE_TIMEOUT = {
        "message": "服务调用超时，请稍后重试",
        "suggestions": [
            "稍后再试",
            "检查网络连接是否正常"
        ]
    }
    
    # 错误场景 4: 数据库连接失败
    DATABASE_ERROR = {
        "message": "数据库操作失败，请稍后重试",
        "suggestions": [
            "稍后再试",
            "如果问题持续，请联系管理员"
        ]
    }
    
    # 错误场景 5: 无效的指令参数
    INVALID_COMMAND_PARAMS = {
        "message": "指令参数错误",
        "suggestions": [
            "请检查指令格式",
            "使用正确的参数格式"
        ]
    }
    
    # 错误场景 6: 工具发现失败
    TOOL_DISCOVERY_FAILED = {
        "message": "Token绑定成功，但未发现可用工具",
        "suggestions": [
            "Token可能无效或已过期",
            "MCP服务可能暂时不可用",
            "您的账户可能没有可用工具",
            "稍后使用 /list_tools 重试"
        ]
    }
    
    # 错误场景 7: 工具不存在
    TOOL_NOT_FOUND = {
        "message": "工具不存在或未注册",
        "suggestions": [
            "使用 /list_tools 查看可用工具列表",
            "确认工具名称拼写正确"
        ]
    }
    
    # 错误场景 8: 工具参数验证失败
    TOOL_PARAM_VALIDATION_FAILED = {
        "message": "参数验证失败，请检查必需参数",
        "suggestions": [
            "使用 /tool_info <tool_name> 查看参数要求",
            "确认所有必需参数都已提供",
            "检查参数类型是否正确"
        ]
    }
    
    # 错误场景 9: 工具调用超时
    TOOL_CALL_TIMEOUT = {
        "message": "工具调用超时，请稍后重试",
        "suggestions": [
            "稍后再试",
            "如果持续超时，请检查网络连接或联系管理员"
        ]
    }
    
    # 错误场景 10: 工具调用时token失效
    TOKEN_INVALID_DURING_CALL = {
        "message": "Token无效或已过期",
        "suggestions": [
            "使用 /update_token <new_token> 更新token",
            "更新token后工具将自动可用"
        ]
    }
    
    # 通用错误
    UNKNOWN_ERROR = {
        "message": "发生未知错误",
        "suggestions": [
            "请稍后重试",
            "如果问题持续，请联系管理员"
        ]
    }
    
    @classmethod
    def get_error_message(
        cls, 
        error_type: ErrorType, 
        details: Optional[str] = None,
        include_suggestions: bool = True
    ) -> str:
        """获取格式化的错误消息
        
        根据错误类型返回友好的错误消息，可选包含建议。
        
        Args:
            error_type: 错误类型枚举
            details: 可选的额外详细信息（不会暴露内部细节）
            include_suggestions: 是否包含建议
            
        Returns:
            格式化的错误消息字符串
        """
        # 获取错误消息配置
        error_config = cls._get_error_config(error_type)
        
        # 构建消息
        message = f"❌ {error_config['message']}"
        
        # 添加详细信息（如果提供）
        if details:
            message += f"\n\n{details}"
        
        # 添加建议（如果需要）
        if include_suggestions and error_config.get('suggestions'):
            message += "\n\n💡 提示："
            for suggestion in error_config['suggestions']:
                message += f"\n  • {suggestion}"
        
        return message
    
    @classmethod
    def _get_error_config(cls, error_type: ErrorType) -> Dict[str, Any]:
        """获取错误配置
        
        Args:
            error_type: 错误类型枚举
            
        Returns:
            错误配置字典
        """
        error_map = {
            ErrorType.USER_NO_TOKEN: cls.USER_NO_TOKEN,
            ErrorType.TOKEN_DECRYPTION_FAILED: cls.TOKEN_DECRYPTION_FAILED,
            ErrorType.MCP_SERVICE_FAILED: cls.MCP_SERVICE_FAILED,
            ErrorType.DATABASE_ERROR: cls.DATABASE_ERROR,
            ErrorType.INVALID_COMMAND_PARAMS: cls.INVALID_COMMAND_PARAMS,
            ErrorType.TOOL_DISCOVERY_FAILED: cls.TOOL_DISCOVERY_FAILED,
            ErrorType.TOOL_NOT_FOUND: cls.TOOL_NOT_FOUND,
            ErrorType.TOOL_PARAM_VALIDATION_FAILED: cls.TOOL_PARAM_VALIDATION_FAILED,
            ErrorType.TOOL_CALL_TIMEOUT: cls.TOOL_CALL_TIMEOUT,
            ErrorType.TOKEN_INVALID_DURING_CALL: cls.TOKEN_INVALID_DURING_CALL,
        }
        
        return error_map.get(error_type, cls.UNKNOWN_ERROR)
    
    @classmethod
    def format_service_error(cls, status_code: int, error_text: Optional[str] = None) -> str:
        """格式化MCP服务错误消息
        
        根据HTTP状态码返回友好的错误消息，不暴露内部细节。
        
        Args:
            status_code: HTTP状态码
            error_text: 可选的错误文本（仅用于日志，不返回给用户）
            
        Returns:
            格式化的错误消息
        """
        # 记录详细错误到日志（包含内部细节）
        if error_text:
            logger.error(f"MCP service error {status_code}: {error_text}")
        
        # 根据状态码返回友好消息（不暴露内部细节）
        if status_code == 401:
            return cls.get_error_message(ErrorType.TOKEN_INVALID_DURING_CALL)
        elif status_code == 404:
            return cls.get_error_message(
                ErrorType.MCP_SERVICE_FAILED,
                details="请求的服务不存在"
            )
        elif status_code >= 500:
            return cls.get_error_message(
                ErrorType.MCP_SERVICE_FAILED,
                details="服务器暂时不可用"
            )
        else:
            return cls.get_error_message(
                ErrorType.MCP_SERVICE_FAILED,
                details=f"HTTP {status_code}"
            )


class ErrorHandler:
    """错误处理器类
    
    提供统一的异常处理和日志记录功能。
    确保所有异常都被正确捕获、记录和处理。
    """
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: str,
        user_id: Optional[str] = None,
        log_level: str = "error"
    ) -> str:
        """处理异常并返回友好的错误消息
        
        捕获异常，记录详细日志（包含内部细节），
        返回友好的错误消息（不暴露内部细节）。
        
        Args:
            exception: 捕获的异常对象
            context: 异常发生的上下文（如：bind_token, call_tool等）
            user_id: 可选的用户标识（用于日志）
            log_level: 日志级别（error, warning, critical）
            
        Returns:
            友好的错误消息字符串
        """
        # 构建日志消息（包含内部细节）
        log_message = f"Exception in {context}"
        if user_id:
            log_message += f" for user {user_id}"
        log_message += f": {str(exception)}"
        
        # 记录日志
        if log_level == "critical":
            logger.critical(log_message, exc_info=True)
        elif log_level == "warning":
            logger.warning(log_message, exc_info=True)
        else:
            logger.error(log_message, exc_info=True)
        
        # 返回友好的错误消息（不暴露内部细节）
        return ErrorMessages.get_error_message(ErrorType.DATABASE_ERROR)
    
    @staticmethod
    def sanitize_token_for_log(token: str) -> str:
        """清理token用于日志记录
        
        只保留token的前4位和后4位，中间用...替代。
        确保日志中不记录完整的明文token。
        
        Args:
            token: 原始token字符串
            
        Returns:
            清理后的token字符串（如：sk-ab...xy）
            
        验证需求：
        - 需求 5.4: 不在日志中记录完整的明文token
        - 需求 15.6: 记录token信息时仅记录token的前4位和后4位
        """
        if not token:
            return "empty"
        
        if len(token) <= 8:
            # 如果token太短，只显示前4位
            return f"{token[:4]}..."
        else:
            # 显示前4位和后4位
            return f"{token[:4]}...{token[-4:]}"
    
    @staticmethod
    def is_retriable_error(exception: Exception) -> bool:
        """判断错误是否可重试
        
        某些错误（如网络超时、临时服务不可用）可以重试，
        而其他错误（如token无效、参数错误）不应重试。
        
        Args:
            exception: 异常对象
            
        Returns:
            如果错误可重试返回True，否则返回False
        """
        import asyncio
        import aiohttp
        
        # 可重试的错误类型
        retriable_exceptions = (
            asyncio.TimeoutError,
            aiohttp.ClientConnectionError,
            aiohttp.ServerTimeoutError,
        )
        
        return isinstance(exception, retriable_exceptions)
