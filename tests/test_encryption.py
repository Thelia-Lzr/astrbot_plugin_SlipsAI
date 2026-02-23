"""
TokenEncryption模块的单元测试

测试token加密和解密功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

from src.encryption import TokenEncryption


class TestTokenEncryption:
    """TokenEncryption类的单元测试"""
    
    def test_init_with_provided_key(self):
        """测试使用提供的密钥初始化"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        assert encryption.get_key() == key
    
    def test_init_generates_key_if_not_exists(self):
        """测试如果密钥文件不存在则生成新密钥"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.key")
            
            # 密钥文件不存在
            assert not os.path.exists(key_file)
            
            # 初始化应该生成新密钥
            encryption = TokenEncryption(key_file_path=key_file)
            
            # 验证密钥文件已创建
            assert os.path.exists(key_file)
            
            # 验证密钥不为空
            assert len(encryption.get_key()) > 0
    
    def test_init_loads_existing_key(self):
        """测试如果密钥文件存在则加载现有密钥"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.key")
            
            # 创建密钥文件
            original_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(original_key)
            
            # 初始化应该加载现有密钥
            encryption = TokenEncryption(key_file_path=key_file)
            
            # 验证加载的密钥与原始密钥相同
            assert encryption.get_key() == original_key
    
    def test_encrypt_decrypt_roundtrip(self):
        """测试加密后解密能得到原始token"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        original_token = "sk-test-token-123456"
        
        # 加密
        encrypted = encryption.encrypt(original_token)
        
        # 验证加密后的token不同于原始token
        assert encrypted != original_token
        
        # 解密
        decrypted = encryption.decrypt(encrypted)
        
        # 验证解密后的token与原始token相同
        assert decrypted == original_token
    
    def test_encrypt_empty_token_raises_error(self):
        """测试加密空token应该抛出异常"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        with pytest.raises(ValueError, match="Token不能为空"):
            encryption.encrypt("")
    
    def test_decrypt_empty_token_raises_error(self):
        """测试解密空token应该抛出异常"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        with pytest.raises(ValueError, match="加密token不能为空"):
            encryption.decrypt("")
    
    def test_decrypt_invalid_token_raises_error(self):
        """测试解密无效token应该抛出异常"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        with pytest.raises(InvalidToken):
            encryption.decrypt("invalid_encrypted_token")
    
    def test_encrypt_produces_different_outputs(self):
        """测试相同输入加密产生不同输出（包含随机IV）"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        token = "sk-test-token"
        
        encrypted1 = encryption.encrypt(token)
        encrypted2 = encryption.encrypt(token)
        
        # 由于包含随机IV，两次加密结果应该不同
        assert encrypted1 != encrypted2
        
        # 但都能正确解密
        assert encryption.decrypt(encrypted1) == token
        assert encryption.decrypt(encrypted2) == token
    
    def test_encrypt_special_characters(self):
        """测试加密包含特殊字符的token"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        special_token = "sk-test!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        
        encrypted = encryption.encrypt(special_token)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == special_token
    
    def test_encrypt_unicode_characters(self):
        """测试加密包含Unicode字符的token"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        unicode_token = "sk-测试-token-🔐"
        
        encrypted = encryption.encrypt(unicode_token)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == unicode_token
    
    def test_key_file_permissions(self):
        """测试密钥文件权限设置为600"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "test_key.key")
            
            # 初始化（生成新密钥）
            encryption = TokenEncryption(key_file_path=key_file)
            
            # 验证文件存在
            assert os.path.exists(key_file)
            
            # 验证文件权限（仅在Unix系统上）
            if os.name != 'nt':  # 不是Windows
                file_stat = os.stat(key_file)
                file_mode = file_stat.st_mode & 0o777
                
                # 权限应该是600（所有者读写）
                assert file_mode == 0o600
    
    def test_decrypt_with_wrong_key_fails(self):
        """测试使用错误的密钥解密应该失败"""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        
        encryption1 = TokenEncryption(encryption_key=key1)
        encryption2 = TokenEncryption(encryption_key=key2)
        
        token = "sk-test-token"
        
        # 使用key1加密
        encrypted = encryption1.encrypt(token)
        
        # 使用key2解密应该失败
        with pytest.raises(InvalidToken):
            encryption2.decrypt(encrypted)
    
    def test_long_token_encryption(self):
        """测试加密长token"""
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # 生成一个很长的token
        long_token = "sk-" + "a" * 1000
        
        encrypted = encryption.encrypt(long_token)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == long_token


# ============================================
# 属性测试 (Property-Based Tests)
# ============================================

from hypothesis import given, strategies as st, assume


