# 当前审计

## 已核实事实

- 当前分支为 `dev`；工作树包含尚未提交的 T14 代码、契约、测试和文档，以及既有未跟踪目录 `output/`。T15 只做增量编辑，不恢复、覆盖、清理或提交这些内容。
- T14 已在仓库内实现参与级四阶段、schema v3 诊断、两轮任务、逐项自动判定和教师只读结果。
- `PblDiagnosticSnapshot` 已保存阶段、阶段决策、证据摘要、缺失要素、知识薄弱点和推理问题；`LearningTaskAttempt` 已保存成绩、证据和学生可见反馈。
- `LearningPlan.decision_basis` 只保存当前判定快照。第二轮完成后会覆盖第一轮依据，因此不能可靠直接展示完整两轮判定历史。
- 学生端已有课堂页和任务页，没有 PBL 学情总览或按课堂聚合的个人报告 API。
- 学生主导航当前为课堂、任务、知识、答疑、记录；答疑页已有明确的历史入口。
- 前端没有图表依赖；现有设计令牌和 CSS 进度条足以实现跨 H5/微信的轻量图表。

## 当前接口与边界

- 学生经 `/student/pbl-sessions`、participation 和 `/student/pbl-learning-plans` 获取分散数据。
- 页面只能调用 `features/pbl/public.ts`；API/Demo 由 `src/bootstrap/wiring.ts` 在启动时选择，API 失败不得切换 Demo。
- PBL application 经 `learning.public.PblLearningPort` 协作，不能从 PBL infrastructure 直接读取 learning ORM。
- OpenAPI 与生成 TypeScript 是生成物，必须由契约生成流程同步。

## 待解决差距

- 缺少不可覆盖的逐轮自动评价记录。
- 缺少按“学生＋课堂”组合个人讨论与多个计划的安全读模型。
- 缺少渐进状态、跨课堂重复薄弱点统计、确定性下一步和可读图表。
- 全班任务可能来源于其他学生的诊断，报告必须区分个人诊断与课堂共同训练，禁止串读来源学生信息。
