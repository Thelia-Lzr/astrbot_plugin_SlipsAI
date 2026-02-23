"""
DatabaseManager单元测试

测试数据库管理器的核心功能，包括：
- 数据库初始化和表创建
- Token的CRUD操作
- 唯一约束验证
- 异常处理
"""

import pytest
import pytest_asyncio
import aiosqlite
import tempfile
import os
from pathlib import Path

from src.database.database_manager import DatabaseManager


@pytest_asyncio.fixture
async def temp_db():
    """创建临时数据库用于测试"""
    # 创建临时文件
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db_manager = DatabaseManager(path)
    await db_manager.initialize()
    
    yield db_manager
    
    # 清理
    await db_manager.close()
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_database_initialization():
    """测试数据库初始化"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 验证数据库文件已创建
        assert os.path.exists(path)
        
        # 验证表已创建
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_tokens'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None
                assert result[0] == "user_tokens"
        
        await db_manager.close()
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_save_token(temp_db):
    """测试保存token"""
    platform = "qq"
    user_id = "123456"
    encrypted_token = "encrypted_test_token"
    
    # 保存token
    result = await temp_db.save_token(platform, user_id, encrypted_token)
    assert result is True
    
    # 验证token已保存
    token = await temp_db.get_token(platform, user_id)
    assert token == encrypted_token


@pytest.mark.asyncio
async def test_save_token_update_existing(temp_db):
    """测试更新已存在的token"""
    platform = "qq"
    user_id = "123456"
    old_token = "old_encrypted_token"
    new_token = "new_encrypted_token"
    
    # 保存初始token
    await temp_db.save_token(platform, user_id, old_token)
    
    # 更新token
    result = await temp_db.save_token(platform, user_id, new_token)
    assert result is True
    
    # 验证token已更新
    token = await temp_db.get_token(platform, user_id)
    assert token == new_token


@pytest.mark.asyncio
async def test_get_token_not_found(temp_db):
    """测试获取不存在的token"""
    token = await temp_db.get_token("qq", "nonexistent")
    assert token is None


@pytest.mark.asyncio
async def test_delete_token(temp_db):
    """测试删除token"""
    platform = "qq"
    user_id = "123456"
    encrypted_token = "encrypted_test_token"
    
    # 先保存token
    await temp_db.save_token(platform, user_id, encrypted_token)
    
    # 删除token
    result = await temp_db.delete_token(platform, user_id)
    assert result is True
    
    # 验证token已删除
    token = await temp_db.get_token(platform, user_id)
    assert token is None


@pytest.mark.asyncio
async def test_delete_token_not_found(temp_db):
    """测试删除不存在的token"""
    result = await temp_db.delete_token("qq", "nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_user_has_token(temp_db):
    """测试检查用户是否有token"""
    platform = "qq"
    user_id = "123456"
    encrypted_token = "encrypted_test_token"
    
    # 初始状态：用户没有token
    has_token = await temp_db.user_has_token(platform, user_id)
    assert has_token is False
    
    # 保存token后
    await temp_db.save_token(platform, user_id, encrypted_token)
    has_token = await temp_db.user_has_token(platform, user_id)
    assert has_token is True
    
    # 删除token后
    await temp_db.delete_token(platform, user_id)
    has_token = await temp_db.user_has_token(platform, user_id)
    assert has_token is False


@pytest.mark.asyncio
async def test_unique_constraint(temp_db):
    """测试唯一约束：同一用户只能有一个token"""
    platform = "qq"
    user_id = "123456"
    token1 = "token1"
    token2 = "token2"
    
    # 保存第一个token
    await temp_db.save_token(platform, user_id, token1)
    
    # 保存第二个token（应该更新而不是插入新记录）
    await temp_db.save_token(platform, user_id, token2)
    
    # 验证只有一条记录，且是最新的token
    token = await temp_db.get_token(platform, user_id)
    assert token == token2
    
    # 验证数据库中只有一条记录
    async with aiosqlite.connect(temp_db.db_path) as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
            (platform, user_id)
        ) as cursor:
            count = await cursor.fetchone()
            assert count[0] == 1


@pytest.mark.asyncio
async def test_multiple_users(temp_db):
    """测试多个用户的token互不影响"""
    users = [
        ("qq", "user1", "token1"),
        ("qq", "user2", "token2"),
        ("telegram", "user1", "token3"),
    ]
    
    # 保存所有用户的token
    for platform, user_id, token in users:
        result = await temp_db.save_token(platform, user_id, token)
        assert result is True
    
    # 验证每个用户的token都正确
    for platform, user_id, expected_token in users:
        token = await temp_db.get_token(platform, user_id)
        assert token == expected_token


@pytest.mark.asyncio
async def test_close_connection(temp_db):
    """测试关闭数据库连接"""
    await temp_db.close()
    
    # 关闭后操作应该失败
    result = await temp_db.save_token("qq", "123", "token")
    assert result is False


@pytest.mark.asyncio
async def test_database_initialization_creates_directory():
    """测试数据库初始化时自动创建目录"""
    # 创建一个不存在的目录路径
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "subdir", "test.db")
    
    try:
        db_manager = DatabaseManager(db_path)
        await db_manager.initialize()
        
        # 验证目录和数据库文件都已创建
        assert os.path.exists(os.path.dirname(db_path))
        assert os.path.exists(db_path)
        
        await db_manager.close()
    finally:
        # 清理
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(os.path.dirname(db_path)):
            os.rmdir(os.path.dirname(db_path))
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@pytest.mark.asyncio
async def test_database_initialization_failure():
    """测试数据库初始化失败的情况"""
    # 使用无效路径（例如只读目录）
    invalid_path = "/invalid/readonly/path/test.db"
    
    db_manager = DatabaseManager(invalid_path)
    
    # 初始化应该抛出异常
    with pytest.raises(Exception):
        await db_manager.initialize()


@pytest.mark.asyncio
async def test_save_token_without_initialization():
    """测试未初始化数据库时保存token"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        # 不调用initialize()
        
        # 保存应该失败
        result = await db_manager.save_token("qq", "123", "token")
        assert result is False
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_get_token_without_initialization():
    """测试未初始化数据库时获取token"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        # 不调用initialize()
        
        # 获取应该返回None
        token = await db_manager.get_token("qq", "123")
        assert token is None
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_delete_token_without_initialization():
    """测试未初始化数据库时删除token"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        # 不调用initialize()
        
        # 删除应该失败
        result = await db_manager.delete_token("qq", "123")
        assert result is False
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_user_has_token_without_initialization():
    """测试未初始化数据库时检查用户token"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        # 不调用initialize()
        
        # 检查应该返回False
        has_token = await db_manager.user_has_token("qq", "123")
        assert has_token is False
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_database_index_creation():
    """测试数据库索引创建"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 验证索引已创建
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_platform_user'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None
                assert result[0] == "idx_platform_user"
        
        await db_manager.close()
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_save_token_rollback_on_error(temp_db, mocker):
    """测试保存token失败时的回滚"""
    # Mock execute方法使其抛出异常
    mocker.patch.object(
        temp_db._connection,
        'execute',
        side_effect=Exception("Database error")
    )
    
    # 保存应该失败
    result = await temp_db.save_token("qq", "123", "token")
    assert result is False


