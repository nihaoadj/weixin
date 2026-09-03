# T08 问答驱动的医学知识巩固闭环

状态：核心闭环、教师补充卡/审核、报告复习标记、班级聚合、`recall` 自评和仓库内验收已实现；最终交付证据见 `deliveries/final-closeout.md`。本文仍是计划与事实索引，不以计划替代验收证据。

## 当前事实

- 学生端已有医学问答、问题线程、病例训练、能力画像、个性化训练、报告和学习记录。
- `VITE_APP_MODE=demo|api` 在启动时固定选择数据源；失败不得切换模式。
- 后端已有 `qa`、`content`、`learning`、`reports`、`analytics` 等模块。页面必须经 feature `public.ts` 调用，跨模块必须经稳定合同或 wiring 注入。
- 当前工作区含大量未提交和未跟踪改动；本任务不得恢复、覆盖、删除或提交他人改动。
- 大模型尚未正式接入。本轮不能依赖模型抽取知识点、生成内容或判分。

## 计划目标

通过“选择主题 → 带上下文问答 → 收藏/追问 → 结束小测 → 间隔复习 → 再次问答”建立学习闭环。可靠学习证据只来自客观小测、确定性病例/微训练评分、教师显式标记和学生主动收藏；未来模型只能提供待学生确认的候选知识点，不能写入分数或复习周期。

## 任务书

| 文档 | 用途 |
| --- | --- |
| [01-product-learning-loop.md](01-product-learning-loop.md) | 用户流程、状态与范围 |
| [02-qa-integration-spec.md](02-qa-integration-spec.md) | 问答主体联动与未来模型边界 |
| [03-catalog-review-content.md](03-catalog-review-content.md) | 知识目录、卡片、审核和调度 |
| [04-data-api-contracts.md](04-data-api-contracts.md) | 模块、数据、API、权限和兼容性 |
| [05-implementation-tasks.md](05-implementation-tasks.md) | M01～M07 实施顺序和验收条件 |
| [06-test-rollout-rollback.md](06-test-rollout-rollback.md) | 测试、迁移、发布与回退 |
| [deliveries/template.md](deliveries/template.md) | 本轮交付记录模板 |

## 边界

本轮不接入真实大模型、不执行生产迁移或历史回填、不发送微信订阅消息、不创建医学计算器或模拟考试。系统知识库为版本化只读内容；教师只能向既有知识点补充卡片，且需经医学审核后才向学生可见。
