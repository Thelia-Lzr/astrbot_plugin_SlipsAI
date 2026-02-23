# 需求文档：用户Token管理系统

## 引言

本文档定义了用户Token管理系统的功能需求和验收标准。该系统允许AstrBot插件的每个聊天用户绑定自己的外部MCP服务token，并在调用外部MCP服务时使用用户专属的token。系统使用SQLite数据库持久化存储用户平台、用户ID和token的映射关系，确保token安全存储（加密）并提供完整的token生命周期管理。

核心价值：
- 用户隔离：每个用户使用自己的token，确保多用户环境下的安全性
- 自动化：token绑定后自动发现和注册MCP工具
- 安全性：token加密存储，密钥独立管理
- 易用性：简单的指令接口，自动化的工具管理

## 术语表

- **System**: 用户Token管理系统
- **User**: 聊天平台上的用户（通过platform和user_id唯一标识）
- **Token**: 用户的MCP服务访问凭证
- **Platform**: 用户所在的聊天平台（如qq、telegram、discord）
- **MCP_Service**: 外部MCP服务器
- **Tool**: MCP服务器提供的可调用工具
- **DatabaseManager**: 数据库管理组件
- **TokenManager**: Token管理组件
- **TokenEncryption**: Token加密组件
- **MCPToolRegistry**: MCP工具注册表组件
- **Encrypted_Token**: 加密后的token字符串
- **Tool_Registry**: 用户工具注册表（内存缓存）
- **User_Key**: 用户唯一标识（格式：platform:user_id）

## 需求

### 需求 1：Token绑定管理

**用户故事：** 作为聊天用户，我想绑定我的MCP服务token，以便系统能够使用我的凭证调用MCP服务。

#### 验收标准

1. WHEN 用户提供有效的token THEN THE System SHALL 加密token并存储到数据库中
2. WHEN 用户绑定token成功 THEN THE System SHALL 自动从MCP服务器发现可用工具
3. WHEN 用户绑定token成功 THEN THE System SHALL 将发现的工具注册到用户的聊天会话中
4. WHEN 用户已有token并再次绑定 THEN THE System SHALL 更新现有token记录
5. WHEN token绑定失败 THEN THE System SHALL 保持数据库状态不变
6. WHEN token绑定成功 THEN THE System SHALL 返回成功消息和已注册工具列表

### 需求 2：Token查询

**用户故事：** 作为聊天用户，我想查询我的token绑定状态，以便确认我是否已经绑定token。

#### 验收标准

1. WHEN 用户查询token状态 THEN THE System SHALL 返回用户是否已绑定token的信息
2. WHEN 用户已绑定token THEN THE System SHALL 返回token的部分信息（前4位和后4位）
3. WHEN 用户未绑定token THEN THE System SHALL 提示用户使用bind_token指令绑定
4. THE System SHALL NOT 在任何响应中返回完整的明文token

### 需求 3：Token更新

**用户故事：** 作为聊天用户，我想更新我的token，以便在token过期或更换时继续使用服务。

#### 验收标准

1. WHEN 用户提供新token THEN THE System SHALL 取消注册旧token关联的工具
2. WHEN 用户提供新token THEN THE System SHALL 更新数据库中的加密token
3. WHEN token更新成功 THEN THE System SHALL 使用新token重新发现和注册工具
4. WHEN token更新成功 THEN THE System SHALL 返回成功消息和重新注册的工具列表
5. WHEN token更新失败 THEN THE System SHALL 保持原有token和工具注册状态不变

### 需求 4：Token解绑

**用户故事：** 作为聊天用户，我想解绑我的token，以便停止使用MCP服务或更换账号。

#### 验收标准

1. WHEN 用户解绑token THEN THE System SHALL 取消注册该用户的所有MCP工具
2. WHEN 用户解绑token THEN THE System SHALL 从数据库中删除该用户的token记录
3. WHEN token解绑成功 THEN THE System SHALL 返回成功消息确认工具已取消注册
4. WHEN 用户未绑定token时尝试解绑 THEN THE System SHALL 返回友好的错误提示

### 需求 5：Token安全存储

**用户故事：** 作为系统管理员，我需要确保用户token安全存储，以便保护用户的敏感凭证信息。

#### 验收标准

1. THE System SHALL 使用Fernet对称加密算法加密所有token
2. THE System SHALL 将加密密钥存储在独立文件中（权限600）
3. THE System SHALL 在数据库中仅存储加密后的token
4. THE System SHALL NOT 在日志中记录完整的明文token
5. WHEN 加密密钥丢失 THEN THE System SHALL 无法解密已存储的token
6. THE System SHALL 在首次运行时自动生成加密密钥

### 需求 6：MCP工具自动发现

**用户故事：** 作为聊天用户，我希望绑定token后系统自动发现可用工具，以便我无需手动配置就能使用MCP服务。

#### 验收标准

