# 数据层工程规范

## 数据流与边界

```text
Page / Component
  → feature public API
  → bootstrap-assembled application port
  → API adapter or Demo adapter
  → explicit DTO/view mapper
  → platform HTTP or feature-owned local store
  → validated OpenAPI DTO / validated local storage
```

- 页面只能依赖 `src/features/*/public.ts` 和共享 UI/纯工具，不得直接调用 `uni.request`、拼接后端地址或读取 storage key。
- `src/bootstrap/wiring.ts` 在当前运行模式下装配各模块 adapter；API 失败不得回退到 Demo，也不得在 adapter 内自行选择模式。
- 前端 feature 只能按 `public → presentation/application → domain` 和 `infrastructure → domain` 的许可方向依赖；`scripts/frontend-boundaries.mjs` 检查 alias、相对、type-only、re-export、动态导入、平台 I/O 与循环。它目前直接运行，不是假定存在的 npm script。
- `docs/openapi.json` 是可审查的服务端契约快照，`src/data/contracts/openapi.generated.ts` 由它生成，二者禁止手改。
- DTO 在 HTTP 边界使用 Zod 校验；snake_case 到领域字段的转换必须在端点 mapper 中显式完成。
- `src/main.ts` 必须先引入 `src/platform/contracts/validationRuntime.ts`，再装载业务模块。该模块将 Zod 设为 `jitless`，使用解释执行避免微信沙箱不支持的动态 `Function` 编译；它不跳过 schema 校验，不改变 DTO、存储格式、API/Demo 装配或错误边界。相关回归位于 `validationRuntime.spec.ts`。
- `src/features/*/domain/ports.ts` 是按职责拆开的领域契约；`src/types/records.ts` 保留稳定 record，`types/domain.ts` 保留旧页面 view。中文标签由 `src/shared/mappers` 转换。
- `features/reports/application/reportDraft.ts` 编排先保存会话再保存报告；adapter 仅负责该步骤的传输或本地持久化。训练评分位于 `features/training/domain/scoring.ts`，不复制到 Demo/API 两套实现。
- `src/platform/contracts/conformance.ts` 在类型检查时验证 Zod 输出与生成 DTO 的兼容性；病例推理、阶段答案、学习计划任务和任务启动结果均有嵌套校验。

## 缓存和隐私

- 只有 GET 可以缓存，相同用户、方法、路径和查询参数的并发请求共享一个 Promise。
- 普通列表/详情缓存 30 秒，题目线程缓存 15 秒，分析数据最长 60 秒；未声明 TTL 的请求不缓存。
- 写操作按资源前缀失效缓存；保存或清除 token、401 失效和退出登录会清空全部内存缓存。
- 并发去重共享底层网络 Promise，每个调用者仍校验自己的 schema。缓存上限 128 项。用户变更使用会话版本号拒绝旧结果；资源失效后尚未完成的旧 GET 不得重新填充缓存。
- API 业务响应不得写入本地持久存储。日志只允许记录方法、路由、状态和耗时，不得记录 token、消息、报告或病例隐藏字段。

## 本地存储

- 底层 key、schema version 和 `StoragePort` 由 `src/platform/storage/storage.ts` 管理；学生私有集合仍必须使用用户作用域 key。身份会话的迁移与格式组合位于 `features/identity/infrastructure/sessionStorage.ts`，应用层只依赖 `SessionStoragePort`；其他业务 schema/store 位于所属 feature infrastructure，训练 schema 位于 `platform/storage/caseSchemas.ts` 作为当前兼容集中存储契约。
- 读写都执行运行时 schema 校验。损坏或旧格式值不能进入领域层；迁移必须幂等并保留当前 v2 数据兼容。
- 当前 schema version 为 3。增加字段或改变结构时必须同时新增迁移测试并提升版本。
- 损坏原值保留以便恢复，不用空数组覆盖。旧私有集合仅在验证成功并写入作用域 key 后删除旧 key；API 模式不迁移 Demo 业务集合。

## 错误与兼容

- 后端错误结构为 `{ detail: { code, message } }`；UI 根据稳定 `code` 决定行为，根据 `message` 展示信息。
- 前端过渡期兼容旧的字符串 `detail`，但新增后端代码必须使用统一异常处理器。
- 旧资源列表接口暂时保留；历史记录、报告队列和学生题目优先使用轻量摘要接口。移除旧接口前必须确认无调用方并单独发布弃用说明。
- 查询不存在返回 `undefined`，旧的可空写操作保持 `null`；权限及非法状态转换抛 `AppError`，不能当成空数据。API 404 与旧字符串错误均统一处理。
- Demo 的班级写入和个性化计划写入本轮不模拟服务端能力，显式抛 `UNSUPPORTED_OPERATION`；对应读取保持空模型。核心会话/报告/题目行为由同一组适配器测试验证。
- 报告 client ID 仅在学生范围内唯一；教师按 client ID 命中多条时返回 409，必须改用摘要中的 report ID。学生页使用明确的 `findReportByConversationAsync`，避免纯数字 client ID 与报告 ID 混淆。

