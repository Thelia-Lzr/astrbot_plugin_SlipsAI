"""
日志配置模块测试

测试日志配置功能，确保日志系统正确配置和工作。

验证需求：需求 15（日志记录）
"""

import logging
import pytest
from pathlib import Path
import tempfile
import os
from src.utils.logging_config import LoggingConfig, configure_default_logging, get_logger


class TestLoggingConfig:
    """测试LoggingConfig类"""
    
    def test_configure_logging_default(self):
        """测试默认日志配置"""
        # 配置日志系统
        LoggingConfig.configure_logging()
        
        # 验证根日志记录器已配置
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0
    
    def test_configure_logging_with_level(self):
        """测试指定日志级别"""
        # 配置为DEBUG级别
        LoggingConfig.configure_logging(log_level="DEBUG")
        
        # 验证日志级别
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_configure_logging_with_file(self):
        """测试日志文件输出"""
        # 创建临时日志文件
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置日志系统
            LoggingConfig.configure_logging(log_file=str(log_file))
            
            # 写入日志
            test_logger = logging.getLogger("test")
            test_logger.info("Test message")
            
            # 验证日志文件已创建
            assert log_file.exists()
            
            # 验证日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test message" in content
    
    def test_configure_logging_console_only(self):
        """测试仅控制台输出"""
        # 配置为仅控制台输出
        LoggingConfig.configure_logging(console_output=True)
        
        # 验证有控制台处理器
        root_logger = logging.getLogger()
        has_console_handler = any(
            isinstance(h, logging.StreamHandler) 
            for h in root_logger.handlers
        )
        assert has_console_handler
    
    def test_configure_logging_from_env(self):
        """测试从环境变量读取日志级别"""
        # 设置环境变量
        os.environ["LOG_LEVEL"] = "WARNING"
        
        try:
            # 配置日志系统（不指定log_level，应从环境变量读取）
            LoggingConfig.configure_logging()
            
            # 验证日志级别
            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING
        finally:
            # 清理环境变量
            del os.environ["LOG_LEVEL"]
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        # 获取日志记录器
        logger = LoggingConfig.get_logger("test_module")
        
        # 验证返回的是Logger实例
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_set_module_level(self):
        """测试设置模块日志级别"""
        # 配置日志系统
        LoggingConfig.configure_logging(log_level="INFO")
        
        # 设置特定模块的日志级别
        LoggingConfig.set_module_level("test_module", "DEBUG")
        
        # 验证模块日志级别
        logger = logging.getLogger("test_module")
        assert logger.level == logging.DEBUG
    
    def test_log_format(self):
        """测试日志格式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置日志系统
            LoggingConfig.configure_logging(log_file=str(log_file))
            
            # 写入日志
            test_logger = logging.getLogger("test")
            test_logger.info("Test message")
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证日志格式包含必要元素
                assert "INFO" in content  # 日志级别
                assert "test" in content  # 模块名
                assert "Test message" in content  # 消息
                # 日期格式验证（YYYY-MM-DD HH:MM:SS）
                import re
                date_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                assert re.search(date_pattern, content)


class TestConfigureDefaultLogging:
    """测试configure_default_logging函数"""
    
    def test_configure_default_logging_with_data_dir(self):
        """测试使用数据目录配置日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            
            # 配置默认日志
            configure_default_logging(data_dir)
            
            # 验证日志文件已创建
            log_file = data_dir / "token_management.log"
            
            # 写入一些日志
            test_logger = logging.getLogger("test")
            test_logger.info("Test message")
            
            # 验证日志文件存在
            assert log_file.exists()
    
    def test_configure_default_logging_without_data_dir(self):
        """测试不使用数据目录配置日志（仅控制台）"""
        # 配置默认日志（不指定数据目录）
        configure_default_logging(None)
        
        # 验证根日志记录器已配置
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0
    
    def test_configure_default_logging_startup_message(self):
        """测试启动消息记录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            log_file = data_dir / "token_management.log"
            
            # 配置默认日志
            configure_default_logging(data_dir)
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证启动消息
                assert "用户Token管理系统启动" in content
    
    def test_configure_default_logging_third_party_levels(self):
        """测试第三方库日志级别设置"""
        # 配置默认日志
        configure_default_logging(None)
        
        # 验证aiohttp和aiosqlite的日志级别被设置为WARNING
        aiohttp_logger = logging.getLogger("aiohttp")
        aiosqlite_logger = logging.getLogger("aiosqlite")
        
        assert aiohttp_logger.level == logging.WARNING
        assert aiosqlite_logger.level == logging.WARNING


class TestGetLogger:
    """测试get_logger便捷函数"""
    
    def test_get_logger_function(self):
        """测试get_logger函数"""
        # 获取日志记录器
        logger = get_logger("test_module")
        
        # 验证返回的是Logger实例
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"


class TestLoggingIntegration:
    """测试日志系统集成"""
    
    def test_multiple_loggers(self):
        """测试多个日志记录器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置日志系统
            LoggingConfig.configure_logging(log_file=str(log_file))
            
            # 创建多个日志记录器
            logger1 = get_logger("module1")
            logger2 = get_logger("module2")
            
            # 写入日志
            logger1.info("Message from module1")
            logger2.info("Message from module2")
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证两个模块的日志都被记录
                assert "module1" in content
                assert "Message from module1" in content
                assert "module2" in content
                assert "Message from module2" in content
    
    def test_different_log_levels(self):
        """测试不同日志级别"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置为INFO级别
            LoggingConfig.configure_logging(log_level="INFO", log_file=str(log_file))
            
            # 创建日志记录器
            logger = get_logger("test")
            
            # 写入不同级别的日志
            logger.debug("Debug message")  # 不应被记录
            logger.info("Info message")    # 应被记录
            logger.warning("Warning message")  # 应被记录
            logger.error("Error message")  # 应被记录
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证日志内容
                assert "Debug message" not in content  # DEBUG不应被记录
                assert "Info message" in content
                assert "Warning message" in content
                assert "Error message" in content
    
    def test_log_with_exception(self):
        """测试异常日志记录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置日志系统
            LoggingConfig.configure_logging(log_file=str(log_file))
            
            # 创建日志记录器
            logger = get_logger("test")
            
            # 记录异常
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.error("An error occurred", exc_info=True)
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证异常信息被记录
                assert "An error occurred" in content
                assert "ValueError" in content
                assert "Test exception" in content


class TestLoggingSecurity:
    """测试日志安全性"""
    
    def test_token_not_logged(self):
        """测试完整token不应被记录到日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # 配置日志系统
            LoggingConfig.configure_logging(log_file=str(log_file))
            
            # 创建日志记录器
            logger = get_logger("test")
            
            # 模拟token（不应直接记录完整token）
            token = "sk-abc123xyz456789"
            
            # 正确的做法：只记录token的前4位和后4位
            from src.error_handling.error_messages import ErrorHandler
            sanitized_token = ErrorHandler.sanitize_token_for_log(token)
            logger.info(f"Token bound: {sanitized_token}")
            
            # 读取日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 验证完整token不在日志中
                assert token not in content
                
                # 验证清理后的token在日志中（前4位和后4位）
                assert "sk-a...6789" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
