# Implementation Plan: Streaming HTTP Support

## Overview

本实现计划将为 MCP 工具调用系统添加流式 HTTP 响应支持，使系统能够处理 Server-Sent Events (SSE) 和 chunked transfer encoding 格式的流式响应。实现将通过扩展现有组件而非修改来保持向后兼容性，支持 AI 模型调用、大文件处理等需要实时输出的场景。

## Tasks

- [ ] 1. 实现 SSE 解析器核心组件
  - [ ] 1.1 创建 SSEParser 类和数据模型
    - 在 `src/mcp_service/` 目录下创建 `sse_parser.py` 文件
    - 实现 `SSEEvent` 数据类（event, data, id, retry 字段）
    - 实现 `SSEParser` 类的基本结构和初始化方法
    - 实现内部缓冲区 `_buffer` 用于处理不完整数据
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ] 1.2 实现 SSE 行解析逻辑
    - 实现 `parse_sse_line()` 方法解析单行 SSE 数据
    - 处理 `event:`, `data:`, `id:`, `retry:` 字段
    - 识别空行作为事件边界
    - 识别并忽略注释行（以 `:` 开头）
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [ ] 1.3 实现 SSE 块解析逻辑
    - 实现 `parse_sse_chunk()` 方法解析字节数据块
    - 处理 UTF-8 解码和不完整字符序列
    - 实现多行 data 字段的正确连接（使用换行符）
    - 维护缓冲区处理跨块边界的数据
    - 实现 `reset()` 方法清空解析器状态
    - _Requirements: 2.7, 2.8, 13.4, 13.5_
  
  - [ ]* 1.4 编写 SSE 解析器单元测试
    - 测试单行事件解析
    - 测试多行 data 字段解析
    - 测试事件边界检测
    - 测试注释行忽略
    - 测试不完整数据缓冲
    - 测试 UTF-8 边界情况
    - _Requirements: 2.1-2.8_
  
  - [ ]* 1.5 编写 SSE 解析器属性测试
    - **Property 3: SSE 解析往返属性**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.7**
    - 使用 Hypothesis 生成随机 SSE 事件，验证格式化后再解析的一致性
  
  - [ ]* 1.6 编写 SSE 缓冲区边界属性测试
    - **Property 5: SSE 缓冲区不变性**
    - **Validates: Requirements 2.8**
    - 验证在任意位置分割数据块，最终解析结果保持一致

- [ ] 2. 实现流式配置和数据模型
  - [ ] 2.1 创建流式数据模型
    - 在 `src/mcp_service/` 目录下创建 `streaming_models.py` 文件
    - 实现 `StreamChunk` 数据类（type, data, error, metadata, timestamp, sequence）
    - 实现 `StreamingStats` 数据类（total_chunks, total_bytes, start_time, end_time, errors, reconnect_count）
    - 添加 `duration` 和 `throughput` 属性到 StreamingStats
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [ ] 2.2 创建流式工具配置
    - 实现 `StreamingToolConfig` 数据类
    - 定义配置字段：enabled, chunk_size, timeout, buffer_size, retry_on_disconnect, max_reconnect_attempts
    - 设置合理的默认值（chunk_size=8192, buffer_size=10, max_reconnect_attempts=3）
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 2.3 实现配置验证逻辑
    - 实现 `validate_streaming_config()` 函数
    - 验证 chunk_size 在 [1024, 1048576] 范围内
    - 验证 buffer_size 在 [1, 1000] 范围内
    - 验证 max_reconnect_attempts 在 [0, 10] 范围内
    - 验证 timeout 为正整数或 None
    - _Requirements: 4.4, 4.5, 4.6_
  
  - [ ]* 2.4 编写数据模型单元测试
    - 测试 StreamChunk 的各种类型（chunk, error, complete, metadata）
    - 测试 StreamingStats 的统计计算（duration, throughput）
    - 测试 StreamingToolConfig 的默认值和验证
    - _Requirements: 4.1-4.6, 9.1-9.6_
  
  - [ ]* 2.5 编写配置验证属性测试
    - **Property 10: 配置参数范围验证**
    - **Validates: Requirements 4.4, 4.5, 4.6**
    - 使用 Hypothesis 生成随机配置，验证验证逻辑的正确性

