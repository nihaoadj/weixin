# 项目文档

从此页进入当前权威文档。历史验收、旧迁移路线和已完成计划均作为阶段资料单列，不能替代当前实现说明或生产验收。

## 首先阅读

| 文档                                         | 职责                                       |
| -------------------------------------------- | ------------------------------------------ |
| [architecture.md](architecture.md)           | 技术栈、模块边界与当前接入状态             |
| [data-layer.md](data-layer.md)               | 数据访问、API/Demo、契约、缓存与错误边界   |
| [更新计划索引](update_plan/README.md)        | 当前产品与工程更新计划、计划门禁和交付入口 |
| [ADR 0001](adr/0001-data-layer-contracts.md) | 数据层的重大工程取舍                       |
| [openapi.json](openapi.json)                 | 已生成的 API 契约快照                      |

## 按职责阅读

| 区域 | 入口                                  | 内容                               |
| ---- | ------------------------------------- | ---------------------------------- |
| 产品 | [功能与角色流程](product/features.md) | 当前功能、学生与教师流程、后续方向 |
| 前端 | [前端文档](frontend/README.md)        | 视觉设计、公开接口和页面边界       |
| 后端 | [后端文档](backend/README.md)         | API、数据库与模块责任              |
| 运行 | [运行文档](operations/README.md)      | 开发、构建、部署和依赖维护         |
| 治理 | [安全边界](governance/security.md)    | 权限、敏感数据、AI 与凭据处置      |

## 历史资料

- [前端阶段记录](records/frontend/README.md)：已完成的动效设计与视觉验收。
- [架构迁移路线](records/architecture/cloud-demo-to-fastapi-migration.md)：从云函数和本地 Demo 到 FastAPI 的历史路线。
- [初始版本比较](audit/initial-version-comparison.md)：初始版本的功能、安全与迁移差异。
- [T01–T25 阶段概述](update_plan/01-25-summary.md)：已归档阶段、当前边界与待验收项。
