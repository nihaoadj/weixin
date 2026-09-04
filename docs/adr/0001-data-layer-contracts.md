# ADR 0001：契约驱动的数据层与兼容门面

状态：采纳。日期：2026-08-30。

## 背景

历史页下载会话和报告完整列表、详情先查列表、学生题目逐题读取线程会放大请求与医疗内容传输。Demo/API 混合分支、递归字段转换和未校验存储也使回归边界不清晰。

## 决策

1. FastAPI OpenAPI 是 DTO 唯一来源，快照、生成类型和合成病例契约 fixture 一起维护。运行时 Zod 验证不能由 TypeScript 断言替代。
2. 页面依赖各 feature 的公开入口；业务多步骤操作进入用例；Repository 定义能力，模式在启动时确定；adapter 执行 HTTP 或 StorageGateway，不自动跨模式兜底。
3. API DTO、稳定英文状态的领域 record 与旧中文状态 view 分离。已冻结的 API 列表接口按合同保留；前端旧 service 签名只有在存在具体消费者、兼容窗口和移除条件时才可单独批准。
4. API 只用有上限的短时内存缓存和并发去重；用户切换拒绝旧响应、写操作按资源失效。医疗业务响应不持久化。
5. 历史和教师列表用摘要分页；详情直查；学生普通题目 feed 一次取得状态，避免 N+1。报告同名会话在教师范围内不猜测匹配项。

## 取舍

- 短时缓存不提供离线功能，刷新与错误重试可能产生新请求；安全隔离优先于跨登录复用。
- offset 分页兼容现有页面，稳定排序不等于并发写入快照。客户端防重复，后续如需要严格快照可新增 cursor API，不能无声更改当前协议。
- 为兼容保留旧 view 类型及已冻结 API 接口；本轮页面已迁移到 feature 公开入口，仓内无消费者的旧前端 facade 不保留。Demo 不新增班级/学习计划的完整服务端模拟，未实现能力明确报错。
- 本地 v2 数据兼容迁移到 v3；校验失败保留原值，不破坏可恢复数据。

## 验证与维护

`npm run contract:check` 在临时目录检查契约漂移；`npm run contract:generate` 才会写入快照。S2 记录了当时的前端类型/Lint/覆盖率/双端构建、后端覆盖率和 E2E 结果，但它们不是已经接入远程 CI 的持续门槛。具体改动按 [数据层规范](../data-layer.md) 和现有 package scripts 复验；共享 Repository 测试覆盖空集合、不存在、权限和状态转换，SQL/HTTP 计数测试验证少量与大量题目/摘要请求复杂度。

## T03 分层补充（2026-08-30）

在不改变 OpenAPI、页面路由或本地 key 的前提下，采用按业务模块的纵向分包：`identity`、`qa`、`reports`、`content`、`training`、`learning`、`classroom`、`analytics` 各自拥有窄 port 和 API/Demo infrastructure；`reports` 的跨资源草稿流程通过 `ReportDraftPersistence` 注入，`training` 的确定性评分属于 domain。`bootstrap/wiring.ts` 是唯一装配点；旧 `services/data` 运行时 facade 和 aggregate 在确认仓库内无消费者后删除，不假设仓库外消费者永久存在。

HTTP/cache、底层 storage、runtime、导航、日志和 Zod/OpenAPI conformance 收敛到 `src/platform`；页面仅依赖各 feature 的 `public.ts`。身份迁移和会话格式位于 identity infrastructure，应用只依赖窄 `SessionStoragePort`。由于 T02 已冻结现有生成命令，本轮保留 `src/data/contracts/openapi.generated.ts` 作为唯一生成输出，`src/platform/contracts` 仅持有运行时 schema 与 conformance 引用；没有手改生成物或升级 storage schema version。

边界规则由 `config/frontend-boundaries.json` 声明、`scripts/frontend-boundaries.mjs` 执行，并以 TypeScript AST/SFC script 解析 alias/相对/type-only/re-export/dynamic import、平台 I/O 别名/解构和全图循环；合法/违规 fixture 自测逐项断言。覆盖率不再整包排除 `services/data`，其中只剩生成物和测试；具体证据见 [T03 交付记录](../update_plan/03-frontend-modularization/deliveries/T03.md)。

## T03 增量修复（2026-08-30）

应用会话服务不再读取平台 key/schema 或执行迁移；`sessionStorage.ts` 是唯一身份存储适配器，负责 v2→v3 兼容、校验和用户作用域迁移。旧运行时 facade/aggregate 没有仓库内消费者，所有测试已迁移到真实 feature/platform 路径后删除。边界门禁不再提供 application→storage 白名单例外。

## T04 后端模块化补充（2026-08-30）

后端按 identity、qa、reports、content、training、learning、classroom、analytics 八个业务模块组织，每个模块保留 api/application/domain/infrastructure/public/wiring 边界。生产路由由各模块 `api` 持有；应用层拥有状态决策与事务；repository/query adapter 拥有 SQL；analytics 的跨表统计是独立只读 reader。`app/api`、`app/models`、`app/schemas` 和旧 `app/services` 仅保留兼容转发。具体 operation、表所有权和兼容入口见 [后端模块映射](../backend/module-map.md)。

认证、报告、内容发布、病例训练、学习计划、班级成员和问答用例均通过不可变 `Actor` 合同做二次授权。`SqlAlchemyUnitOfWork` 是 request-scoped 实现，repository 只 flush，应用用例是唯一 commit/rollback 拥有者。跨模块 training→learning 采用 bootstrap composition root + `TrainingCasePort` 的显式两阶段应用调用，依靠已有唯一约束和重试读取实现顺序及并发幂等。

AI 调用不持有业务写事务；transport 通过 port 注入并执行有限重试和确定性 fallback。training/learning 的 AI 审计与业务写入同事务，医学问答的非急症审计同事务；审计或提交失败 rollback 并映射 503。急症分流不调用外部 AI、无持久化 audit。日志仅保留模型、prompt 版本、延迟、fallback、失败类别和关联 ID，不记录提示词、回答或隐藏病例事实。

领域/application 层使用 transport-neutral `AppError`，由 HTTP 边界映射现有错误响应和状态码。旧 service 路径只保留兼容门面、seed 或测试适配；生产默认 assessment gateway 是 `CaseAiGateway`，不再通过 legacy hook 反向导入旧 service，禁止出现第二套生产业务实现。教师报告范围继续由 `ReportPolicy.teacher_scope = "submitted_global"` 保持当前行为，待产品授权政策决定后再替换策略并补测试。

T04 未新增数据库迁移；canonical 模型由 `app/bootstrap/model_registry.py` 唯一注册，工作区继承的 0009 revision 保持原样。`backend/scripts/check_boundaries.py` 与 `config/backend-boundaries.json` 提供 AST 正/负自测，并解析相对导入、别名/from re-export、TYPE_CHECKING 依赖、循环、来源追踪的 SQL/commit；它拒绝核心层框架/ORM/transport 依赖、API 数据库写调用、模块 infrastructure 穿透、动态导入逃逸、`Any` 和全局 ignore 逃逸。AI 候选总分不可信修复作为独立安全修复记录在 T04 交付中，未改变 API 字段。
