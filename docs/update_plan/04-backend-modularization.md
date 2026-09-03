# T04 后端业务分包与分层重构任务书

状态：待执行。优先级：P1。执行角色：熟悉 FastAPI、SQLAlchemy、事务和领域建模的后端工程师。

## 1. 目标与范围

把路由中的业务决策、查询和提交行为，以及混合 HTTP/ORM/业务规则的大 service，拆成业务模块内的接口、应用、领域和基础设施职责。保持单体部署、API 行为、权限与数据兼容，并用自动检查约束后续依赖。

本任务不重新设计产品状态机、不重写历史迁移、不批量更名数据库表、不切换生产数据库、不建立无实际需求的通用 CRUD 框架。已经存在的安全缺陷由 T06 明确预期后修复，不能当作“保持行为”而保留漏洞。

## 2. 输入与依赖

必读：[架构](../architecture.md)、[数据库](../database.md)、[API](../api.md)、[安全](../security.md)、[总计划](README.md)、[T01](01-test-database-safety.md)、[T05](05-critical-tests-coverage.md)。

代码起点：[题目路由](../../backend/app/api/problems.py)、[报告路由](../../backend/app/api/reports.py)、[个性化服务](../../backend/app/services/personalized.py)、[病例训练服务](../../backend/app/services/case_training.py)、[医学 AI](../../backend/app/services/medical_ai.py)、[模型注册](../../backend/app/models/__init__.py)、[Alembic env](../../backend/alembic/env.py)。

先完成 T04-01 设计；实际重构需要 T01 已验收、T05-01/02 形成基线、T02 基础后端检查可用。与 T03 共享业务术语，但不要求前后端每一个目录完全一致。

## 3. 目标业务分包

默认放在 `backend/app/modules/` 下，模块名与前端 identity、qa、reports、content、training、learning、classroom、analytics 对齐。医学审核归 content；普通题目作答线程归 qa，题目内容和发布策略归 content；学习通知先归 learning。

公共目录以职责划分：`app/bootstrap/` 装配 app/router/依赖及模型注册；`app/platform/` 负责数据库连接、配置、日志和外部客户端；`app/shared/` 只承载稳定、无业务反向依赖的基础类型和错误。开发数据与导入脚本归独立开发工具/seed 包，业务运行代码不得导入其常量或 payload。

| 层/边界         | 应包含的逻辑                                                      | 约束                                                       |
| --------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| api/            | FastAPI router、请求响应 schema、身份依赖适配、异常映射           | 不执行业务 SQL、不决定训练/发布状态、不 commit             |
| application/    | 用例、查询服务、port、事务/UoW 边界、跨能力编排                   | 不依赖 FastAPI，不直接调用 httpx 或其他模块 ORM            |
| domain/         | 状态机、评分、权限判断所需纯策略、领域对象和值对象                | 不导入 FastAPI、SQLAlchemy、Pydantic 请求 schema、配置单例 |
| infrastructure/ | ORM models、repository/query adapter、数据库 mapper、外部服务适配 | 实现 port；不能自行改变用例状态流                          |
| public.py       | 公开应用合同和必要类型                                            | 不把所有内部对象重新导出给其他模块                         |
| wiring.py       | 组装模块实现                                                      | 仅 bootstrap 使用，不向任意业务层暴露 service locator      |

简单查询无需制造多层无逻辑包装，但仍必须有明确 SQL 归属。领域对象只在有业务意义的地方建立，禁止为了层数给每张表复制三份无差异模型。

## 4. 必须明确的依赖与数据规则

1. 接口调用用例；用例依赖 port 和领域；infrastructure 实现 port，由 bootstrap 注入。领域/应用错误由 HTTP 边界映射，不能在核心规则里抛 HTTPException。
2. 认证解析在 HTTP 边界完成，但应用用例仍检查 actor 的角色、owner、资源范围和状态；不能假设“从 router 进来就一定有权限”。
3. 每个业务写操作有唯一的事务拥有者。repository 负责读取/flush，不私自 commit；聚合写入由应用 UoW 或等价机制提交/回滚。
4. 外部 AI/微信调用不能长期持有数据库写事务；重试和审计需定义一致性策略。必须保留幂等性，不因分层拆开就让重复请求产生多条 assessment/plan。
5. 一个模块拥有其写模型；其他模块经公开应用 port 使用。跨模块事务由明确的上层用例/共享 UoW 组织，不形成 learning 和 training 相互导入。
6. analytics 的跨表读查询必须有独立只读 query adapter 和明确读模型合同；允许为性能保留集合 SQL，但不能把查询用途扩大为修改其他模块 ORM。所需跨表依赖在 ADR 精确列出，不为绕过边界设置整包白名单。
7. ORM 表名、列名、relationship、索引、唯一约束与序列化输出必须与原合同对照。Python 文件移动不构成生成数据库重建迁移的理由。
8. 元数据由启动/迁移专用注册入口加载；模型映射跨模块关系需要的装配依赖仅位于该入口及精确声明的 ORM 位置，不能沿此路径污染 domain/application。

