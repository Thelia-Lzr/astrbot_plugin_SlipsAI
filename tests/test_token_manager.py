"""
TokenManager单元测试

测试TokenManager类的核心功能，包括：
- token绑定流程（加密+存储）
- token获取流程（查询+解密）
- token更新和删除
- 用户不存在的情况
- 输入参数验证

验证需求：
- 需求 1（Token绑定管理）
- 需求 3（Token更新）
- 需求 4（Token解绑）
"""

import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
from src.token_management.token_manager import TokenManager
from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption


@pytest_asyncio.fixture
async def db_manager():
    """创建临时数据库管理器"""
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


@pytest.fixture
def sync_token_manager(encryption):
    """创建同步TokenManager实例（用于验证测试）"""
    # 创建一个临时数据库管理器（不初始化）
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name
    
    db_manager = DatabaseManager(db_path)
    manager = TokenManager(db_manager, encryption)
    
    yield manager
    
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def token_manager(db_manager, encryption):
    """创建TokenManager实例"""
    return TokenManager(db_manager, encryption)


class TestTokenManagerInit:
    """测试TokenManager初始化"""
    
    @pytest.mark.asyncio
    async def test_init_success(self, db_manager, encryption):
        """测试成功初始化"""
        manager = TokenManager(db_manager, encryption)
        assert manager.db_manager == db_manager
        assert manager.encryption == encryption


class TestTokenManagerValidation:
    """测试输入参数验证"""
    
    def test_validate_platform_empty(self, sync_token_manager):
        """测试空platform验证"""
        assert not sync_token_manager._validate_platform("")
        assert not sync_token_manager._validate_platform(None)
    
    def test_validate_platform_too_long(self, sync_token_manager):
        """测试platform长度超过50字符"""
        long_platform = "a" * 51
        assert not sync_token_manager._validate_platform(long_platform)
    
    def test_validate_platform_valid(self, sync_token_manager):
        """测试有效的platform"""
        assert sync_token_manager._validate_platform("qq")
        assert sync_token_manager._validate_platform("telegram")
        assert sync_token_manager._validate_platform("a" * 50)  # 边界值
    
    def test_validate_user_id_empty(self, sync_token_manager):
        """测试空user_id验证"""
        assert not sync_token_manager._validate_user_id("")
        assert not sync_token_manager._validate_user_id(None)
    
    def test_validate_user_id_too_long(self, sync_token_manager):
        """测试user_id长度超过100字符"""
        long_user_id = "a" * 101
        assert not sync_token_manager._validate_user_id(long_user_id)
    
    def test_validate_user_id_valid(self, sync_token_manager):
        """测试有效的user_id"""
        assert sync_token_manager._validate_user_id("123456")
        assert sync_token_manager._validate_user_id("user_abc")
        assert sync_token_manager._validate_user_id("a" * 100)  # 边界值
    
    def test_validate_token_empty(self, sync_token_manager):
        """测试空token验证"""
        assert not sync_token_manager._validate_token("")
        assert not sync_token_manager._validate_token(None)
    
    def test_validate_token_valid(self, sync_token_manager):
        """测试有效的token"""
        assert sync_token_manager._validate_token("sk-abc123")
        assert sync_token_manager._validate_token("token_xyz")


