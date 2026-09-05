# 架构设计

## 技术栈

```text
前端：uni-app + Vue 3 + TypeScript + Vite
后端：Python + FastAPI + SQLAlchemy + Alembic
数据库：SQLite（开发与受管测试）
AI：可选的服务端 gateway；测试禁用真实外部调用
```

## 总体架构

```text
微信小程序 / H5
        ↓
feature public API → bootstrap wiring → platform HTTP
        ↓
FastAPI HTTP API
        ↓
模块 application / domain / infrastructure
        ↓
SQLite（开发或 launcher-owned 临时测试库）
```

微信小程序只是客户端入口，不再绑定微信云函数作为核心后端。H5 可接入同一套 FastAPI API。PostgreSQL、对象存储、生产 AI 网关和其他客户端接入是后续方向，不是当前运行调用链或发布承诺。

## 前端目录职责

```text
src/
├── pages/        路由入口，只组合公开 feature API、页面状态和交互
├── components/   可复用 UI，不直接写业务持久化逻辑
├── features/     identity/qa/reports/content/training/learning/classroom/analytics
│   ├── public.ts 对外稳定应用能力和展示类型
│   ├── presentation/（按需）页面/组件状态
│   ├── application/ 用例编排与窄 port
│   ├── domain/      领域 port、对象和纯规则
│   └── infrastructure API/Demo adapter、Zod、mapper、本地集合
├── platform/      runtime、HTTP/cache、底层 storage、导航、日志和契约
├── bootstrap/     唯一 API/Demo 组合根与 Demo 初始数据装配
├── shared/        有明确复用者的纯 mapper/status 工具
├── types/         兼容的纯领域/展示类型（不承载 I/O）
├── utils/         无状态纯函数
├── services/      不再承载运行时代码（历史测试已迁移到真实模块）
├── data/          仅保留 `contracts/openapi.generated.ts` 生成物
└── static/        图片等静态资源
```

前端数据访问规则：

- 页面只从 `src/features/*/public.ts` 引入业务能力；页面和组件不导入 feature 的 `application/domain/infrastructure`。
- `src/bootstrap/wiring.ts` 是唯一运行时组合根，按 `VITE_APP_MODE=demo|api` 装配每个 feature 的 port 实现；请求失败不会切换数据源。
- `src/platform/http/apiClient.ts` 负责 FastAPI 传输、token、错误、请求去重和显式内存缓存；身份失效通过平台 API 清理，不反向导入页面。
- `VITE_APP_MODE=demo|api` 显式决定运行模式，禁止请求失败时自动切换数据源。
- `src/platform/storage/storage.ts` 只提供底层存取、key 和运行时校验；身份迁移/会话格式由 `features/identity/infrastructure/sessionStorage.ts` 适配，QA、报告、内容和训练的实际本地 store 归各自 feature infrastructure。
- API/Demo adapter 只实现所属 feature 的窄 domain port。报告应用用例通过显式 persistence port 保证“先会话、后草稿”。
- `src/platform/contracts` 持有 Zod/契约 conformance；当前生成文件仍由既有工具写入 `src/data/contracts/openapi.generated.ts`，该文件是唯一生成物且禁止手改。
- 旧 `src/services/*` facade、旧 `src/data/*` aggregate/mapper 已无仓库内消费者并已删除；生成 OpenAPI 类型仍按既有命令保留在 `src/data/contracts/openapi.generated.ts`。
- 外部 JSON 先经过 Zod 边界校验，再由显式 mapper 转换为领域类型。
- 页面不直接散落 `uni.request`、storage key 或后端 URL。

完整的数据流、缓存和错误约定见 [data-layer.md](./data-layer.md)。
公开应用接口见 [frontend/public-interfaces.md](frontend/public-interfaces.md)；依赖门禁由 `scripts/frontend-boundaries.mjs` 和 `config/frontend-boundaries.json` 实施，直接运行脚本（尚无 npm alias）。

## 前端模块映射