## 5. 分步实施

### T04-01 建立接口、表与职责清单

枚举全部路由、OpenAPI operation、响应字段、状态码、数据库表、模型、服务和调用方。建立“旧符号 → 新模块/层/公开接口”表，标出 HTTPException、select、commit、httpx 和种子依赖的位置。

确定模块可允许的依赖图；重点解决 reports/qa、content/training、learning/training、analytics/各模块的关系。记录 actor 合同、UoW 合同、领域错误映射和只读统计查询例外。先给报告迁移准备设计，不等待整份文档任务完成。

产出：ADR、模块依赖图、接口和模型对照表。完成标准：每个生产路由和表有明确拥有者，无双重写入责任。

### T04-02 提取平台依赖与业务常量

整理数据库 factory、配置、JWT、日志、AI/微信 transport 和 app 生命周期，保留 T01 的测试注入接口。合同导出不能连接业务库、自动建表或导入种子。

将病例阶段、能力维度、评分权重、安全文案等按实际语义放入领域/展示/配置边界。当前 case_training 导入 case_seed 的 SAFETY_NOTICE、personalized 从请求 schema 导入维度定义，需要解除这种反向依赖；seed 改为消费业务定义，而非成为业务规则的来源。

生产代码不得 import 测试工具或开发 seed。Demo/showcase 初始化由明确的非生产启动配置触发，而不是业务模块导入时发生。

产出：受控平台接口、常量归属、无副作用导入测试。

### T04-03 迁移报告领域作为样板

提取创建草稿、提交批阅、教师批阅用例，以及报告可见性、状态转换、摘要查询。将 SQL 和序列化分别归 query/repository adapter 与响应 mapper，router 只解析输入、传 actor、调用应用用例和返回响应。

保留 reviewer 记录、报告与会话 ID 兼容、学生范围、教师可见范围、pending/reviewed 统计口径。模拟中途异常验证事务回滚；直接调用应用用例也必须拒绝越权与非法状态。

旧接口返回结构和错误码不得因把 dict 换成 DTO 而改变。用 T05 的报告行为矩阵与 OpenAPI 比较确认，再推广样板。

### T04-04 迁移内容、审核与发布规则

把题目/病例创建、更新、clone、送审、审核、发布拆成应用用例。发布用例必须统一处理 owner、内容完整性、审核状态、当前内容 digest 和版本检查；不要分散在多个 router 中复制判断。

处理现有“摘要不一致则将审核状态失效并返回冲突”的写入语义：明确这是需要持久化的状态变更还是整体回滚，按当前合同/安全要求保留并用测试证明。不能因统一 rollback 而把安全失效标记撤销。

版本唯一冲突重试应有上限；发版/审核状态由服务端决定；public 与 authoring DTO 继续分离，不让学生拿到 rubric 或隐藏事实。

### T04-05 迁移训练、学习计划与 AI 编排

拆分训练状态转换、确定性评分、患者回复和 assessment 写入；训练完成后创建学习计划的流程放到可明确依赖两方 port 的编排层，避免模块双向调用。

个性化服务按计划选择/生成、任务启动/提交、微训练结果、通知和响应映射分责。AI 生成及其 schema 校验通过注入 port；确定性评分归领域，模型仅改写允许的反馈。

明确 source_assessment、task position、task attempt 等唯一约束与数据库 IntegrityError 到业务冲突的映射；并发重复请求不能产生重复计划，task-linked assessment 不能递归生成计划。

为 AI 审计选择显式策略：审计不再在通用 helper 中随意 commit 业务 session；说明独立短事务/随业务事务等选择以及审计失败时的行为，并保持日志脱敏。网络失败的 fallback 不应改变 API/Demo 客户端运行模式。

### T04-06 迁移认证、问答、班级和统计

认证模块分开账号策略、微信交换客户端、token 签发与 HTTP 响应；保留 auth_provider 隔离、服务端教师白名单以及生产 Demo 禁用。

问答负责会话和消息及普通题目作答；班级负责 owner/member；统计通过只读 query adapter 返回既有口径。保持摘要轻量化、稳定排序、分页上限、预览长度和固定查询次数，不把集合查询改成循环逐行查询。

同步类型检查，新 domain/application 全面消除 HTTP 和 ORM 类型泄漏。不可用 Any 或全局 ignore_errors 替代明确 port。

