# 实施计划

## 1. 后端分层与事务

- 在 PBL application 定义 `PblRepository`、`PblInferenceGateway`、`QuestionPublicationPort`、`ClassroomScopePort` 和 UoW 依赖；use case 只使用不可变 record，不出现 SQLAlchemy、Session、ORM 或供应商 DTO。
- PBL infrastructure repository 只操作 PBL 自有表。班级 owner/member 校验通过 classroom `public.py` 的纯 `ClassroomScopePort` 完成；具体实现由 bootstrap composition 注入。
- content `public.py` 仅暴露 `PublishQuestionCommand`、`PublishedQuestionRecord` 和 `QuestionPublicationPort` 协议；SQLAlchemy adapter 留在 content infrastructure。PBL 不导入 content ORM。
- API schema/mapper 只接收和返回 application record；教师诊断用例一次返回 snapshot 与 suggestions 聚合，删除 API 层数据库查询。
- 消息处理分两段事务：第一段原子插入消息并递增 revision 后提交；事务外调用模型；第二段比较 revision、写 assistant message/snapshot/suggestions 后提交。旧 revision 不覆盖新结果。

## 2. 数据与幂等迁移

- 新增单一后继迁移 `202609xx_0016_pbl_message_idempotency.py` 和 `pbl_messages` 表；学生消息唯一 `(participation_id, client_message_id)`，assistant 消息关联 request message/revision。
- 将 participation 现有 JSON messages 按顺序 backfill 后移除 JSON 字段；upgrade/downgrade 保留对话顺序、角色、裁剪内容、revision 和诊断引用。
- 保持 snapshot revision、problem origin 和 participation 唯一约束；为活动课堂、教师 ready 队列和消息历史增加复合索引。
- suggestion 状态固定为 `proposed|edited|rejected|superseded|published`。新 ready 只 supersede `proposed`；已编辑、拒绝或发布的建议不被 AI 覆盖。

## 3. Provider 与配置

- 三个 adapter 互不继承，共享严格 Pydantic parser、最多 20 条历史的脱敏 request builder 和安全错误分类。
- Coze SDK client factory、Bot mapper、Workflow mapper 分文件。fake client 注入 SDK 边界；Bot 使用匿名 user/conversation/chat stream，Workflow 使用 conversation/workflow chat，并分别只接受官方完成事件。
- participation 只保存匿名 Coze user/conversation 引用。请求只含 session ID、主题、`pathology-general-v1` 允许目录、当前问题和裁剪历史，不含学生、班级、openid 或 token。
- Workflow 要求 `COZE_WORKFLOW_ID`，且 `COZE_APP_ID`、`COZE_BOT_ID` 恰好一个非空；分别映射正确 SDK 参数。生产拒绝普通 API，禁止 provider/mode fallback。
- `ready` 必须含带稳定 finding ID 的分析项，每题关联至少一个现有 finding；`probing` 仅一条追问；失败状态无建议题。元数据只保留安全标识、conversation、prompt 版本、耗时和失败分类。

## 4. API、前端与合同

- 保留已锁定路由，补 `GET /classes/{class_id}/pbl-sessions`、`GET /teacher/pbl-diagnostics/{id}`。教师列表使用 `limit/offset` 和 `{items,total,limit,offset}`；创建返回 201，重复关闭和采用返回同一资源。
- 所有路由使用专用 Pydantic request/response model。学生 DTO 只含本人的消息、回复、追问和薄弱分析；教师 DTO 才含建议题和安全 provider 元数据。
- `features/pbl` 维持统一页面合同，API/Demo 只在 bootstrap 选择；补教师建课/关闭、诊断详情、建议编辑/拒绝/采用和学生明确入口。
- 学生页展示知识薄弱点、推理阶段、依据摘要和改进方向；教师页处理筛选、加载、空、失败、版本冲突和重复点击状态。
- 完成源 schema 后，用生成流程更新 OpenAPI、TypeScript、Zod mapper 和 fixture，禁止手改生成物。

## 5. 交付顺序

严格依次执行：分层/边界 → 数据与迁移 → provider 合同 → API/权限 → 前端 → 生成契约 → 单元/集成/E2E → delivery。任何合同变化都先修订本计划再继续。