| 业务模块  | 领域/应用拥有者                                         | API/Demo infrastructure                                                  | 页面公开入口                   |
| --------- | ------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------ |
| identity  | `features/identity/domain`、`application/session.ts`    | `sessionDependencies.ts`、`remoteAuth.ts`                                | `features/identity/public.ts`  |
| qa        | `features/qa/domain`、`application/medicalAssistant.ts` | `apiQaRepository.ts`、`demoQaRepository.ts`、会话/问答 store             | `features/qa/public.ts`        |
| reports   | `features/reports/domain`、`application/reportDraft.ts` | `apiReportRepository.ts`、`demoReportRepository.ts`、report mapper/store | `features/reports/public.ts`   |
| content   | `features/content/domain`                               | `apiContentRepository.ts`、病例/题目 store、case mapper                  | `features/content/public.ts`   |
| training  | `features/training/domain`（含确定性评分）              | `apiTrainingRepository.ts`、`demoCaseStore.ts`、case mapper              | `features/training/public.ts`  |
| learning  | `features/learning/domain`                              | `apiLearningRepository.ts`、`demoLearningRepository.ts`                  | `features/learning/public.ts`  |
| classroom | `features/classroom/domain`                             | `apiClassroomRepository.ts`、`demoClassroomRepository.ts`                | `features/classroom/public.ts` |
| analytics | `features/analytics/domain`                             | `apiAnalyticsRepository.ts`、`demoAnalyticsRepository.ts`                | `features/analytics/public.ts` |
| pbl       | `features/pbl/domain`                                   | `apiPblRepository.ts`、`demoPblRepository.ts`                            | `features/pbl/public.ts`       |

跨模块依赖只向领域 port 或公开接口收敛；实际 API/Demo 选择和跨模块对象连接集中在 `bootstrap/wiring.ts`。`types/domain.ts` 的中文状态和 `types/records.ts` 的稳定英文状态由 `shared/mappers/presentation.ts` 转换，避免 DTO、存储值和页面标签混用。

## 后端目录职责

```text
backend/
├── app/modules/<module>/
│   ├── api/           FastAPI router 与该模块 HTTP schema
│   ├── application/   用例、port、事务编排与 record
│   ├── domain/        无框架状态、评分、安全与可见性策略
│   ├── infrastructure/ ORM、repository、query/外部服务 adapter
│   ├── public.py      跨模块公开合同与 view mapper
│   └── wiring.py      模块实现装配入口
├── app/bootstrap/    app/router、模型注册、开发 seed 与跨模块 composition root
├── app/platform/     数据库 Base、UoW/AI 等平台适配
├── app/shared/       Actor、AppError、稳定基础合同
├── app/api/          旧 HTTP 导入兼容 alias，不拥有路由实现
├── app/models/       旧 ORM 导入兼容 re-export，不定义表
├── app/schemas/      旧 schema 导入兼容 re-export，不定义合同
├── app/services/     旧 facade、测试/开发 seed 兼容入口，不是生产业务实现
├── app/db.py         数据库连接与 metadata 初始化入口
├── app/dependencies.py 认证依赖与 User→Actor 适配
└── tests/            后端 API、领域、迁移与安全测试
```

八个业务模块为 `identity`、`qa`、`reports`、`content`、`training`、`learning`、`classroom`、`analytics`。生产 `app.main` 直接装配各模块 `api` router；`app/bootstrap/model_registry.py` 是唯一跨模块 ORM metadata 注册汇合点。中央兼容目录仍因历史调用方存在，但没有 ORM/Pydantic 定义或生产业务逻辑。R05 进一步规定：一个模块的 `api` 只能由另一模块的 `api` 或 `wiring` 直接引用；application/domain/infrastructure 跨模块协作必须通过 `public.py` 合同或明确 port。`backend/scripts/check_boundaries.py` 与 `config/backend-boundaries.json` 负责检查这项规则。

## 当前接入状态

配置 `VITE_APP_MODE=api` 和 `VITE_API_BASE_URL` 后，前端以下链路会走 FastAPI：

- Demo 登录与 token 保存
- AI 问答
- 对话保存与历史记录
- 报告生成、提交和教师批阅
- 教师题目创建、编辑、发布、拒绝
- 学生题目列表与作答线程
- 结构化病例五阶段训练、医学审核和 clone version
- 班级管理、病例/学生学情分析与日期范围下钻
- 个性化学习计划、微训练、复盘和站内通知
- 题目统计中的作答数量

