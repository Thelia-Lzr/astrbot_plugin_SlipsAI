"""
数据库管理模块

该模块提供SQLite数据库的异步操作接口，用于管理用户token数据。
使用aiosqlite实现异步数据库操作，确保数据库操作的原子性和一致性。

职责：
- 管理SQLite数据库连接生命周期
- 执行用户token的增删改查操作
- 确保数据库操作的原子性和一致性
- 处理数据库异常和错误
"""

import aiosqlite
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器
    
    管理SQLite数据库连接和用户token数据的CRUD操作。
    使用aiosqlite实现异步数据库操作，支持参数化查询防止SQL注入。
    
    Attributes:
        db_path: 数据库文件路径
        _connection: 数据库连接对象（私有）
    """
    
    def __init__(self, db_path: str):
        """初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
        logger.info(f"DatabaseManager initialized with path: {db_path}")
    
    async def initialize(self) -> None:
        """创建数据库表结构
        
        创建user_tokens表和相关索引。如果表已存在则不会重复创建。
        表结构包含：id, platform, user_id, encrypted_token, created_at, updated_at
        
        Raises:
            Exception: 数据库初始化失败时抛出异常
        """
        try:
            # 确保数据目录存在
            db_dir = Path(self.db_path).parent
            if not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")
            
            # 连接数据库
            self._connection = await aiosqlite.connect(self.db_path)
            
            # 创建user_tokens表
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS user_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    encrypted_token TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, user_id)
                )
            """)
            
            # 创建索引以优化查询性能
            await self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform_user 
                ON user_tokens(platform, user_id)
            """)
            
            await self._connection.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def save_token(self, platform: str, user_id: str, encrypted_token: str) -> bool:
        """保存或更新用户token
        
        使用INSERT OR REPLACE语句实现upsert操作。
        如果用户已有token，则更新现有记录；否则创建新记录。
        使用参数化查询防止SQL注入攻击。
        
        Args:
            platform: 用户所在平台（如：qq, telegram, discord）
            user_id: 用户在该平台的唯一标识
            encrypted_token: 加密后的token字符串
        
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        if not self._connection:
            logger.error("Database connection not initialized")
            return False
        
        try:
            # 使用参数化查询防止SQL注入
            await self._connection.execute("""
                INSERT INTO user_tokens (platform, user_id, encrypted_token, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(platform, user_id) 
                DO UPDATE SET 
                    encrypted_token = excluded.encrypted_token,
                    updated_at = CURRENT_TIMESTAMP
            """, (platform, user_id, encrypted_token))
            
            await self._connection.commit()
            logger.info(f"Token saved for user {platform}:{user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save token for {platform}:{user_id}: {e}")
            await self._connection.rollback()
            return False
    
    async def get_token(self, platform: str, user_id: str) -> Optional[str]:
        """获取用户的加密token
        
        从数据库中查询指定用户的加密token。
        使用参数化查询防止SQL注入攻击。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
        
        Returns:
            Optional[str]: 加密的token字符串，如果用户不存在则返回None
        """
        if not self._connection:
            logger.error("Database connection not initialized")
            return None
        
        try:
            # 使用参数化查询防止SQL注入
            async with self._connection.execute(
                "SELECT encrypted_token FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    logger.debug(f"Token retrieved for user {platform}:{user_id}")
                    return row[0]
                else:
                    logger.debug(f"No token found for user {platform}:{user_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get token for {platform}:{user_id}: {e}")
            return None
    
    async def delete_token(self, platform: str, user_id: str) -> bool:
        """删除用户token
        
        从数据库中删除指定用户的token记录。
        使用参数化查询防止SQL注入攻击。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
        
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        if not self._connection:
            logger.error("Database connection not initialized")
            return False
        
        try:
            # 使用参数化查询防止SQL注入
            cursor = await self._connection.execute(
                "DELETE FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id)
            )
            
            await self._connection.commit()
            
            # 检查是否有记录被删除
            if cursor.rowcount > 0:
                logger.info(f"Token deleted for user {platform}:{user_id}")
                return True
            else:
                logger.warning(f"No token found to delete for user {platform}:{user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete token for {platform}:{user_id}: {e}")
            await self._connection.rollback()
            return False
    
    async def user_has_token(self, platform: str, user_id: str) -> bool:
        """检查用户是否已绑定token
        
        查询数据库检查指定用户是否存在token记录。
        使用参数化查询防止SQL注入攻击。
        
        Args:
            platform: 用户所在平台
            user_id: 用户ID
        
        Returns:
            bool: 用户已绑定token返回True，否则返回False
        """
        if not self._connection:
            logger.error("Database connection not initialized")
            return False
        
        try:
            # 使用参数化查询防止SQL注入
            async with self._connection.execute(
                "SELECT 1 FROM user_tokens WHERE platform = ? AND user_id = ? LIMIT 1",
                (platform, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                has_token = row is not None
                logger.debug(f"User {platform}:{user_id} has token: {has_token}")
                return has_token
                
        except Exception as e:
            logger.error(f"Failed to check token for {platform}:{user_id}: {e}")
            return False
    
    async def close(self) -> None:
        """关闭数据库连接
        
        释放数据库连接资源。应在应用程序关闭时调用。
        """
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
