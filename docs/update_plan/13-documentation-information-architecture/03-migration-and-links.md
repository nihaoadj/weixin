# 迁移与链接策略

## 文件映射

| 原路径                                  | 目标路径                                                            | 类别                 |
| --------------------------------------- | ------------------------------------------------------------------- | -------------------- |
| `docs/features.md`                      | `docs/product/features.md`                                          | 当前产品文档         |
| `docs/frontend-design.md`               | `docs/frontend/design.md`                                           | 当前前端设计         |
| `docs/frontend-public-interfaces.md`    | `docs/frontend/public-interfaces.md`                                | 当前前端接口边界     |
| `docs/api.md`                           | `docs/backend/api.md`                                               | 当前后端接口         |
| `docs/database.md`                      | `docs/backend/database.md`                                          | 当前后端数据库说明   |
| `docs/backend-module-map.md`            | `docs/backend/module-map.md`                                        | 当前后端模块说明     |
| `docs/development.md`                   | `docs/operations/development.md`                                    | 当前开发流程         |
| `docs/deployment.md`                    | `docs/operations/deployment.md`                                     | 当前运行与部署       |
| `docs/dependency-upgrade.md`            | `docs/operations/dependency-upgrade.md`                             | 当前依赖维护         |
| `docs/security.md`                      | `docs/governance/security.md`                                       | 当前安全治理         |
| `docs/frontend-editor-motion.md`        | `docs/records/frontend/editor-motion-2026-08-31.md`                 | 阶段设计记录         |
| `docs/frontend-validation.md`           | `docs/records/frontend/validation-2026-08-31.md`                    | 阶段验收记录         |
| `docs/migration.md`                     | `docs/records/architecture/cloud-demo-to-fastapi-migration.md`      | 阶段迁移路线         |
| `docs/update_plan/README.md`            | `docs/update_plan/01-07-engineering-governance/README.md`           | T01–T07 共享总任务书 |
| `docs/update_plan/01-*.md` 至 `07-*.md` | `docs/update_plan/01-*/README.md`                                   | T01–T07 独立任务书   |
| `docs/update_plan/execution-status.md`  | `docs/update_plan/01-07-engineering-governance/execution-status.md` | 共享执行记录         |
| `docs/update_plan/deliveries/`          | 各 T01–T07 的 `deliveries/`，或共享治理目录的 `deliveries/`         | 任务与阶段证据       |

## 链接兼容策略

1. 使用 `git mv` 保留已跟踪文件的历史。
2. 仓内 Markdown、`AGENTS.md` 和 ADR 的相对路径一次性更新到目标位置；不保留内容重复的跳转页。
3. 为每个新增二级目录建立精简 `README.md`，只索引本目录的当前资料和阅读顺序。
4. 为 `docs/update_plan/` 重建简短索引，列出 T01–T13 的独立目录和共享工程治理入口。
5. 移动后以脚本逐个解析相对 Markdown 文档链接，检查路径存在性；另执行格式、尾随空白和 Git 补丁检查。

阶段交付中指向当时源码快照、构建截图或临时证据目录的链接保持原文，不将不存在的阶段产物伪造为当前文件。此类链接不属于当前文档导航的验收范围，交付记录会明确该边界。

## 兼容与回退

仓库内部没有发布的文档 URL 合同。本轮更新的相对链接会随文件移动同步改写；若发现未覆盖的外部书签，可在后续单独添加迁移说明。回退通过 `git mv` 将文件移回原位置并恢复本轮链接与入口页，不涉及代码、数据库或生成物。
