# Requirements Document

## Introduction

本需求文档定义了为 MCP 工具调用系统添加流式 HTTP 响应支持的功能需求。该功能使系统能够处理 Server-Sent Events (SSE) 和 chunked transfer encoding 格式的流式响应，支持 AI 模型调用、大文件处理等需要实时输出的场景。系统将保持对现有非流式工具的完全向后兼容，同时为新的流式工具提供无缝集成能力。

## Glossary

- **System**: MCP 工具调用系统
- **StreamingCaller**: 流式 MCP 服务调用器组件
- **SSEParser**: Server-Sent Events 解析器组件
- **Registry**: MCP 工具注册表组件
- **Tool**: MCP 工具实例
- **Chunk**: 流式响应中的单个数据块
- **Token**: 用户身份验证令牌
- **SSE**: Server-Sent Events，一种 HTTP 流式传输协议
- **Event**: SSE 协议中的单个事件单元
- **Buffer**: 解析器内部用于存储不完整数据的缓冲区

## Requirements

### Requirement 1: 流式 HTTP 请求支持

**User Story:** 作为系统开发者，我希望系统能够发起流式 HTTP 请求，以便接收服务器的实时数据流。

#### Acceptance Criteria

1. WHEN StreamingCaller 发起流式请求 THEN THE System SHALL 在 HTTP 请求头中设置 Accept: text/event-stream
2. WHEN StreamingCaller 建立连接 THEN THE System SHALL 使用 aiohttp 的流式 API 进行数据传输
3. WHEN 流式请求发起前 THEN THE System SHALL 验证用户 token 的有效性
4. WHEN 用户 token 无效 THEN THE System SHALL 立即返回错误而不发起 HTTP 请求
5. WHEN 流式连接建立 THEN THE System SHALL 在 Authorization 头中包含用户 token

### Requirement 2: SSE 数据解析

**User Story:** 作为系统开发者，我希望系统能够正确解析 SSE 格式的数据，以便提取服务器发送的事件和数据。

#### Acceptance Criteria

1. WHEN SSEParser 接收到包含 event: 字段的行 THEN THE System SHALL 解析出事件类型
2. WHEN SSEParser 接收到包含 data: 字段的行 THEN THE System SHALL 解析出事件数据
3. WHEN SSEParser 接收到包含 id: 字段的行 THEN THE System SHALL 解析出事件 ID
4. WHEN SSEParser 接收到包含 retry: 字段的行 THEN THE System SHALL 解析出重连延迟值
5. WHEN SSEParser 接收到空行 THEN THE System SHALL 识别为事件边界并输出完整事件
6. WHEN SSEParser 接收到以冒号开头的行 THEN THE System SHALL 将其识别为注释并忽略
7. WHEN SSEParser 接收到多行 data: 字段 THEN THE System SHALL 使用换行符连接所有数据行
8. WHEN SSEParser 接收到不完整的数据块 THEN THE System SHALL 将其保存在 Buffer 中等待后续数据

### Requirement 3: 流式数据传输

**User Story:** 作为系统用户，我希望能够实时接收流式工具的输出，以便及时查看处理进度和结果。

#### Acceptance Criteria

1. WHEN StreamingCaller 接收到数据块 THEN THE System SHALL 通过异步生成器 yield 该数据块
2. WHEN 数据块被 yield THEN THE System SHALL 包含 type 字段标识块类型
3. WHEN 数据块类型为 chunk THEN THE System SHALL 包含 data 字段和 sequence 序列号
4. WHEN 数据块类型为 error THEN THE System SHALL 包含 error 字段描述错误信息
5. WHEN 数据块类型为 complete THEN THE System SHALL 包含 metadata 字段提供统计信息
6. WHEN 流式传输过程中 THEN THE System SHALL 确保 sequence 序列号严格递增
7. WHEN 流式传输完成 THEN THE System SHALL yield 一个 type 为 complete 的最终数据块

### Requirement 4: 工具流式配置

**User Story:** 作为系统管理员，我希望能够为每个工具独立配置是否启用流式模式，以便灵活控制工具行为。

#### Acceptance Criteria

