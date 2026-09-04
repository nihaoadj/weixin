# T10：T09 收口与 dev 基线加固

状态：**仓库内完成；真实 Coze 外部联调未验证。** 起始基线为本地 `dev` 提交 `7eeb46b`。本目录保留本轮计划、验收和外部边界，不把本地 Mock 验收表述为真实 Coze 或生产验证。

## 目标

把 T09 从“功能骨架已落地、仓库边界未通过”收口为“仓库内完成、真实 Coze 外部联调未验证”：修复 PBL 分层和 content 发布桥接，补齐配置、结构化校验、权限、幂等、前端课堂管理和 Mock E2E，并形成完整交付证据。

## 文档

- [01-current-gaps.md](01-current-gaps.md)：基线事实与缺口。
- [02-implementation-plan.md](02-implementation-plan.md)：决策完整的实施顺序。
- [03-verification-rollback.md](03-verification-rollback.md)：验收矩阵、外部阻塞与回退。
- [04-execution-checklist.md](04-execution-checklist.md)：逐阶段任务、出口条件与提交门禁。
- [deliveries/template.md](deliveries/template.md)：本轮证据模板。

## 非目标

本轮不连接真实 Coze、不创建或轮换生产凭据、不迁移生产数据库、不推送或合并远端分支，也不扩展病理学总论之外的教学目录。
