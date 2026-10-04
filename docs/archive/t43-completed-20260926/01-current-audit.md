# 01 当前事实与差距

状态：本节表格保留 2026-09-22 文档编写时的基线事实与原始差距，不充当 2026-09-23 实施现状。工作区为 dev，原检查时比 github/dev 领先 8 次提交，存在大量暂存、未暂存和未跟踪修改。不能以 HEAD 覆盖工作树。

## 历史快照：2026-09-23 实施后增量复核（已被 2026-09-24 当前实施快照更新）

工作树现已新增迁移 `20260923_0031`、课堂包/最终报告/教师题库模型及部分后端 API；新建 PBL 会话固定 v7，迁移中旧会话固定 v6。教师草稿、按题目摘要的客观题医学审核、整包发布、题库副本、学生客观/讨论任务提交、病例任务启动/回调、终态报告及受控修复命令已有定向测试。analytics 后端已切到只读最终报告口径，并提供逐学生课堂进度接口；前端现有 v2 Zod/mapper、学情工作区的总览/进度/知识/学生列表及学生综合详情。教师 PBL 首页巩固分区和详情页现改读课堂终态报告，学情综合详情可打开该报告；学生任务包与教师逐学生课堂进度已有局部页面，Demo 报告适配器只如实返回空结果。它们仍是部分接线：课堂进度真实交互、教师题库页面与完整 Demo 状态均未闭合；修复工具真实受管库演练和病例五阶段 API 全流程仍缺。不能依据下表保留的 2026-09-22 原始差距推断当前代码没有对应符号。逐项证据以[实施进度记录](deliveries/implementation-progress.md)为准；下一执行者先重做只读审计，再使用下表追溯变更动机。

## 历史快照：2026-09-24 初次再核验（已被下方当前实施快照更新）

后端已有 `POST /teacher/pbl-work-items/{snapshot_id}/task-package`、包 GET/PUT/医学提交/发布及题库五端点；当时教师诊断详情仍调用旧逐建议反馈发布，`reviewed-resources`、题库前端及病例上下文也尚未接通。新增一个病例五阶段 HTTP 到最终报告测试已通过，但不能扩展为所有分支已通过。该段仅解释本计划如何随实现演进，不能作为当前断点清单。详细当前差距见[第11册](11-remaining-work-handoff.md)的“本轮复核基线”。

## 2026-09-24 当前实施快照

该快照取代上述历史快照中“当前缺少”的判断；历史描述保留作实施轨迹，不能再作为本轮断点清单。当前已观察到：教师 v7 课堂诊断详情走 `TeacherClassroomPackageReview` 的整包流程，`learning/public.ts` 和仓储支持草稿、资源核验、医学提交与发布；教师题库有 content public、API/Demo adapter、内容入口及列表/详情编辑归档页。学生正式包提交病例后，训练/分析页通过 `/student/classroom-case-attempts/{attempt_id}/context` 向服务端解析任务包身份，URL 参数仅作返回提示；结束后重新读取本人包。analytics v2 通过最终报告只读端口形成学情统计，PBL 本课报告及逐学生课堂进度有读路由和前端局部页面。Demo 现有合成课堂诊断 `90003`–`90006`：无明确薄弱点双轮验证、`90004` 病例重练和推理微训练两轮、首轮达标、二轮耗尽；微训练路径覆盖资源查询/绑定、审核评分依据保存、学生文本评分及未达标目标激活第二轮。另有病例任务 task-id 幂等 start/attempt 上下文与 assessment 回包，病例仅写入所属整包评价。Analytics Demo 现能派生逾期与 `report_unavailable` 状态，报告不可用采用显式故障 fixture；教师题库测试覆盖空列表、主动复制、编辑与归档。

