# 实施顺序

## S0 计划门禁

- 建立 T17 文档与 delivery，验证格式、链接、尾随空白、`git diff --check` 和 skill self-check。
- 门禁通过前不修改运行时代码。

## S1 数据、权限与查询

- 新增 0020 模型、迁移、历史回填和保护性 downgrade。
- classroom 增加学生有效班级摘要用例；PBL repository 增加可见摘要、幂等主动创建和固定沟通方式。
- 先完成迁移、owner/member、跨学生和创建幂等测试。

## S2 AI 与统一应用用例

- 升级 transport-neutral record、schema v4、request builder、CheckedGateway 和所有 provider fixture。
- 增加主动创建、start、统一详情/消息用例；保留现有阶段状态机、发布事务和学习判定。
- 完成 guided/direct、无效证据、方式不匹配、provider unavailable 和安全分流测试。

## S3 API、契约与 Demo

- 添加学生班级及 learning-dialogues 路由和 DTO；扩展教师诊断来源字段。
- Demo 实现相同班级范围、创建/start 幂等、固定方式和 schema v4 行为。
- 运行 contract generate，审阅 OpenAPI、生成类型和 fixture 后执行 contract check。

## S4 前端统一

- 扩展 pbl 公开类型/adapter，重构学生研讨页的新建、首次选择和统一消息流。
- 主导航改为三项并处理旧 chat、历史、报告和续开兼容。
- 教师队列展示来源与沟通方式；无病例主动研讨隐藏病例重练。
- 更新相关单元、导航和 E2E；验证 320～1440 宽度、键盘、焦点和空/错/加载状态。

## S5 文档与交付

- 更新架构、数据层、数据库、安全、公开接口、模块图、根 AGENTS 和计划索引。
- 逐项记录验证命令、退出码、风险、未执行外部项和回退。
