# 05 API、公开接口与 Demo 合同

状态：本册同时记录规范合同与当前实现状态，不能把目标当作已实现。2026-09-25 增量：任务包题目增加 `included_in_package`，教师 PUT 仍提交全量候选，按 stable_key 同步排除/恢复首轮及第二轮；API 与 Demo 发布/医学提交/学生任务均只消费 included 项，题目来源行保留以满足题库 revision/回执外键。`20260924_0032` 临时库迁移、后端目标覆盖、教师页面、Demo 生命周期与 API mapper 均有定向测试。此前工作树已接入教师整包读写/资源核验/医学审核/发布、v7 课堂诊断整包审阅、教师个人题库 API/Demo 与页面、学生任务包、终态报告和病例回程上下文。Demo 90003–90006 覆盖无明确薄弱点、病例/微训练补强、首轮达标与二轮耗尽。真实微信交互、完整 API/Demo 状态矩阵、真实受管库和外部验收尚未完成。字段和证据逐阶段更新于[实施进度记录](deliveries/implementation-progress.md)。沿用现有全局 API 前缀，下表写 router 相对路径。

## 新增与替换端点

| 方法与路径                                                    | 输入                                                                                                                                          | 输出与权限                                                                                     |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| POST /teacher/pbl-work-items/{snapshot_id}/task-package       | client_request_id                                                                                                                             | ensure 草稿；本班课堂完成快照，已有草稿原样返回                                                |
| GET /teacher/classroom-task-packages/{id}                     | 无                                                                                                                                            | 教师草稿/冻结详情，含审核所需答案与规则                                                        |
| GET /teacher/classroom-task-packages/{id}/reviewed-resources  | point_code、task_type、dimension_id?                                                                                                          | 本课堂目标可用的完整已审核两轮资源；服务端从诊断快照解析病例，不接收客户端 case_id             |
| PUT /teacher/classroom-task-packages/{id}                     | version、items、feedback_draft                                                                                                                | 替换整份草稿，返回新版本；禁止改身份/课堂目标                                                  |
| POST /teacher/classroom-task-packages/{id}/publish            | client_request_id、version、draft_digest、reviewed_all=true、feedback?                                                                        | package_id、plan_id、published_version、published_at；固定原学生                               |
| GET /teacher/classes/{class_id}/classroom-task-progress-items | session_id、status?、limit/offset                                                                                                             | 逐学生课堂进度；未发布无包，报告缺失显式标记；已接入，待完整验收                               |
| GET /student/classroom-task-packages                          | status=active/completed、limit/offset                                                                                                         | 本人一课堂一条摘要                                                                             |
| GET /student/classroom-task-packages/{id}                     | 无                                                                                                                                            | 本人公开任务、进度及final_report_id可空                                                        |
| POST /student/classroom-tasks/{task_id}/submit                | client_submission_id、answer                                                                                                                  | 公开任务结果、包状态、final_report_id                                                          |
| POST /student/classroom-tasks/{task_id}/start                 | client_request_id                                                                                                                             | 幂等返回本人attempt；focused_retry返回case_attempt_id，其他类型返回公开作答定义                |
| GET /teacher/classroom-final-reports                          | class_id、session_id?、student_id?、limit/offset                                                                                              | 仅有权范围终态报告摘要；日期统计由 analytics 负责                                              |
| GET /teacher/classroom-final-reports/{id}                     | 无                                                                                                                                            | 最小化最终报告                                                                                 |
| GET /student/classroom-final-reports/{id}                     | 无                                                                                                                                            | 本人最终报告                                                                                   |
| POST /teacher/question-bank/import                            | package_item_id、source_digest、client_request_id、title、prompt、options、answer、explanation、point_codes、dimension_ids、deidentified=true | 教师确认去标识化内容的题库项；服务端重新校验                                                   |
| GET /teacher/question-bank                                    | status=active/archived、point_code?、task_type?、q?、limit/offset                                                                             | 仅本人题库摘要                                                                                 |
| GET /teacher/question-bank/{id}                               | 无                                                                                                                                            | 本人题目详情及版本                                                                             |
| PUT /teacher/question-bank/{id}                               | version、题目白名单内容                                                                                                                       | 新不可变revision；不修改课堂题目                                                               |
| POST /teacher/question-bank/{id}/archive                      | version、client_request_id                                                                                                                    | archived；不物理删除                                                                           |
| GET /teacher/classroom-package-items/{item_id}/bank-source    | 无                                                                                                                                            | 仅课堂所属教师；校验整包项目的必要医学状态，返回不含学生身份的题库预览白名单；病例隐藏重练拒绝 |
| GET /student/classroom-case-attempts/{attempt_id}/context     | 无                                                                                                                                            | 按本人进行中或已评估 attempt 的服务端任务关联返回课堂任务/任务包身份；独立病例返回 false/null  |

