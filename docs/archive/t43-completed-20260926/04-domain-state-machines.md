# 04 领域模型与状态机

状态：设计目标；部分表、字段和纯规则已在工作树实现，未完成的事务、资源与页面链路仍按本册验收。具体事实以[实施进度记录](deliveries/implementation-progress.md)和源码为准，不得把设计字段自动视为已验收。

## 数据拥有者与存储选择

继续使用 LearningPlan/LearningTask/LearningPlanEvaluation 执行两轮，不另建第二套任务执行引擎。新增 classroom_task_packages 管理草稿和发布身份，一包发布时关联一个 LearningPlan；计划 source_type 新增 classroom_package，source_id 为包 ID。保留旧唯一键，新增包 UNIQUE(student_id, session_id)，学生和班级由课堂参与记录确定。

| 对象/拥有者                               | 关键字段与约束                                                                                                                                                                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| classroom_task_packages / learning        | id、student_id、class_id、session_id、completion_snapshot_id、teacher_id、status、version、draft_digest、reviewed_version、plan_id、published_at、due_at；plan_id 唯一，发布后内容不可变                                                   |
| classroom_package_items / learning        | id、package_id、stable_key、position、cycle_number、task_type、primary_point_code、point_codes、target_type/code、public_definition、private_rubric、source_ref/version/digest、medical_status；UNIQUE(package_id,stable_key,cycle_number) |
| classroom_final_reports / learning        | id、package_id 唯一、student/class/session、schema_version=1、policy_version、source_digest、result、completed_at、payload；append-only                                                                                                    |
| teacher_question_bank_items / content     | id、owner_teacher_id、status=active/archived、version、current_revision_id、created_at/updated_at                                                                                                                                          |
| teacher_question_bank_revisions / content | bank_item_id、version 唯一、题型、题干、选项、答案、解析、知识编码、维度、source_item_ref、source_digest、medical_status；不可覆盖版本                                                                                                     |
| teaching_command_receipts / learning      | teacher_id、operation、client_request_id 唯一，request_digest、resource_id、result_version；用于整包发布幂等                                                                                                                               |
| bank_import_receipts / content            | teacher_id、source_package_item_id、source_digest 唯一，bank_item_id；另记录 client_request_id/payload_digest 防不同输入复用                                                                                                               |

包状态 draft/build_failed/published；执行状态由 plan 派生 cycle_1/cycle_2/completed。draft 只保存当前版本，发布与报告保存不可变快照；教师反馈沿用 append-only 记录，引用包/plan。关闭未发布诊断由 PBL 状态承载，不删除草稿。

包和题库主键使用服务端整数ID；创建/更新/完成时间存UTC，展示与自然日筛选使用Asia/Shanghai。新包期限固定published_at+7天，本期不新增延期/改期。题目stable_key由服务端创建并持久化，编辑不得改；每对变式共享key，cycle_number只能1或2。task position在发布时按主知识节点的课堂目标顺序、题目草稿顺序、轮次确定并冻结，不以节点名称排序改变作答顺序。

补充外键与约束：包的student/class/session/teacher/completion_snapshot均为真实FK，plan_id可空且仅published时非空；report.package_id与package.plan_id唯一，result枚举约束；题库revision的bank_item_id为FK。新增t43_legacy_plan_mappings保存legacy_plan_id唯一、package_id唯一及转换时间。归属对象删除遵循既有保留策略，禁止级联删除已发布包、报告或题库revision。

## 状态转换

| 触发           | 前置                                                  | 原子结果                                                          |
| -------------- | ----------------------------------------------------- | ----------------------------------------------------------------- |
| 完成课堂诊断   | 本人四阶段合法证据、完成快照唯一                      | 冻结诊断；允许构建草稿                                            |
| 构建/重试草稿  | 无发布包；完成快照、课堂目标有效                      | 按固定资源版本生成或记录 build_failed；重复调用不覆盖已有教师编辑 |
| 保存草稿       | version 匹配、未发布                                  | 校验所有题、递增版本/摘要、清空 reviewed_version                  |
| 发布整包       | version/digest/两轮确认一致，所有资源合法且无审核阻塞 | 冻结题目、创建唯一 plan 和任务、记录可选反馈、发布回执及学生通知  |
| 提交任务       | 本人、活动轮次、前序完成、包已发布                    | 保存一次作答，评价当前轮；同提交键同答案返回原结果，异答案409     |
| 首轮失败       | 当轮必需任务完成                                      | 保存cycle1评价、只激活失败目标cycle2                              |
| 达标或二轮结束 | 终态条件满足                                          | 保存最终评价、plan completed、唯一最终报告及完成通知              |