- [ ] 3. Checkpoint - 确保核心组件测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 4. 扩展 MCPTool 支持流式配置
  - [ ] 4.1 修改 MCPTool 类添加流式配置支持
    - 在 `src/tool_registry/mcp_tool_registry.py` 中找到 MCPTool 类
    - 在 `__init__` 方法中添加 `streaming_config` 可选参数
    - 添加 `is_streaming` 属性判断工具是否为流式模式
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 4.2 实现配置序列化和反序列化
    - 修改 `to_dict()` 方法包含 streaming_config
    - 修改 `from_dict()` 类方法解析 streaming_config
    - 确保向后兼容（streaming_config 为可选）
    - _Requirements: 4.7, 11.4_
  
  - [ ]* 4.3 编写 MCPTool 扩展单元测试
    - 测试带流式配置的工具创建
    - 测试 is_streaming 属性判断
    - 测试配置序列化和反序列化
    - 测试向后兼容性（无 streaming_config）
    - _Requirements: 4.1-4.7, 11.4_
  
  - [ ]* 4.4 编写工具配置序列化属性测试
    - **Property 11: 工具配置序列化往返**
    - **Validates: Requirements 4.7**
    - 验证序列化后再反序列化得到等价配置

- [ ] 5. 实现流式 MCP 服务调用器
  - [ ] 5.1 创建 StreamingMCPServiceCaller 类
    - 在 `src/mcp_service/` 目录下创建 `streaming_mcp_service_caller.py` 文件
    - 继承自 `MCPServiceCaller` 类
    - 初始化方法接受 TokenManager 和 MCPServiceConfig
    - 添加并发控制字典跟踪每用户的活跃流
    - _Requirements: 1.1, 1.2, 12.1_
  
  - [ ] 5.2 实现 HTTP 流式响应读取
    - 实现 `_stream_response()` 异步生成器方法
    - 使用 aiohttp 的 `iter_chunked()` 逐块读取响应
    - 处理超时和网络错误
    - 确保连接在生成器结束时正确关闭
    - _Requirements: 1.2, 7.7, 10.3_
  
  - [ ] 5.3 实现核心流式调用逻辑
    - 实现 `call_service_streaming()` 异步生成器方法
    - 在发起请求前验证用户 token
    - 设置正确的 HTTP 请求头（Accept: text/event-stream, Authorization）
    - 使用 SSEParser 解析响应数据
    - 通过异步生成器 yield StreamChunk 字典
    - 维护 sequence 序列号确保严格递增
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 3.6_
  
  - [ ] 5.4 实现统计信息收集
    - 在流式传输开始时初始化 StreamingStats
    - 记录每个数据块的大小和数量
    - 记录开始和结束时间
    - 在 complete 数据块中包含完整统计信息
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ] 5.5 实现错误处理逻辑
    - 处理 HTTP 非 200 状态码，yield error 数据块
    - 处理网络连接中断，yield error 数据块
    - 处理超时，yield error 数据块
    - 处理 token 过期（HTTP 401），yield 特定错误消息
    - 确保 error 后不再 yield 其他数据块
    - 确保所有错误情况下连接被正确关闭
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7_
  
  - [ ] 5.6 实现并发控制
    - 在调用开始时检查用户并发数
    - 如果超过限制（5个）则立即返回错误
    - 在调用开始时增加并发计数
    - 在调用结束（正常或异常）时减少并发计数
    - _Requirements: 10.2, 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ]* 5.7 编写 StreamingMCPServiceCaller 单元测试
    - 使用 aioresponses mock HTTP 请求
    - 测试成功的流式调用
    - 测试 token 验证
    - 测试各种错误场景（网络错误、HTTP 错误、超时）
    - 测试统计信息收集
    - 测试并发控制
    - 测试连接清理
    - _Requirements: 1.1-1.5, 3.1-3.7, 7.1-7.7, 9.1-9.6, 10.2-10.4, 12.1-12.5_
  
  - [ ]* 5.8 编写数据块序列属性测试
    - **Property 6: 数据块序列单调性**
    - **Validates: Requirements 3.6, 13.1, 13.2**
    - 验证所有 yield 的数据块 sequence 严格递增
  
  - [ ]* 5.9 编写数据块结构属性测试
    - **Property 7: 数据块结构完整性**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    - 验证每个数据块包含正确的必需字段

