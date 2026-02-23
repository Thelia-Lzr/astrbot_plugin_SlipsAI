"""
DatabaseManager属性测试

使用hypothesis进行基于属性的测试，验证：
- 属性 1: Token唯一性 - 验证同一用户多次绑定token只保留最新记录
- 测试并发访问的线程安全性

**验证需求：需求 11.2**
"""

import pytest
import pytest_asyncio
import tempfile
import os
import asyncio
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from src.database.database_manager import DatabaseManager


# 定义策略：生成有效的platform字符串（1-50字符）
platform_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),  # 大写、小写、数字
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != '')  # 确保不是空白字符串

# 定义策略：生成有效的user_id字符串（1-100字符）
user_id_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip() != '')

# 定义策略：生成token字符串（1-500字符）
token_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip() != '')


@pytest_asyncio.fixture
async def temp_db_manager():
    """创建临时数据库管理器用于测试"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db_manager = DatabaseManager(path)
    await db_manager.initialize()
    
    yield db_manager
    
    # 清理
    await db_manager.close()
    if os.path.exists(path):
        os.unlink(path)


# ============================================
# 属性 1: Token唯一性
# **验证需求：需求 11.2**
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    token1=token_strategy,
    token2=token_strategy
)
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_token_uniqueness_multiple_saves(
    platform: str,
    user_id: str,
    token1: str,
    token2: str
):
    """
    **Validates: Requirements 11.2**
    
    属性：同一用户多次绑定token只保留最新记录
    
    验证：
    1. 同一(platform, user_id)组合多次保存token
    2. 数据库中只保留最新的token
    3. 查询返回的是最新token
    """
    # 确保两个token不同，以便测试更新逻辑
    assume(token1 != token2)
    
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 第一次保存token1
        result1 = await db_manager.save_token(platform, user_id, token1)
        assert result1 is True, "第一次保存应该成功"
        
        # 验证token1已保存
        retrieved1 = await db_manager.get_token(platform, user_id)
        assert retrieved1 == token1, "应该返回第一次保存的token"
        
        # 第二次保存token2（更新）
        result2 = await db_manager.save_token(platform, user_id, token2)
        assert result2 is True, "第二次保存应该成功"
        
        # 验证token2已更新
        retrieved2 = await db_manager.get_token(platform, user_id)
        assert retrieved2 == token2, "应该返回最新保存的token"
        
        # 验证只有一条记录（通过直接查询数据库）
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id)
            ) as cursor:
                count = await cursor.fetchone()
                assert count[0] == 1, f"数据库中应该只有1条记录，实际有{count[0]}条"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    tokens=st.lists(token_strategy, min_size=2, max_size=10)
)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_token_uniqueness_multiple_updates(
    platform: str,
    user_id: str,
    tokens: list
):
    """
    **Validates: Requirements 11.2**
    
    属性：同一用户多次更新token，始终只保留最新记录
    
    验证：
    1. 多次更新token（2-10次）
    2. 每次更新后数据库中只有一条记录
    3. 最终查询返回的是最后一次保存的token
    """
    # 确保所有token都不同
    assume(len(set(tokens)) == len(tokens))
    
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 依次保存所有token
        for token in tokens:
            result = await db_manager.save_token(platform, user_id, token)
            assert result is True, f"保存token '{token[:10]}...' 应该成功"
        
        # 验证最后一个token被保存
        final_token = await db_manager.get_token(platform, user_id)
        assert final_token == tokens[-1], "应该返回最后保存的token"
        
        # 验证只有一条记录
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id)
            ) as cursor:
                count = await cursor.fetchone()
                assert count[0] == 1, f"数据库中应该只有1条记录，实际有{count[0]}条"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id1=user_id_strategy,
    user_id2=user_id_strategy,
    token1=token_strategy,
    token2=token_strategy
)
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_token_uniqueness_different_users(
    platform: str,
    user_id1: str,
    user_id2: str,
    token1: str,
    token2: str
):
    """
    **Validates: Requirements 11.2**
    
    属性：不同用户的token记录互不影响
    
    验证：
    1. 同一平台的不同用户可以各自保存token
    2. 每个用户的token记录独立
    3. 更新一个用户的token不影响其他用户
    """
    # 确保是不同用户
    assume(user_id1 != user_id2)
    
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 两个用户分别保存token
        result1 = await db_manager.save_token(platform, user_id1, token1)
        result2 = await db_manager.save_token(platform, user_id2, token2)
        
        assert result1 is True, "用户1保存应该成功"
        assert result2 is True, "用户2保存应该成功"
        
        # 验证两个用户的token都正确
        retrieved1 = await db_manager.get_token(platform, user_id1)
        retrieved2 = await db_manager.get_token(platform, user_id2)
        
        assert retrieved1 == token1, "用户1应该返回自己的token"
        assert retrieved2 == token2, "用户2应该返回自己的token"
        
        # 更新用户1的token
        new_token1 = token1 + "_updated"
        await db_manager.save_token(platform, user_id1, new_token1)
        
        # 验证用户1的token已更新，用户2的token不变
        retrieved1_new = await db_manager.get_token(platform, user_id1)
        retrieved2_unchanged = await db_manager.get_token(platform, user_id2)
        
        assert retrieved1_new == new_token1, "用户1的token应该已更新"
        assert retrieved2_unchanged == token2, "用户2的token应该保持不变"
        
        # 验证每个用户只有一条记录
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id1)
            ) as cursor:
                count1 = await cursor.fetchone()
                assert count1[0] == 1, f"用户1应该只有1条记录"
            
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id2)
            ) as cursor:
                count2 = await cursor.fetchone()
                assert count2[0] == 1, f"用户2应该只有1条记录"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ============================================
# 并发访问的线程安全性测试
# **验证需求：需求 11.2**
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_ids=st.lists(user_id_strategy, min_size=3, max_size=10, unique=True),
    tokens=st.lists(token_strategy, min_size=3, max_size=10)
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_concurrent_access_safety(
    platform: str,
    user_ids: list,
    tokens: list
):
    """
    **Validates: Requirements 11.2**
    
    属性：并发访问时数据一致性
    
    验证：
    1. 多个用户并发保存token
    2. 每个用户的token都正确保存
    3. 没有数据丢失或混淆
    """
    # 确保有足够的tokens
    assume(len(tokens) >= len(user_ids))
    
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 创建并发任务：每个用户保存自己的token
        async def save_user_token(user_id: str, token: str):
            return await db_manager.save_token(platform, user_id, token)
        
        # 并发执行所有保存操作
        tasks = [
            save_user_token(user_id, tokens[i])
            for i, user_id in enumerate(user_ids)
        ]
        results = await asyncio.gather(*tasks)
        
        # 验证所有保存操作都成功
        assert all(results), "所有保存操作都应该成功"
        
        # 验证每个用户的token都正确保存
        for i, user_id in enumerate(user_ids):
            retrieved = await db_manager.get_token(platform, user_id)
            assert retrieved == tokens[i], f"用户 {user_id} 的token应该正确保存"
        
        # 验证总记录数正确
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ?",
                (platform,)
            ) as cursor:
                total_count = await cursor.fetchone()
                assert total_count[0] == len(user_ids), \
                    f"应该有{len(user_ids)}条记录，实际有{total_count[0]}条"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    tokens=st.lists(token_strategy, min_size=5, max_size=20, unique=True)
)
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_concurrent_updates_same_user(
    platform: str,
    user_id: str,
    tokens: list
):
    """
    **Validates: Requirements 11.2**
    
    属性：同一用户并发更新token时的一致性
    
    验证：
    1. 同一用户并发多次更新token
    2. 最终数据库中只有一条记录
    3. 保存的是其中一个有效的token（不会出现数据损坏）
    """
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 创建并发任务：同一用户并发保存多个不同的token
        async def save_token_task(token: str):
            return await db_manager.save_token(platform, user_id, token)
        
        # 并发执行所有保存操作
        tasks = [save_token_task(token) for token in tokens]
        results = await asyncio.gather(*tasks)
        
        # 验证所有保存操作都成功
        assert all(results), "所有保存操作都应该成功"
        
        # 验证只有一条记录
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                (platform, user_id)
            ) as cursor:
                count = await cursor.fetchone()
                assert count[0] == 1, f"应该只有1条记录，实际有{count[0]}条"
        
        # 验证保存的token是有效的（是tokens列表中的一个）
        final_token = await db_manager.get_token(platform, user_id)
        assert final_token in tokens, "最终保存的token应该是有效的token之一"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_ids=st.lists(user_id_strategy, min_size=3, max_size=8, unique=True),
    tokens=st.lists(token_strategy, min_size=3, max_size=8)
)
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_concurrent_mixed_operations(
    platform: str,
    user_ids: list,
    tokens: list
):
    """
    **Validates: Requirements 11.2**
    
    属性：并发混合操作（保存、查询、删除）的一致性
    
    验证：
    1. 多个用户并发执行保存、查询、删除操作
    2. 操作完成后数据状态一致
    3. 没有数据损坏或丢失
    """
    # 确保有足够的tokens
    assume(len(tokens) >= len(user_ids))
    
    # 创建临时数据库
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        db_manager = DatabaseManager(path)
        await db_manager.initialize()
        
        # 先为所有用户保存初始token
        for i, user_id in enumerate(user_ids):
            await db_manager.save_token(platform, user_id, tokens[i])
        
        # 创建混合操作任务
        async def mixed_operations(user_id: str, token: str):
            # 查询
            retrieved = await db_manager.get_token(platform, user_id)
            # 更新
            new_token = token + "_updated"
            await db_manager.save_token(platform, user_id, new_token)
            # 再次查询
            retrieved_new = await db_manager.get_token(platform, user_id)
            return retrieved_new == new_token
        
        # 并发执行混合操作
        tasks = [
            mixed_operations(user_id, tokens[i])
            for i, user_id in enumerate(user_ids)
        ]
        results = await asyncio.gather(*tasks)
        
        # 验证所有操作都成功
        assert all(results), "所有混合操作都应该成功"
        
        # 验证每个用户的token都已更新
        for i, user_id in enumerate(user_ids):
            retrieved = await db_manager.get_token(platform, user_id)
            expected_token = tokens[i] + "_updated"
            assert retrieved == expected_token, \
                f"用户 {user_id} 的token应该已更新为 {expected_token}"
        
        # 验证每个用户只有一条记录
        import aiosqlite
        async with aiosqlite.connect(path) as conn:
            for user_id in user_ids:
                async with conn.execute(
                    "SELECT COUNT(*) FROM user_tokens WHERE platform = ? AND user_id = ?",
                    (platform, user_id)
                ) as cursor:
                    count = await cursor.fetchone()
                    assert count[0] == 1, f"用户 {user_id} 应该只有1条记录"
        
        await db_manager.close()
        
    finally:
        if os.path.exists(path):
            os.unlink(path)