旧 `src/services`、`src/data` 运行时入口已清理，仓库内测试已迁移到真实 feature/platform 模块；仅生成 OpenAPI 类型保留在 `src/data/contracts/openapi.generated.ts`。新代码不得继续引用已删除路径。

## 分页和查询预算

- 会话/报告摘要为 `{ items, total, limit, offset }`，默认 20、最大 100，按 `updated_at DESC, id DESC` 稳定排序；预览最多 160 字。报告计数是全部可见数据的计数，不是当前页计数。
- 学生题目 feed 返回全部可见普通题目的轻量数组，SQL 使用集合/EXISTS 查询，HTTP 为单次请求；不附带消息或病例隐藏事实。
- 分页刷新增加请求版本保护，追加页去重并保留已加载记录；追加失败允许再次点击加载更多。页码式 offset 不承诺写入期间的快照隔离，刷新可重新取得最新排序。

## 稳定错误码

| code                                  | 含义                             |
| ------------------------------------- | -------------------------------- |
| AUTH_REQUIRED / ROLE_REQUIRED         | 未登录、身份失效或需要指定角色   |
| FORBIDDEN                             | 没有访问权限                     |
| RESOURCE_NOT_FOUND                    | 不存在或对当前角色不可见         |
| STATE_CONFLICT                        | 状态冲突或查询标识不唯一         |
| VALIDATION_ERROR / INVALID_DATE_RANGE | 输入校验失败                     |
| SERVICE_ERROR                         | 服务端异常（不泄漏内部错误内容） |
| CONTRACT_ERROR                        | 前端拒绝异常 DTO                 |
| NETWORK_ERROR / API_CONFIG_ERROR      | 网络或配置异常                   |
| STALE_SESSION                         | 请求属于已失效的旧会话           |
| UNSUPPORTED_OPERATION                 | 当前适配器未提供该能力           |

## 契约工作流

修改 Pydantic schema 或路由后，在审阅生成差异的工作树执行：

```bash
npm run contract:generate
npm run contract:check
```

`contract:generate` 会写入 `docs/openapi.json`、`src/data/contracts/openapi.generated.ts` 与 fixture；`contract:check` 在系统临时目录生成并按内容比较，不改写快照。远程 CI 是否已接入仍须由平台证据确认。提交必须同时包含后端改动、OpenAPI 快照、生成类型、mapper 和契约测试。

# T14：PBL 当前合同

PBL 诊断快照使用 schema v3，知识薄弱点只能引用 `pathology-general-v3` 的稳定知识点编码，推理问题单独引用能力维度。请求携带 participation 当前阶段和证据起始 revision；响应的阶段证据只允许引用当前窗口内的学生消息。教师队列按最新有效诊断分页（每页 20 条），详情保留 revision。

采用发布在一个事务中写入编辑后的正式题、来源、两轮任务和通知；两轮资源不完整时原子失败。`client_message_id` 返回同一次处理结果，不以最新快照替代重试结果。学习计划保持 `(student_id, source_type, source_id)` 唯一约束，并在同一计划内以 cycle 和 variant 字段区分两轮。API 与 Demo adapter 都返回个人阶段、逐项判定依据和耗尽状态；API 错误不回退 Demo。

# T15：PBL 学情报告合同

`GET /student/pbl-learning-reports` 和 `GET /student/pbl-learning-reports/{session_id}` 按当前学生聚合 PBL 报告。即使本人没有 participation，只要本人收到该课堂的学习计划，也会得到标记为“课堂共同训练”的报告；其他学生的诊断不会进入响应。总览按 session 输出状态统计、下一行动、本人反复出现的目标和最近课堂，详情输出四阶段证据、个人薄弱点、任务、两轮目标对照和判定时间线。

前端 `reportContract.ts` 对 API DTO 做 Zod 校验和显式 mapper，Demo repository 返回相同领域合同。报告只包含任务公开题面、本人得分/反馈和证据是否存在，不包含完整消息、原始答案、正确选项、private rubric、模型提示、隐藏病例事实、教师 ID 或 provider failure；API 请求失败仍不得切换 Demo。

# T17：统一研讨合同

学生统一入口使用 `GET /student/classes` 和 `/student/learning-dialogues` 的列表、创建、start、详情及消息接口。创建请求以学生范围内的 `client_session_id` 幂等，服务端校验有效班级与同一主题下 1～3 个稳定知识点；教师课堂通过 start 首次写入 `interaction_style`，相同方式幂等、不同方式冲突。消息仍以 `client_message_id` 幂等，并保持完成锁定。

新 AI 推理只产生 schema v4，请求与响应均携带 `interaction_style`。CheckedGateway 拒绝方式不匹配、非当前阶段学生消息证据和越级完成；direct 的首问只能得到解释与理解检验，不能单凭提问进入 ready。schema v3 历史诊断仍可查看和采用。旧 QA 接口继续兼容但标记 deprecated，旧 conversation/report 数据不自动写入 PBL session、snapshot 或 learning plan。