### T04-07 迁移模型注册、脚本并清理旧入口

同步 app factory/router 注册、Alembic target_metadata、seed 和合同导出器。跨表 relationship 在新包位置仍可正确初始化；比较迁移前后 metadata，纯分包不应产生表/列删除。

保留必要的旧导入转发期，并记录消费者。所有仓库内调用完成后删除旧 service 实现和无引用转发；历史 Alembic revision 如依赖旧导入，优先提供窄兼容入口而非改写已发布脚本，并明确这类兼容入口的保留原因。

复跑空库/旧库/head 的迁移矩阵，特别包含实际 0009；不因 Python package 变化漏注册模型。

### T04-08 实现包依赖检查并完成验收

提供 `backend:boundaries`，采用 Python AST/合适的包分析工具，检查绝对/相对导入、re-export、TYPE_CHECKING 和循环依赖。禁止 domain/application 导入 FastAPI/ORM/transport、api 执行业务 SQL/commit、模块穿透其他模块 infrastructure、生产模块依赖 seed/tests。

元数据注册、统计读模型等例外按具体路径和用途列出，要求规则自测，不允许允许整个 app 随意互相依赖。动态 import 无法静态确认时列入显式审核清单，禁止用动态导入逃避规则。

## 6. 验收矩阵

| ID    | 方法                                       | 通过条件                                     |
| ----- | ------------------------------------------ | -------------------------------------------- |
| BE-01 | 扫描模块依赖和违规 fixture                 | 合法图通过，禁止依赖能失败，无未声明环       |
| BE-02 | 无 FastAPI/DB 的纯领域测试                 | 评分、阶段、发布前置规则可独立测试           |
| BE-03 | 直接调用应用用例尝试越权                   | 跨学生、跨教师、无审核权限均拒绝             |
| BE-04 | 报告写入中途失败、非法状态请求             | 事务一致；无半写入或无归属 commit            |
| BE-05 | 审核后修改内容再发布                       | 拒绝过期审核，状态/digest 处理符合合同       |
| BE-06 | 并发/重复完成训练和启动任务                | 无重复 assessment/plan/attempt，无递归计划   |
| BE-07 | AI 超时、坏输出、审计异常                  | 有界处理，评分确定，安全日志和一致性策略明确 |
| BE-08 | OpenAPI/响应合同与旧新 metadata 比较       | 无未批准接口变化，无表/列丢失                |
| BE-09 | T01 迁移、安全 fixture 全量回归            | 实际 head 可升级，开发资源不受影响           |
| BE-10 | 原有 10,000 attempt 性能场景、摘要查询测试 | 原查询预算保留，无 N+1；主验收环境性能不退化 |
| BE-11 | 搜索旧 service、模型注册及 seed 导入       | 无重复业务实现；必要历史兼容入口有清单       |

现有性能测试要求统计三类查询总 SQL 次数小于 30、运行小于 2 秒；先在同一固定环境记录基线，保持预算。若 CI 资源波动影响时间，需报告多次测量并区分资源问题，不能直接放大阈值掩盖 N+1。

## 7. 验证命令

T01 完成、相关目标命令实现之后，从根目录执行：

```bash
npm run backend:test:safety
npm run backend:test:migrations
npm run backend:boundaries
npm run backend:type-check
npm run backend:check
npm run backend:test:critical
npm run contract:check
npm run test:e2e
```

纯结构迁移应保持现有生成合同内容一致；因代码移动改变 operationId 的非预期差异也需解决或独立审阅，不直接重新生成接受所有变化。

## 8. 完成标准与交付物

- [ ] BE-01～BE-11 全部有结果；HTTP、数据库和领域的边界可由代码和测试证明。
- [ ] 每个生产路由、表和外部集成都有唯一责任模块；不存在“剩下全放 services”的尾部大包。
- [ ] 所有写用例有明确事务拥有者；网络调用、审计、冲突和幂等处理有设计与验证。
- [ ] 新 domain/application 满足类型与依赖检查；没有通过 Any、忽略文件或动态 import 绕过。
- [ ] 迁移/注册/契约/性能和安全 fixture 保持通过，旧业务实现清理完成。
- [ ] 交付 ADR、模块/路由/表映射、UoW 和错误合同、依赖自测、回归证据及 `deliveries/T04.md`。

## 9. 回退与风险

按业务模块回退代码及注册，不对数据库执行反向破坏来配合目录回退。若没有 schema 变更，包重构回退不应需要 Alembic downgrade。确需新迁移时另列数据影响、备份和恢复步骤，保持与 T01 的迁移合同。发现状态政策或旧安全缺陷存在歧义时先记录期望与证据交 T06/负责人决定，不能任意改行为再让测试追随实现。
