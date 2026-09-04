# API、数据与模块设计

## 待实现目标与模块归属

content 拥有目录、病例、正式题和来源；classroom 提供角色/成员范围；pbl 拥有课堂、请求、诊断与建议；learning 拥有任务、证据和核验；analytics 聚合公开读模型。跨模块仅经 public port 与 wiring，发布链在同一数据库 UoW 内提交，各 adapter 不提前 commit。

## 合同

- knowledge/tree 保留平面列表合同并增加 parent_code、description、prerequisite_codes、related_codes；system 字段兼容表达五个主题。知识点详情含公开资源关联，禁止下发答案。
- 建课增加 case_id、knowledge_point_codes；冻结 case_version、case_digest、public_context，最多三点且属于主题。增加 version 和 phase，PATCH 阶段检查版本。
- 学生列表支持 status=active|closed|all；关闭/退班只能读取本人已存在参与记录，不能新增。消息包含稳定 id，响应提供完整服务端序列。
- 诊断合同版本 2：knowledge gap 包含 id、point_code、summary、evidence_message_ids、evidence_summary、confidence；reasoning issue 包含 id、dimension_id、issue_type、summary、evidence_message_ids、evidence_summary、improvement；建议含 title、prompt、objective、linked_findings。所有 ID、范围和长度由运行时 schema 校验；安全提示单独字段。
- 教师诊断列表支持 class_id/session_id/student_id/suggestion_status、limit/offset。source metadata 来自授权的公开 port；详情带旧 revision 摘要，旧版诊断只读且排除新版统计。
- adopt-and-publish 接收 version/title/prompt/target_student_ids/whole_class/include_case_retry，默认来源学生。拒绝空题、跨班级目标、rejected/superseded、过期版本；已发布重试返回同一结果，不再次覆盖文案。

## 持久化与幂等

新增 0016 的后继迁移；旧迁移不改写。PBL session 增加病例上下文、目标、phase/version；snapshot 增加 schema_version/safety_notice/request_message_id；message 保存处理 revision/status，并按 client_message_id 返回对应快照。数据库条件更新实现 revision/version compare-and-swap，不仅比较内存对象。

LearningPlan 增加 source_type/source_id、PBL source metadata 和 verification 状态，source_assessment_id 改为可空，唯一(student_id,source_type,source_id)。旧计划回填 case_assessment，旧 current-plan 仍查询病例来源，新增分页列表读取 PBL 计划，避免多个 PBL 干预互相 supersede。

任务增加 discussion/knowledge_review/retest，复用 micro_drill/focused_retry。讨论任务保存学生作答及提交 ID；客观题按服务器答案判分；微训练按已审核 rubric 评分；完整病例通过 training 公共 port。证据仅保存资源/attempt 引用及必要结果。每任务的提交 ID 唯一，重复提交不重复调度或评分。完成后 verification=pending，教师可标记 improved/needs_work，保留核验人、时间和反馈。

学习 public 提供事务内派发端口，content public 提供病例上下文和正式发布端口。PBL adopt 原子写题目、来源、任务和通知。新增教师计划列表/核验及课堂汇总；所有查询都检查教师归属和学生范围。客观成绩、回忆自评、AI 推测和教师确认分开呈现。

## 兼容与生成

保留旧病例评估流程、生成路径、API/Demo 装配入口。旧 PBL JSON 以 legacy 标记只读展示，不强行转换证据。更改 Pydantic 后运行 contract:generate，再 contract:check；同步 Zod、mapper、类型 conformance 与 fixture。现有调用者和测试必须迁移到新建课/采用合同，不以可选绕过新权限与病例要求。

## 实施中核实的补充设计

- 既有基础迁移可能从当前 ORM 创建表，0017 因此按已存在列检查执行增量变更，不能重复添加列。结构降级在仍有 PBL 来源计划时明确拒绝，要求先恢复备份。
- 内置卡片通过 `knowledge_card_contributions.catalog_card_code` 绑定稳定编码，复用现有审核、回忆揭示和自评接口。PBL 发布仅选用已审核卡片；开发种子的审核记录明确标注为合成演示，不能视为真实专家审核。
- PBL 任务继续保存在 learning 模块；PBL 应用仅通过 `PblLearningPort` 协調同一事务。客观卡作答复用学习复习应用并延迟提交，整笔事务由应用用例提交。
- 新增接口包括讨论阶段、诊断修订历史、学生 PBL 计划列表、任务提交、教师学习结果核验和课堂汇总。病例评估的 current-plan 保留原来源筛选，PBL 计划独立并存。
- 消息处理超过 60 秒且没有结果时，以条件更新持久化 unavailable/interrupted_request 结果；重试读取该次结果，学生可另发消息继续。迟到的推理结果不能覆盖中断结果。
- 完整病例训练结束后，learning 在原任务上记录 assessment 引用与成绩；所有任务完成时自动进入 pending_teacher，避免另建病例来源计划。