题库 q 只匹配本人标题，最长100字。分页默认20、最大100，offset非负，默认 updated_at DESC,id DESC；报告按 completed_at DESC,id DESC。总数在权限和筛选后计算，空集返回200，指定他人资源404。跨角色403，非法字段422，状态/版本/幂等冲突409；继续使用统一 detail.code/message 结构。

ensure 在build_failed时使用同一路径重试，只填补尚未成功构建的草稿，不覆盖教师已保存内容；状态冲突返回409。新增 POST /teacher/classroom-task-packages/{id}/submit-medical-review，输入version、item_ids、client_request_id；仅为本包需要审核的题目版本调用content公开审核port，返回resource_id/status集合，提交本身不批准。专家继续使用既有medical_review权限和内容医学审核入口。

GET /teacher/classroom-task-packages/{id}/reviewed-resources 的规范输入为 `point_code`、`task_type`、`dimension_id?`。`point_code` 必须是当前纳入候选题的 `primary_point_code`，仅出现在其 `point_codes` 关联列表中的次要节点不能使资源可选；构建时题目所有 `point_codes` 也必须属于课堂目标。服务端通过包所属诊断读取 `case_id`，再由内容公开端口返回与本课堂主目标精确匹配的已审核双轮资源；不能以 `source_supported` 冒充医学审核。选择资源后以PUT中的 `resource_ref/version/digest` 保存，服务端重新解析并校验版本、目标和两轮配对；版本失效、目标不匹配或任一轮缺失均拒绝保存/发布。普通教师不能借资源接口读取病例隐藏资料。实际测试与尚未完成的真实资源验收见交付记录。

代码侧还通过 PBL-owned `PblClassroomPackageContextPort` 从 `(completion_snapshot_id, session_id)` 解析不可由客户端替换的课堂病例 ID；病例及 reasoning blueprint 的 query、草稿 PUT、冻结发布前复核必须命中该病例，且病例 `knowledge_point_codes` 必须包含任务 `primary_point_code`。病例审核 digest 将有序知识节点关联纳入，因此变更关联会使旧审核摘要失效。微训练 resource variants 必须带可见 objective/options 与审核私有 criteria；PUT 只能保存经引用重新解析的 criteria，不得由教师覆盖。旧 `MedicalReview` 记录保留，摘要不匹配时 fail closed 并要求正式复审，禁止迁移脚本或 Demo 伪造重新审核。后端专项与全量证据见交付记录。

`GET /student/classroom-case-attempts/{attempt_id}/context` 只接受当前学生本人可读取的病例尝试；训练中断时也需要解析上下文以安全返回任务包。服务端从 attempt 的 `learning_task_id → student-owned LearningTask → classroom_package LearningPlan` 解析回程身份。独立病例返回 `{is_classroom_task:false,task_id:null,package_id:null}`。客户端的 package/task 路由参数只可作失败回程提示，不作为归属或授权依据；打开任务包仍须调用学生本人范围的包详情接口验证。

API `POST /student/classroom-tasks/{task_id}/start` 的 `case_attempt_id` 保持正整数 schema，不因 Demo 放宽生成 OpenAPI。现有 Demo training 的 attempt ID 是字符串，因此 learning feature 内部的 start 结果可用 `string | number`；API adapter 继续返回 number，Demo adapter 返回训练 feature 的原始 string。小程序仅在生成路由时转为字符串，attempt/assessment 仍经 training public API 读取。任何时候都不能把路由 `packageId` 或 `taskId` 当授权源。

analytics列表返回items{student_id,nickname,completed_classrooms,improved_classrooms,last_completed_at|null}及total/limit/offset；详情返回period、completed_classrooms、improved_rate|null、knowledge[]、dimensions[]、report_page。overview返回相同口径班级聚合；单独progress返回published/completed/in_progress/overdue计数。日期默认30天，最大366天，date_from不得晚于date_to；相同范围的列表计数与详情聚合必须一致。

课堂进度的规范计数入口是 `GET /analytics/classroom-progress`，不是另建 `/teacher/classes/{class_id}/classroom-task-progress`。该接口只返回按发布窗聚合的四项计数。逐学生列表使用已接入的 `GET /teacher/classes/{class_id}/classroom-task-progress-items`：输入必填 `session_id`、`status=unpublished|in_progress|overdue|completed` 可选、`limit/offset`；返回 `items[{student_id,nickname,package_id|null,execution_status,completed,total,current_cycle|null,due_at|null,final_report_id|null}]` 与 total/limit/offset。`execution_status` 还可能是 `report_unavailable`，该状态可在无筛选列表看到，当前不作为请求筛选值。列表以课堂当前参与者及该课堂已发布包的学生并集为基准；未发布者 `package_id=null`，已完成项必须有最终报告，否则返回 `report_unavailable` 而非假报告。仅课堂所属教师可查，跨班/跨课堂标识统一 404；归档班级的历史只读按既有授权策略处理。结果统计仍只读最终报告，逐学生进度不得混入 `/analytics/students`。当前实现、测试范围及小程序未验收项见[实施进度记录](deliveries/implementation-progress.md)。