- [ ] 6. 实现连接重试机制
  - [ ] 6.1 实现重连逻辑
    - 在 StreamingMCPServiceCaller 中添加 `_retry_connection()` 方法
    - 检查 streaming_config 的 retry_on_disconnect 配置
    - 实现指数退避策略（1秒、2秒、4秒）
    - 限制重连次数不超过 max_reconnect_attempts
    - 在重连时使用上次接收的事件 ID（如果可用）
    - 在 StreamingStats 中记录重连次数
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ]* 6.2 编写重连机制单元测试
    - 测试重连触发条件
    - 测试指数退避延迟
    - 测试重连次数限制
    - 测试重连统计记录
    - _Requirements: 8.1-8.5_
  
  - [ ]* 6.3 编写重连指数退避属性测试
    - **Property 20: 重连指数退避**
    - **Validates: Requirements 8.2**
    - 验证重连延迟遵循指数退避策略

- [ ] 7. Checkpoint - 确保流式调用器测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 8. 扩展 MCPToolRegistry 支持流式调用
  - [ ] 8.1 修改 MCPToolRegistry 初始化
    - 在 `__init__` 方法中添加 `streaming_caller` 可选参数
    - 如果未提供则自动创建 StreamingMCPServiceCaller 实例
    - _Requirements: 5.1, 5.2_
  
  - [ ] 8.2 实现流式工具调用方法
    - 实现 `call_tool_streaming()` 异步生成器方法
    - 验证工具存在于用户注册表中
    - 验证工具是流式工具
    - 调用 StreamingMCPServiceCaller 的 call_service_streaming()
    - 直接 yield 接收到的数据块
    - _Requirements: 5.1, 6.1, 6.2_
  
  - [ ] 8.3 实现自动路由的 call_tool 方法
    - 修改现有 `call_tool()` 方法添加流式检测
    - 如果工具是流式工具，调用 call_tool_streaming() 并收集所有块
    - 如果工具是非流式工具，使用原有逻辑
    - 返回格式包含 streaming 标志
    - _Requirements: 5.3, 5.4, 5.5, 11.1, 11.2, 11.5_
  
  - [ ]* 8.4 编写 MCPToolRegistry 扩展单元测试
    - 测试流式工具调用
    - 测试非流式工具调用（向后兼容）
    - 测试自动路由逻辑
    - 测试用户隔离
    - 测试工具不存在的错误处理
    - _Requirements: 5.1-5.5, 6.1-6.3, 11.1-11.5_
  
  - [ ]* 8.5 编写工具调用自动路由属性测试
    - **Property 12: 工具调用自动路由**
    - **Validates: Requirements 5.1, 5.2, 5.3**
    - 验证系统根据工具配置自动选择正确的调用方式
  
  - [ ]* 8.6 编写用户隔离属性测试
    - **Property 14: 用户 Token 隔离**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - 验证不同用户的流式调用使用各自的 token

- [ ] 9. 实现资源管理和安全控制
  - [ ] 9.1 实现 SSE 解析器缓冲区限制
    - 在 SSEParser 的 parse_sse_chunk() 中检查缓冲区大小
    - 如果缓冲区超过 1MB，抛出异常
    - 在 StreamingMCPServiceCaller 中捕获并 yield error
    - _Requirements: 10.1, 14.5_
  
  - [ ] 9.2 实现流式传输时长限制
    - 在 call_service_streaming() 中添加最大持续时间检查（1小时）
    - 超时后自动终止连接并 yield error
    - _Requirements: 14.6_
  
  - [ ] 9.3 实现 Token 安全日志
    - 在所有日志记录中仅记录 token 的最后 4 个字符
    - 在错误消息中不包含完整 token
    - _Requirements: 6.4, 14.3, 14.4_
  
  - [ ] 9.4 实现 HTTPS 和 SSL 验证
    - 确保 StreamingMCPServiceCaller 默认使用 HTTPS
    - 确保默认验证 SSL 证书
    - 从 MCPServiceConfig 读取 verify_ssl 配置
    - _Requirements: 14.1, 14.2_
  
  - [ ]* 9.5 编写资源管理单元测试
    - 测试缓冲区大小限制
    - 测试流式传输时长限制
    - 测试并发数限制
    - 测试资源清理
    - _Requirements: 10.1-10.5, 14.5, 14.6_
  
  - [ ]* 9.6 编写安全性单元测试
    - 测试 Token 日志安全性
    - 测试 HTTPS 使用
    - 测试 SSL 证书验证
    - _Requirements: 14.1-14.4_