1. WHEN 用户绑定token成功 THEN THE System SHALL 调用MCP服务器的工具列表API
2. WHEN MCP服务器返回工具列表 THEN THE System SHALL 验证每个工具的schema格式
3. WHEN 工具schema验证通过 THEN THE System SHALL 将工具添加到用户的工具注册表
4. WHEN 工具发现失败 THEN THE System SHALL 记录警告日志但不影响token绑定
5. WHEN 工具发现失败 THEN THE System SHALL 返回警告消息提示用户未发现可用工具

### 需求 7：MCP工具注册

**用户故事：** 作为聊天用户，我希望发现的工具自动注册到我的会话中，以便我可以直接调用这些工具。

#### 验收标准

1. WHEN 工具发现成功 THEN THE System SHALL 为每个工具创建动态处理器
2. WHEN 工具注册成功 THEN THE System SHALL 将工具信息存储在用户的工具注册表中
3. THE System SHALL 为每个用户维护独立的工具注册表
4. WHEN 用户查询工具列表 THEN THE System SHALL 返回该用户已注册的所有工具名称
5. WHEN 用户查询工具详情 THEN THE System SHALL 返回工具的描述、参数schema和端点信息

### 需求 8：MCP工具调用

**用户故事：** 作为聊天用户，我想调用已注册的MCP工具，以便使用MCP服务提供的功能。

#### 验收标准

1. WHEN 用户调用已注册的工具 THEN THE System SHALL 验证工具是否存在于用户的注册表中
2. WHEN 用户调用工具 THEN THE System SHALL 验证提供的参数是否符合工具的schema
3. WHEN 参数验证通过 THEN THE System SHALL 使用用户的token调用MCP服务
4. WHEN MCP服务返回成功响应 THEN THE System SHALL 格式化结果并返回给用户
5. WHEN MCP服务返回错误 THEN THE System SHALL 返回友好的错误消息
6. WHEN 用户调用未注册的工具 THEN THE System SHALL 返回工具不存在的错误提示

### 需求 9：工具隔离性

**用户故事：** 作为聊天用户，我需要确保只能调用使用我自己token授权的工具，以便保护我的账号安全。

#### 验收标准

1. THE System SHALL 为每个用户维护独立的工具注册表
2. WHEN 用户调用工具 THEN THE System SHALL 仅使用该用户的token进行认证
3. WHEN 用户A调用工具 THEN THE System SHALL NOT 使用用户B的token
4. WHEN 用户查询工具列表 THEN THE System SHALL 仅返回该用户已注册的工具
5. THE System SHALL 通过User_Key（platform:user_id）确保用户隔离

### 需求 10：工具生命周期管理

**用户故事：** 作为聊天用户，我希望系统自动管理工具的生命周期，以便在token变更时工具状态保持一致。

#### 验收标准

1. WHEN 用户更新token THEN THE System SHALL 自动取消注册旧工具
2. WHEN 用户更新token THEN THE System SHALL 使用新token重新注册工具
3. WHEN 用户解绑token THEN THE System SHALL 自动取消注册所有工具
4. WHEN 工具取消注册后 THEN THE System SHALL 拒绝该用户对这些工具的调用请求
5. WHEN 用户重新绑定token THEN THE System SHALL 重新发现和注册工具

### 需求 11：数据持久化

**用户故事：** 作为系统管理员，我需要确保用户token数据持久化存储，以便系统重启后用户无需重新绑定token。

#### 验收标准

1. THE System SHALL 使用SQLite数据库存储用户token数据
2. THE System SHALL 在数据库中为每个（platform, user_id）组合维护唯一记录
3. WHEN 系统重启后 THEN THE System SHALL 能够从数据库中恢复用户token
4. THE System SHALL 记录token的创建时间和最后更新时间
5. WHEN 数据库操作失败 THEN THE System SHALL 记录错误日志并返回友好错误消息

### 需求 12：错误处理

**用户故事：** 作为聊天用户，我希望在操作失败时收到清晰的错误提示，以便我知道如何解决问题。

#### 验收标准

1. WHEN 用户未绑定token时调用服务 THEN THE System SHALL 提示用户先绑定token
2. WHEN token解密失败 THEN THE System SHALL 提示用户重新绑定token
3. WHEN MCP服务调用超时 THEN THE System SHALL 返回超时错误并建议稍后重试
4. WHEN MCP服务返回401错误 THEN THE System SHALL 提示用户token可能已过期
5. WHEN 数据库操作失败 THEN THE System SHALL 返回通用错误消息不暴露内部细节
6. WHEN 工具参数验证失败 THEN THE System SHALL 提示用户检查必需参数
7. THE System SHALL NOT 在用户错误消息中暴露系统内部实现细节

### 需求 13：指令接口

**用户故事：** 作为聊天用户，我想通过简单的指令管理我的token和工具，以便快速完成操作。

#### 验收标准

