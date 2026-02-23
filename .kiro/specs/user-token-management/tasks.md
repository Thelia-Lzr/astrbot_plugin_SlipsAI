# 实现计划：用户Token管理系统

## 概述

本实现计划将用户Token管理系统的设计转化为可执行的编码任务。系统使用Python实现，包含7个核心组件：数据库管理、Token加密、Token管理协调、MCP服务调用、MCP工具注册表、指令处理器和配置管理。

核心功能：
- Token绑定与管理（加密存储、更新、删除）
- MCP工具自动发现与注册
- 工具隔离性（每个用户只能调用自己的工具）
- 动态工具调用
- 工具生命周期管理

数据存储路径：/AstrBot/data/
实现语言：Python 3.8+

## 任务列表

- [x] 1. 创建项目结构和依赖配置
  - 创建目录结构：数据库、加密、工具注册等模块
  - 创建 requirements.txt 文件，列出所有运行时和开发依赖
  - 创建 mcp_config.py 配置文件，定义MCP服务器配置类
  - _需求：需求 14（配置管理）_

- [x] 2. 实现Token加密模块（TokenEncryption）
  - [x] 2.1 实现TokenEncryption类的核心功能
    - 实现 __init__ 方法：初始化加密器，生成或加载密钥
    - 实现 encrypt 方法：使用Fernet加密token
    - 实现 decrypt 方法：解密token
    - 实现 get_key 方法：获取加密密钥
    - 实现密钥文件的生成和加载逻辑（/AstrBot/data/encryption.key）
    - 设置密钥文件权限为600（仅所有者可读写）
    - _需求：需求 5（Token安全存储）_
  
  - [x] 2.2 编写TokenEncryption的属性测试
    - **属性 2: 加密可逆性**
    - **验证需求：需求 5.1**
    - 使用hypothesis生成随机token字符串
    - 验证加密后解密能得到原始token
    - 测试空字符串和特殊字符的加密

- [x] 3. 实现数据库管理模块（DatabaseManager）
  - [x] 3.1 实现DatabaseManager类的核心功能
    - 实现 __init__ 方法：初始化数据库路径
    - 实现 initialize 方法：创建user_tokens表和索引
    - 实现 save_token 方法：保存或更新用户token（使用参数化查询）
    - 实现 get_token 方法：获取用户的加密token
    - 实现 delete_token 方法：删除用户token
    - 实现 user_has_token 方法：检查用户是否已绑定token
    - 实现 close 方法：关闭数据库连接
    - 使用aiosqlite实现异步数据库操作
    - _需求：需求 11（数据持久化）、需求 20（数据库事务管理）_
  
  - [x] 3.2 编写DatabaseManager的属性测试
    - **属性 1: Token唯一性**
    - **验证需求：需求 11.2**
    - 验证同一用户多次绑定token只保留最新记录
    - 测试并发访问的线程安全性
  
  - [x] 3.3 编写DatabaseManager的单元测试
    - 测试数据库初始化和表创建
    - 测试token的CRUD操作
    - 测试唯一约束（platform, user_id组合）
    - 测试异常处理（数据库锁、磁盘满等）
    - _需求：需求 11（数据持久化）_

- [x] 4. 实现Token管理协调模块（TokenManager）
  - [x] 4.1 实现TokenManager类的核心功能
    - 实现 __init__ 方法：初始化DatabaseManager和TokenEncryption
    - 实现 bind_token 方法：绑定用户token（加密后存储）
    - 实现 get_user_token 方法：获取用户token（解密后返回）
    - 实现 update_token 方法：更新用户token
    - 实现 unbind_token 方法：解绑用户token
    - 实现 has_token 方法：检查用户是否已绑定token
    - 实现输入参数验证（platform长度1-50，user_id长度1-100）
    - _需求：需求 1（Token绑定管理）、需求 3（Token更新）、需求 4（Token解绑）_
  
  - [x] 4.2 编写TokenManager的属性测试
    - **属性 3: Token隔离性**
    - **验证需求：需求 9.2, 9.3**
    - 验证不同用户的token互不影响
    - **属性 5: 操作原子性**
    - **验证需求：需求 1.5, 20.1, 20.3**
    - 验证token绑定操作的原子性
  
  - [x] 4.3 编写TokenManager的单元测试
    - 测试token绑定流程（加密+存储）
    - 测试token获取流程（查询+解密）
    - 测试token更新和删除
    - 测试用户不存在的情况
    - _需求：需求 1、需求 3、需求 4_

- [x] 5. 检查点 - 确保核心数据层测试通过
  - 确保所有测试通过，如有问题请向用户提问