1. WHEN Tool 被创建时 THEN THE System SHALL 支持可选的 streaming_config 参数
2. WHEN Tool 的 streaming_config 存在且 enabled 为 true THEN THE Tool SHALL 被识别为流式工具
3. WHEN Tool 的 streaming_config 不存在或 enabled 为 false THEN THE Tool SHALL 被识别为非流式工具
4. WHEN streaming_config 被设置 THEN THE System SHALL 验证 chunk_size 在 1024 到 1048576 字节范围内
5. WHEN streaming_config 被设置 THEN THE System SHALL 验证 buffer_size 在 1 到 1000 范围内
6. WHEN streaming_config 被设置 THEN THE System SHALL 验证 max_reconnect_attempts 在 0 到 10 范围内
7. WHEN Tool 被序列化 THEN THE System SHALL 包含 streaming_config 配置信息

### Requirement 5: 工具调用路由

**User Story:** 作为系统用户，我希望系统能够自动识别工具类型并选择合适的调用方式，以便无需手动区分流式和非流式工具。

#### Acceptance Criteria

1. WHEN Registry 调用流式工具 THEN THE System SHALL 使用 StreamingCaller 进行调用
2. WHEN Registry 调用非流式工具 THEN THE System SHALL 使用标准 MCPServiceCaller 进行调用
3. WHEN Registry 的 call_tool 方法被调用 THEN THE System SHALL 根据工具配置自动选择调用方式
4. WHEN call_tool 调用流式工具 THEN THE System SHALL 收集所有数据块后返回完整结果
5. WHEN call_tool 调用非流式工具 THEN THE System SHALL 保持原有行为和返回格式不变

### Requirement 6: 用户隔离

**User Story:** 作为系统用户，我希望我的流式调用使用我自己的 token，以便确保数据安全和隔离。

#### Acceptance Criteria

1. WHEN 不同用户调用相同流式工具 THEN THE System SHALL 为每个用户使用各自的 token
2. WHEN StreamingCaller 发起请求 THEN THE System SHALL 从 TokenManager 获取指定用户的 token
3. WHEN 并发流式调用发生 THEN THE System SHALL 确保不同用户的 token 不会混淆
4. WHEN 流式调用过程中 THEN THE System SHALL 不在日志中记录完整 token 内容

### Requirement 7: 错误处理

**User Story:** 作为系统用户，我希望系统能够优雅处理流式传输中的各种错误，以便了解问题原因并采取相应措施。

#### Acceptance Criteria

1. WHEN 网络连接中断 THEN THE System SHALL yield error 类型数据块并终止生成器
2. WHEN HTTP 响应状态码非 200 THEN THE System SHALL yield error 类型数据块包含状态码和错误信息
3. WHEN token 在流式传输中过期（HTTP 401）THEN THE System SHALL yield error 类型数据块提示重新绑定
4. WHEN 流式传输超时 THEN THE System SHALL yield error 类型数据块并关闭连接
5. WHEN SSE 解析遇到格式错误 THEN THE System SHALL 记录警告并继续解析后续数据
6. WHEN error 类型数据块被 yield 后 THEN THE System SHALL 不再 yield 任何其他数据块
7. WHEN 流式传输发生异常 THEN THE System SHALL 确保 HTTP 连接被正确关闭

### Requirement 8: 连接重试

**User Story:** 作为系统用户，我希望系统在网络不稳定时能够自动重试连接，以便提高流式传输的可靠性。

#### Acceptance Criteria

1. WHEN streaming_config 的 retry_on_disconnect 为 true THEN THE System SHALL 在连接断开时尝试重连
2. WHEN 重连尝试发生 THEN THE System SHALL 使用指数退避策略（1秒、2秒、4秒）
3. WHEN 重连次数达到 max_reconnect_attempts THEN THE System SHALL 停止重试并返回错误
4. WHEN 重连成功 THEN THE System SHALL 从上次接收的事件 ID 继续传输（如果服务器支持）
5. WHEN 重连过程中 THEN THE System SHALL 在 StreamingStats 中记录重连次数

### Requirement 9: 统计信息收集

**User Story:** 作为系统管理员，我希望系统能够收集流式传输的统计信息，以便监控性能和诊断问题。

#### Acceptance Criteria

1. WHEN 流式传输开始 THEN THE System SHALL 记录开始时间
2. WHEN 数据块被接收 THEN THE System SHALL 累加总块数和总字节数
3. WHEN 流式传输完成 THEN THE System SHALL 记录结束时间
4. WHEN 流式传输完成 THEN THE System SHALL 在 complete 数据块中包含统计信息
5. WHEN 统计信息被查询 THEN THE System SHALL 提供传输持续时间和吞吐量计算
6. WHEN 错误发生 THEN THE System SHALL 在 StreamingStats 中记录错误信息

