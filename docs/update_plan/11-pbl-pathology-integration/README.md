# T11：PBL 主线与病理学知识体系

状态：仓库内实施与本地验收完成。起始分支为 dev，HEAD 为 7eeb46b，工作区包含 T10 未提交实现；本轮未覆盖、恢复或代为提交既有工作。命令、转换、外部阻塞和回退证据见[实施证据](deliveries/T11.md)。

后继更新：参与级自动阶段与两轮自动判定由 [T14](../14-pbl-automatic-mastery-loop/README.md) 实施；本目录继续保留 T11 当时的历史事实和证据，不倒改原结论。

## 目标与非目标

统一病理学总论知识体系，将课堂、诊断、教师采用、定向任务、复习、再测与教师核验贯通。开发使用 DeepSeek 普通模型 API；生产 Coze 约束保留。本轮不测试真实 Coze，不部署生产，不扩展系统病理学或小组协作，不提交或推送。

## 文档与执行顺序

1. [当前审计](01-current-audit.md)：基线、权限与数据影响。
2. [产品流程](02-product-workflows.md)：角色、页面和状态。
3. [知识体系](03-pathology-knowledge-system.md)：五主题、三十知识点和资源。
4. [接口与模块设计](04-api-data-module-design.md)：合同、事务、兼容。
5. [AI 开发接入](05-ai-development-integration.md)：配置、隔离、错误与秘密保护。
6. [数据转换](06-data-transition.md)：备份、清理、恢复。
7. [实施任务](07-implementation-tasks.md)：阶段门禁。
8. [验收与回退](08-verification-rollback.md)：用例矩阵与检查。
9. [交付模板](deliveries/template.md)、[实施证据](deliveries/T11.md)。

计划目标不等同于当前实现。先完成文档格式、链接、空白和工程 skill 门禁，再实施运行时代码。阶段出现新事实时先修订对应文档。真实外部验收与本地 Mock 分开记录。
