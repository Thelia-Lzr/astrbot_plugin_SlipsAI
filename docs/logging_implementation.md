# 日志记录实现文档

## 概述

本文档描述了用户Token管理系统的日志记录实现。系统使用Python标准库的logging模块，提供统一的日志配置和记录功能。

## 日志配置模块

### 位置
`src/utils/logging_config.py`

### 核心组件

#### 1. LoggingConfig类

提供统一的日志配置功能，支持控制台和文件输出。

**主要方法**:

- `configure_logging(log_level, log_file, console_output)`: 配置日志系统
  - `log_level`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - `log_file`: 日志文件路径（可选）
  - `console_output`: 是否输出到控制台（默认True）

- `get_logger(name)`: 获取日志记录器
  - `name`: 模块名称（通常使用 `__name__`）

- `set_module_level(module_name, level)`: 设置特定模块的日志级别
  - `module_name`: 模块名称
  - `level`: 日志级别

#### 2. configure_default_logging函数

为用户Token管理系统配置默认的日志设置的便捷函数。

**参数**:
- `data_dir`: 数据目录路径，用于存储日志文件（可选）

**功能**:
- 配置日志级别（从环境变量 `LOG_LEVEL` 读取或使用默认值INFO）
- 配置日志文件输出（如果提供了data_dir）
- 配置控制台输出
- 记录系统启动信息
- 降低第三方库（aiohttp, aiosqlite）的日志级别

#### 3. get_logger函数

获取日志记录器的便捷函数。

**参数**:
- `name`: 模块名称（通常使用 `__name__`）

**返回**:
- 日志记录器实例

## 日志格式

### 默认格式
```
%(asctime)s - %(levelname)s - %(name)s - %(message)s
```

### 示例输出
```
2024-01-15 10:30:45 - INFO - src.token_management.token_manager - Token bound successfully for user qq:123456
2024-01-15 10:30:46 - DEBUG - src.database.database_manager - Token retrieved for user qq:123456
2024-01-15 10:30:47 - ERROR - src.mcp_service.mcp_service_caller - MCP service call failed: HTTP 500
```

### 日期格式
```
%Y-%m-%d %H:%M:%S
```

## 日志级别

系统使用以下日志级别：

| 级别 | 用途 | 示例 |
|------|------|------|
| **DEBUG** | 详细的调试信息（参数、中间结果等） | Token加密成功，原始长度: 32, 加密后长度: 128 |
| **INFO** | 正常操作信息 | Token绑定成功 for user qq:123456 |
| **WARNING** | 警告信息（不影响功能但需要注意） | 工具发现失败，token可能过期 |
| **ERROR** | 错误信息（操作失败） | 数据库操作失败: connection timeout |
| **CRITICAL** | 严重错误（系统级问题） | 数据库初始化失败，插件无法启动 |

## 日志记录内容

### 需求 15.1: Token管理操作

系统记录所有token管理操作：

**Token绑定**:
```python
logger.info(f"User {platform}:{user_id} attempting to bind token")
logger.debug(f"Token prefix: {token[:4]}...")
logger.info(f"Token bound successfully for user {platform}:{user_id}")
```

**Token更新**:
```python
logger.info(f"User {platform}:{user_id} attempting to update token")
logger.info(f"Updating token for user {platform}:{user_id}")
logger.info(f"Token updated successfully for user {platform}:{user_id}")
```

**Token解绑**:
```python
logger.info(f"User {platform}:{user_id} attempting to unbind token")
logger.info(f"Deleting token for user {platform}:{user_id}")
logger.info(f"Token unbound successfully for user {platform}:{user_id}")
```

### 需求 15.2: MCP服务调用

系统记录所有MCP服务调用的结果：

**成功调用**:
```python
logger.info(f"MCP service called successfully for user {platform}:{user_id}")
logger.debug(f"Response status: 200, data: {response_data}")
```

**失败调用**:
```python
logger.error(f"MCP service call failed: HTTP {status_code}")
logger.error(f"MCP service error {status_code}: {error_text}")
```

**超时**:
```python
logger.error("MCP service call timeout")
```

### 需求 15.3: 工具操作

系统记录工具注册和取消注册操作：

**工具发现**:
```python
logger.debug(f"Discovering tools from: {tools_endpoint}")
logger.info(f"Discovered {len(tools)} tools from MCP server")
logger.info(f"Validated {len(validated_tools)} tools")
```

**工具注册**:
```python
logger.info(f"Attempting to register MCP tools for user {platform}:{user_id}")
logger.debug(f"Registered tool '{tool.name}' for user {user_key}")
logger.info(f"Registered {tool_count} tools for user {user_key}")
```

**工具取消注册**:
```python
logger.info(f"Unregistering MCP tools for user {platform}:{user_id}")
logger.info(f"Unregistered {tool_count} tools for user {user_key}")
```

**工具调用**:
```python
logger.info(f"User {platform}:{user_id} calling tool: {tool_name}")
logger.debug(f"Parsed parameters: {params}")
logger.info(f"Tool '{tool_name}' called successfully for user {user_key}")
```

