# 用户Token管理系统 - 项目结构

## 目录结构

```
astrbot_plugin_SlipsAI/
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── mcp_config.py            # MCP服务器配置文件
│   ├── database/                # 数据库管理模块
│   │   ├── __init__.py
│   │   └── database_manager.py  # DatabaseManager类（待实现）
│   ├── encryption/              # 加密模块
│   │   ├── __init__.py
│   │   └── token_encryption.py  # TokenEncryption类（待实现）
│   ├── token_management/        # Token管理模块
│   │   ├── __init__.py
│   │   └── token_manager.py     # TokenManager类（待实现）
│   ├── mcp_service/             # MCP服务调用模块
│   │   ├── __init__.py
│   │   └── mcp_service_caller.py # MCPServiceCaller类（待实现）
│   ├── tool_registry/           # 工具注册表模块
│   │   ├── __init__.py
│   │   └── mcp_tool_registry.py # MCPToolRegistry类（待实现）
│   ├── command_handlers/        # 指令处理器模块
│   │   ├── __init__.py
│   │   └── handlers.py          # CommandHandlers类（待实现）
│   └── utils/                   # 工具函数模块
│       ├── __init__.py
│       └── helpers.py           # 辅助函数（待实现）
├── tests/                       # 测试目录
│   ├── __init__.py
│   ├── test_database.py         # 数据库测试（待实现）
│   ├── test_encryption.py       # 加密测试（待实现）
│   ├── test_token_manager.py    # Token管理测试（待实现）
│   ├── test_mcp_service.py      # MCP服务测试（待实现）
│   ├── test_tool_registry.py    # 工具注册表测试（待实现）
│   └── test_integration.py      # 集成测试（待实现）
├── requirements.txt             # 项目依赖文件
├── main.py                      # 主入口文件
├── metadata.yaml                # 插件元数据
├── README.md                    # 项目说明
└── PROJECT_STRUCTURE.md         # 本文件

```

## 模块说明

### 1. database/ - 数据库管理模块
**职责**: 管理SQLite数据库连接和用户token数据的CRUD操作

**核心类**: `DatabaseManager`
- 初始化数据库表结构
- 保存、获取、更新、删除用户token
- 处理数据库异常和错误

### 2. encryption/ - 加密模块
**职责**: 提供token的加密和解密功能

**核心类**: `TokenEncryption`
- 使用Fernet对称加密算法加密token
- 解密存储的token
- 管理加密密钥的生成和存储

### 3. token_management/ - Token管理模块
**职责**: 协调数据库管理和加密操作

**核心类**: `TokenManager`
- 绑定、获取、更新、解绑用户token
- 协调DatabaseManager和TokenEncryption组件
- 验证输入参数的有效性

### 4. mcp_service/ - MCP服务调用模块
**职责**: 使用用户token调用外部MCP服务

**核心类**: `MCPServiceCaller`
- 获取用户token并调用外部MCP服务
- 处理HTTP请求和响应
- 处理token无效或过期的情况

### 5. tool_registry/ - 工具注册表模块
**职责**: 管理MCP工具的发现、注册和调用

**核心类**: `MCPToolRegistry`
- 从MCP服务器发现可用工具
- 为每个用户维护独立的工具注册表
- 动态创建工具处理器
- 调用工具时自动使用用户的token

### 6. command_handlers/ - 指令处理器模块
**职责**: 处理用户指令，提供token管理和工具调用的用户界面

**核心类**: `CommandHandlers`
- 处理 /bind_token、/unbind_token、/check_token 等指令
- 处理 /list_tools、/tool_info 等工具查询指令
- 处理动态工具调用请求

### 7. utils/ - 工具函数模块
**职责**: 提供通用的辅助函数

**功能**:
- 参数解析
- 日志格式化
- 错误处理辅助函数

### 8. mcp_config.py - MCP服务器配置
**职责**: 管理MCP服务器配置

**核心类**: `MCPServiceConfig`
- 管理MCP服务器的基础URL和端点配置
- 支持环境变量覆盖
- 管理连接参数（超时、重试等）

## 依赖说明

### 运行时依赖
- `aiosqlite >= 0.17.0` - 异步SQLite数据库操作
- `cryptography >= 41.0.0` - Fernet加密算法
- `aiohttp >= 3.8.0` - 异步HTTP客户端

### 开发依赖
- `pytest >= 7.0.0` - 单元测试框架
- `pytest-asyncio >= 0.21.0` - 异步测试支持
- `hypothesis >= 6.0.0` - 基于属性的测试
- `pytest-mock >= 3.10.0` - Mock支持
- `aioresponses >= 0.7.0` - Mock HTTP请求
- `pytest-cov >= 4.0.0` - 代码覆盖率
- `black >= 23.0.0` - 代码格式化
- `pylint >= 2.17.0` - 代码检查
- `mypy >= 1.0.0` - 类型检查

## 安装依赖

```bash
# 安装所有依赖（包括开发依赖）
pip install -r requirements.txt

# 仅安装运行时依赖
pip install aiosqlite>=0.17.0 cryptography>=41.0.0 aiohttp>=3.8.0
```

## 配置说明

### 环境变量
系统支持以下环境变量配置：

1. **MCP_BASE_URL** - MCP服务器基础URL
   ```bash
   export MCP_BASE_URL=https://prod-mcp.example.com
   ```

2. **MCP_TIMEOUT** - HTTP请求超时时间（秒）
   ```bash
   export MCP_TIMEOUT=45
   ```

3. **MCP_MAX_RETRIES** - 最大重试次数
   ```bash
   export MCP_MAX_RETRIES=5
   ```

### 数据存储
- 数据库文件: `/AstrBot/data/user_tokens.db`
- 加密密钥文件: `/AstrBot/data/encryption.key`

## 开发指南

### 代码风格
- 使用 `black` 进行代码格式化
- 使用 `pylint` 进行代码检查
- 使用 `mypy` 进行类型检查

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_database.py

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html

# 运行属性测试
pytest tests/ -k "property"
```

### 代码检查
```bash
# 格式化代码
black src/ tests/

# 代码检查
pylint src/

# 类型检查
mypy src/
```

## 下一步任务

根据 tasks.md 文件，接下来需要实现：

1. ✅ **Task 1**: 创建项目结构和依赖配置（已完成）
2. **Task 2**: 实现数据库管理模块（DatabaseManager）
3. **Task 3**: 实现加密模块（TokenEncryption）
4. **Task 4**: 实现Token管理模块（TokenManager）
5. **Task 5**: 实现MCP工具注册表（MCPToolRegistry）
6. **Task 6**: 实现指令处理器（CommandHandlers）
7. **Task 7**: 编写单元测试
8. **Task 8**: 编写属性测试
9. **Task 9**: 集成测试和文档

## 参考文档

- 需求文档: `.kiro/specs/user-token-management/requirements.md`
- 设计文档: `.kiro/specs/user-token-management/design.md`
- 任务列表: `.kiro/specs/user-token-management/tasks.md`
