"""
手动测试check_token指令处理器

这个脚本用于手动验证check_token指令的实现是否正确。
由于测试框架的限制，我们创建一个简单的集成测试来验证功能。
"""

import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

# Mock astrbot module
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.star'] = MagicMock()
sys.modules['astrbot.api.event'] = MagicMock()

from src.plugin import TokenManagementPlugin


class MockContext:
    """模拟AstrBot Context对象"""
    pass


class MockAstrMessageEvent:
    """模拟AstrBot消息事件对象"""
    
    def __init__(self, message_str: str, platform: str = "qq", user_id: str = "test_user"):
        self.message_str = message_str
        self._platform = platform
        self._user_id = user_id
        self._results = []
    
    def get_platform_name(self) -> str:
        return self._platform
    
    def get_sender_id(self) -> str:
        return self._user_id
    
    def plain_result(self, text: str):
        """模拟返回纯文本结果"""
        self._results.append(text)
        return text


async def test_check_token_no_token():
    """测试场景1：用户未绑定token"""
    print("\n=== 测试场景1：用户未绑定token ===")
    
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 创建事件
    event = MockAstrMessageEvent("/check_token", platform="qq", user_id="user1")
    
    # 执行命令
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证结果
    print(f"返回结果数量: {len(results)}")
    print(f"返回内容:\n{results[0]}")
    
    # 检查关键信息
    assert "还没有绑定token" in results[0], "应该提示用户未绑定token"
    assert "/bind_token" in results[0], "应该包含bind_token指令提示"
    
    print("✅ 测试通过：正确提示用户未绑定token")
    
    await plugin.db_manager.close()


async def test_check_token_with_token():
    """测试场景2：用户已绑定token"""
    print("\n=== 测试场景2：用户已绑定token ===")
    
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 先绑定token
    test_token = "sk-test-1234567890abcdef"
    await plugin.token_manager.bind_token("qq", "user2", test_token)
    print(f"已绑定token: {test_token}")
    
    # Mock工具列表
    from unittest.mock import AsyncMock
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["translate", "summarize"])
    
    # 创建事件
    event = MockAstrMessageEvent("/check_token", platform="qq", user_id="user2")
    
    # 执行命令
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证结果
    print(f"返回结果数量: {len(results)}")
    print(f"返回内容:\n{results[0]}")
    
    # 检查关键信息
    assert "Token已绑定" in results[0], "应该显示token已绑定"
    assert "sk-t...cdef" in results[0], "应该显示token的前4位和后4位"
    assert test_token not in results[0], "不应该显示完整token"
    assert "已注册工具: 2 个" in results[0], "应该显示工具数量"
    assert "/list_tools" in results[0], "应该包含list_tools提示"
    assert "/update_token" in results[0], "应该包含update_token提示"
    assert "/unbind_token" in results[0], "应该包含unbind_token提示"
    
    print("✅ 测试通过：正确显示token状态和部分信息")
    
    await plugin.db_manager.close()


async def test_check_token_short_token():
    """测试场景3：短token的显示"""
    print("\n=== 测试场景3：短token的显示 ===")
    
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定短token
    short_token = "short12"
    await plugin.token_manager.bind_token("qq", "user3", short_token)
    print(f"已绑定短token: {short_token}")
    
    # Mock工具列表
    from unittest.mock import AsyncMock
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=[])
    
    # 创建事件
    event = MockAstrMessageEvent("/check_token", platform="qq", user_id="user3")
    
    # 执行命令
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证结果
    print(f"返回结果数量: {len(results)}")
    print(f"返回内容:\n{results[0]}")
    
    # 检查关键信息
    assert "Token已绑定" in results[0], "应该显示token已绑定"
    assert "shor..." in results[0], "应该只显示前4位"
    assert short_token not in results[0], "不应该显示完整token"
    assert "已注册工具: 0 个" in results[0], "应该显示0个工具"
    
    print("✅ 测试通过：正确处理短token")
    
    await plugin.db_manager.close()


async def test_check_token_long_token():
    """测试场景4：长token的显示"""
    print("\n=== 测试场景4：长token的显示 ===")
    
    # 创建插件实例
    context = MockContext()
    plugin = TokenManagementPlugin(context)
    await plugin.db_manager.initialize()
    
    # 绑定长token
    long_token = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
    await plugin.token_manager.bind_token("qq", "user4", long_token)
    print(f"已绑定长token: {long_token}")
    
    # Mock工具列表
    from unittest.mock import AsyncMock
    plugin.tool_registry.list_user_tools = AsyncMock(return_value=["tool1", "tool2", "tool3"])
    
    # 创建事件
    event = MockAstrMessageEvent("/check_token", platform="qq", user_id="user4")
    
    # 执行命令
    results = []
    async for result in plugin.check_token_command(event):
        results.append(result)
    
    # 验证结果
    print(f"返回结果数量: {len(results)}")
    print(f"返回内容:\n{results[0]}")
    
    # 检查关键信息
    assert "Token已绑定" in results[0], "应该显示token已绑定"
    assert "sk-p...wxyz" in results[0], "应该显示前4位和后4位"
    assert "1234567890abcdefghijklmnopqrstuvwxyz" not in results[0], "不应该显示中间部分"
    assert "已注册工具: 3 个" in results[0], "应该显示3个工具"
    
    print("✅ 测试通过：正确处理长token")
    
    await plugin.db_manager.close()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试check_token指令处理器")
    print("=" * 60)
    
    try:
        await test_check_token_no_token()
        await test_check_token_with_token()
        await test_check_token_short_token()
        await test_check_token_long_token()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        # 清理测试数据库
        test_db = Path("./data/user_tokens.db")
        if test_db.exists():
            test_db.unlink()
            print("\n已清理测试数据库")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