- [x] 6. 实现MCP配置管理模块（MCPConfig）
  - [x] 6.1 实现MCPServiceConfig类
    - 实现数据类定义：base_url、service_endpoints、timeout等字段
    - 实现 __post_init__ 方法：支持环境变量覆盖（MCP_BASE_URL、MCP_TIMEOUT、MCP_MAX_RETRIES）
    - 实现 get_service_url 方法：获取完整的服务URL
    - 实现 validate 方法：验证配置的有效性
    - 实现 add_service 方法：动态添加服务端点
    - 实现 get_config_summary 方法：获取配置摘要
    - _需求：需求 14（配置管理）_
  
  - [x] 6.2 编写MCPConfig的单元测试
    - 测试默认配置加载
    - 测试环境变量覆盖
    - 测试配置验证
    - 测试服务URL生成
    - _需求：需求 14_

- [x] 7. 实现MCP服务调用模块（MCPServiceCaller）
  - [x] 7.1 实现MCPServiceCaller类的核心功能
    - 实现 __init__ 方法：初始化TokenManager和MCPConfig
    - 实现 call_service 方法：使用用户token调用MCP服务
    - 使用aiohttp发送HTTP请求，设置Authorization头（Bearer token）
    - 实现超时和重试逻辑（根据MCPConfig配置）
    - 处理HTTP状态码：200（成功）、401（token无效）、其他错误
    - 实现 validate_token 方法：验证token是否有效
    - _需求：需求 8（MCP工具调用）、需求 17（安全要求）_
  
  - [x] 7.2 编写MCPServiceCaller的单元测试
    - 测试成功的服务调用
    - 测试HTTP错误响应（401, 404, 500等）
    - 测试网络超时
    - 测试无效token的处理
    - 使用aioresponses模拟外部MCP服务
    - _需求：需求 8、需求 12（错误处理）_

- [x] 8. 实现MCP工具注册表模块（MCPToolRegistry）
  - [x] 8.1 实现MCPTool数据模型
    - 创建MCPTool数据类：name、description、parameters、endpoint、method
    - 实现 to_dict 方法：转换为字典格式
    - 实现 from_dict 类方法：从字典创建工具实例
    - 实现 validate_params 方法：验证参数是否符合schema
    - _需求：需求 18（工具参数验证）_
  
  - [x] 8.2 实现MCPToolRegistry类的核心功能
    - 实现 __init__ 方法：初始化TokenManager、MCPConfig和工具注册表（字典）
    - 实现 discover_tools 方法：从MCP服务器发现可用工具
    - 调用MCP服务器的 /v1/tools/list 端点
    - 验证工具schema格式
    - 实现 register_user_tools 方法：为用户注册MCP工具
    - 获取用户token，调用discover_tools
    - 将工具存储在注册表中（user_key: {tool_name: MCPTool}）
    - 实现 unregister_user_tools 方法：取消注册用户的MCP工具
    - 实现 call_tool 方法：调用用户的MCP工具
    - 验证工具是否已注册
    - 验证参数schema
    - 使用用户token调用MCP服务
    - 实现 list_user_tools 方法：列出用户可用的MCP工具
    - 实现 get_tool_info 方法：获取工具的详细信息
    - _需求：需求 6（MCP工具自动发现）、需求 7（MCP工具注册）、需求 8（MCP工具调用）、需求 9（工具隔离性）、需求 10（工具生命周期管理）_
  
  - [x] 8.3 编写MCPToolRegistry的属性测试
    - **属性 7: 工具注册一致性**
    - **验证需求：需求 6.2, 6.3, 7.2**
    - 验证注册的工具是MCP服务器提供工具的子集
    - **属性 8: 工具调用隔离性**
    - **验证需求：需求 9.1, 9.2, 9.5**
    - 验证不同用户调用同名工具使用各自的token
    - **属性 9: 工具生命周期一致性**
    - **验证需求：需求 1.2, 1.3, 4.1, 10.3**
    - 验证token绑定后自动注册工具，解绑后自动取消注册
  
  - [x] 8.4 编写MCPToolRegistry的单元测试
    - 测试工具发现流程
    - 测试工具注册和取消注册
    - 测试工具调用流程
    - 测试工具隔离性
    - 测试工具参数验证
    - 使用mock模拟MCP服务器的工具列表API
    - _需求：需求 6、需求 7、需求 8、需求 9_

- [x] 9. 检查点 - 确保MCP服务层测试通过
  - 确保所有测试通过，如有问题请向用户提问