1. THE System SHALL 提供 /bind_token 指令用于绑定token
2. THE System SHALL 提供 /unbind_token 指令用于解绑token
3. THE System SHALL 提供 /check_token 指令用于查询token状态
4. THE System SHALL 提供 /update_token 指令用于更新token
5. THE System SHALL 提供 /list_tools 指令用于列出可用工具
6. THE System SHALL 提供 /tool_info 指令用于查看工具详细信息
7. WHEN 用户提供的指令参数不正确 THEN THE System SHALL 返回用法提示

### 需求 14：配置管理

**用户故事：** 作为系统管理员，我需要配置MCP服务器连接参数，以便系统能够正确连接到MCP服务。

#### 验收标准

1. THE System SHALL 支持配置MCP服务器的基础URL
2. THE System SHALL 支持配置服务端点映射
3. THE System SHALL 支持配置HTTP请求超时时间
4. THE System SHALL 支持配置请求失败时的重试次数和延迟
5. THE System SHALL 支持通过环境变量覆盖配置参数
6. THE System SHALL 在启动时验证配置的有效性
7. WHEN 配置无效 THEN THE System SHALL 记录错误并使用默认配置

### 需求 15：日志记录

**用户故事：** 作为系统管理员，我需要详细的日志记录，以便排查问题和监控系统运行状态。

#### 验收标准

1. THE System SHALL 记录所有token绑定、更新、解绑操作
2. THE System SHALL 记录所有MCP服务调用的结果
3. THE System SHALL 记录工具注册和取消注册操作
4. THE System SHALL 使用适当的日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
5. THE System SHALL NOT 在日志中记录完整的明文token
6. WHEN 记录token信息时 THEN THE System SHALL 仅记录token的前4位和后4位
7. THE System SHALL 记录操作的用户标识（platform和user_id）和时间戳

### 需求 16：性能要求

**用户故事：** 作为聊天用户，我希望系统响应迅速，以便获得良好的使用体验。

#### 验收标准

1. WHEN 用户绑定token THEN THE System SHALL 在100毫秒内完成数据库操作
2. WHEN 用户查询token THEN THE System SHALL 在50毫秒内返回结果
3. WHEN 调用MCP服务 THEN THE System SHALL 在配置的超时时间内返回结果或超时错误
4. THE System SHALL 使用数据库索引优化查询性能
5. THE System SHALL 使用异步操作避免阻塞用户请求
6. THE System SHALL 支持至少10个并发用户同时操作

### 需求 17：安全要求

**用户故事：** 作为系统管理员，我需要确保系统安全，以便保护用户数据和防止滥用。

#### 验收标准

1. THE System SHALL 使用参数化查询防止SQL注入攻击
2. THE System SHALL 验证所有用户输入的长度和格式
3. THE System SHALL 使用HTTPS调用MCP服务
4. THE System SHALL 验证MCP服务器的SSL证书
5. THE System SHALL 通过Authorization头传输token（不在URL中）
6. THE System SHALL 限制单用户的token绑定频率（每分钟最多5次）
7. THE System SHALL 限制单用户的MCP服务调用频率（每分钟最多20次）
8. THE System SHALL 将加密密钥文件权限设置为600（仅所有者可读写）

### 需求 18：工具参数验证

**用户故事：** 作为聊天用户，我希望系统验证我提供的工具参数，以便在调用前发现参数错误。

#### 验收标准

1. WHEN 用户调用工具 THEN THE System SHALL 验证所有必需参数是否提供
2. WHEN 用户调用工具 THEN THE System SHALL 验证参数类型是否符合schema定义
3. WHEN 参数验证失败 THEN THE System SHALL 返回具体的验证错误信息
4. WHEN 参数验证失败 THEN THE System SHALL NOT 调用MCP服务
5. THE System SHALL 使用工具的JSON Schema定义验证参数

### 需求 19：工具信息查询

**用户故事：** 作为聊天用户，我想查看工具的详细信息，以便了解如何正确使用工具。

#### 验收标准

1. WHEN 用户查询工具信息 THEN THE System SHALL 返回工具的名称和描述
2. WHEN 用户查询工具信息 THEN THE System SHALL 返回工具的参数列表
3. WHEN 用户查询工具信息 THEN THE System SHALL 标识哪些参数是必需的
4. WHEN 用户查询工具信息 THEN THE System SHALL 返回每个参数的类型和描述
5. WHEN 用户查询工具信息 THEN THE System SHALL 返回工具的API端点和HTTP方法
6. WHEN 用户查询不存在的工具 THEN THE System SHALL 返回工具不存在的错误提示

### 需求 20：数据库事务管理

**用户故事：** 作为系统管理员，我需要确保数据库操作的原子性，以便在操作失败时保持数据一致性。

#### 验收标准

1. WHEN token绑定操作失败 THEN THE System SHALL 回滚所有数据库更改
2. WHEN token更新操作失败 THEN THE System SHALL 保持原有token不变
3. THE System SHALL 使用数据库事务确保操作的原子性
4. WHEN 并发操作发生冲突 THEN THE System SHALL 使用数据库锁机制处理
5. THE System SHALL 在数据库操作完成后及时提交或回滚事务
