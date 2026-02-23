"""MCPTool数据模型单元测试

测试MCPTool类的序列化、反序列化和参数验证功能。

验证需求：需求 18（工具参数验证）
"""

import pytest
from src.tool_registry.mcp_tool import MCPTool


class TestMCPToolDataModel:
    """MCPTool数据模型测试类"""
    
    def test_create_tool_with_defaults(self):
        """测试使用默认值创建工具"""
        tool = MCPTool(
            name="test_tool",
            description="测试工具",
            parameters={"required": ["param1"]},
            endpoint="/v1/test"
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.parameters == {"required": ["param1"]}
        assert tool.endpoint == "/v1/test"
        assert tool.method == "POST"  # 默认值
    
    def test_create_tool_with_custom_method(self):
        """测试使用自定义HTTP方法创建工具"""
        tool = MCPTool(
            name="get_tool",
            description="GET工具",
            parameters={},
            endpoint="/v1/get",
            method="GET"
        )
        
        assert tool.method == "GET"
    
    def test_to_dict(self):
        """测试to_dict方法"""
        tool = MCPTool(
            name="translate",
            description="翻译文本",
            parameters={
                "required": ["text", "target"],
                "properties": {
                    "text": {"type": "string"},
                    "target": {"type": "string"}
                }
            },
            endpoint="/v1/translate",
            method="POST"
        )
        
        result = tool.to_dict()
        
        assert result == {
            "name": "translate",
            "description": "翻译文本",
            "parameters": {
                "required": ["text", "target"],
                "properties": {
                    "text": {"type": "string"},
                    "target": {"type": "string"}
                }
            },
            "endpoint": "/v1/translate",
            "method": "POST"
        }
    
    def test_from_dict_with_all_fields(self):
        """测试from_dict方法（包含所有字段）"""
        data = {
            "name": "summarize",
            "description": "总结文本",
            "parameters": {"required": ["text"]},
            "endpoint": "/v1/summarize",
            "method": "POST"
        }
        
        tool = MCPTool.from_dict(data)
        
        assert tool.name == "summarize"
        assert tool.description == "总结文本"
        assert tool.parameters == {"required": ["text"]}
        assert tool.endpoint == "/v1/summarize"
        assert tool.method == "POST"
    
    def test_from_dict_without_method(self):
        """测试from_dict方法（不包含method字段，使用默认值）"""
        data = {
            "name": "analyze",
            "description": "分析文本",
            "parameters": {},
            "endpoint": "/v1/analyze"
        }
        
        tool = MCPTool.from_dict(data)
        
        assert tool.name == "analyze"
        assert tool.method == "POST"  # 默认值
    
    def test_from_dict_missing_required_field(self):
        """测试from_dict方法缺少必需字段时抛出异常"""
        data = {
            "name": "incomplete_tool",
            "description": "不完整的工具"
            # 缺少 parameters 和 endpoint
        }
        
        with pytest.raises(KeyError):
            MCPTool.from_dict(data)
    
    def test_to_dict_from_dict_roundtrip(self):
        """测试to_dict和from_dict的往返转换"""
        original = MCPTool(
            name="roundtrip",
            description="往返测试",
            parameters={"required": ["a", "b"]},
            endpoint="/v1/roundtrip",
            method="PUT"
        )
        
        # 转换为字典再转回对象
        data = original.to_dict()
        restored = MCPTool.from_dict(data)
        
        # 验证所有字段都正确恢复
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.parameters == original.parameters
        assert restored.endpoint == original.endpoint
        assert restored.method == original.method


class TestMCPToolParameterValidation:
    """MCPTool参数验证测试类
    
    验证需求：需求 18（工具参数验证）
    """
    
    def test_validate_params_all_required_present(self):
        """测试所有必需参数都存在时验证通过"""
        tool = MCPTool(
            name="translate",
            description="翻译工具",
            parameters={
                "required": ["text", "target"],
                "properties": {
                    "text": {"type": "string"},
                    "target": {"type": "string"}
                }
            },
            endpoint="/v1/translate"
        )
        
        params = {"text": "Hello", "target": "zh"}
        assert tool.validate_params(params) is True
    
    def test_validate_params_with_extra_params(self):
        """测试提供额外参数时验证通过"""
        tool = MCPTool(
            name="translate",
            description="翻译工具",
            parameters={
                "required": ["text", "target"]
            },
            endpoint="/v1/translate"
        )
        
        params = {"text": "Hello", "target": "zh", "extra": "value"}
        assert tool.validate_params(params) is True
    
    def test_validate_params_missing_required(self):
        """测试缺少必需参数时验证失败"""
        tool = MCPTool(
            name="translate",
            description="翻译工具",
            parameters={
                "required": ["text", "target"]
            },
            endpoint="/v1/translate"
        )
        
        params = {"text": "Hello"}  # 缺少 target
        assert tool.validate_params(params) is False
    
    def test_validate_params_no_required_fields(self):
        """测试没有必需参数时验证总是通过"""
        tool = MCPTool(
            name="optional_tool",
            description="可选参数工具",
            parameters={
                "properties": {
                    "optional_param": {"type": "string"}
                }
            },
            endpoint="/v1/optional"
        )
        
        # 空参数应该通过
        assert tool.validate_params({}) is True
        
        # 有参数也应该通过
        assert tool.validate_params({"optional_param": "value"}) is True
    
    def test_validate_params_empty_required_list(self):
        """测试required为空列表时验证总是通过"""
        tool = MCPTool(
            name="no_required",
            description="无必需参数",
            parameters={"required": []},
            endpoint="/v1/no_required"
        )
        
        assert tool.validate_params({}) is True
        assert tool.validate_params({"any": "param"}) is True
    
    def test_validate_params_multiple_missing(self):
        """测试缺少多个必需参数时验证失败"""
        tool = MCPTool(
            name="multi_param",
            description="多参数工具",
            parameters={
                "required": ["param1", "param2", "param3"]
            },
            endpoint="/v1/multi"
        )
        
        # 缺少所有参数
        assert tool.validate_params({}) is False
        
        # 只有一个参数
        assert tool.validate_params({"param1": "value"}) is False
        
        # 有两个参数
        assert tool.validate_params({"param1": "v1", "param2": "v2"}) is False
        
        # 所有参数都有
        assert tool.validate_params({
            "param1": "v1",
            "param2": "v2",
            "param3": "v3"
        }) is True


class TestMCPToolEdgeCases:
    """MCPTool边界情况测试"""
    
    def test_empty_parameters(self):
        """测试空参数schema"""
        tool = MCPTool(
            name="empty_params",
            description="空参数",
            parameters={},
            endpoint="/v1/empty"
        )
        
        assert tool.validate_params({}) is True
        assert tool.validate_params({"any": "value"}) is True
    
    def test_complex_parameters_schema(self):
        """测试复杂的参数schema"""
        tool = MCPTool(
            name="complex",
            description="复杂参数",
            parameters={
                "required": ["config"],
                "properties": {
                    "config": {
                        "type": "object",
                        "properties": {
                            "nested": {"type": "string"}
                        }
                    }
                }
            },
            endpoint="/v1/complex"
        )
        
        # 只检查必需参数存在，不验证类型
        assert tool.validate_params({"config": {"nested": "value"}}) is True
        assert tool.validate_params({"config": "any_value"}) is True
        assert tool.validate_params({}) is False
    
    def test_special_characters_in_fields(self):
        """测试字段中包含特殊字符"""
        tool = MCPTool(
            name="special-tool_123",
            description="特殊字符：中文、emoji 🚀",
            parameters={"required": ["param-with-dash", "param_with_underscore"]},
            endpoint="/v1/special/path?query=value"
        )
        
        assert tool.name == "special-tool_123"
        assert "🚀" in tool.description
        
        # 验证参数名可以包含特殊字符
        params = {
            "param-with-dash": "value1",
            "param_with_underscore": "value2"
        }
        assert tool.validate_params(params) is True
    
    def test_unicode_in_parameters(self):
        """测试参数中包含Unicode字符"""
        tool = MCPTool(
            name="unicode_tool",
            description="Unicode工具",
            parameters={"required": ["中文参数", "日本語"]},
            endpoint="/v1/unicode"
        )
        
        params = {"中文参数": "值", "日本語": "値"}
        assert tool.validate_params(params) is True
