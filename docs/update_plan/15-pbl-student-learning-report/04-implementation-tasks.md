# 实施任务

## S0 计划门禁

- [x] 核实工作树、公开接口、迁移、权限和 API/Demo 边界。
- [x] 建立 T15 文档集并更新计划索引。
- [x] Scoped Prettier、相对链接、尾随空白、`git diff --check` 和 skill self-check 通过。

## S1 数据与领域

- [x] 新增 0019、`LearningPlanEvaluation`、关系和模型注册。
- [x] 自动判定事务内追加幂等评价历史。
- [x] 新增默认 dry-run 的安全历史回填脚本及保护性 downgrade。
- [x] 建立报告状态、目标对照和确定性说明纯规则。

## S2 后端 API

- [x] 扩展 PBL repository 和 learning public port 的窄读合同。
- [x] 组合本人 participation、个人诊断、多个计划和评价历史。
- [x] 新增分页总览与 session 详情，并完成权限和隐私负向测试。

## S3 前端 API/Demo

- [x] 扩展 PBL domain port、Zod schema、mapper、API adapter 和 public API。
- [x] Demo 按相同状态、目标和隐私规则生成总览与详情。
- [x] 更新 OpenAPI、生成类型和契约检查。

## S4 学生页面

- [x] 新增学情总览、详情和轻量可访问图表组件。
- [x] 更新主导航、路由与学习记录二级导航。
- [x] 完成六种状态、空态、错误重试、行动入口和响应式布局。

## S5 文档与验收

- [x] 更新架构、数据层、数据库、安全、公开接口、模块图和 AGENTS 当前状态。
- [x] T14 只增加 T15 后继引用。
- [x] 执行迁移、后端、契约、前端、双端构建、API/Demo E2E、边界和秘密检查。
- [x] 将实际命令、退出码、未执行项和回退写入 T15 交付记录。