剩余差距：前端全局 coverage 仍低于既定 85%/80% 门槛；分页/返回/缓存切换与 `report_unavailable` 的真实页面恢复仍需复核。最终报告 builder 故障原子回滚已有 API 故障注入用例，完整后端复跑正在执行。PBL 旧 follow-ups、`task_published`、`createLearningPlan` 和 `TeacherPblClassrooms` 旧进度调用均已静态分类为 v6/旧学习兼容或当前未挂接组件，不作为新版课堂写入路径；还需审查该分类不会由官方导航重新暴露。已执行前端全量 355 tests、定向 Demo 测试、type/lint/boundary/contract/build；微信开发者工具因 `wechatide.cmd` 未找到，普通编译、真实点击/输入/滚动和截图仍 Unverified。历史 plan 自动转换本期明确不做；第07册只读聚合审计，`--apply` 拒绝写入是批准策略。真实数据库演练、Coze、授权医学审核、真机仍属外部验收，不由代码存在推导通过。

## 2026-09-25 继续实施复核

病例资源边界修复阶段运行的全量后端 `backend:check` 退出 0：318 passed、88.70% coverage、Ruff 通过；随后 `backend:test:safety` 14 passed、`backend:test:migrations` 22 passed。另对病例资源目标边界补足 `test_t43_package_draft.py` 到 14 项并全通过。检查发现病例/推理蓝图已做医学批准与版本/digest校验，但资源 query/save 原先没有确认其知识节点属于包任务主目标，也没有在保存时重新锁定到诊断所属课堂病例；微训练资源落库还丢失审核 criteria，导致医疗状态回落。现将关联知识节点纳入 `case_digest`，资源列表和保存/报告终态验证双重校验诊断绑定病例 ID 与任务主知识点，微训练两轮目标文本/options/criteria 使用审核蓝图权威值，并拒绝编辑者自改私有评分规则。新摘要规则使旧 `MedicalReview.case_digest` 无法再冒充包含知识关联的审核；旧记录保留但对新课堂评分资源失效，必须走授权复审，不做自动重签。该改动没有 schema 或 Alembic 迁移，也没有连接/修改真实数据库。之后新增的 `20260924_0032` 软排除迁移详见下方续跑增量；本段 318 passed 不代表包含该后续迁移的完整全量复跑。

此前前端页面行为测试覆盖整包审阅确认/固定学生、题库过滤和并发请求竞态/副本版本、v7/v6 分流、逐学生课堂进度与报告返回，以及学生提交恢复、学情范围分页、教师身份切换。最近全量 Vitest 已更新为 83 files / 411 passed；学生学习首页、任务包详情、病例训练和病例分析报告的身份隔离行为测试 12 项通过。Lint、type-check、前端边界检查通过；此前题库/学情/学生任务页 14 项行为测试与三个 learning adapter 文件 17 项合同测试通过。课堂包 adapter 为 99.28%/100%/90.91%，教师终态报告 adapter 为 100%/100%/100%。

最近 `npm run test:coverage` 的 411 项测试全通过但命令退出 1：lines/statements 71.44%、functions 60.71%、branches 76.51%，低于 85%/85%/80%。不得降低阈值。Demo watcher 已重新编译最新学生端身份清除状态并输出 `Build complete. Watching for changes...`，但 DevTools 普通编译、真实小程序点击/输入/滚动、截图、其他角色/局部失败、权限负向完整矩阵及返回等真实页面恢复仍待验收；真实数据库恢复演练及 Coze/专家/生产/真机也未完成。详细退出码见[实施进度记录](deliveries/implementation-progress.md)。

### 2026-09-25 后续增量：整包候选软排除

新增 `classroom_package_items.included_in_package` 与迁移 `20260924_0032`；旧题默认为纳入。教师可以按 stable key 成对排除/恢复首轮与第二轮变式，保存与发布均拒绝半对状态或移除必要课堂目标覆盖。被排除的题目行及来源关系保留，避免破坏个人题库副本/回执外键；医学新提交、正式计划和学生可执行任务只读取纳入项。排除项不会因当前审核资源版本过期而阻止保存；新选择的资源绑定不会随排除项持久化，既有来源引用保留，重新纳入时仍重新验证资源。API、Demo、领域映射、教师审阅 UI 与定向测试已同步。此次增量定向证据及未覆盖项见[实施进度记录](deliveries/implementation-progress.md)；不能据此宣称完整 T43 门禁通过。当前 Alembic 工作树单一 head 为 `20260924_0032`，并无证据表明真实数据库已升级。

