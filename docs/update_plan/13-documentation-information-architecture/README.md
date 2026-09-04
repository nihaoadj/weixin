# T13：文档信息架构整理

状态：仓库内完成。本轮整理文档的入口、目录层级和阶段记录位置，不改变应用行为、API、数据、迁移、权限或 AI 配置。

## 目标

让首次查看仓库的人能从 `docs/README.md` 找到当前权威文档，从 `docs/update_plan/README.md` 找到当前更新计划，并在需要时进入完整的历史计划与交付证据。

## 非目标

- 不删除历史任务书、交付记录或验收结论，不改写其内容含义。
- 不运行数据库迁移、种子、外部服务、模型调用、构建或 E2E。
- 不把历史计划的结论提升为当前实现或生产验收事实。

## 文档索引

1. [当前审计](01-current-audit.md)
2. [目标信息架构](02-target-information-architecture.md)
3. [迁移与链接策略](03-migration-and-links.md)
4. [实施任务](04-implementation-tasks.md)
5. [验证与回退](05-verification-and-rollback.md)
6. [交付记录](deliveries/T13.md)

执行本轮整理时遵守仓库根目录 [AGENTS.md](../../../AGENTS.md) 的文档计划门禁、已有工作保护和链接验证要求。