既有 /analytics/overview、/analytics/students/{student_id} 由 analytics owner 调整合同，新增 /analytics/students 列表（class_id 必填、日期筛选及分页）。详情 class_id 必填并由服务端校验 owner 与该班当前成员或历史报告归属，不依赖前端先读 plan 才授权。所有相关 mapper/Zod/生成合同同步。病例分析旧端点不再从独立病例证据提供新教师表现，处理见第07册。

上述overview和student详情在原路径发布新版DTO，schema_version=2、data_basis=completed_classroom_packages；不保留同一路径静默返回旧结构的分支。旧均分/综合分字段移除，API与小程序必须同批更新；旧客户端契约拒绝时显示更新提示，不能恢复旧证据统计。新增 GET /analytics/classroom-progress（class_id、date_from/to、session_id可选）返回第04册进度口径。既有知识统计路径同步改读报告的knowledge投影；旧病例详情保留授权检查后返回409 STATE_CONFLICT和退役说明，官方页面只渲染迁移提示而不发起该查询。

2026-09-24 当前增量核验：analytics v2 总览、学生列表/详情、知识、计数及逐学生进度路由与 `learning` 学生包/任务、最终报告及教师报告路由均已进入 OpenAPI。教师学情组件通过 analytics public API 展示仅基于最终报告的综合口径；PBL 跟进页只读本课堂最终报告，课堂进度另列未发布/进行中/逾期/已完成/报告暂不可用。Demo analytics 从 learning Demo 的正式包/报告读模型聚合；新增生命周期测试覆盖首轮直接通过、首轮失败→只激活目标→二轮达标、病例同路径、二轮耗尽、逾期、报告暂不可用与题库空/归档。报告暂不可用由非公开 fixture 故障开关模拟读取缺失，生产合同与 OpenAPI 不因此扩展。旧 analytics/PBL API 保留的兼容 consumer 已静态分类：新 v7 发布入口不调用旧 `task_published`；旧 `getTeacherPblFollowUps` / `createLearningPlan` 仅留在旧 port/adapter、v6 兼容或测试/未挂接组件。真实微信交互和页面筛选分页/返回/错误恢复仍待验收。教师最终报告列表 GET 仍只声明 class_id、session_id、student_id 与分页，日期统计由 analytics 负责。

student详情的report_page接受独立report_limit/report_offset，默认20/0；summary不受该分页影响。教师全班overview允许沿既有规则选择本人班级集合，集合中的报告按report_id去重；student详情与列表必须单班，不能以缺省class_id扩大范围。

## DTO 定义

PackageSummary：id、session{id,title,topic_code,goal_points}、class_name、execution_status、current_cycle、due_at、progress{completed,total}、final_report_id|null。学生不接收teacher_id、其他学生、来源诊断ID。

TeacherPackage：上述字段加 student{id,name}、class_id、snapshot_id、version、draft_digest、publication_status、items、blocking_issues[]。blocking_issues 为 code/item_id?/message，不返回provider原始错误。

PackageItem：id、stable_key、position、cycle_number、task_type、primary_point_code、point_codes、dimension_ids、target、public_definition、resource_version、medical_review_status。TeacherPackageItem 另含 answer_key、explanation、assessment_rules、source_digest、`included_in_package`；该字段表示该题轮次是否属于当前草稿/正式任务包，不是医学审核状态。StudentPackageItem 未作答不含答案解析和私有评分字段，也不暴露未激活第二轮题面；正式发布只复制 included 项。

FinalReport：id、package_id、session_summary、class_name、diagnosis_summary、result、policy_version、published_version、completed_at、target_results[]、cycle_evaluations[]、task_summaries[]。result 仅 improved/needs_reinforcement。TargetResult 含类型、编码、标签、最终有效轮次、score|null、threshold|null、evidence_present、passed；无综合分。TeacherFinalReport 增加学生展示身份，学生版删除内部身份与诊断定位字段。

BankItem：id、version、status、task_type、title、prompt、options、answer、explanation、point_codes、dimension_ids、medical_review_status、updated_at。仅教师可用；来源审计引用不输出学生身份/诊断正文。每条入库一个具体轮次题目，首轮/第二轮分别可入库，UI 明确题目版本。

answer schema：choice 为 selected_option 整数；discussion 为 text 1–4000字；micro_drill 使用资源定义的结构化 answer_schema；focused_retry 走现有 training attempt，不接受客户端分数或伪造完成。最终评分只来自服务端。