### 计划编写时的历史调用链基线

以下事实描述 T43 计划形成时观察到的旧实现，保留用于解释改造来源；它们不是当前运行时代码状态。当前差距以本文件上方 2026-09-25 续跑记录和[第11册](11-remaining-work-handoff.md)中的接手快照为准。

| 当前代码位置（仓库根相对路径）                                   | 计划编写时观察到的事实                                                 | 当时的 T43 差距                                |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------- |
| backend/app/modules/pbl/infrastructure/provider_schema.py        | v6 ready 必须有 finding、建议题和补充卡；complete 必须 ready           | 无薄弱点且证据充分的完成路径不可表达           |
| backend/app/modules/pbl/application/use_cases.py                 | adopt 以单 suggestion 发布开放题并创建两轮资源                         | 整包预览、编辑、一次发布和个人唯一包尚无       |
| backend/app/modules/learning/infrastructure/pbl_interventions.py | create 按 student + pbl_suggestion + suggestion ID 幂等                | 同课堂可有多计划                               |
| backend/app/modules/learning/infrastructure/models.py            | 学习计划唯一键为 student/source_type/source_id；评价按 plan/cycle 唯一 | 缺课堂任务包标识、发布冻结、最终报告表         |
| backend/app/modules/learning/infrastructure/pbl_mastery.py       | 当前轮全部完成才判定；第一轮失败激活第二轮；第二轮失败也 completed     | 可复用规则，需适配整包与报告原子生成           |
| backend/app/modules/training/application/use_cases.py            | 病例 assessment 生成后按有效班级写 class_detail 证据                   | 单病例绕过整包完成进入教师统计                 |
| backend/app/modules/learning/application/use_cases.py            | 独立病例完成可以自动生成个性化计划                                     | 独立练习需退出正式课堂待办，不递归生成教师任务 |
| backend/app/modules/pbl/application/reporting.py                 | 学生只读报告在讨论中也存在，按 session 聚合多计划                      | 过程学习记录与最终报告需明确分型               |
| backend/app/modules/pbl/application/use_cases.py                 | follow_ups 读取已发布计划，包括进行中                                  | 最终报告列表与课堂进度需分开                   |
| src/pages/teacher/pbl-follow-up-detail/pbl-follow-up-detail.vue  | 先读 plan，再按计划身份读近 30 天 analytics                            | 综合学情应迁回学情页                           |
| src/pages/teacher/analytics/student-detail.vue                   | 历史深链转向 PBL 跟进                                                  | 恢复受服务端授权的学生综合学情                 |
| src/components/teacher/TeacherPblWorkItemDetail.vue              | 已有单建议选择、编辑、反馈并发布、指定/全班目标                        | 改为固定学生的两轮整包编辑                     |
| src/pages/student/case-report/case-report.vue                    | assessment 展示为“模型报告/兜底报告”，可进入个性化计划                 | 改为学生训练分析，课堂病例回到所属任务包       |

