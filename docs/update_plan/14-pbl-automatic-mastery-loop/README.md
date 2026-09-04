# T14：PBL 自动阶段与自动巩固闭环

状态：仓库内实施与本地验收完成；真实 Coze schema v3、微信真机、医学专家审核与生产部署仍待外部验收。

## Summary

将 PBL 四阶段由课堂级教师手工标签改为学生参与级自动状态机，并以版本化、确定性的逐项目标规则自动判定“已改善”或“继续巩固”。教师仍审阅和发布 AI 建议题，但最终学习结果区只读，不再决定学生下一步。

自动巩固最多两轮：首轮未达标时仅激活失败目标的第二轮等价变式；第二轮仍未达标时保留 `needs_reinforcement`，设置 `automation_exhausted=true`，提示需要线下支持。

## 目标

- 每个 `PblParticipation` 独立维护 `problem_framing → hypothesis → evidence → synthesis → completed`。
- AI schema v3 提供阶段评估，服务端验证阶段、证据时序和相邻推进。
- 在采用发布事务中预创建两轮任务，第二轮初始为 inactive。
- 使用逐项阈值和证据完整性自动评估轮次，失败关闭式处理。
- 学生看到个人阶段、缺失要素、两轮任务和系统判定；教师看到阶段分布和只读结果依据。
- API、Demo、Coze Bot/Workflow、开发专用 OpenAI-compatible 使用同一合同。

## 非目标

- 不授权真实 Coze、微信真机、生产部署、外部账号或医学专家审核。
- 不允许 AI 绕过教师自动发布医学教学内容。
- 不把 Demo 或开发专用提供方结果当作生产闭环证据。
- 不删除历史人工核验字段，也不静默丢弃 schema v3 或第二轮业务数据。

## 文档索引

1. [当前审计](01-current-audit.md)
2. [产品状态机](02-product-state-machine.md)
3. [自动判定与变式策略](03-automatic-decision-and-variants.md)
4. [API 与数据设计](04-api-data-design.md)
5. [实施任务](05-implementation-tasks.md)
6. [验证与回退](06-verification-rollback.md)
7. [交付模板](deliveries/template.md)
8. [T14 交付记录](deliveries/T14.md)

实施遵守根目录 [AGENTS.md](../../../AGENTS.md) 和相关权威文档；计划门禁通过后才修改运行时代码。实际命令、退出码、已知限制和回退说明见 [T14 交付记录](deliveries/T14.md)。

后继更新：[T15 学生 PBL 学情报告与改善轨迹](../15-pbl-student-learning-report/README.md) 在不改变 T14 判定规则的前提下增加不可覆盖的轮次历史和学生只读报告。