- [ ] 10. 集成测试和端到端测试
  - [ ]* 10.1 编写端到端流式调用集成测试
    - 创建 mock MCP 服务器返回 SSE 响应
    - 测试完整的流式调用流程
    - 验证所有数据块正确接收
    - 验证统计信息准确性
    - _Requirements: 1.1-1.5, 3.1-3.7, 9.1-9.6_
  
  - [ ]* 10.2 编写多用户并发流式调用集成测试
    - 模拟多个用户同时调用流式工具
    - 验证用户隔离
    - 验证 token 不混淆
    - 验证并发控制
    - _Requirements: 6.1-6.4, 12.1-12.5_
  
  - [ ]* 10.3 编写流式和非流式混合调用集成测试
    - 测试用户同时拥有流式和非流式工具
    - 验证自动路由正确性
    - 验证向后兼容性
    - _Requirements: 5.1-5.5, 11.1-11.5_
  
  - [ ]* 10.4 编写错误恢复集成测试
    - 模拟网络中断和重连
    - 模拟 token 过期
    - 模拟服务器错误
    - 验证错误处理和资源清理
    - _Requirements: 7.1-7.7, 8.1-8.5_
  
  - [ ]* 10.5 编写向后兼容性集成测试
    - 运行现有的非流式工具测试套件
    - 验证所有现有测试通过
    - 验证现有工具行为不变
    - _Requirements: 11.1-11.5_

- [ ] 11. 性能测试
  - [ ]* 11.1 编写吞吐量性能测试
    - 测试单个流式传输的吞吐量（目标 > 1 MB/s）
    - 测试 CPU 开销（目标 < 5%）
    - 测试内存占用（目标 < 10MB per stream）
    - _Requirements: 15.3, 15.4_
  
  - [ ]* 11.2 编写延迟性能测试
    - 测试首块延迟（目标 < 100ms）
    - 测试块间延迟（目标 < 10ms）
    - _Requirements: 15.1, 15.2_
  
  - [ ]* 11.3 编写并发性能测试
    - 测试 50 个并发流式传输
    - 验证系统稳定性
    - 监控资源使用
    - _Requirements: 15.5_

- [ ] 12. 文档更新
  - [ ] 12.1 更新 PROJECT_STRUCTURE.md
    - 添加新的流式组件说明
    - 更新模块依赖关系
    - 添加流式调用示例
  
  - [ ] 12.2 创建流式功能使用文档
    - 在 `docs/` 目录下创建 `streaming_usage.md`
    - 说明如何配置流式工具
    - 提供流式调用示例代码
    - 说明错误处理和最佳实践
  
  - [ ] 12.3 更新 README.md
    - 添加流式支持功能说明
    - 添加快速开始示例
    - 更新依赖列表（确保 aiohttp >= 3.8.0）

- [ ] 13. Final Checkpoint - 完整性验证
  - 确保所有测试通过（单元测试、属性测试、集成测试、性能测试）
  - 验证代码覆盖率达到 90% 以上
  - 验证所有需求都有对应的实现和测试
  - 如有问题请询问用户

## Notes

- 标记 `*` 的任务为可选测试任务，可根据时间和资源情况跳过
- 每个任务都明确引用了相关的需求编号，确保可追溯性
- Checkpoint 任务用于在关键节点验证进度和质量
- 属性测试使用 Hypothesis 库，验证通用正确性属性
- 集成测试需要 mock MCP 服务器，使用 aiohttp.web 创建测试服务器
- 性能测试应在接近生产环境的条件下运行
- 所有实现必须保持向后兼容性，现有非流式工具不受影响
