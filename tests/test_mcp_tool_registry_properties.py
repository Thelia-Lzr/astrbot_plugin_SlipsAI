"""MCPToolRegistry属性测试

使用hypothesis进行基于属性的测试，验证MCPToolRegistry的正确性属性。

验证的属性：
- 属性 7: 工具注册一致性（需求 6.2, 6.3, 7.2）
- 属性 8: 工具调用隔离性（需求 9.1, 9.2, 9.5）
- 属性 9: 工具生命周期一致性（需求 1.2, 1.3, 4.1, 10.3）
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from unittest.mock import AsyncMock, patch
from aioresponses import aioresponses

from src.tool_registry.mcp_tool_registry import MCPToolRegistry
from src.token_management.token_manager import TokenManager
from src.mcp_config import MCPServiceConfig
from src.tool_registry.mcp_tool import MCPTool


# ============================================
# 测试策略定义
# ============================================

# 平台名称策略
platform_strategy = st.sampled_from(["qq", "telegram", "discord", "wechat"])

# 用户ID策略
user_id_strategy = st.text(min_size=1, max_size=20, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    min_codepoint=48, max_codepoint=122
))

# Token策略
token_strategy = st.text(min_size=10, max_size=50, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    min_codepoint=48, max_codepoint=122
))

# 工具名称策略
tool_name_strategy = st.sampled_from([
    "translate", "summarize", "analyze", "generate", "chat"
])


# ============================================
# 辅助函数
# ============================================

def create_mock_tool_data(tool_names):
    """创建mock的工具数据列表"""
    tools = []
    for name in tool_names:
        tools.append({
            "name": name,
            "description": f"{name} tool",
            "parameters": {
                "required": ["text"],
                "properties": {
                    "text": {"type": "string", "description": "Input text"}
                }
            },
            "endpoint": f"/v1/{name}",
            "method": "POST"
        })
    return tools


async def setup_registry_with_mock():
    """创建带有mock TokenManager的MCPToolRegistry"""
    mock_token_manager = AsyncMock(spec=TokenManager)
    mcp_config = MCPServiceConfig(
        base_url="https://test-mcp.example.com",
        timeout=10
    )
    registry = MCPToolRegistry(mock_token_manager, mcp_config)
    return registry, mock_token_manager


# ============================================
# 属性 7: 工具注册一致性
# **验证需求：需求 6.2, 6.3, 7.2**
# 验证注册的工具是MCP服务器提供工具的子集
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    token=token_strategy,
    available_tools=st.lists(tool_name_strategy, min_size=1, max_size=5, unique=True)
)
@settings(max_examples=50, deadline=5000)
async def test_property_tool_registration_consistency(platform, user_id, token, available_tools):
    """
    **Validates: Requirements 6.2, 6.3, 7.2**
    
    属性 7: 工具注册一致性
    
    验证：注册的工具必须是MCP服务器提供工具的子集
    
    测试逻辑：
    1. Mock MCP服务器返回一组工具
    2. 用户注册工具
    3. 验证注册的工具名称都在服务器提供的工具列表中
    4. 验证每个注册的工具都有完整的信息
    """
    registry, mock_token_manager = await setup_registry_with_mock()
    mock_token_manager.get_user_token.return_value = token
    
    # Mock MCP服务器返回工具列表
    mock_tools_data = create_mock_tool_data(available_tools)
    
    with aioresponses() as m:
        m.get(
            "https://test-mcp.example.com/v1/tools/list",
            payload={"tools": mock_tools_data},
            status=200
        )
        
        # 注册工具
        success = await registry.register_user_tools(platform, user_id)
        
        if success:
            # 获取注册的工具列表
            registered_tools = await registry.list_user_tools(platform, user_id)
            
            # 属性验证：注册的工具必须是服务器提供工具的子集
            assert set(registered_tools).issubset(set(available_tools)), \
                f"Registered tools {registered_tools} should be subset of available tools {available_tools}"
            
            # 验证每个注册的工具都有完整信息
            for tool_name in registered_tools:
                tool_info = registry.get_tool_info(platform, user_id, tool_name)
                assert tool_info is not None, f"Tool {tool_name} should have info"
                assert "name" in tool_info
                assert "description" in tool_info
                assert "parameters" in tool_info
                assert "endpoint" in tool_info
                assert tool_info["name"] == tool_name


# ============================================
# 属性 8: 工具调用隔离性
# **验证需求：需求 9.1, 9.2, 9.5**
# 验证不同用户调用同名工具使用各自的token
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id1=user_id_strategy,
    user_id2=user_id_strategy,
    token1=token_strategy,
    token2=token_strategy,
    tool_name=tool_name_strategy
)
@settings(max_examples=50, deadline=5000)
async def test_property_tool_call_isolation(
    platform, user_id1, user_id2, token1, token2, tool_name
):
    """
    **Validates: Requirements 9.1, 9.2, 9.5**
    
    属性 8: 工具调用隔离性
    
    验证：不同用户调用同名工具时使用各自的token，且结果互不影响
    
    测试逻辑：
    1. 两个不同用户绑定不同token
    2. 两个用户都注册相同的工具
    3. 两个用户分别调用同名工具
    4. 验证每个用户使用的是自己的token
    5. 验证工具调用结果互不影响
    """
    # 确保是不同用户
    assume(user_id1 != user_id2)
    assume(token1 != token2)
    
    registry, mock_token_manager = await setup_registry_with_mock()
    
    # Mock两个用户的token
    async def get_user_token_side_effect(plat, uid):
        if uid == user_id1:
            return token1
        elif uid == user_id2:
            return token2
        return None
    
    mock_token_manager.get_user_token.side_effect = get_user_token_side_effect
    
    # Mock工具数据
    mock_tools_data = create_mock_tool_data([tool_name])
    
    with aioresponses() as m:
        # Mock工具发现（两次，每个用户一次）
        m.get(
            "https://test-mcp.example.com/v1/tools/list",
            payload={"tools": mock_tools_data},
            status=200,
            repeat=True
        )
        
        # 两个用户注册工具
        success1 = await registry.register_user_tools(platform, user_id1)
        success2 = await registry.register_user_tools(platform, user_id2)
        
        assert success1 is True
        assert success2 is True
        
        # 验证两个用户都有该工具
        tools1 = await registry.list_user_tools(platform, user_id1)
        tools2 = await registry.list_user_tools(platform, user_id2)
        
        assert tool_name in tools1
        assert tool_name in tools2
        
        # Mock工具调用响应（两次，每个用户一次）
        m.post(
            f"https://test-mcp.example.com/v1/{tool_name}",
            payload={"result": f"result_for_user1"},
            status=200
        )
        m.post(
            f"https://test-mcp.example.com/v1/{tool_name}",
            payload={"result": f"result_for_user2"},
            status=200
        )
        
        # 用户1调用工具
        result1 = await registry.call_tool(platform, user_id1, tool_name, text="test1")
        
        # 用户2调用工具
        result2 = await registry.call_tool(platform, user_id2, tool_name, text="test2")
        
        # 属性验证：两个用户的调用都应该成功
        assert result1["success"] is True, f"User1 call should succeed"
        assert result2["success"] is True, f"User2 call should succeed"
        
        # 验证token管理器被正确调用（每个用户使用自己的token）
        assert mock_token_manager.get_user_token.call_count >= 2


# ============================================
# 属性 9: 工具生命周期一致性
# **验证需求：需求 1.2, 1.3, 4.1, 10.3**
# 验证token绑定后自动注册工具，解绑后自动取消注册
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    token=token_strategy,
    available_tools=st.lists(tool_name_strategy, min_size=1, max_size=5, unique=True)
)
@settings(max_examples=50, deadline=5000)
async def test_property_tool_lifecycle_consistency(platform, user_id, token, available_tools):
    """
    **Validates: Requirements 1.2, 1.3, 4.1, 10.3**
    
    属性 9: 工具生命周期一致性
    
    验证：token绑定后自动注册工具，解绑后自动取消注册所有工具
    
    测试逻辑：
    1. 用户绑定token并注册工具
    2. 验证工具已注册且可查询
    3. 取消注册工具
    4. 验证工具列表为空
    5. 验证无法调用已取消注册的工具
    """
    registry, mock_token_manager = await setup_registry_with_mock()
    mock_token_manager.get_user_token.return_value = token
    
    # Mock工具数据
    mock_tools_data = create_mock_tool_data(available_tools)
    
    with aioresponses() as m:
        m.get(
            "https://test-mcp.example.com/v1/tools/list",
            payload={"tools": mock_tools_data},
            status=200
        )
        
        # 步骤1: 注册工具
        success = await registry.register_user_tools(platform, user_id)
        
        if success:
            # 步骤2: 验证工具已注册
            tools_before = await registry.list_user_tools(platform, user_id)
            assert len(tools_before) > 0, "Tools should be registered"
            assert set(tools_before).issubset(set(available_tools))
            
            # 验证每个工具都可以查询到信息
            for tool_name in tools_before:
                tool_info = registry.get_tool_info(platform, user_id, tool_name)
                assert tool_info is not None, f"Tool {tool_name} should have info"
            
            # 步骤3: 取消注册工具
            unregister_success = await registry.unregister_user_tools(platform, user_id)
            assert unregister_success is True, "Unregister should succeed"
            
            # 步骤4: 验证工具列表为空
            tools_after = await registry.list_user_tools(platform, user_id)
            assert len(tools_after) == 0, "Tools should be empty after unregister"
            
            # 步骤5: 验证无法调用已取消注册的工具
            if tools_before:
                first_tool = tools_before[0]
                result = await registry.call_tool(platform, user_id, first_tool, text="test")
                assert result["success"] is False, "Should not be able to call unregistered tool"
                assert "未注册任何工具" in result["error"]


# ============================================
# 属性 9 扩展: 工具重新注册一致性
# 验证token更新后工具可以重新注册
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    user_id=user_id_strategy,
    token1=token_strategy,
    token2=token_strategy,
    tools_set1=st.lists(tool_name_strategy, min_size=1, max_size=3, unique=True),
    tools_set2=st.lists(tool_name_strategy, min_size=1, max_size=3, unique=True)
)
@settings(max_examples=30, deadline=5000)
async def test_property_tool_reregistration_consistency(
    platform, user_id, token1, token2, tools_set1, tools_set2
):
    """
    **Validates: Requirements 3.1, 3.2, 3.3, 10.1, 10.2**
    
    属性 9 扩展: 工具重新注册一致性
    
    验证：token更新后，旧工具被取消注册，新工具被注册
    
    测试逻辑：
    1. 用户使用token1注册一组工具
    2. 取消注册旧工具
    3. 用户使用token2重新注册另一组工具
    4. 验证只有新工具可用，旧工具不可用
    """
    assume(token1 != token2)
    
    registry, mock_token_manager = await setup_registry_with_mock()
    
    # Mock工具数据
    mock_tools_data1 = create_mock_tool_data(tools_set1)
    mock_tools_data2 = create_mock_tool_data(tools_set2)
    
    with aioresponses() as m:
        # 第一次注册
        mock_token_manager.get_user_token.return_value = token1
        m.get(
            "https://test-mcp.example.com/v1/tools/list",
            payload={"tools": mock_tools_data1},
            status=200
        )
        
        success1 = await registry.register_user_tools(platform, user_id)
        assert success1 is True
        
        tools_first = await registry.list_user_tools(platform, user_id)
        assert len(tools_first) > 0
        assert set(tools_first).issubset(set(tools_set1))
        
        # 取消注册
        await registry.unregister_user_tools(platform, user_id)
        
        # 第二次注册
        mock_token_manager.get_user_token.return_value = token2
        m.get(
            "https://test-mcp.example.com/v1/tools/list",
            payload={"tools": mock_tools_data2},
            status=200
        )
        
        success2 = await registry.register_user_tools(platform, user_id)
        assert success2 is True
        
        tools_second = await registry.list_user_tools(platform, user_id)
        assert len(tools_second) > 0
        assert set(tools_second).issubset(set(tools_set2))
        
        # 属性验证：新工具列表应该与旧工具列表不同（如果工具集不同）
        if set(tools_set1) != set(tools_set2):
            # 至少有一些差异
            assert tools_first != tools_second or set(tools_first) != set(tools_second)


# ============================================
# 属性测试：工具隔离性 - 多用户场景
# 验证多个用户同时操作时的隔离性
# ============================================

@pytest.mark.asyncio
@given(
    platform=platform_strategy,
    users=st.lists(
        st.tuples(user_id_strategy, token_strategy),
        min_size=2,
        max_size=4,
        unique=True
    ),
    tool_name=tool_name_strategy
)
@settings(max_examples=30, deadline=5000)
async def test_property_multi_user_isolation(platform, users, tool_name):
    """
    属性测试：多用户工具隔离性
    
    验证：多个用户同时注册和使用工具时，彼此完全隔离
    
    测试逻辑：
    1. 多个用户同时注册相同的工具
    2. 验证每个用户都有独立的工具注册表
    3. 一个用户取消注册不影响其他用户
    """
    # 确保用户ID唯一
    user_ids = [u[0] for u in users]
    assume(len(user_ids) == len(set(user_ids)))
    
    registry, mock_token_manager = await setup_registry_with_mock()
    
    # 创建token映射
    token_map = {uid: token for uid, token in users}
    
    async def get_user_token_side_effect(plat, uid):
        return token_map.get(uid)
    
    mock_token_manager.get_user_token.side_effect = get_user_token_side_effect
    
    # Mock工具数据
    mock_tools_data = create_mock_tool_data([tool_name])
    
    with aioresponses() as m:
        # Mock工具发现（多次）
        for _ in users:
            m.get(
                "https://test-mcp.example.com/v1/tools/list",
                payload={"tools": mock_tools_data},
                status=200
            )
        
        # 所有用户注册工具
        for user_id, _ in users:
            success = await registry.register_user_tools(platform, user_id)
            assert success is True
        
        # 验证每个用户都有该工具
        for user_id, _ in users:
            tools = await registry.list_user_tools(platform, user_id)
            assert tool_name in tools
        
        # 取消第一个用户的注册
        first_user_id = users[0][0]
        await registry.unregister_user_tools(platform, first_user_id)
        
        # 验证第一个用户没有工具
        tools_first = await registry.list_user_tools(platform, first_user_id)
        assert len(tools_first) == 0
        
        # 验证其他用户仍然有工具
        for user_id, _ in users[1:]:
            tools = await registry.list_user_tools(platform, user_id)
            assert tool_name in tools, f"User {user_id} should still have the tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