### 需求 15.4: 适当的日志级别

系统使用适当的日志级别记录不同类型的信息：

- **DEBUG**: 详细的调试信息（参数、中间结果、内部状态）
- **INFO**: 正常操作（token绑定、工具注册、服务调用成功）
- **WARNING**: 警告信息（工具发现失败、token可能过期）
- **ERROR**: 错误信息（数据库操作失败、HTTP错误、超时）
- **CRITICAL**: 严重错误（数据库初始化失败、系统级问题）

### 需求 15.5: Token安全

系统确保日志中不记录完整的明文token：

**使用ErrorHandler.sanitize_token_for_log()方法**:
```python
from src.error_handling.error_messages import ErrorHandler

# 清理token用于日志记录
sanitized_token = ErrorHandler.sanitize_token_for_log(token)
logger.info(f"Token bound: {sanitized_token}")
# 输出: Token bound: sk-ab...xy
```

**规则**:
- 只保留token的前4位和后4位
- 中间用...替代
- 如果token长度<=8，只显示前4位

**示例**:
```python
# 原始token: sk-abc123xyz456
# 日志中显示: sk-ab...56

# 原始token: short
# 日志中显示: shor...
```

### 需求 15.6: 用户标识和时间戳

系统记录操作的用户标识和时间戳：

**用户标识格式**: `platform:user_id`
```python
logger.info(f"Token bound successfully for user {platform}:{user_id}")
# 输出: Token bound successfully for user qq:123456
```

**时间戳**: 自动包含在日志格式中
```
2024-01-15 10:30:45 - INFO - src.token_management.token_manager - Token bound successfully for user qq:123456
```

## 组件级日志记录

### DatabaseManager

**日志记录内容**:
- 数据库初始化
- Token的CRUD操作
- 数据库连接状态
- 错误和异常

**示例**:
```python
logger.info(f"DatabaseManager initialized with path: {db_path}")
logger.info(f"Token saved for user {platform}:{user_id}")
logger.debug(f"Token retrieved for user {platform}:{user_id}")
logger.error(f"Failed to save token for {platform}:{user_id}: {e}")
```

### TokenEncryption

**日志记录内容**:
- 加密器初始化
- 密钥生成和加载
- 加密和解密操作
- 错误和异常

**示例**:
```python
logger.info("TokenEncryption初始化成功")
logger.info(f"从文件加载加密密钥: {key_file_path}")
logger.debug(f"Token加密成功，原始长度: {len(token)}, 加密后长度: {len(encrypted_str)}")
logger.error(f"Token加密失败: {e}")
```

### TokenManager

**日志记录内容**:
- Token管理器初始化
- Token绑定、更新、解绑操作
- 参数验证
- 错误和异常

**示例**:
```python
logger.info("TokenManager initialized")
logger.info(f"Token bound successfully for user {platform}:{user_id}")
logger.warning("Platform is empty")
logger.error(f"Invalid platform parameter: {platform}")
```

### MCPServiceCaller

**日志记录内容**:
- MCP服务调用
- HTTP请求和响应
- 重试逻辑
- 错误和异常

**示例**:
```python
logger.info(f"Calling MCP service: {service_name}")
logger.debug(f"Request headers: {headers}")
logger.info(f"MCP service call successful: {service_name}")
logger.error(f"MCP service call failed: HTTP {status_code}")
```

### MCPToolRegistry

**日志记录内容**:
- 工具发现
- 工具注册和取消注册
- 工具调用
- 错误和异常

**示例**:
```python
logger.info("MCPToolRegistry initialized")
logger.debug(f"Discovering tools from: {tools_endpoint}")
logger.info(f"Registered {tool_count} tools for user {user_key}")
logger.warning(f"Tool schema validation failed: {tool.get('name')}")
```

### CommandHandlers (plugin.py)

**日志记录内容**:
- 指令处理
- 用户操作
- 错误和异常

**示例**:
```python
logger.info(f"User {platform}:{user_id} attempting to bind token")
logger.debug(f"bind_token command called without token parameter")
logger.error(f"Unexpected error in bind_token_command: {e}", exc_info=True)
```

## 环境变量配置

### LOG_LEVEL

设置日志级别：

```bash
export LOG_LEVEL=DEBUG
export LOG_LEVEL=INFO
export LOG_LEVEL=WARNING
export LOG_LEVEL=ERROR
export LOG_LEVEL=CRITICAL
```

**默认值**: INFO

**示例**:
```bash
# 开发环境：使用DEBUG级别
export LOG_LEVEL=DEBUG

# 生产环境：使用INFO级别
export LOG_LEVEL=INFO

# 仅记录错误：使用ERROR级别
export LOG_LEVEL=ERROR
```

## 日志文件

### 位置
`/AstrBot/data/token_management.log` 或 `./data/token_management.log`

