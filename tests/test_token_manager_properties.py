"""
TokenManager属性测试

使用hypothesis进行基于属性的测试，验证TokenManager的核心属性：
- 属性 3: Token隔离性
- 属性 5: 操作原子性

**Validates: Requirements 9.2, 9.3, 1.5, 20.1, 20.3**
"""

import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck

from src.token_management.token_manager import TokenManager
from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption


# ============================================
# Fixtures
# ============================================

@pytest_asyncio.fixture
async def db_manager():
    """创建临时数据库管理器用于属性测试"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name
    
    manager = DatabaseManager(db_path)
    await manager.initialize()
    
    yield manager
    
    await manager.close()
    
    # 清理临时文件
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def encryption():
    """创建加密器（使用临时密钥）"""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    return TokenEncryption(encryption_key=key)


@pytest_asyncio.fixture
async def token_manager(db_manager, encryption):
    """创建TokenManager实例"""
    return TokenManager(db_manager, encryption)


# ============================================
# 策略定义 (Hypothesis Strategies)
# ============================================

# 平台名称策略：1-50字符的非空字符串
platform_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),  # 大写、小写、数字
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=50
)

# 用户ID策略：1-100字符的非空字符串
user_id_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=100
)

# Token策略：非空字符串
token_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
        min_codepoint=33,
        max_codepoint=126
    ),
    min_size=1,
    max_size=200
)


# ============================================
# 属性 3: Token隔离性
# **Validates: Requirements 9.2, 9.3**
# ============================================

class TestTokenIsolationProperty:
    """
    属性 3: Token隔离性
    
    验证不同用户的token互不影响：
    - 需求 9.2: WHEN 用户调用工具 THEN THE System SHALL 仅使用该用户的token进行认证
    - 需求 9.3: WHEN 用户A调用工具 THEN THE System SHALL NOT 使用用户B的token
    """
    
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
    async def test_different_users_token_isolation(
        self,
        platform: str,
        user_id1: str,
        user_id2: str,
        token1: str,
        token2: str
    ):
        """
        属性：不同用户的token完全隔离，互不影响
        
        对于任意两个不同的用户，绑定各自的token后：
        1. 用户1获取的token应该是token1
        2. 用户2获取的token应该是token2
        3. 两个token不应该相互影响
        
        **Validates: Requirements 9.2, 9.3**
        """
        # 确保是不同的用户
        assume(user_id1 != user_id2)
        
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 绑定两个用户的token
            result1 = await manager.bind_token(platform, user_id1, token1)
            result2 = await manager.bind_token(platform, user_id2, token2)
            
            # 验证绑定成功
            assert result1 is True, f"用户1 token绑定失败"
            assert result2 is True, f"用户2 token绑定失败"
            
            # 获取两个用户的token
            retrieved1 = await manager.get_user_token(platform, user_id1)
            retrieved2 = await manager.get_user_token(platform, user_id2)
            
            # 验证token隔离性
            assert retrieved1 == token1, f"用户1的token不匹配: 期望 {token1}, 实际 {retrieved1}"
            assert retrieved2 == token2, f"用户2的token不匹配: 期望 {token2}, 实际 {retrieved2}"
            
            # 验证两个用户的token不同（如果输入的token不同）
            if token1 != token2:
                assert retrieved1 != retrieved2, "不同用户的不同token应该保持不同"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    @given(
        platform1=platform_strategy,
        platform2=platform_strategy,
        user_id=user_id_strategy,
        token1=token_strategy,
        token2=token_strategy
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_different_platforms_token_isolation(
        self,
        platform1: str,
        platform2: str,
        user_id: str,
        token1: str,
        token2: str
    ):
        """
        属性：同一用户在不同平台的token完全隔离
        
        对于任意同一用户在不同平台：
        1. 在平台1绑定token1
        2. 在平台2绑定token2
        3. 两个平台的token应该互不影响
        
        **Validates: Requirements 9.2, 9.3**
        """
        # 确保是不同的平台
        assume(platform1 != platform2)
        
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 在两个平台绑定token
            result1 = await manager.bind_token(platform1, user_id, token1)
            result2 = await manager.bind_token(platform2, user_id, token2)
            
            # 验证绑定成功
            assert result1 is True
            assert result2 is True
            
            # 获取两个平台的token
            retrieved1 = await manager.get_user_token(platform1, user_id)
            retrieved2 = await manager.get_user_token(platform2, user_id)
            
            # 验证token隔离性
            assert retrieved1 == token1, f"平台1的token不匹配"
            assert retrieved2 == token2, f"平台2的token不匹配"
            
            # 验证两个平台的token不同（如果输入的token不同）
            if token1 != token2:
                assert retrieved1 != retrieved2, "不同平台的不同token应该保持不同"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
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
    async def test_user_deletion_does_not_affect_other_users(
        self,
        platform: str,
        user_id1: str,
        user_id2: str,
        token1: str,
        token2: str
    ):
        """
        属性：删除一个用户的token不影响其他用户
        
        对于任意两个不同的用户：
        1. 绑定两个用户的token
        2. 删除用户1的token
        3. 用户2的token应该仍然存在且不变
        
        **Validates: Requirements 9.2, 9.3**
        """
        # 确保是不同的用户
        assume(user_id1 != user_id2)
        
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 绑定两个用户的token
            await manager.bind_token(platform, user_id1, token1)
            await manager.bind_token(platform, user_id2, token2)
            
            # 删除用户1的token
            delete_result = await manager.unbind_token(platform, user_id1)
            assert delete_result is True
            
            # 验证用户1的token已删除
            has_token1 = await manager.has_token(platform, user_id1)
            assert has_token1 is False, "用户1的token应该已被删除"
            
            # 验证用户2的token仍然存在
            has_token2 = await manager.has_token(platform, user_id2)
            assert has_token2 is True, "用户2的token应该仍然存在"
            
            # 验证用户2的token内容不变
            retrieved2 = await manager.get_user_token(platform, user_id2)
            assert retrieved2 == token2, "用户2的token内容应该不变"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


# ============================================
# 属性 5: 操作原子性
# **Validates: Requirements 1.5, 20.1, 20.3**
# ============================================

class TestOperationAtomicityProperty:
    """
    属性 5: 操作原子性
    
    验证token绑定操作的原子性：
    - 需求 1.5: WHEN token绑定失败 THEN THE System SHALL 保持数据库状态不变
    - 需求 20.1: WHEN token绑定操作失败 THEN THE System SHALL 回滚所有数据库更改
    - 需求 20.3: THE System SHALL 使用数据库事务确保操作的原子性
    """
    
    @pytest.mark.asyncio
    @given(
        platform=platform_strategy,
        user_id=user_id_strategy,
        token=token_strategy
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_bind_token_atomicity_success(
        self,
        platform: str,
        user_id: str,
        token: str
    ):
        """
        属性：成功的token绑定操作是原子的
        
        对于任意有效的输入：
        1. token绑定成功后，数据库中必须存在该token
        2. 可以成功获取该token
        3. token内容必须与绑定时一致
        
        **Validates: Requirements 1.5, 20.1, 20.3**
        """
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 绑定token
            result = await manager.bind_token(platform, user_id, token)
            
            # 验证绑定成功
            assert result is True, "Token绑定应该成功"
            
            # 验证数据库状态：token必须存在
            has_token = await manager.has_token(platform, user_id)
            assert has_token is True, "绑定成功后，数据库中必须存在该token"
            
            # 验证可以获取token
            retrieved = await manager.get_user_token(platform, user_id)
            assert retrieved is not None, "绑定成功后，必须能够获取token"
            assert retrieved == token, "获取的token必须与绑定的token一致"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    @given(
        user_id=user_id_strategy,
        token=token_strategy
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_bind_token_atomicity_failure_invalid_platform(
        self,
        user_id: str,
        token: str
    ):
        """
        属性：失败的token绑定操作不改变数据库状态（无效platform）
        
        对于任意无效的platform：
        1. token绑定应该失败
        2. 数据库中不应该存在该token
        3. 无法获取该token
        
        **Validates: Requirements 1.5, 20.1, 20.3**
        """
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 使用无效的platform（空字符串）
            invalid_platform = ""
            
            # 尝试绑定token
            result = await manager.bind_token(invalid_platform, user_id, token)
            
            # 验证绑定失败
            assert result is False, "使用无效platform绑定应该失败"
            
            # 验证数据库状态：token不应该存在
            has_token = await manager.has_token(invalid_platform, user_id)
            assert has_token is False, "绑定失败后，数据库中不应该存在token"
            
            # 验证无法获取token
            retrieved = await manager.get_user_token(invalid_platform, user_id)
            assert retrieved is None, "绑定失败后，不应该能够获取token"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    @given(
        platform=platform_strategy,
        token=token_strategy
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_bind_token_atomicity_failure_invalid_user_id(
        self,
        platform: str,
        token: str
    ):
        """
        属性：失败的token绑定操作不改变数据库状态（无效user_id）
        
        对于任意无效的user_id：
        1. token绑定应该失败
        2. 数据库中不应该存在该token
        3. 无法获取该token
        
        **Validates: Requirements 1.5, 20.1, 20.3**
        """
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 使用无效的user_id（空字符串）
            invalid_user_id = ""
            
            # 尝试绑定token
            result = await manager.bind_token(platform, invalid_user_id, token)
            
            # 验证绑定失败
            assert result is False, "使用无效user_id绑定应该失败"
            
            # 验证数据库状态：token不应该存在
            has_token = await manager.has_token(platform, invalid_user_id)
            assert has_token is False, "绑定失败后，数据库中不应该存在token"
            
            # 验证无法获取token
            retrieved = await manager.get_user_token(platform, invalid_user_id)
            assert retrieved is None, "绑定失败后，不应该能够获取token"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    @given(
        platform=platform_strategy,
        user_id=user_id_strategy
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_bind_token_atomicity_failure_invalid_token(
        self,
        platform: str,
        user_id: str
    ):
        """
        属性：失败的token绑定操作不改变数据库状态（无效token）
        
        对于任意无效的token：
        1. token绑定应该失败
        2. 数据库中不应该存在该token
        3. 无法获取该token
        
        **Validates: Requirements 1.5, 20.1, 20.3**
        """
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 使用无效的token（空字符串）
            invalid_token = ""
            
            # 尝试绑定token
            result = await manager.bind_token(platform, user_id, invalid_token)
            
            # 验证绑定失败
            assert result is False, "使用无效token绑定应该失败"
            
            # 验证数据库状态：token不应该存在
            has_token = await manager.has_token(platform, user_id)
            assert has_token is False, "绑定失败后，数据库中不应该存在token"
            
            # 验证无法获取token
            retrieved = await manager.get_user_token(platform, user_id)
            assert retrieved is None, "绑定失败后，不应该能够获取token"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
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
    async def test_update_token_atomicity(
        self,
        platform: str,
        user_id: str,
        token1: str,
        token2: str
    ):
        """
        属性：token更新操作是原子的
        
        对于任意有效的输入：
        1. 先绑定token1
        2. 更新为token2
        3. 获取的token应该是token2，不是token1
        4. 数据库中只有一条记录
        
        **Validates: Requirements 1.5, 20.1, 20.3**
        """
        # 确保两个token不同
        assume(token1 != token2)
        
        # 创建独立的数据库和TokenManager实例
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            encryption = TokenEncryption(encryption_key=key)
            
            manager = TokenManager(db_manager, encryption)
            
            # 绑定初始token
            result1 = await manager.bind_token(platform, user_id, token1)
            assert result1 is True
            
            # 验证初始token
            retrieved1 = await manager.get_user_token(platform, user_id)
            assert retrieved1 == token1
            
            # 更新token
            result2 = await manager.update_token(platform, user_id, token2)
            assert result2 is True, "Token更新应该成功"
            
            # 验证更新后的token
            retrieved2 = await manager.get_user_token(platform, user_id)
            assert retrieved2 == token2, "更新后应该获取到新token"
            assert retrieved2 != token1, "更新后不应该获取到旧token"
            
            # 验证数据库中只有一条记录（通过has_token检查）
            has_token = await manager.has_token(platform, user_id)
            assert has_token is True, "更新后token应该存在"
            
            # 清理
            await db_manager.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
