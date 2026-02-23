"""
Token管理协调模块

该模块协调数据库管理和加密操作，提供高层token管理接口。
作为业务逻辑层，处理token的绑定、查询、更新和删除操作。

职责：
- 协调DatabaseManager和TokenEncryption组件
- 提供业务层的token管理接口
- 处理token绑定、更新、删除的业务逻辑
- 验证输入参数的有效性

验证需求：
- 需求 1（Token绑定管理）
- 需求 3（Token更新）
- 需求 4（Token解绑）
"""

import logging
from typing import Optional
from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption


logger = logging.getLogger(__name__)


class TokenManager:
    """Token管理器
    
    协调数据库管理和加密操作，提供高层token管理接口。
    负责验证输入参数、加密token、存储到数据库等业务逻辑。
    
    Attributes:
        db_manager: 数据库管理器实例
        encryption: Token加密器实例
    """
    
    def __init__(self, db_manager: DatabaseManager, encryption: TokenEncryption):
        """初始化token管理器
        
        Args:
            db_manager: 数据库管理器实例
            encryption: Token加密器实例
        """
        self.db_manager = db_manager
        self.encryption = encryption
        logger.info("TokenManager initialized")
    
    def _validate_platform(self, platform: str) -> bool:
        """验证platform参数
        
        Args:
            platform: 用户所在平台
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        if not platform:
            logger.warning("Platform is empty")
            return False
        
        if len(platform) < 1 or len(platform) > 50:
            logger.warning(f"Platform length invalid: {len(platform)}")
            return False
        
        return True
    
    def _validate_user_id(self, user_id: str) -> bool:
        """验证user_id参数
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        if not user_id:
            logger.warning("User ID is empty")
            return False
        
        if len(user_id) < 1 or len(user_id) > 100:
            logger.warning(f"User ID length invalid: {len(user_id)}")
            return False
        
        return True
    
    def _validate_token(self, token: str) -> bool:
        """验证token参数
        
        Args:
            token: Token字符串
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        if not token:
            logger.warning("Token is empty")
            return False
        
        return True
    
    async def bind_token(self, platform: str, user_id: str, token: str) -> bool:
        """绑定用户token（加密后存储）
        
        验证输入参数，加密token，然后存储到数据库。
        如果用户已有token，则更新现有记录。
        
        Args:
            platform: 用户所在平台（长度1-50字符）
            user_id: 用户ID（长度1-100字符）
            token: 原始token字符串
            
        Returns:
            bool: 绑定成功返回True，失败返回False
            
        验证需求：
        - 需求 1.1: 加密token并存储到数据库中
        - 需求 1.4: 用户已有token并再次绑定时更新现有token记录
        - 需求 1.5: token绑定失败时保持数据库状态不变
        """
        # 验证输入参数
        if not self._validate_platform(platform):
            logger.error(f"Invalid platform parameter: {platform}")
            return False
        
        if not self._validate_user_id(user_id):
            logger.error(f"Invalid user_id parameter: {user_id}")
            return False
        
        if not self._validate_token(token):
            logger.error("Invalid token parameter")
            return False
        
        try:
            # 加密token
            encrypted_token = self.encryption.encrypt(token)
            logger.debug(f"Token encrypted for user {platform}:{user_id}")
            
            # 保存到数据库
            success = await self.db_manager.save_token(platform, user_id, encrypted_token)
            
            if success:
                logger.info(f"Token bound successfully for user {platform}:{user_id}")
            else:
                logger.error(f"Failed to bind token for user {platform}:{user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during token binding for {platform}:{user_id}: {e}")
            return False
    
    async def get_user_token(self, platform: str, user_id: str) -> Optional[str]:
        """获取用户token（解密后返回）
        
        从数据库获取加密的token，然后解密并返回原始token。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
            
        Returns:
            Optional[str]: 解密后的token字符串，如果用户未绑定token则返回None
            
        验证需求：
        - 需求 2.1: 返回用户是否已绑定token的信息
        """
        # 验证输入参数
        if not self._validate_platform(platform):
            logger.error(f"Invalid platform parameter: {platform}")
            return None
        
        if not self._validate_user_id(user_id):
            logger.error(f"Invalid user_id parameter: {user_id}")
            return None
        
        try:
            # 从数据库获取加密token
            encrypted_token = await self.db_manager.get_token(platform, user_id)
            
            if encrypted_token is None:
                logger.debug(f"No token found for user {platform}:{user_id}")
                return None
            
            # 解密token
            token = self.encryption.decrypt(encrypted_token)
            logger.debug(f"Token retrieved and decrypted for user {platform}:{user_id}")
            
            return token
            
        except Exception as e:
            logger.error(f"Exception during token retrieval for {platform}:{user_id}: {e}")
            return None
    
    async def update_token(self, platform: str, user_id: str, new_token: str) -> bool:
        """更新用户token
        
        验证输入参数，加密新token，然后更新数据库中的记录。
        实际上与bind_token的实现相同，因为数据库使用upsert操作。
        
        Args:
            platform: 用户所在平台（长度1-50字符）
            user_id: 用户ID（长度1-100字符）
            new_token: 新的token字符串
            
        Returns:
            bool: 更新成功返回True，失败返回False
            
        验证需求：
        - 需求 3.2: 更新数据库中的加密token
        - 需求 3.5: token更新失败时保持原有token状态不变
        """
        # 验证输入参数
        if not self._validate_platform(platform):
            logger.error(f"Invalid platform parameter: {platform}")
            return False
        
        if not self._validate_user_id(user_id):
            logger.error(f"Invalid user_id parameter: {user_id}")
            return False
        
        if not self._validate_token(new_token):
            logger.error("Invalid token parameter")
            return False
        
        try:
            # 加密新token
            encrypted_token = self.encryption.encrypt(new_token)
            logger.debug(f"New token encrypted for user {platform}:{user_id}")
            
            # 更新数据库
            success = await self.db_manager.save_token(platform, user_id, encrypted_token)
            
            if success:
                logger.info(f"Token updated successfully for user {platform}:{user_id}")
            else:
                logger.error(f"Failed to update token for user {platform}:{user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during token update for {platform}:{user_id}: {e}")
            return False
    
    async def unbind_token(self, platform: str, user_id: str) -> bool:
        """解绑用户token
        
        从数据库中删除用户的token记录。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
            
        Returns:
            bool: 解绑成功返回True，失败返回False
            
        验证需求：
        - 需求 4.2: 从数据库中删除该用户的token记录
        """
        # 验证输入参数
        if not self._validate_platform(platform):
            logger.error(f"Invalid platform parameter: {platform}")
            return False
        
        if not self._validate_user_id(user_id):
            logger.error(f"Invalid user_id parameter: {user_id}")
            return False
        
        try:
            # 从数据库删除token
            success = await self.db_manager.delete_token(platform, user_id)
            
            if success:
                logger.info(f"Token unbound successfully for user {platform}:{user_id}")
            else:
                logger.warning(f"No token to unbind for user {platform}:{user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during token unbinding for {platform}:{user_id}: {e}")
            return False
    
    async def has_token(self, platform: str, user_id: str) -> bool:
        """检查用户是否已绑定token
        
        查询数据库检查用户是否存在token记录。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
            
        Returns:
            bool: 用户已绑定token返回True，否则返回False
            
        验证需求：
        - 需求 2.1: 返回用户是否已绑定token的信息
        """
        # 验证输入参数
        if not self._validate_platform(platform):
            logger.error(f"Invalid platform parameter: {platform}")
            return False
        
        if not self._validate_user_id(user_id):
            logger.error(f"Invalid user_id parameter: {user_id}")
            return False
        
        try:
            # 检查数据库
            has_token = await self.db_manager.user_has_token(platform, user_id)
            logger.debug(f"User {platform}:{user_id} has token: {has_token}")
            
            return has_token
            
        except Exception as e:
            logger.error(f"Exception during token check for {platform}:{user_id}: {e}")
            return False
