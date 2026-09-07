# T18：学习资料溯源与学情统计可信度

状态：仓库内实施完成；真实 Coze、真机、医学专家审核和生产验收仍为外部项。

## Summary

修复 API 学情报告遗漏 schema v4 统一研讨诊断的问题，使 API 和 Demo 用同一套个人完成讨论、反复目标和两轮改善口径。学生端补充学习目标和资料来源说明，不改变教师采用发布、自动判定或旧独立病例训练。

## 目标与非目标

- 目标：兼容 v3/v4 合法完成诊断；以不同个人完成讨论为反复重点计数单位；公开分母；显示任务学习目标和来源；消除“医学问答”旧入口文案。
- 非目标：不新增迁移、不回填历史 JSON、不阻断缺少资料来源的历史任务、不改变 PBL 两轮阈值、不调用真实 Coze、不执行生产操作。

## 文档索引

1. [当前审计](01-current-audit.md)
2. [设计与兼容](02-design-and-compatibility.md)
3. [实施任务](03-implementation-tasks.md)
4. [验证与回退](04-verification-and-rollback.md)
5. [交付模板](deliveries/template.md)

实施遵守仓库根目录 [AGENTS.md](../../../AGENTS.md)。
