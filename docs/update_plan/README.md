# 更新计划索引

本目录只展示当前产品与工程更新。每轮新计划使用 `NN-short-name/` 独立目录，至少包含当前事实、目标与非目标、模块或接口设计、实施顺序、验证与回退，以及 `deliveries/` 下的证据。计划中的目标不是当前实现事实。

开始任何功能、修复、重构、迁移、契约或工程规则变更前，先阅读根目录 [AGENTS.md](../../AGENTS.md)、本索引和任务关联的权威文档；记录现有工作区改动，建立计划并完成格式、相对链接、尾随空白和相关工程 skill self-check，才修改运行时代码。

## 独立计划

| 计划                                                                             | 状态与范围                             |
| -------------------------------------------------------------------------------- | -------------------------------------- |
| [T01 测试环境隔离与数据库安全](01-test-database-safety/README.md)                | 测试资源隔离、迁移验证与数据库安全     |
| [T02 质量门禁、CI 与交付治理](02-quality-ci-delivery/README.md)                  | 质量检查、契约漂移与交付治理           |
| [T03 前端业务分包与分层重构](03-frontend-modularization/README.md)               | 前端模块边界、装配与公开接口           |
| [T04 后端业务分包与分层重构](04-backend-modularization/README.md)                | 后端模块、依赖方向与数据责任           |
| [T05 关键业务回归与覆盖率治理](05-critical-tests-coverage/README.md)             | 关键业务测试、覆盖率与端到端验收       |
| [T06 安全、隐私与发布边界](06-security-privacy-release/README.md)                | 权限、敏感数据、凭据与发布边界         |
| [T07 工程规范、AGENTS 与项目 Skill](07-standards-agents-skills/README.md)        | 工程规则、权威文档与检查路由           |
| [T08 问答驱动的医学知识巩固闭环](08-qa-knowledge-mastery-loop/README.md)         | 当前仓库侧交付索引；不含真实大模型接入 |
| [T09 病理学 PBL 教学助手最小闭环](09-pathology-pbl-teaching-assistant/README.md) | PBL 的产品、AI 与教师审核最低要求      |
| [T10 T09 收口与 dev 基线加固](10-t09-completion-hardening/README.md)             | PBL 分层、提供方、权限与回归的加固计划 |
| [T11 PBL 主线与病理学知识体系](11-pbl-pathology-integration/README.md)           | 病理学目录、课堂、学习反馈与开发联调   |
| [T12 PBL 前端流程与流畅度优化](12-pbl-frontend-flow-polish/README.md)            | 学生导航、任务提示与教师同页切换       |
| [T13 文档信息架构整理](13-documentation-information-architecture/README.md)      | 当前文档分组、阶段资料与链接治理       |
| [T14 PBL 自动阶段与自动巩固闭环](14-pbl-automatic-mastery-loop/README.md)        | 参与级阶段、两轮任务与系统自动判定     |
| [T15 学生 PBL 学情报告与改善轨迹](15-pbl-student-learning-report/README.md)      | 学生累计学情、单课证据与改善对照       |
| [T16 前端信息架构与导航精简](16-frontend-information-architecture/README.md)     | 四项主导航、跳转层级与页面空间治理     |

## 共享工程治理记录

[T01–T07 共享工程治理记录](01-07-engineering-governance/README.md) 保存总任务书、执行状态和跨任务交付证据。每个 T01–T07 计划自身的交付文件已与任务书放在同一目录。

## 交付记录

每轮计划在自身 `deliveries/` 目录记录命令、退出码、证据、未执行项、风险和回退。跨任务阶段记录保留在共享工程治理目录。未经用户明确授权，不提交或推送。
