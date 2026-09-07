# 接口、数据与 AI 合同

## 数据库 0020

`pbl_sessions` 新增：

- `session_kind`：非空 `classroom | student_initiated`，历史回填 `classroom`。
- `created_by_student_id`：可空用户外键并建立索引。
- `client_session_id`：可空、最长 100；与创建学生组成唯一约束。

约束要求 classroom 的两个创建字段均为空，student_initiated 的两个字段均非空。学生主动 session 的 `teacher_id` 从班级 owner 派生，客户端不得提交。

`pbl_participations` 新增：

- `interaction_style`：非空 `guided | direct`，历史回填 `guided`。
- `style_selected_at`：非空时间；历史使用参与记录创建时间或迁移时间回填。

0020 downgrade 在存在 student_initiated session 或非 guided participation 时拒绝；安全条件满足时才可删除新增列和约束。

## HTTP 合同

- `GET /student/classes`：本人有效班级的 `id/name/code` 摘要。
- `GET /student/learning-dialogues?limit&offset`：稳定排序的统一摘要分页，只返回本人可见的课堂 session 和本人主动 session。
- `POST /student/learning-dialogues`：接收 `client_session_id/class_id/interaction_style/goal_point_codes`；服务端验证同一主题、派生 topic/teacher，并幂等创建 session 与 participation。
- `POST /student/learning-dialogues/{id}/start`：接收 `interaction_style`；相同选择幂等，不同选择返回 `STATE_CONFLICT`。
- `GET /student/learning-dialogues/{id}`：返回 session、participation、消息和最新诊断。
- `POST /student/learning-dialogues/{id}/messages`：接收 `client_message_id/content`，复用消息幂等、阶段证据和完成锁定。

旧 `/student/pbl-sessions*`、`/v1/medical-chat`、conversation 和 report 接口保留；旧入口新增 OpenAPI deprecated 标记，新前端不再调用其写能力。

教师诊断响应增加 `session_kind`、`interaction_style`；教师 session 列表不混入学生主动 session，教师建议队列按既有班级 owner 范围查询两种来源。

## AI schema v4

- `InferenceRequest` 增加 `interaction_style`；provider 输入明确当前阶段、证据窗口和两种回复规则。
- `ProviderPayload.schema_version` 固定为 4，并回显同一 `interaction_style`；CheckedGateway 拒绝不匹配。
- 其余知识薄弱点、推理问题、建议题、安全和阶段字段沿用 v3；`ready` 仍只允许 synthesis 合法 complete。
- 新推理只保存 v4。历史 v3 可读取、展示和采用；采用规则接受兼容的 v3/v4 诊断。
- Bot、Workflow、开发 OpenAI-compatible 和测试 Mock 使用同一结构；禁止 provider/mode fallback。
