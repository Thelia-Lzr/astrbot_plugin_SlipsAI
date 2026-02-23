"""MCP工具数据模型

该模块定义了MCPTool数据类，用于表示MCP服务器提供的工具。
包含工具的基本信息、参数schema和序列化/反序列化方法。

验证需求：需求 18（工具参数验证）
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class MCPTool:
    """MCP工具数据模型
    
    表示一个MCP服务器提供的工具，包含工具的名称、描述、参数schema、
    API端点和HTTP方法。
    
    Attributes:
        name: 工具的唯一标识名称
        description: 工具的功能描述
        parameters: JSON Schema格式的参数定义
        endpoint: 工具对应的MCP服务API端点
        method: HTTP请求方法（默认POST）
    """
    
    name: str
    description: str
    parameters: Dict[str, Any]
    endpoint: str
    method: str = "POST"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        将MCPTool实例转换为字典，便于序列化和存储。
        
        Returns:
            包含所有工具信息的字典
            
        Example:
            >>> tool = MCPTool(
            ...     name="translate",
            ...     description="翻译文本",
            ...     parameters={"required": ["text", "target"]},
            ...     endpoint="/v1/translate"
            ... )
            >>> tool.to_dict()
            {
                'name': 'translate',
                'description': '翻译文本',
                'parameters': {'required': ['text', 'target']},
                'endpoint': '/v1/translate',
                'method': 'POST'
            }
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "endpoint": self.endpoint,
            "method": self.method
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPTool":
        """从字典创建工具实例
        
        从字典数据创建MCPTool实例，用于反序列化。
        
        Args:
            data: 包含工具信息的字典，必须包含name、description、
                  parameters、endpoint字段，method字段可选
        
        Returns:
            MCPTool实例
            
        Raises:
            KeyError: 如果缺少必需字段
            
        Example:
            >>> data = {
            ...     'name': 'translate',
            ...     'description': '翻译文本',
            ...     'parameters': {'required': ['text', 'target']},
            ...     'endpoint': '/v1/translate',
            ...     'method': 'POST'
            ... }
            >>> tool = MCPTool.from_dict(data)
            >>> tool.name
            'translate'
        """
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=data["parameters"],
            endpoint=data["endpoint"],
            method=data.get("method", "POST")
        )
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数是否符合schema
        
        检查提供的参数是否满足工具的参数schema要求。
        当前实现检查所有必需参数是否存在。
        
        Args:
            params: 要验证的参数字典
        
        Returns:
            如果所有必需参数都存在返回True，否则返回False
            
        Note:
            这是简化版本的参数验证，仅检查必需参数是否存在。
            完整的JSON Schema验证可以使用jsonschema库实现。
            
        Example:
            >>> tool = MCPTool(
            ...     name="translate",
            ...     description="翻译文本",
            ...     parameters={
            ...         "required": ["text", "target"],
            ...         "properties": {
            ...             "text": {"type": "string"},
            ...             "target": {"type": "string"}
            ...         }
            ...     },
            ...     endpoint="/v1/translate"
            ... )
            >>> tool.validate_params({"text": "Hello", "target": "zh"})
            True
            >>> tool.validate_params({"text": "Hello"})
            False
        """
        # 获取必需参数列表
        required = self.parameters.get("required", [])
        
        # 检查所有必需参数是否都在提供的参数中
        return all(param in params for param in required)
