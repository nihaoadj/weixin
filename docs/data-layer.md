# 数据层工程规范

## 数据流与边界

```text
Page / Component
  → services compatibility facade
  → use case (multi-resource business ordering)
  → Repository port
  → API adapter or Demo adapter
  → explicit mapper
  → validated OpenAPI DTO / validated local storage
```

- 页面只能依赖领域类型和 service facade，不得直接调用 `uni.request`、拼接后端地址或读取 storage key。
- `VITE_APP_MODE` 在 Repository 容器初始化时选择一次 adapter；API 失败不得回退到 Demo。
- `docs/openapi.json` 是可审查的服务端契约快照，`src/data/contracts/openapi.generated.ts` 由它生成，二者禁止手改。
- DTO 在 HTTP 边界使用 Zod 校验；snake_case 到领域字段的转换必须在端点 mapper 中显式完成。
- `src/types/records.ts` 是核心 Repository 的领域契约，状态为 `draft/pending_review/reviewed`、`draft/published/rejected`、`answered/unanswered`。原 `types/domain.ts` 暂留作页面兼容类型；中文标签由 `mappers/presentation.ts` 和 `mappers/status.ts` 转换。
- `repositories/core.ts` 按会话、报告和题目定义窄接口；病例、学习计划、教师分析分别有独立接口。容器/门面只在初始化时选模式。
- `usecases/reportDraft.ts` 编排先保存会话再保存报告；adapter 仅负责该步骤的传输或本地持久化。病例旧 service 导出保持兼容，训练和审核状态已使用英文代码。
- `contracts/conformance.ts` 在类型检查时验证 Zod 输出与生成 DTO 的兼容性；病例推理、阶段答案、学习计划任务和任务启动结果均有嵌套校验。

## 缓存和隐私

- 只有 GET 可以缓存，相同用户、方法、路径和查询参数的并发请求共享一个 Promise。
- 普通列表/详情缓存 30 秒，题目线程缓存 15 秒，分析数据最长 60 秒；未声明 TTL 的请求不缓存。
- 写操作按资源前缀失效缓存；保存或清除 token、401 失效和退出登录会清空全部内存缓存。
- 并发去重共享底层网络 Promise，每个调用者仍校验自己的 schema。缓存上限 128 项。用户变更使用会话版本号拒绝旧结果；资源失效后尚未完成的旧 GET 不得重新填充缓存。
- API 业务响应不得写入本地持久存储。日志只允许记录方法、路由、状态和耗时，不得记录 token、消息、报告或病例隐藏字段。

## 本地存储

- 所有 key 和 schema version 由 `src/data/storage.ts` 管理；学生私有集合必须使用用户作用域 key。
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

修改 Pydantic schema 或路由后执行：

```bash
npm run contract:generate
npm run contract:check
```

CI 会重新生成契约并检查工作区差异。提交必须同时包含后端改动、OpenAPI 快照、生成类型、mapper 和契约测试。