当前已接入的课堂 micro_drill 使用短文本 `text`（1–4000字）。评分器只读取已验证的题面答案字段，其他客户端键不成为关键词命中或评价证据；原请求 payload 可保留作幂等比对。后续接入其他结构化 answer_schema 时须实现对应校验与学生控件，不能只把整个自由 dict 交给通用文本提取器评分。

PUT草稿的items为完整集合，已有item_id和stable_key不可改；题型、target和主节点不可任意改，资源替换须同目标同型。教师可将一组完整的两轮候选标记为 `included_in_package=false`，也可在仍为草稿时恢复；不得省略其数据库身份或仅提交部分轮次。移除只表示排除在当前发布集合之外，不物理删除题目来源行：`TeacherQuestionBankRevision` 与 `BankImportReceipt` 可用外键引用该行，保留它们以维护题库来源追溯和幂等回执。excluded 行仍由有权教师在草稿中查看、恢复或按原规则复制题库；不会进入医学提交的新请求、发布计划/任务、学生 DTO、评分、终态报告或教师结果统计。已发布包冻结 inclusion 状态，PUT 一律拒绝。

服务端按 `(package_id, stable_key)` 校验候选对必须恰好含 cycle 1 与 cycle 2，且两轮 inclusion 状态相同；只允许整对加入/排除。coverage 在 included 集合上重验：每个课堂知识目标仍至少有一组双轮 `retest`，每个诊断推理目标仍至少有一组双轮 `micro_drill`；因此只要不会移除某目标最后一组必需覆盖，其他完整候选对可排除。客户端可提前禁用最后一组必需候选的移除按钮，但服务端校验为最终权威。保存时 inclusion 与题面、资源引用共同进入规范化草稿摘要，版本 CAS 成功后清除 `reviewed_version`；即使只排除/恢复候选，也必须重新确认并审阅实际发布的完整集合。该规则以 `20260924_0032` 将 `included_in_package` 默认 true 写入 `classroom_package_items`，历史行升级后均保持包含。

每包最多60个两轮任务项，included 首轮最多30项且不得为零，标题1–200字、题干1–2000字、解释1–2000字，反馈0–1000字，幂等键1–100字且不得全为空白；超限422并保留草稿。included 的第二轮对应评分项必须成对存在。题库编辑使用同一题目长度与结构校验；归档不可恢复是本期默认，历史revision仍可读，不提供物理删除。

## 应用边界

pbl public 提供诊断范围、冻结快照与教学反馈；learning public 新增 ensure/save/publish package、complete task、FinalReportReadPort；content public 新增 teacher bank 与资源审核验证端口。application 不导入其他模块 api/ORM。

前端 pbl/public.ts 提供诊断整包和课堂进度组合；learning/public.ts 提供学生包与最终报告；content/public.ts 提供题库；analytics/public.ts 提供综合学情。页面只消费领域view。bootstrap wiring 唯一选择 API/Demo，禁止 API 失败回退。

## 幂等、缓存和一致性

发布键在 teacher+operation 范围唯一，同键同规范化请求返回原回执，异payload409；先验证授权再返回回执。不同键并发发布同包，只允许一个成功，另一个返回409并可GET确认。PUT 必须版本条件更新。消息、任务、入库均保留独立幂等身份。

发布事务同时冻结资源摘要；中途医学状态/目录/版本变化触发409，不部分发布。题库编辑新增revision且使原有医学批准失效。发布、任务提交和入库分别失效其相关GET缓存；身份切换使在途响应失效。API业务数据只内存缓存。

## Demo

增加版本化、用户作用域的包/报告/教师题库集合，旧 Demo 数据只迁移可证明关联，其余标记历史；不清空已有 storage。当前 Demo 已提供四个显式合成 PBL 诊断：`90003` 无薄弱点验证（失败后只激活变式并通过）、`90004` 薄弱点病例重练与推理微训练（assessment 映射到目标，失败目标才激活二轮，终态统一报告）、`90005` 首轮直接达标和 `90006` 二轮耗尽。回归还覆盖病例 task-id 幂等与身份隔离、逾期和报告暂不可用进度态；题库从空状态进入教师显式复制、筛选、编辑及归档，副本不改已发布任务。报告不可用由测试 fixture 注入，不作为正常业务动作；应与正常发布/完成种子区分。未解决项是完整页面状态同态/真实微信交互、更多 API/Demo conformance 与报告写入故障原子回滚验收。相同学生/班级/课堂 ID 在各 feature 一致；不得在页面拼装伪报告。Demo 标注合成，不能证明医学审核或后端授权。

## 契约链

修改 Pydantic → contract:generate → 审查 OpenAPI/生成类型/fixture → Zod与显式mapper → conformance及API/Demo测试 → contract:check。旧接口的兼容变更与弃用响应必须同时生成，不能只隐藏按钮。
