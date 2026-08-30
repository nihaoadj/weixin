# 项目文档

本文档集按“少量主文档、职责清晰分离”的方式组织，不再按审计编号或技术主题碎片化拆分。

| 文档                                                                         | 职责                                            |
| ---------------------------------------------------------------------------- | ----------------------------------------------- |
| [architecture.md](./architecture.md)                                         | 总体架构、技术栈、目录边界和端侧支持            |
| [features.md](./features.md)                                                 | 当前功能、角色流程和后续功能规划                |
| [api.md](./api.md)                                                           | FastAPI 接口契约、认证方式和主要请求响应        |
| [database.md](./database.md)                                                 | SQLite 开发库、核心表结构和未来 PostgreSQL 迁移 |
| [deployment.md](./deployment.md)                                             | 本地运行、构建、环境变量和部署路径              |
| [migration.md](./migration.md)                                               | 从微信云函数/本地 Demo 迁移到 FastAPI 的路线    |
| [development.md](./development.md)                                           | 开发规范、质量门禁、测试和 Git 注意事项         |
| [audit/initial-version-comparison.md](./audit/initial-version-comparison.md) | 初始版本功能映射、安全泄露和迁移差异            |

当前路线：

```text
前端：uni-app + Vue 3 + TypeScript + Vite
后端：Python + FastAPI
数据库：SQLite
后续生产库：PostgreSQL
```
