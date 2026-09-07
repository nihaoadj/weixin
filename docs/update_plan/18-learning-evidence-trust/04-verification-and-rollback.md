# 验证与回退

## 验证

- 先运行计划门禁：scoped Prettier、相对链接、尾随空白、`git diff --check` 和工程 skill self-check。
- 后端：安全 fixture、学情报告和 T17 统一研讨回归、完整 backend check、模块边界。
- 契约：`contract:generate` 后审阅 OpenAPI/生成类型/fixture 差异，再运行 `contract:check`。
- 前端：报告和任务组件测试、lint、类型检查、边界、H5/微信构建、API/Demo E2E。
- 安全：秘密扫描；真实 Coze、真机、生产数据库和医学专家审核仅记录为外部项。

## 回退

- 本次无迁移。新增响应字段和 JSON 元数据均可由旧客户端忽略。
- 前端回退后任务与报告数据保持；后端回退前确认客户端能容忍缺少新增字段，再撤回 API 输出。
- 不删除或伪造历史诊断、计划、任务、尝试或评价。