- [x] 10. 实现指令处理器模块（CommandHandlers）
  - [x] 10.1 实现TokenManagementPlugin类的基础结构
    - 继承AstrBot的Star基类
    - 实现 __init__ 方法：初始化所有组件
    - 初始化DatabaseManager、TokenEncryption、TokenManager
    - 初始化MCPConfig、MCPServiceCaller、MCPToolRegistry
    - 实现插件生命周期方法（如果需要）
    - _需求：需求 13（指令接口）_
  
  - [x] 10.2 实现bind_token指令处理器
    - 使用 @filter.command("bind_token") 装饰器
    - 解析指令参数：提取token
    - 验证参数格式（token非空）
    - 调用TokenManager.bind_token绑定token
    - 调用MCPToolRegistry.register_user_tools自动注册工具
    - 返回成功消息和已注册工具列表
    - 处理错误情况：参数缺失、绑定失败、工具注册失败
    - _需求：需求 1（Token绑定管理）、需求 6（MCP工具自动发现）、需求 7（MCP工具注册）_
  
  - [x] 10.3 实现unbind_token指令处理器
    - 使用 @filter.command("unbind_token") 装饰器
    - 调用MCPToolRegistry.unregister_user_tools取消注册工具
    - 调用TokenManager.unbind_token删除token
    - 返回成功消息确认工具已取消注册
    - 处理错误情况：用户未绑定token、解绑失败
    - _需求：需求 4（Token解绑）、需求 10（工具生命周期管理）_
  
  - [x] 10.4 实现check_token指令处理器
    - 使用 @filter.command("check_token") 装饰器
    - 调用TokenManager.has_token检查token状态
    - 如果已绑定，返回token的部分信息（前4位和后4位）
    - 如果未绑定，提示用户使用bind_token指令
    - _需求：需求 2（Token查询）_
  
  - [x] 10.5 实现update_token指令处理器
    - 使用 @filter.command("update_token") 装饰器
    - 解析指令参数：提取新token
    - 调用MCPToolRegistry.unregister_user_tools取消注册旧工具
    - 调用TokenManager.update_token更新token
    - 调用MCPToolRegistry.register_user_tools重新注册工具
    - 返回成功消息和重新注册的工具列表
    - 处理错误情况：参数缺失、更新失败、工具注册失败
    - _需求：需求 3（Token更新）、需求 10（工具生命周期管理）_
  
  - [x] 10.6 实现list_tools指令处理器
    - 使用 @filter.command("list_tools") 装饰器
    - 调用MCPToolRegistry.list_user_tools获取工具列表
    - 格式化工具列表，包含工具名称和描述
    - 如果用户未绑定token或无工具，返回友好提示
    - _需求：需求 7（MCP工具注册）、需求 19（工具信息查询）_
  
  - [x] 10.7 实现tool_info指令处理器
    - 使用 @filter.command("tool_info") 装饰器
    - 解析指令参数：提取工具名称
    - 调用MCPToolRegistry.get_tool_info获取工具详细信息
    - 格式化工具信息：名称、描述、参数schema、端点、HTTP方法
    - 标识必需参数和可选参数
    - 处理错误情况：参数缺失、工具不存在
    - _需求：需求 19（工具信息查询）_
  
  - [x] 10.8 实现动态工具调用处理器
    - 实现消息处理方法，检查消息是否匹配工具调用格式
    - 解析工具名称和参数（支持 key=value 格式）
    - 调用MCPToolRegistry.call_tool执行工具
    - 格式化工具执行结果并返回
    - 处理错误情况：工具不存在、参数验证失败、调用失败
    - _需求：需求 8（MCP工具调用）、需求 18（工具参数验证）_
  
  - [x] 10.9 编写CommandHandlers的单元测试
    - 测试各个指令的参数解析
    - 测试指令执行流程
    - 测试错误消息格式
    - 使用mock模拟AstrMessageEvent
    - _需求：需求 13（指令接口）_

- [x] 11. 实现错误处理和日志记录
  - [x] 11.1 实现统一的错误处理机制
    - 为每个组件添加异常处理
    - 实现友好的错误消息（不暴露内部细节）
    - 处理10种错误场景（参考设计文档）
    - _需求：需求 12（错误处理）_
  
  - [x] 11.2 实现日志记录功能
    - 配置Python logging模块
    - 记录所有token管理操作（绑定、更新、解绑）
    - 记录所有工具操作（注册、调用）
    - 使用适当的日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
    - 确保日志中不记录完整明文token（仅记录前4位和后4位）
    - _需求：需求 15（日志记录）_
  
  - [x] 11.3 编写错误处理的单元测试
    - 测试各种错误场景的处理
    - 验证错误消息不暴露敏感信息
    - 验证日志记录的完整性和安全性
    - _需求：需求 12、需求 15_