class TestTokenEncryptionProperties:
    """TokenEncryption的属性测试
    
    使用hypothesis进行基于属性的测试，验证加密功能的正确性属性。
    """
    
    @given(st.text(min_size=1))
    def test_property_encryption_reversibility(self, token: str):
        """
        **属性 2: 加密可逆性**
        **Validates: Requirements 5.1**
        
        对于任意token字符串，加密后解密必须得到原始token。
        
        这个属性验证了加密和解密操作的正确性：
        - 对于任何非空字符串token
        - encrypt(token)后再decrypt()
        - 必须得到原始的token
        
        Args:
            token: hypothesis生成的随机字符串
        """
        # 跳过空字符串（已在单元测试中测试）
        assume(len(token.strip()) > 0)
        
        # 初始化加密器
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # 加密
        encrypted = encryption.encrypt(token)
        
        # 验证加密后的结果不同于原始token（除非是特殊情况）
        # 注意：由于base64编码，加密结果总是不同的
        assert encrypted != token
        
        # 解密
        decrypted = encryption.decrypt(encrypted)
        
        # 验证解密后得到原始token
        assert decrypted == token, \
            f"加密可逆性失败: 原始='{token}', 解密后='{decrypted}'"
    
    @given(st.text(min_size=0, max_size=0))
    def test_property_empty_string_encryption(self, token: str):
        """
        测试空字符串加密
        
        验证空字符串加密应该抛出ValueError异常。
        
        Args:
            token: 空字符串
        """
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        with pytest.raises(ValueError, match="Token不能为空"):
            encryption.encrypt(token)
    
    @given(st.text(
        alphabet=st.characters(
            blacklist_categories=('Cs',),  # 排除代理字符
            blacklist_characters='\x00'     # 排除null字符
        ),
        min_size=1,
        max_size=1000
    ))
    def test_property_special_characters_encryption(self, token: str):
        """
        测试特殊字符的加密
        
        验证包含各种特殊字符（Unicode、标点符号等）的token
        都能正确加密和解密。
        
        Args:
            token: hypothesis生成的包含特殊字符的随机字符串
        """
        # 跳过空白字符串
        assume(len(token.strip()) > 0)
        
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # 加密和解密
        encrypted = encryption.encrypt(token)
        decrypted = encryption.decrypt(encrypted)
        
        # 验证可逆性
        assert decrypted == token, \
            f"特殊字符加密失败: 原始='{token}', 解密后='{decrypted}'"
    
    @given(
        st.text(min_size=1, max_size=100),
        st.integers(min_value=2, max_value=10)
    )
    def test_property_multiple_encrypt_decrypt_cycles(self, token: str, cycles: int):
        """
        测试多次加密解密循环
        
        验证对同一token进行多次加密-解密循环后，
        仍然能得到原始token。
        
        Args:
            token: 原始token字符串
            cycles: 加密解密循环次数
        """
        assume(len(token.strip()) > 0)
        
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        current = token
        
        # 进行多次加密-解密循环
        for _ in range(cycles):
            encrypted = encryption.encrypt(current)
            current = encryption.decrypt(encrypted)
        
        # 验证最终结果与原始token相同
        assert current == token, \
            f"多次循环后加密可逆性失败: 原始='{token}', 最终='{current}'"
    
    @given(st.text(min_size=1, max_size=100))
    def test_property_encryption_produces_different_outputs(self, token: str):
        """
        测试加密的随机性
        
        验证对同一token进行多次加密，由于包含随机IV，
        应该产生不同的加密结果，但都能正确解密。
        
        Args:
            token: 原始token字符串
        """
        assume(len(token.strip()) > 0)
        
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # 加密两次
        encrypted1 = encryption.encrypt(token)
        encrypted2 = encryption.encrypt(token)
        
        # 验证两次加密结果不同（由于随机IV）
        assert encrypted1 != encrypted2, \
            "相同输入的两次加密应该产生不同结果"
        
        # 验证都能正确解密
        decrypted1 = encryption.decrypt(encrypted1)
        decrypted2 = encryption.decrypt(encrypted2)
        
        assert decrypted1 == token
        assert decrypted2 == token
    
    @given(st.text(min_size=1, max_size=5000))
    def test_property_long_token_encryption(self, token: str):
        """
        测试长token的加密
        
        验证即使是很长的token字符串，也能正确加密和解密。
        
        Args:
            token: hypothesis生成的长字符串（最多5000字符）
        """
        assume(len(token.strip()) > 0)
        
        key = Fernet.generate_key()
        encryption = TokenEncryption(encryption_key=key)
        
        # 加密和解密
        encrypted = encryption.encrypt(token)
        decrypted = encryption.decrypt(encrypted)
        
        # 验证可逆性
        assert decrypted == token, \
            f"长token加密失败: 长度={len(token)}"
        
        # 验证加密后的长度合理（应该比原始长度长）
        assert len(encrypted) > len(token), \
            "加密后的长度应该大于原始长度"
