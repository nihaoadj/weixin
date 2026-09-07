# 设计与兼容

## 统计口径

- 有效个人讨论：当前学生的 participation 已完成，且存在最新 `ready`、`synthesis + complete`、schema 为 3 或 4 的快照。
- 每份报告最多使用一个有效个人快照；每个 `(target_type, target_code)` 在该报告内最多记一次。
- `completed_personal_discussions` 为有效个人讨论数。`recurring_targets[].occurrences` 是目标出现于多少份不同有效个人报告，故不超过该分母。
- 课堂共同训练可以保留在报告和任务进度中，但不进入个人诊断分母或反复重点。

## 接口与 UI

- `ReportPageSummary` 新增整数 `completed_personal_discussions`；这是向后兼容的只读字段。
- 报告任务新增公开 `reference` 字段；为空时前端显示“教师采用的 PBL 训练，未提供单独资料来源”。
- 新发布任务的公开定义写入 `target_label` 和可选 `reference`；旧 JSON 不回填，前端以任务类型或目标编码降级。
- 反复重点显示“出现 X 次 / N 次完成讨论”，条宽为 `X/N`，不设置人为最小宽度；零分母不显示区块。

## 安全、发布与回退

- 只输出任务公开题面、目标标签、公开来源、本人得分和反馈；不扩大诊断、答案、rubric 或身份数据范围。
- 无数据库模式变更。后端先发布新增字段，前端随后发布；旧客户端忽略字段，旧任务保留原 JSON。
- 回退只撤回代码，不删除任务、计划、评价或 JSON 元数据；不以 Demo 验证真实 Coze 或医学内容正确性。
