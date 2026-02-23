"""
Token加密模块

提供token的加密和解密功能，确保token安全存储。
使用Fernet对称加密算法（基于AES-128-CBC）。

验证需求：需求 5（Token安全存储）
"""

import os
import stat
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)


class TokenEncryption:
    """
    Token加密类
    
    使用Fernet对称加密算法加密和解密token。
    密钥存储在独立文件中，权限设置为600（仅所有者可读写）。
    
    Attributes:
        _fernet: Fernet加密器实例
        _key: 加密密钥（bytes）
        _key_file_path: 密钥文件路径
    """
    
    def __init__(
        self, 
        key_file_path: str = "/AstrBot/data/encryption.key",
        encryption_key: Optional[bytes] = None
    ):
        """
        初始化加密器
        
        如果提供了encryption_key，则使用该密钥。
        否则，尝试从key_file_path加载密钥。
        如果文件不存在，则生成新密钥并保存到文件。
        
        Args:
            key_file_path: 密钥文件路径，默认为 /AstrBot/data/encryption.key
            encryption_key: 可选的加密密钥（用于测试或自定义密钥）
            
        Raises:
            ValueError: 如果提供的密钥格式无效
            OSError: 如果无法创建或访问密钥文件
        """
        self._key_file_path = Path(key_file_path)
        
        if encryption_key is not None:
            # 使用提供的密钥
            self._key = encryption_key
            logger.info("使用提供的加密密钥初始化")
        else:
            # 尝试加载或生成密钥
            self._key = self._load_or_generate_key()
        
        try:
            self._fernet = Fernet(self._key)
            logger.info("TokenEncryption初始化成功")
        except Exception as e:
            logger.error(f"初始化Fernet加密器失败: {e}")
            raise ValueError(f"无效的加密密钥: {e}")
    
    def _load_or_generate_key(self) -> bytes:
        """
        加载现有密钥或生成新密钥
        
        如果密钥文件存在，则从文件加载密钥。
        否则，生成新密钥并保存到文件。
        
        Returns:
            加密密钥（bytes）
            
        Raises:
            OSError: 如果无法创建目录或文件
        """
        if self._key_file_path.exists():
            # 加载现有密钥
            logger.info(f"从文件加载加密密钥: {self._key_file_path}")
            return self._load_key_from_file()
        else:
            # 生成新密钥
            logger.info(f"生成新的加密密钥并保存到: {self._key_file_path}")
            return self._generate_and_save_key()
    
    def _load_key_from_file(self) -> bytes:
        """
        从文件加载加密密钥
        
        Returns:
            加密密钥（bytes）
            
        Raises:
            OSError: 如果无法读取文件
            ValueError: 如果密钥格式无效
        """
        try:
            with open(self._key_file_path, 'rb') as key_file:
                key = key_file.read()
            
            # 验证密钥格式（Fernet密钥应该是44字节的base64编码）
            if len(key) == 0:
                raise ValueError("密钥文件为空")
            
            logger.debug(f"成功加载密钥，长度: {len(key)} 字节")
            return key
        except OSError as e:
            logger.error(f"无法读取密钥文件 {self._key_file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"加载密钥时发生错误: {e}")
            raise ValueError(f"无效的密钥文件: {e}")
    
    def _generate_and_save_key(self) -> bytes:
        """
        生成新的加密密钥并保存到文件
        
        生成Fernet密钥，创建必要的目录，保存密钥到文件，
        并设置文件权限为600（仅所有者可读写）。
        
        Returns:
            生成的加密密钥（bytes）
            
        Raises:
            OSError: 如果无法创建目录或文件
        """
        # 生成新密钥
        key = Fernet.generate_key()
        logger.debug(f"生成新密钥，长度: {len(key)} 字节")
        
        # 创建目录（如果不存在）
        try:
            self._key_file_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"确保目录存在: {self._key_file_path.parent}")
        except OSError as e:
            logger.error(f"无法创建目录 {self._key_file_path.parent}: {e}")
            raise
        
        # 保存密钥到文件
        try:
            with open(self._key_file_path, 'wb') as key_file:
                key_file.write(key)
            logger.info(f"密钥已保存到文件: {self._key_file_path}")
        except OSError as e:
            logger.error(f"无法写入密钥文件 {self._key_file_path}: {e}")
            raise
        
        # 设置文件权限为600（仅所有者可读写）
        try:
            os.chmod(self._key_file_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"密钥文件权限已设置为600: {self._key_file_path}")
        except OSError as e:
            logger.warning(f"无法设置密钥文件权限: {e}")
            # 不抛出异常，因为在某些系统上可能不支持chmod
        
        return key
    
    def encrypt(self, token: str) -> str:
        """
        加密token
        
        使用Fernet对称加密算法加密token字符串。
        加密结果包含随机IV，因此相同输入会产生不同输出。
        
        Args:
            token: 原始token字符串
            
        Returns:
            base64编码的加密字符串
            
        Raises:
            ValueError: 如果token为空
            Exception: 如果加密过程失败
            
        验证需求：需求 5.1（使用Fernet对称加密算法加密所有token）
        """
        if not token:
            raise ValueError("Token不能为空")
        
        try:
            # 将字符串转换为bytes
            token_bytes = token.encode('utf-8')
            
            # 加密
            encrypted_bytes = self._fernet.encrypt(token_bytes)
            
            # 转换为字符串（base64编码）
            encrypted_str = encrypted_bytes.decode('utf-8')
            
            logger.debug(f"Token加密成功，原始长度: {len(token)}, 加密后长度: {len(encrypted_str)}")
            return encrypted_str
        except Exception as e:
            logger.error(f"Token加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_token: str) -> str:
        """
        解密token
        
        使用Fernet对称加密算法解密token字符串。
        
        Args:
            encrypted_token: base64编码的加密字符串
            
        Returns:
            原始token字符串
            
        Raises:
            ValueError: 如果encrypted_token为空或格式无效
            InvalidToken: 如果解密失败（密钥不匹配或数据损坏）
            
        验证需求：需求 5.1（解密存储的token）
        """
        if not encrypted_token:
            raise ValueError("加密token不能为空")
        
        try:
            # 将字符串转换为bytes
            encrypted_bytes = encrypted_token.encode('utf-8')
            
            # 解密
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            
            # 转换为字符串
            decrypted_str = decrypted_bytes.decode('utf-8')
            
            logger.debug(f"Token解密成功，解密后长度: {len(decrypted_str)}")
            return decrypted_str
        except InvalidToken as e:
            logger.error(f"Token解密失败: 无效的token或密钥不匹配")
            raise InvalidToken("Token解密失败，密钥可能已更改或数据已损坏")
        except Exception as e:
            logger.error(f"Token解密失败: {e}")
            raise
    
    def get_key(self) -> bytes:
        """
        获取当前使用的加密密钥
        
        注意：此方法应谨慎使用，仅用于密钥备份或迁移场景。
        不应在日志或用户界面中暴露密钥。
        
        Returns:
            加密密钥（bytes）
            
        验证需求：需求 5.2（将加密密钥存储在独立文件中）
        """
        return self._key