- [x] 12. 实现安全功能
  - [x] 12.1 实现输入验证
    - 验证platform和user_id的长度和格式
    - 验证token不包含危险字符
    - 使用参数化查询防止SQL注入
    - _需求：需求 17（安全要求）_
  
  - [x] 12.2 实现速率限制（可选）
    - 实现token绑定频率限制（每分钟最多5次）
    - 实现MCP服务调用频率限制（每分钟最多20次）
    - 使用内存字典或Redis存储速率限制状态
    - _需求：需求 17.6, 17.7_
  
  - [x] 12.3 编写安全功能的单元测试
    - 测试输入验证
    - 测试速率限制
    - 测试SQL注入防护
    - _需求：需求 17_

- [x] 13. 检查点 - 确保所有功能测试通过
  - 确保所有测试通过，如有问题请向用户提问

- [x] 14. 集成测试和端到端测试
  - [x] 14.1 编写完整的用户绑定流程测试
    - 模拟用户发送 /bind_token 指令
    - 验证token正确存储到数据库
    - 验证工具自动注册成功
    - 验证返回成功消息包含工具列表
    - _需求：需求 1、需求 6、需求 7_
  
  - [x] 14.2 编写完整的MCP工具调用流程测试
    - 先绑定token并注册工具
    - 模拟用户调用工具
    - 使用mock MCP服务验证请求头包含正确token
    - 验证返回正确的工具执行结果
    - _需求：需求 8_
  
  - [x] 14.3 编写Token更新流程测试
    - 绑定初始token并注册工具
    - 更新为新token
    - 验证工具重新注册
    - 验证后续调用使用新token
    - _需求：需求 3、需求 10_
  
  - [x] 14.4 编写多用户并发测试
    - 多个用户同时绑定token
    - 多个用户同时注册工具
    - 多个用户同时调用工具
    - 验证token和工具不会混淆
    - _需求：需求 9_
  
  - [x] 14.5 编写Token解绑与工具清理测试
    - 用户绑定token并注册工具
    - 用户解绑token
    - 验证工具自动取消注册
    - 验证无法再调用工具
    - _需求：需求 4、需求 10_

- [x] 15. 创建插件入口文件和文档
  - [x] 15.1 创建插件主文件
    - 创建 main.py 或 __init__.py 作为插件入口
    - 导入所有组件并初始化
    - 注册插件到AstrBot框架
    - _需求：需求 13_
  
  - [x] 15.2 创建README文档
    - 编写功能说明
    - 编写安装指南（pip install -r requirements.txt）
    - 编写配置说明（环境变量、MCP服务器URL）
    - 编写使用示例（各个指令的用法）
    - 编写故障排除指南
  
  - [x] 15.3 创建示例配置文件
    - 创建 .env.example 文件，展示环境变量配置
    - 创建 mcp_config_example.py，展示自定义配置

- [x] 16. 最终检查点 - 完整系统验证
  - 运行所有单元测试、属性测试和集成测试
  - 验证所有18个正确性属性
  - 验证所有20个功能需求的验收标准
  - 检查代码覆盖率（目标：>80%）
  - 确保所有测试通过，如有问题请向用户提问

## 注意事项

1. **测试优先**：每个核心组件实现后立即编写测试，确保功能正确
2. **安全第一**：token加密存储，日志不记录明文token，使用参数化查询
3. **错误处理**：所有外部调用（数据库、HTTP）都要有异常处理
4. **用户隔离**：确保每个用户只能访问自己的token和工具
5. **异步操作**：使用asyncio和aiohttp实现异步操作，避免阻塞
6. **配置灵活**：支持环境变量覆盖配置，方便部署
7. **日志记录**：记录所有关键操作，使用适当的日志级别
8. **代码质量**：遵循PEP 8代码规范，使用类型注解

## 依赖项

运行时依赖：
- aiosqlite >= 0.17.0（异步SQLite数据库）
- cryptography >= 41.0.0（Fernet加密）
- aiohttp >= 3.8.0（异步HTTP客户端）

开发依赖：
- pytest >= 7.0.0（单元测试）
- pytest-asyncio >= 0.21.0（异步测试）
- hypothesis >= 6.0.0（属性测试）
- pytest-mock >= 3.10.0（Mock支持）
- aioresponses >= 0.7.0（Mock HTTP请求）
- pytest-cov >= 4.0.0（代码覆盖率）

## 实现顺序说明

任务按照自底向上的顺序组织：
1. 首先实现基础设施（加密、数据库）
2. 然后实现业务逻辑层（Token管理、MCP服务调用）
3. 接着实现应用层（工具注册、指令处理）
4. 最后进行集成测试和文档编写

每个阶段都有检查点，确保代码质量和功能正确性。