@pytest.mark.asyncio
async def test_delete_token_rollback_on_error(temp_db, mocker):
    """测试删除token失败时的回滚"""
    # 先保存一个token
    await temp_db.save_token("qq", "123", "token")
    
    # Mock execute方法使其抛出异常
    mocker.patch.object(
        temp_db._connection,
        'execute',
        side_effect=Exception("Database error")
    )
    
    # 删除应该失败
    result = await temp_db.delete_token("qq", "123")
    assert result is False


@pytest.mark.asyncio
async def test_concurrent_token_operations(temp_db):
    """测试并发token操作"""
    import asyncio
    
    platform = "qq"
    user_id = "123456"
    
    # 并发保存多个token
    async def save_token_task(token_value):
        return await temp_db.save_token(platform, user_id, token_value)
    
    # 创建10个并发任务
    tasks = [save_token_task(f"token_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # 所有操作都应该成功
    assert all(results)
    
    # 最终应该只有一条记录
    async with aiosqlite.connect(temp_db.db_path) as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
            (platform, user_id)
        ) as cursor:
            count = await cursor.fetchone()
            assert count[0] == 1


@pytest.mark.asyncio
async def test_empty_string_handling(temp_db):
    """测试空字符串的处理"""
    # 保存空字符串token
    result = await temp_db.save_token("qq", "123", "")
    assert result is True
    
    # 验证可以获取空字符串
    token = await temp_db.get_token("qq", "123")
    assert token == ""


@pytest.mark.asyncio
async def test_special_characters_in_token(temp_db):
    """测试token中包含特殊字符"""
    special_token = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
    
    result = await temp_db.save_token("qq", "123", special_token)
    assert result is True
    
    token = await temp_db.get_token("qq", "123")
    assert token == special_token


@pytest.mark.asyncio
async def test_long_token_string(temp_db):
    """测试长token字符串"""
    # 创建一个很长的token（10KB）
    long_token = "a" * 10240
    
    result = await temp_db.save_token("qq", "123", long_token)
    assert result is True
    
    token = await temp_db.get_token("qq", "123")
    assert token == long_token
    assert len(token) == 10240


@pytest.mark.asyncio
async def test_unicode_characters(temp_db):
    """测试Unicode字符"""
    unicode_token = "token_中文_日本語_한국어_🎉"
    
    result = await temp_db.save_token("qq", "123", unicode_token)
    assert result is True
    
    token = await temp_db.get_token("qq", "123")
    assert token == unicode_token


@pytest.mark.asyncio
async def test_get_token_exception_handling(temp_db, mocker):
    """测试获取token时的异常处理"""
    # Mock execute方法使其抛出异常
    mocker.patch.object(
        temp_db._connection,
        'execute',
        side_effect=Exception("Database error")
    )
    
    # 获取应该返回None
    token = await temp_db.get_token("qq", "123")
    assert token is None


@pytest.mark.asyncio
async def test_user_has_token_exception_handling(temp_db, mocker):
    """测试检查用户token时的异常处理"""
    # Mock execute方法使其抛出异常
    mocker.patch.object(
        temp_db._connection,
        'execute',
        side_effect=Exception("Database error")
    )
    
    # 检查应该返回False
    has_token = await temp_db.user_has_token("qq", "123")
    assert has_token is False
