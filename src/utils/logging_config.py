"""
日志配置模块

该模块提供统一的日志配置，确保所有组件使用一致的日志格式和级别。

职责：
- 配置Python logging模块
- 设置日志格式（包含时间戳、日志级别、模块名、消息）
- 设置日志级别（支持环境变量覆盖）
- 配置日志输出（控制台和文件）
- 确保日志中不记录完整明文token

验证需求：需求 15（日志记录）
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


class LoggingConfig:
    """日志配置类
    
    提供统一的日志配置功能，支持控制台和文件输出。
    
    Attributes:
        DEFAULT_LEVEL: 默认日志级别
        DEFAULT_FORMAT: 默认日志格式
        DEFAULT_DATE_FORMAT: 默认日期格式
    """
    
    # 默认日志级别（可通过环境变量 LOG_LEVEL 覆盖）
    DEFAULT_LEVEL = logging.INFO
    
    # 日志格式：时间戳 - 日志级别 - 模块名 - 消息
    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    
    # 日期格式
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @classmethod
    def configure_logging(
        cls,
        log_level: Optional[str] = None,
        log_file: Optional[str] = None,
        console_output: bool = True
    ) -> None:
        """配置日志系统
        
        设置日志级别、格式和输出目标（控制台和/或文件）。
        
        Args:
            log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
                      如果为None，则从环境变量 LOG_LEVEL 读取，默认为INFO
            log_file: 日志文件路径，如果为None则不输出到文件
            console_output: 是否输出到控制台，默认为True
            
        验证需求：
        - 需求 15.4: 使用适当的日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
        """
        # 确定日志级别
        if log_level is None:
            # 从环境变量读取日志级别
            log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # 转换日志级别字符串为logging常量
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        numeric_level = level_map.get(log_level, cls.DEFAULT_LEVEL)
        
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 清除现有的处理器（避免重复配置）
        root_logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=cls.DEFAULT_FORMAT,
            datefmt=cls.DEFAULT_DATE_FORMAT
        )
        
        # 配置控制台输出
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # 配置文件输出
        if log_file:
            # 确保日志目录存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # 记录配置信息
        root_logger.info(f"Logging configured: level={log_level}, console={console_output}, file={log_file}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取日志记录器
        
        为指定模块创建日志记录器。
        
        Args:
            name: 模块名称（通常使用 __name__）
            
        Returns:
            日志记录器实例
        """
        return logging.getLogger(name)
    
    @classmethod
    def set_module_level(cls, module_name: str, level: str) -> None:
        """设置特定模块的日志级别
        
        允许为不同模块设置不同的日志级别。
        
        Args:
            module_name: 模块名称
            level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        numeric_level = level_map.get(level.upper(), logging.INFO)
        logger = logging.getLogger(module_name)
        logger.setLevel(numeric_level)
        
        logging.info(f"Set log level for module '{module_name}' to {level}")


def configure_default_logging(data_dir: Optional[Path] = None) -> None:
    """配置默认日志设置
    
    为用户Token管理系统配置默认的日志设置。
    这是一个便捷函数，用于快速配置日志系统。
    
    Args:
        data_dir: 数据目录路径，用于存储日志文件
                 如果为None，则不输出到文件
    
    验证需求：
    - 需求 15.1: 记录所有token绑定、更新、解绑操作
    - 需求 15.2: 记录所有MCP服务调用的结果
    - 需求 15.3: 记录工具注册和取消注册操作
    - 需求 15.4: 使用适当的日志级别
    """
    # 确定日志文件路径
    log_file = None
    if data_dir:
        log_file = str(data_dir / "token_management.log")
    
    # 配置日志系统
    LoggingConfig.configure_logging(
        log_level=None,  # 从环境变量读取或使用默认值
        log_file=log_file,
        console_output=True
    )
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("用户Token管理系统启动")
    logger.info("=" * 60)
    
    # 可选：为特定模块设置不同的日志级别
    # 例如：降低aiohttp的日志级别以减少噪音
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


# 便捷函数：获取日志记录器
def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数
    
    Args:
        name: 模块名称（通常使用 __name__）
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)