class TestTokenManagerBindToken:
    """测试token绑定功能"""
    
    @pytest.mark.asyncio
    async def test_bind_token_success(self, token_manager):
        """测试成功绑定token
        
        验证需求 1.1: 加密token并存储到数据库中
        """
        platform = "qq"
        user_id = "123456"
        token = "sk-test-token-123"
        
        # 绑定token
        result = await token_manager.bind_token(platform, user_id, token)
        assert result is True
        
        # 验证token已存储
        has_token = await token_manager.has_token(platform, user_id)
        assert has_token is True
    
    @pytest.mark.asyncio
    async def test_bind_token_update_existing(self, token_manager):
        """测试更新已存在的token
        
        验证需求 1.4: 用户已有token并再次绑定时更新现有token记录
        """
        platform = "qq"
        user_id = "123456"
        old_token = "sk-old-token"
        new_token = "sk-new-token"
        
        # 首次绑定
        result1 = await token_manager.bind_token(platform, user_id, old_token)
        assert result1 is True
        
        # 再次绑定（更新）
        result2 = await token_manager.bind_token(platform, user_id, new_token)
        assert result2 is True
        
        # 验证token已更新
        retrieved_token = await token_manager.get_user_token(platform, user_id)
        assert retrieved_token == new_token
    
    @pytest.mark.asyncio
    async def test_bind_token_invalid_platform(self, token_manager):
        """测试无效的platform参数"""
        result = await token_manager.bind_token("", "123456", "sk-token")
        assert result is False
        
        result = await token_manager.bind_token("a" * 51, "123456", "sk-token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_bind_token_invalid_user_id(self, token_manager):
        """测试无效的user_id参数"""
        result = await token_manager.bind_token("qq", "", "sk-token")
        assert result is False
        
        result = await token_manager.bind_token("qq", "a" * 101, "sk-token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_bind_token_invalid_token(self, token_manager):
        """测试无效的token参数"""
        result = await token_manager.bind_token("qq", "123456", "")
        assert result is False


class TestTokenManagerGetUserToken:
    """测试token获取功能"""
    
    @pytest.mark.asyncio
    async def test_get_user_token_success(self, token_manager):
        """测试成功获取token
        
        验证需求 2.1: 返回用户是否已绑定token的信息
        """
        platform = "qq"
        user_id = "123456"
        token = "sk-test-token-123"
        
        # 先绑定token
        await token_manager.bind_token(platform, user_id, token)
        
        # 获取token
        retrieved_token = await token_manager.get_user_token(platform, user_id)
        assert retrieved_token == token
    
    @pytest.mark.asyncio
    async def test_get_user_token_not_found(self, token_manager):
        """测试获取不存在的token"""
        platform = "qq"
        user_id = "999999"
        
        # 获取不存在的token
        retrieved_token = await token_manager.get_user_token(platform, user_id)
        assert retrieved_token is None
    
    @pytest.mark.asyncio
    async def test_get_user_token_invalid_platform(self, token_manager):
        """测试无效的platform参数"""
        result = await token_manager.get_user_token("", "123456")
        assert result is None
        
        result = await token_manager.get_user_token("a" * 51, "123456")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_token_invalid_user_id(self, token_manager):
        """测试无效的user_id参数"""
        result = await token_manager.get_user_token("qq", "")
        assert result is None
        
        result = await token_manager.get_user_token("qq", "a" * 101)
        assert result is None


class TestTokenManagerUpdateToken:
    """测试token更新功能"""
    
    @pytest.mark.asyncio
    async def test_update_token_success(self, token_manager):
        """测试成功更新token
        
        验证需求 3.2: 更新数据库中的加密token
        """
        platform = "qq"
        user_id = "123456"
        old_token = "sk-old-token"
        new_token = "sk-new-token"
        
        # 先绑定旧token
        await token_manager.bind_token(platform, user_id, old_token)
        
        # 更新token
        result = await token_manager.update_token(platform, user_id, new_token)
        assert result is True
        
        # 验证token已更新
        retrieved_token = await token_manager.get_user_token(platform, user_id)
        assert retrieved_token == new_token
    
    @pytest.mark.asyncio
    async def test_update_token_not_exists(self, token_manager):
        """测试更新不存在的token（实际上会创建新记录）"""
        platform = "qq"
        user_id = "999999"
        new_token = "sk-new-token"
        
        # 更新不存在的token
        result = await token_manager.update_token(platform, user_id, new_token)
        assert result is True
        
        # 验证token已创建
        retrieved_token = await token_manager.get_user_token(platform, user_id)
        assert retrieved_token == new_token
    
    @pytest.mark.asyncio
    async def test_update_token_invalid_platform(self, token_manager):
        """测试无效的platform参数"""
        result = await token_manager.update_token("", "123456", "sk-token")
        assert result is False
        
        result = await token_manager.update_token("a" * 51, "123456", "sk-token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_token_invalid_user_id(self, token_manager):
        """测试无效的user_id参数"""
        result = await token_manager.update_token("qq", "", "sk-token")
        assert result is False
        
        result = await token_manager.update_token("qq", "a" * 101, "sk-token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_token_invalid_token(self, token_manager):
        """测试无效的token参数"""
        result = await token_manager.update_token("qq", "123456", "")
        assert result is False


class TestTokenManagerUnbindToken:
    """测试token解绑功能"""
    
    @pytest.mark.asyncio
    async def test_unbind_token_success(self, token_manager):
        """测试成功解绑token
        
        验证需求 4.2: 从数据库中删除该用户的token记录
        """
        platform = "qq"
        user_id = "123456"
        token = "sk-test-token"
        
        # 先绑定token
        await token_manager.bind_token(platform, user_id, token)
        
        # 解绑token
        result = await token_manager.unbind_token(platform, user_id)
        assert result is True
        
        # 验证token已删除
        has_token = await token_manager.has_token(platform, user_id)
        assert has_token is False
    
    @pytest.mark.asyncio
    async def test_unbind_token_not_exists(self, token_manager):
        """测试解绑不存在的token"""
        platform = "qq"
        user_id = "999999"
        
        # 解绑不存在的token
        result = await token_manager.unbind_token(platform, user_id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_unbind_token_invalid_platform(self, token_manager):
        """测试无效的platform参数"""
        result = await token_manager.unbind_token("", "123456")
        assert result is False
        
        result = await token_manager.unbind_token("a" * 51, "123456")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_unbind_token_invalid_user_id(self, token_manager):
        """测试无效的user_id参数"""
        result = await token_manager.unbind_token("qq", "")
        assert result is False
        
        result = await token_manager.unbind_token("qq", "a" * 101)
        assert result is False


class TestTokenManagerHasToken:
    """测试token检查功能"""
    
    @pytest.mark.asyncio
    async def test_has_token_true(self, token_manager):
        """测试用户已绑定token的情况
        
        验证需求 2.1: 返回用户是否已绑定token的信息
        """
        platform = "qq"
        user_id = "123456"
        token = "sk-test-token"
        
        # 先绑定token
        await token_manager.bind_token(platform, user_id, token)
        
        # 检查token
        has_token = await token_manager.has_token(platform, user_id)
        assert has_token is True
    
    @pytest.mark.asyncio
    async def test_has_token_false(self, token_manager):
        """测试用户未绑定token的情况"""
        platform = "qq"
        user_id = "999999"
        
        # 检查不存在的token
        has_token = await token_manager.has_token(platform, user_id)
        assert has_token is False
    
    @pytest.mark.asyncio
    async def test_has_token_invalid_platform(self, token_manager):
        """测试无效的platform参数"""
        result = await token_manager.has_token("", "123456")
        assert result is False
        
        result = await token_manager.has_token("a" * 51, "123456")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_has_token_invalid_user_id(self, token_manager):
        """测试无效的user_id参数"""
        result = await token_manager.has_token("qq", "")
        assert result is False
        
        result = await token_manager.has_token("qq", "a" * 101)
        assert result is False


class TestTokenManagerMultipleUsers:
    """测试多用户场景"""
    
    @pytest.mark.asyncio
    async def test_multiple_users_different_platforms(self, token_manager):
        """测试不同平台的用户"""
        # 绑定多个用户的token
        await token_manager.bind_token("qq", "user1", "token1")
        await token_manager.bind_token("telegram", "user2", "token2")
        await token_manager.bind_token("discord", "user3", "token3")
        
        # 验证每个用户的token
        token1 = await token_manager.get_user_token("qq", "user1")
        token2 = await token_manager.get_user_token("telegram", "user2")
        token3 = await token_manager.get_user_token("discord", "user3")
        
        assert token1 == "token1"
        assert token2 == "token2"
        assert token3 == "token3"
    
    @pytest.mark.asyncio
    async def test_multiple_users_same_platform(self, token_manager):
        """测试同一平台的多个用户"""
        # 绑定同一平台的多个用户
        await token_manager.bind_token("qq", "user1", "token1")
        await token_manager.bind_token("qq", "user2", "token2")
        await token_manager.bind_token("qq", "user3", "token3")
        
        # 验证每个用户的token
        token1 = await token_manager.get_user_token("qq", "user1")
        token2 = await token_manager.get_user_token("qq", "user2")
        token3 = await token_manager.get_user_token("qq", "user3")
        
        assert token1 == "token1"
        assert token2 == "token2"
        assert token3 == "token3"
    
    @pytest.mark.asyncio
    async def test_user_isolation(self, token_manager):
        """测试用户隔离性：删除一个用户的token不影响其他用户"""
        # 绑定多个用户
        await token_manager.bind_token("qq", "user1", "token1")
        await token_manager.bind_token("qq", "user2", "token2")
        
        # 删除user1的token
        await token_manager.unbind_token("qq", "user1")
        
        # 验证user1的token已删除
        has_token1 = await token_manager.has_token("qq", "user1")
        assert has_token1 is False
        
        # 验证user2的token仍然存在
        has_token2 = await token_manager.has_token("qq", "user2")
        assert has_token2 is True
        
        token2 = await token_manager.get_user_token("qq", "user2")
        assert token2 == "token2"