### 文件管理
- 日志文件自动创建
- 使用UTF-8编码
- 追加模式写入
- 建议定期清理或轮转

### 日志轮转（可选）

可以使用Python的RotatingFileHandler实现日志轮转：

```python
from logging.handlers import RotatingFileHandler

# 创建轮转文件处理器
handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,           # 保留5个备份
    encoding='utf-8'
)
```

## 使用示例

### 基本使用

```python
from src.utils.logging_config import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 记录不同级别的日志
logger.debug("详细的调试信息")
logger.info("正常操作信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 记录异常

```python
try:
    # 执行操作
    result = await some_operation()
except Exception as e:
    # 记录异常（包含堆栈跟踪）
    logger.error(f"Operation failed: {e}", exc_info=True)
```

### 记录Token信息

```python
from src.error_handling.error_messages import ErrorHandler

# 清理token用于日志记录
sanitized_token = ErrorHandler.sanitize_token_for_log(token)
logger.info(f"Token bound: {sanitized_token}")
```

### 记录用户操作

```python
# 记录用户标识
user_key = f"{platform}:{user_id}"
logger.info(f"User {user_key} performed action")
```

## 测试

### 测试文件
`tests/test_logging_config.py`

### 测试覆盖
- 日志配置功能
- 日志级别设置
- 日志文件输出
- 控制台输出
- 环境变量配置
- 日志格式
- 多个日志记录器
- 不同日志级别
- 异常日志记录
- Token安全性

### 运行测试

```bash
# 运行所有日志配置测试
pytest tests/test_logging_config.py -v

# 运行特定测试
pytest tests/test_logging_config.py::TestLoggingConfig::test_configure_logging_default -v
```

## 验收标准检查

### 需求 15.1: 记录所有token绑定、更新、解绑操作
✅ **已实现** - 所有token管理操作都有详细的日志记录

### 需求 15.2: 记录所有MCP服务调用的结果
✅ **已实现** - 所有MCP服务调用（成功和失败）都有日志记录

### 需求 15.3: 记录工具注册和取消注册操作
✅ **已实现** - 工具发现、注册、取消注册、调用都有日志记录

### 需求 15.4: 使用适当的日志级别
✅ **已实现** - 系统使用DEBUG、INFO、WARNING、ERROR、CRITICAL五个级别

### 需求 15.5: 不在日志中记录完整的明文token
✅ **已实现** - 使用ErrorHandler.sanitize_token_for_log()清理token

### 需求 15.6: 记录token信息时仅记录前4位和后4位
✅ **已实现** - sanitize_token_for_log()方法确保只记录前4位和后4位

### 需求 15.7: 记录操作的用户标识和时间戳
✅ **已实现** - 所有日志都包含用户标识（platform:user_id）和时间戳

## 最佳实践

### 1. 使用适当的日志级别
- DEBUG: 仅在开发和调试时使用
- INFO: 记录正常操作
- WARNING: 记录警告但不影响功能
- ERROR: 记录错误和异常
- CRITICAL: 记录严重错误

### 2. 不记录敏感信息
- 不记录完整的token
- 不记录密码或密钥
- 不记录用户的个人敏感信息

### 3. 提供足够的上下文
- 记录用户标识（platform:user_id）
- 记录操作类型
- 记录相关参数（清理后）

### 4. 使用结构化日志
- 使用一致的格式
- 包含时间戳、级别、模块名
- 使用清晰的消息

### 5. 记录异常堆栈
- 使用 `exc_info=True` 记录完整堆栈
- 帮助调试和问题排查

## 故障排查

### 问题1: 日志未输出

**可能原因**:
- 日志级别设置过高
- 日志处理器未配置

**解决方案**:
```python
# 检查日志级别
logger = logging.getLogger()
print(f"Current log level: {logger.level}")

# 降低日志级别
LoggingConfig.configure_logging(log_level="DEBUG")
```

### 问题2: 日志文件未创建

**可能原因**:
- 目录不存在
- 权限不足

**解决方案**:
```python
# 确保目录存在
log_dir = Path(log_file).parent
log_dir.mkdir(parents=True, exist_ok=True)

# 检查权限
import os
print(f"Directory writable: {os.access(log_dir, os.W_OK)}")
```

### 问题3: 日志输出重复

**可能原因**:
- 多次配置日志系统
- 处理器未清除

**解决方案**:
```python
# 清除现有处理器
root_logger = logging.getLogger()
root_logger.handlers.clear()

# 重新配置
LoggingConfig.configure_logging()
```

## 总结

用户Token管理系统已经实现了完整的日志记录功能，满足需求15的所有验收标准：

1. ✅ 记录所有token管理操作
2. ✅ 记录所有MCP服务调用
3. ✅ 记录工具操作
4. ✅ 使用适当的日志级别
5. ✅ 不记录完整明文token
6. ✅ 仅记录token的前4位和后4位
7. ✅ 记录用户标识和时间戳

系统提供了统一的日志配置模块，支持控制台和文件输出，支持环境变量配置，并确保日志安全性。