`VITE_APP_MODE=demo` 时前端使用确定性本地数据；两种模式不会在运行中混写。

# 第二阶段服务边界

`modules/classroom` 负责班级 owner/member 隔离；`modules/content` 负责病例审核状态机和 digest；`modules/analytics` 负责固定时间范围、eligible/started/completed pair 和 current/baseline assessment 口径。前端 `features/analytics` 只通过 infrastructure mapper 消费 DTO，统计结果由后端生成。旧 `app/services/analytics.py` 仅转发到 analytics application。

# V3 个性化训练编排

完整病例 assessment 完成后由 `modules/learning` application 幂等创建 `LearningPlan`，确定性选择目标维度和三项 `LearningTask`。任务启动按类型分流到完整 `CaseAttempt` 或唯一 `LearningTaskAttempt`；服务端状态机保证顺序解锁、重复提交幂等和 task-linked assessment 不递归创建新计划。learning 只依赖 `training.public.TrainingCasePort`，不穿透 training application。

`learning.infrastructure.practice_generator` 只接收审核蓝图的公开字段，输出结构化 public definition；AI 日志保存 task/blueprint/digest 元数据，不保存 prompt 原文。没有真实凭据时由 deterministic fallback 完成同一合同。训练 AI 候选只能更新经学生答案白名单校验的反馈/下一步，不能写入确定性分数、权重、总分或 evidence。

# T09：`pbl` 是独立业务模块，拥有课堂会话、参与记录、诊断快照和教师建议题；前端只能通过 `features/pbl/public.ts`，并由 `src/bootstrap/wiring.ts` 选择 API/Demo adapter。建议题发布走 content 的公开桥接，PBL 不直接管理正式题生命周期。

# T14：PBL 参与级阶段与自动巩固

每个 `PblParticipation` 独立维护明确问题、提出假设、讨论证据、总结解释和完成状态。AI schema v3 只提出当前阶段的 `continue/advance/complete`，PBL application 与 repository 共同校验当前阶段开始后的学生消息证据和相邻推进；完成后新消息被锁定，相同消息 ID 仍返回原结果。

教师采用发布仍是医学教学内容进入学生端的唯一入口。content 在事务内提供 `pathology-general-v3` 两轮已审核资源，learning 预建 cycle 1/2；cycle 2 初始 inactive。learning 的确定性 `pbl-mastery-v1` 按知识再测 100、推理微训练 70、病例目标维度 70 逐项判定，首轮失败仅激活失败目标，二轮失败进入耗尽且需要线下支持。教师结果区只读，旧阶段 PATCH 和 verify POST 仅保留 deprecated 冲突合同。

# T15：学生 PBL 学情报告读模型

`pbl` application 通过窄 port 读取本人 participation/阶段快照和本人 learning plans，将同一 session 的个人讨论、课堂共同训练、任务、attempt 与不可覆盖的轮次评价组装为只读报告。报告状态和说明由确定性规则生成，不调用 AI、不计算综合分。前端 `features/pbl` 的 API/Demo adapter 实现同一 `reports/report` 合同，“学情”总览与详情页面只经 `features/pbl/public.ts` 读取。

# T16：前端信息架构与导航

学生一级导航固定为课堂、学习、学情、答疑，对应 `StudentPrimaryRoute` 的四个根页面；病例训练、知识地图和练习题继续使用既有 `studentCases` 路径，但由 `view=cases|knowledge|questions` 在学习模块的二级资源页中切换。一级切换使用 `reLaunch`，一级进入详情使用 `navigateTo`，连续训练步骤使用 `redirectTo`；二级页通过明确的逻辑父页面处理直接打开和返回兜底。

教师工作区仍使用 `overview|reports|problems|pbl` 内部 key 和 `?tab=` 深链接，并以 `v-show` 保留切换状态；展示标签收敛为待办、学情、内容、PBL。H5/微信原生导航栏是一级页面唯一可见标题，正文使用不可见页面标题和紧凑上下文条提供无障碍名称，不重复渲染同义 Hero。此变化只影响前端路由语义、页面组合和样式，不改变 feature API、API/Demo 装配、后端接口或数据合同。