| 当前代码位置（仓库根相对路径）                                   | 当前事实                                                               | T43 差距                                       |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------- |
| backend/app/modules/pbl/infrastructure/provider_schema.py        | v6 ready 必须有 finding、建议题和补充卡；complete 必须 ready           | 无薄弱点且证据充分的完成路径不可表达           |
| backend/app/modules/pbl/application/use_cases.py                 | adopt 以单 suggestion 发布开放题并创建两轮资源                         | 整包预览、编辑、一次发布和个人唯一包尚无       |
| backend/app/modules/learning/infrastructure/pbl_interventions.py | create 按 student + pbl_suggestion + suggestion ID 幂等                | 同课堂可有多计划                               |
| backend/app/modules/learning/infrastructure/models.py            | 学习计划唯一键为 student/source_type/source_id；评价按 plan/cycle 唯一 | 缺课堂任务包标识、发布冻结、最终报告表         |
| backend/app/modules/learning/infrastructure/pbl_mastery.py       | 当前轮全部完成才判定；第一轮失败激活第二轮；第二轮失败也 completed     | 可复用规则，需适配整包与报告原子生成           |
| backend/app/modules/training/application/use_cases.py            | 病例 assessment 生成后按有效班级写 class_detail 证据                   | 单病例绕过整包完成进入教师统计                 |
| backend/app/modules/learning/application/use_cases.py            | 独立病例完成可以自动生成个性化计划                                     | 独立练习需退出正式课堂待办，不递归生成教师任务 |
| backend/app/modules/pbl/application/reporting.py                 | 学生只读报告在讨论中也存在，按 session 聚合多计划                      | 过程学习记录与最终报告需明确分型               |
| backend/app/modules/pbl/application/use_cases.py                 | follow_ups 读取已发布计划，包括进行中                                  | 最终报告列表与课堂进度需分开                   |
| src/pages/teacher/pbl-follow-up-detail/pbl-follow-up-detail.vue  | 先读 plan，再按计划身份读近 30 天 analytics                            | 综合学情应迁回学情页                           |
| src/pages/teacher/analytics/student-detail.vue                   | 历史深链转向 PBL 跟进                                                  | 恢复受服务端授权的学生综合学情                 |
| src/components/teacher/TeacherPblWorkItemDetail.vue              | 已有单建议选择、编辑、反馈并发布、指定/全班目标                        | 改为固定学生的两轮整包编辑                     |
| src/pages/student/case-report/case-report.vue                    | assessment 展示为“模型报告/兜底报告”，可进入个性化计划                 | 改为学生训练分析，课堂病例回到所属任务包       |

现有 PBL 教学审阅已经有诊断详情入口；不能把“所有题目目前都在内容页审阅”写为代码事实。T43 要消除的是单建议发布模型及内容页可绕行的相关入口，统一实际任务预览和发布。

## 边界与依赖

pbl 拥有课堂、诊断和教师教学审阅；learning 拥有任务执行、评价与最终报告；content 拥有题库、公开资源和医学审核；analytics 通过 learning 的只读 port 聚合最终报告。跨模块只用 public 合同或显式 port，由 wiring/composition 装配。

本计划编写时的 Alembic head 曾为 `20260923_0031`；2026-09-25 后续增量新增 `20260924_0032`，当前工作树单一 head 为 `20260924_0032`。尚未据此推断任何开发、共享或生产数据库已升级。OpenAPI 和 TypeScript 为生成物。API/Demo 只能在 bootstrap 选择。旧 reports.Report 是已退役的普通问答报告，不复活为 T43 报告容器。

## 接手审计清单

1. 保存 git status、branch、diff/stat 与目标文件哈希，记录实际基线；不输出配置秘密。
2. 核对新课堂目标编码、当前有效成员、已归档班级策略和旧任务引用。
3. 搜索所有 suggestion adoption、任务提交、病例完成回调、教师 analytics 消费者与内容发布入口。
4. 核对 Demo seed/store/adapter 的用户作用域和旧数据版本。
5. 核对 package.json 的真实命令。旧 test:mp:* 多数指向禁用 WebSocket 脚本，不能用于 T43 验收。

## 工作树保护

2026-09-22 的原文档交付只新增 T43 文档并修改计划索引、阶段概述、根规则；之后 T43 已有运行时代码改动，不能把原文档交付范围误作整个实施范围。T41 及更早未跟踪目录保留原样、退出当前计划索引；不恢复已删除文档，不清理截图，不提交或推送。
