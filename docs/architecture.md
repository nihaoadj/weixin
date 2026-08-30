# 架构设计

## 技术栈

```text
前端：uni-app + Vue 3 + TypeScript + Vite
后端：Python + FastAPI
数据库：SQLite，生产阶段迁移 PostgreSQL
AI：FastAPI 统一网关
```

## 总体架构

```text
微信小程序 / H5
        ↓
uni.request
        ↓
FastAPI HTTP API
        ↓
SQLite 开发库
        ↓
PostgreSQL（生产） / 服务端 AI 网关 / 对象存储（按需）
```

微信小程序只是客户端入口，不再绑定微信云函数作为核心后端。H5、App 或其他端后续都可以接入同一套 FastAPI API。

## 前端目录职责

```text
src/
├── pages/        页面级 Vue SFC，只处理页面状态、跳转和用户交互
├── components/   可复用 UI 组件，不直接写业务持久化逻辑
├── data/         OpenAPI 契约、Repository port、API/Demo adapter、存储网关和 Demo 种子
├── services/     兼容 facade、认证、AI 和业务服务边界
├── types/        与传输 DTO 解耦的领域/展示类型
├── utils/        无状态纯函数
└── static/       图片等静态资源
```

前端数据访问规则：

- `src/services/apiClient.ts` 只负责 FastAPI 传输、token、错误、请求去重和显式内存缓存。
- `VITE_APP_MODE=demo|api` 显式决定运行模式，禁止请求失败时自动切换数据源。
- `src/data/repositories` 定义 port，`src/data/adapters` 分别实现 API 和 Demo adapter，模式在启动时选择一次。
- `src/services/repositoryAsync.ts` 保留页面兼容 facade；生成 DTO 不能直接暴露给页面。
- `src/data/storage.ts` 统一存储 key、用户隔离、版本与运行时校验；API 业务数据不持久缓存。
- 外部 JSON 先经过 Zod 边界校验，再由显式 mapper 转换为领域类型。
- 页面不直接散落 `uni.request`、storage key 或后端 URL。

完整的数据流、缓存和错误约定见 [data-layer.md](./data-layer.md)。

## 后端目录职责

```text
backend/
├── app/api/          FastAPI 路由
├── app/core/         配置、JWT、安全基础设施
├── app/models/       SQLAlchemy 数据库模型，按领域拆分
├── app/schemas/      Pydantic 请求/响应模型，按接口领域拆分
├── app/services/     业务服务，例如医学 AI 安全兜底
├── app/db.py         数据库连接和初始化
├── app/dependencies.py 认证与权限依赖
└── tests/            后端 API 测试
```

后端现在已经从单文件 `models.py`、`schemas.py` 拆分为目录模块，更适合继续扩展。

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

`api/classes.py` 与 `models/classroom.py` 负责班级 owner/member 隔离；`api/medical_review.py` 负责病例审核状态机和 digest；`services/analytics.py` 负责固定时间范围、eligible/started/completed pair 和 current/baseline assessment 口径。前端 `teacherInsights.ts` 只做 DTO 转换，统计结果由后端生成。

# V3 个性化训练编排

完整病例 assessment 完成后由 `personalized.ensure_learning_plan` 幂等创建 `LearningPlan`，确定性选择目标维度和三项 `LearningTask`。任务启动按类型分流到完整 `CaseAttempt` 或唯一 `LearningTaskAttempt`；服务端状态机保证顺序解锁、重复提交幂等和 task-linked assessment 不递归创建新计划。

`case_ai.generate_practice_definition` 只接收审核蓝图的公开字段，输出结构化 public definition；AI 日志保存 task/blueprint/digest 元数据，不保存 prompt 原文。没有真实凭据时由 deterministic fallback 完成同一合同。
