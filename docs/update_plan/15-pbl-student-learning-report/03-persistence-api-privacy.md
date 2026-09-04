# 持久化、API 与隐私

## 0019 评价历史

learning 模块新增 `learning_plan_evaluations`：

| 字段                   | 规则                                                        |
| ---------------------- | ----------------------------------------------------------- |
| `id`                   | 主键                                                        |
| `plan_id`              | `learning_plans.id` 外键，级联删除并建立索引                |
| `cycle_number`         | 评价轮次，必须大于零                                        |
| `policy_version`       | 实际判定策略版本                                            |
| `result`               | `improved`、`next_cycle_activated` 或 `needs_reinforcement` |
| `checks`               | 仅保存目标编码、阈值、成绩、证据存在性和通过状态            |
| `failed_targets`       | 未达标目标类型和编码                                        |
| `automation_exhausted` | 本次评价后是否耗尽自动轮次                                  |
| `record_source`        | `runtime`、`backfill` 或 `legacy`                           |
| `evaluated_at`         | 评价时间                                                    |
| `created_at`           | 写入时间                                                    |

`plan_id + cycle_number` 唯一。自动判定写计划当前快照、评价历史、任务激活和通知时使用同一事务；重复评价命中既有记录且不覆盖。

0019 upgrade 创建空表。独立历史脚本默认 dry-run，依据任务、attempt 和当前 decision basis 重建可证明的轮次；无法证明逐项依据的人工历史只写 `legacy` 空 checks。apply 需要显式非生产确认和不存在的新备份路径。存在评价记录时 downgrade 拒绝，要求使用兼容读版本或已验证备份恢复。

## 学生 API

新增：

- `GET /student/pbl-learning-reports?limit=20&offset=0`
- `GET /student/pbl-learning-reports/{session_id}`

列表返回 `summary`、按最近活动倒序的 `items`、`total`、`limit`、`offset`。summary 包含六种状态数量、下一步、重复目标；列表项包含 session、病例标题、当前阶段、计划/目标进度、状态和更新时间。

详情返回：

- session 的公开上下文；
- `phase_progress`；
- 本人的 `knowledge_gaps` 和 `reasoning_issues`；
- `plans`、公开任务进度和 `evaluations`；
- 按 plan/target 聚合的 `target_progress`；
- 确定性 `summary_text`、`next_action` 和事件 `timeline`。

报告用 session ID 作稳定详情键。数据来源是本人 participation 和本人 learning plan 的并集；不存在任一来源时返回 404。列表默认 `limit=20`，允许 1～100。

## 映射与隐私

- PBL repository 提供本人参与及阶段快照的窄 record；learning public port 提供本人计划及评价历史。PBL application 组合报告，跨模块不穿透 ORM。
- 个人薄弱点只能来自 snapshot 所属 participation 的学生等于当前 actor；其他来源计划标记 `assignment_basis=classroom`，不返回来源学生或来源诊断。
- 任务只返回 prompt、类型、轮次、状态、目标编码、成绩、反馈和证据存在性；不返回原始 answer、正确选项、private rubric 或隐藏病例事实。
- 不返回 teacher/provider 标识、failure reason、完整消息或模型提示；服务端日志只记录内部 student/session/plan、策略版本和结果编码。
- 前端 API adapter 使用 Zod 运行时校验并显式映射；Demo 实现同一领域合同，不能作为 API 权限证据。