### Requirement 10: 资源管理

**User Story:** 作为系统管理员，我希望系统能够有效管理资源，以便防止内存泄漏和资源耗尽。

#### Acceptance Criteria

1. WHEN SSEParser 的 Buffer 大小超过 1MB THEN THE System SHALL yield error 并清空 Buffer
2. WHEN 用户的并发流式调用数超过限制（5个）THEN THE System SHALL 拒绝新的调用请求
3. WHEN 流式传输结束（正常或异常）THEN THE System SHALL 确保 HTTP 连接被关闭
4. WHEN 流式传输结束 THEN THE System SHALL 释放所有相关资源（Buffer、统计对象等）
5. WHEN 系统运行时 THEN THE System SHALL 确保每个流式传输的内存占用不超过 10MB

### Requirement 11: 向后兼容性

**User Story:** 作为现有系统用户，我希望添加流式支持后现有的非流式工具仍能正常工作，以便无需修改现有代码。

#### Acceptance Criteria

1. WHEN 非流式工具被调用 THEN THE System SHALL 使用原有的 MCPServiceCaller 进行处理
2. WHEN 非流式工具返回结果 THEN THE System SHALL 保持原有的返回格式不变
3. WHEN 现有测试套件运行 THEN THE System SHALL 通过所有非流式工具的测试用例
4. WHEN Tool 不包含 streaming_config THEN THE System SHALL 将其视为非流式工具
5. WHEN Registry 的现有方法被调用 THEN THE System SHALL 保持原有行为不变

### Requirement 12: 并发控制

**User Story:** 作为系统管理员，我希望系统能够限制并发流式调用数量，以便保护系统资源不被耗尽。

#### Acceptance Criteria

1. WHEN 系统启动时 THEN THE System SHALL 设置每用户最大并发流式调用数为 5
2. WHEN 用户发起新的流式调用 THEN THE System SHALL 检查当前并发数是否超限
3. WHEN 并发数超限 THEN THE System SHALL 返回错误信息提示用户等待
4. WHEN 流式调用完成 THEN THE System SHALL 减少该用户的并发计数
5. WHEN 流式调用异常终止 THEN THE System SHALL 确保并发计数被正确更新

### Requirement 13: 数据完整性

**User Story:** 作为系统用户，我希望流式传输能够保证数据完整性，以便确保接收到的数据准确无误。

#### Acceptance Criteria

1. WHEN 所有数据块被接收 THEN THE System SHALL 确保没有数据块丢失
2. WHEN 数据块被 yield THEN THE System SHALL 确保数据块按接收顺序输出
3. WHEN 流式传输完成 THEN THE System SHALL 确保 complete 数据块中的总块数与实际 yield 的块数一致
4. WHEN UTF-8 字符被分割在块边界 THEN THE System SHALL 正确处理并保证字符完整性
5. WHEN 多行数据字段被解析 THEN THE System SHALL 使用换行符正确连接所有行

### Requirement 14: 安全性

**User Story:** 作为系统管理员，我希望流式传输遵循安全最佳实践，以便保护用户数据和系统安全。

#### Acceptance Criteria

1. WHEN 流式请求发起 THEN THE System SHALL 默认使用 HTTPS 协议
2. WHEN 流式请求发起 THEN THE System SHALL 默认验证 SSL 证书
3. WHEN 错误信息被生成 THEN THE System SHALL 确保不包含完整 token 内容
4. WHEN 日志记录发生 THEN THE System SHALL 仅记录 token 的最后 4 个字符
5. WHEN SSE 数据被解析 THEN THE System SHALL 限制单个事件大小不超过 1MB
6. WHEN 流式传输持续时间超过 1 小时 THEN THE System SHALL 自动终止连接

### Requirement 15: 性能要求

**User Story:** 作为系统用户，我希望流式传输具有良好的性能表现，以便获得流畅的使用体验。

#### Acceptance Criteria

1. WHEN 流式传输开始 THEN THE System SHALL 在 100 毫秒内 yield 第一个数据块
2. WHEN 数据块被接收 THEN THE System SHALL 在 10 毫秒内完成解析并 yield
3. WHEN 单个流式传输进行时 THEN THE System SHALL 确保吞吐量达到 1 MB/s 以上
4. WHEN 流式传输进行时 THEN THE System SHALL 确保 CPU 开销低于 5%
5. WHEN 50 个并发流式传输进行时 THEN THE System SHALL 保持系统稳定运行