草稿构建使用服务端可重入操作，不增加后台队列基础设施。对话完成事务不依赖后续资源构建成功；教师打开诊断后通过显式 POST ensure 构建，GET 无写副作用。

reviewed_version不需要独立确认接口：发布请求的reviewed_all、version、draft_digest通过验证后，在同一发布事务写reviewed_version=version及published_version。未发布时为null；客户端勾选只表示本次拟提交确认，不能成为服务端已审阅事实。feedback_draft是包内未发送草稿，发布时仅采用请求显式提供的feedback；省略不发送、不新建空反馈，已有“仅反馈”的记录不重复发送。

新增字段补充：包持久化feedback_draft、published_version、diagnosis_outcome及record_source=runtime/legacy_verified；题目持久化dimension_ids、candidate_key和content_resource_id；报告持久化record_source。草稿医学资源由content拥有，学习包只持有版本/digest引用，不复制医学审批状态机。任何医学审批状态从content即时校验，包内medical_status仅为读取投影，不作为授权依据。

所有数据库写操作由 application/UoW 提交。并发使用版本条件更新及唯一约束兜底，冲突回滚后读幂等回执。task assessment、评价、报告、通知必须同一事务；外部 AI 反馈失败不得让已提交确定性结果依赖网络重跑。病例模块已保存 assessment 而回调失败时，由相同 assessment ID 重试完成任务，不能重做病例或创建新计划。

## 目标覆盖与判定

本期支持知识巩固 knowledge_review、客观再测 retest、推理 micro_drill、正式讨论 discussion、已有审核病例重练 focused_retry。全部题目关联课堂目标集合，能力题同时关联维度；目录前置节点可作补充阅读，不自动成为新必做目标。

每个课堂目标至少一组两轮知识验证；已确认 reasoning_issue 至少一组两轮微训练。知识巩固完成是过程条件，再测100分达标；微训练与病例目标维度70分达标，缺证据失败；讨论只检查完成及证据，不生成分数。保留现有首轮失败时第二轮讨论激活规则。多题同目标逐题全部过线才算目标通过，不能用平均分掩盖失败。

进度分母为当前已激活必需任务；inactive/skipped 不计。终态完成与达标分开：improved 或 needs_reinforcement，第二种须 automation_exhausted=true。报告保留首轮已通过目标与第二轮补强目标的最终有效结果，不能只取第二轮而丢失首轮成绩。

## 最终报告与综合统计

报告冻结发布版本、诊断摘要、节点/维度、逐项结果、两轮历史、完成时间与策略版本。缺值为 null，不保存完整聊天、原始回答、隐藏病例、正确选项或评分内部规则。学生与教师 DTO 分别白名单输出，教师不读取私人续问。

analytics 新增 FinalReportReadPort，只读报告和课堂包进度的窄视图。最终报告是唯一结果统计源；旧 evidence events 保留但不参与新教师结果聚合，不再把病例/任务/轮次与报告相加。

统计按 class_id 和 completed_at 的上海自然日筛选：完成课堂数=报告数；达标课堂率=improved/报告数；每节点掌握率=该节点全部必需检查通过的报告数/包含该节点有效评价的报告数。能力维度仅同维度求每份报告内最终有效检查均值，再按报告等权汇总。变化只比较同节点/维度的相邻两个时间窗，缺任一窗为 null；不提供跨能力综合分或学生排名。少于5名学生隐藏班级薄弱排序。

“学习进度”另按 published_at 统计该日期窗发布的包及其中已完成数，明确其分母，与 completed_at 的结果窗不混算。综合详情报告列表与结果卡均来自最终报告；进行中只可跳课堂进度，不能成为未完成报告。
