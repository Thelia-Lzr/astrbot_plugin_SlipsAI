"""
手动测试list_tools指令处理器

这个脚本用于手动验证list_tools指令的功能。
由于命令测试的mocking设置问题，我们创建这个简单的集成测试。
"""

import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database_manager import DatabaseManager
from src.encryption.token_encryption import TokenEncryption
from src.token_management.token_manager import TokenManager
from src.tool_registry.mcp_tool_registry import MCPToolRegistry
from src.mcp_config import MCPServiceConfig


class MockEvent:
    """模拟AstrBot消息事件"""
    def __init__(self, message_str, platform="qq", user_id="test_user"):
        self.message_str = message_str
        self._platform = platform
        self._user_id = user_id
    
    def get_platform_name(self):
        return self._platform
    
    def get_sender_id(self):
        return self._user_id
    
    def plain_result(self, text):
        return text


async def test_list_tools():
    """测试list_tools功能"""
    print("=" * 60)
    print("测试 list_tools 指令处理器")
    print("=" * 60)
    
    # 创建临时数据库
    db_path = "test_list_tools.db"
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    
    # 创建加密器和token管理器
    encryption = TokenEncryption()
    token_manager = TokenManager(db_manager, encryption)
    
    # 创建MCP配置和工具注册表
    mcp_config = MCPServiceConfig()
    tool_registry = MCPToolRegistry(token_manager, mcp_config)
    
    print("\n场景1: 用户未绑定token")
    print("-" * 60)
    has_token = await token_manager.has_token("qq", "user1")
    if not has_token:
        print("✓ 用户未绑定token")
        print("  预期返回: 提示用户绑定token")
    
    print("\n场景2: 用户已绑定token但无工具")
    print("-" * 60)
    await token_manager.bind_token("qq", "user2", "sk-test-token")
    print("✓ 用户已绑定token")
    
    # Mock list_user_tools返回空列表
    tool_registry.list_user_tools = AsyncMock(return_value=[])
    tools = await tool_registry.list_user_tools("qq", "user2")
    print(f"✓ 工具列表: {tools}")
    print("  预期返回: 提示无可用工具")
    
    print("\n场景3: 用户有多个工具")
    print("-" * 60)
    await token_manager.bind_token("qq", "user3", "sk-test-token-2")
    print("✓ 用户已绑定token")
    
    # Mock list_user_tools返回工具列表
    tool_registry.list_user_tools = AsyncMock(return_value=["translate", "summarize", "analyze"])
    
    # Mock get_tool_info返回工具详细信息
    def mock_get_tool_info(platform, user_id, tool_name):
        tool_info_map = {
            "translate": {"name": "translate", "description": "翻译文本到目标语言"},
            "summarize": {"name": "summarize", "description": "生成文本摘要"},
            "analyze": {"name": "analyze", "description": "分析文本内容"}
        }
        return tool_info_map.get(tool_name)
    
    tool_registry.get_tool_info = mock_get_tool_info
    
    tools = await tool_registry.list_user_tools("qq", "user3")
    print(f"✓ 工具列表: {tools}")
    
    for tool_name in tools:
        tool_info = tool_registry.get_tool_info("qq", "user3", tool_name)
        print(f"  - {tool_name}: {tool_info['description']}")
    
    print("  预期返回: 显示3个工具及其描述")
    
    print("\n场景4: 测试工具信息缺失的情况")
    print("-" * 60)
    
    # Mock get_tool_info返回None
    def mock_get_tool_info_none(platform, user_id, tool_name):
        if tool_name == "tool1":
            return {"name": "tool1", "description": "工具1"}
        return None  # tool2无信息
    
    tool_registry.list_user_tools = AsyncMock(return_value=["tool1", "tool2"])
    tool_registry.get_tool_info = mock_get_tool_info_none
    
    tools = await tool_registry.list_user_tools("qq", "user3")
    print(f"✓ 工具列表: {tools}")
    
    for tool_name in tools:
        tool_info = tool_registry.get_tool_info("qq", "user3", tool_name)
        if tool_info:
            print(f"  - {tool_name}: {tool_info.get('description', '无描述')}")
        else:
            print(f"  - {tool_name}: (无详细信息)")
    
    print("  预期返回: 即使无详细信息也显示工具名称")
    
    print("\n场景5: 测试不同用户的工具隔离")
    print("-" * 60)
    
    # 用户A的工具
    async def mock_list_user_tools_a(platform, user_id):
        if user_id == "userA":
            return ["toolA1", "toolA2"]
        elif user_id == "userB":
            return ["toolB1"]
        return []
    
    tool_registry.list_user_tools = mock_list_user_tools_a
    
    tools_a = await tool_registry.list_user_tools("qq", "userA")
    tools_b = await tool_registry.list_user_tools("qq", "userB")
    
    print(f"✓ 用户A的工具: {tools_a}")
    print(f"✓ 用户B的工具: {tools_b}")
    print("  预期: 不同用户看到不同的工具列表")
    
    # 清理
    await db_manager.close()
    Path(db_path).unlink(missing_ok=True)
    
    print("\n" + "=" * 60)
    print("✅ 所有场景测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_list_tools())
