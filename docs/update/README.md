# 审计整改与个性化跨病例训练——自动化更新指南

> 文档版本：3.0  
> 编写日期：2026-08-23  
> 主要执行者：GPT-5.6 Terra  
> 计划周期：6 周，分为两个强制质量阶段  
> 唯一目标：先修复上一阶段未闭环和安全缺口，再完成“评估—个性化计划—微训练—跨病例迁移—能力复盘”的比赛展示闭环。

本文件是当前唯一有效的后续实施规格。历史更新目标、旧审计结论和代码中的占位描述均不得覆盖本文件的固定决定。

将本文件交给执行者时，直接使用下面的启动指令：

```text
请完整阅读 D:/CODE/weixin/wxprogrom7.15/docs/update/README.md，将其视为决策完备且唯一有效的下一阶段实施规格。请按文档顺序自主完成审计复核、代码更新、Alembic 迁移、Demo/API 双模式实现、测试、修复、质量门和最终验收。不要重复询问文档已经固定的产品或技术选择。缺少真实 AI 地址、密钥或模型名时，按本文规定使用确定性兜底继续完成。第一阶段质量门未通过时不得开始个性化训练功能。不要自动提交、推送、部署、导入真实数据或修改微信后台配置。
```

## 0. 强制执行协议

### 0.1 自主执行边界

1. 开始前阅读根目录说明、`docs/`、前后端配置、迁移、测试和当前工作树，建立真实基线。
2. 仓库存在大量历史删除、修改和未跟踪文件；它们属于项目迁移现状，不得清理、回滚或覆盖与本任务无关的内容。
3. 所有实现决策以本文件为准。发现代码与本文冲突时，修复代码、测试和其他文档，不削弱本文验收要求。
4. 第一阶段只收口安全、教师闭环、班级和学情功能；通过全部质量门后才能创建第二阶段迁移和页面。
5. AI 凭据缺失不构成阻塞。真实 client、mock、结构化校验、一次重试、审计和确定性兜底仍必须完整实现。
6. 数据库变更只能新增 Alembic 迁移，不修改 `20260823_0001` 至 `20260823_0004` 历史迁移，不直接删除或重建开发数据库。
7. 允许在临时目录或现有测试脚本限定的 E2E 数据库中验证空库、旧库、升级和降级；不得对现有开发数据执行破坏性操作。
8. 禁止 `git reset --hard`、`git checkout --`、递归删除仓库、自动 commit、push、发布、部署、真实账号配置和真实医学数据导入。
9. 只有真实第三方凭据、微信合法域名、生产部署和仓库外医学专家签署属于外部事项。其余问题由执行者自行定位、实现和验证。
10. 最终报告只能陈述实际完成和实际运行的结果；失败或未运行的检查必须如实列出。

### 0.2 工作树保护

执行开始时记录：

```powershell
git status --short
git diff --stat
git diff -- docs/update/README.md
```

执行过程中：

- 只修改本次功能涉及的前后端、迁移、测试和文档。
- 不格式化整个仓库，不批量移动无关文件。
- 若目标文件已有用户改动，先理解并保留其中与本文不冲突的内容。
- 每个阶段结束后检查 `git diff --check` 和 `git status --short`。

### 0.3 不得重新决策的固定事项

| 事项           | 固定决定                                                           |
| -------------- | ------------------------------------------------------------------ |
| 产品目标       | 比赛展示增强，重点展示个性化临床推理训练闭环                       |
| 主用户         | 临床医学本科生、病例作者教师、医学审核专家                         |
| 主展示端       | 微信小程序；H5 保持完整功能和 E2E 可用                             |
| 运行模式       | 显式 Demo/API 双模式，禁止静默混用数据                             |
| 数据库         | 本期继续 SQLite 和 Alembic                                         |
| 登录           | 继续演示身份，不接正式微信认证                                     |
| AI             | OpenAI-compatible 动态微训练生成，结构化响应、一次重试、确定性兜底 |
| 真实 AI 不可用 | 所有主流程仍可完成，界面明确标注 fallback                          |
| 正式能力成绩   | 只由完整 guided case assessment 更新                               |
| 微训练成绩     | 独立展示为练习掌握度，不混入正式六维均分                           |
| 个性化计划     | 每个计划固定三项任务                                               |
| 跨病例迁移     | 使用已经医学审核通过的完整病例，不动态发布新病例                   |
| 动态内容范围   | 仅基于 approved practice blueprint 生成微训练表述和情境变化        |
| 动态内容评分   | 服务端固定 criteria 决定分数，AI 不决定总分                        |
| 站内提醒       | 只建设应用内通知和未完成卡片，不接微信订阅消息                     |
| 教师能力       | 本期只查看学生计划，不发布作业、不人工改写计划                     |
| 医学审核       | 具体病例版本 approved 且 digest 一致后才能发布                     |
| 作者自审       | 禁止                                                               |
| 新展示病例     | 急性胸痛、右下腹痛，均为 basic 五阶段合成病例                      |
| 非目标         | 作业运营、正式微信登录、PostgreSQL、对象存储、生产部署、外部推送   |

## 1. 当前真实审计基线

### 1.1 已实际通过的自动检查

审计日期为 2026-08-23，当前基线如下：

- 前端 lint 和类型检查通过。
- 前端共 9 个测试文件、25 个测试通过。
- 前端覆盖率：lines/statements 95.48%、functions 97.14%、branches 78.09%。
- 后端 Ruff 和 22 个测试通过，总覆盖率 92.40%。
- `case_attempts`、`problems`、`case_ai`、`case_training` 等病例核心模块覆盖率达到或接近上一阶段模块门。
- 微信小程序生产构建通过。
- H5 生产构建通过。
- Playwright 共 4 个 E2E 通过。
- API 模式构建产物隐藏事实扫描通过，学生公开接口未直接返回完整病例定义、参考路径或量表 criteria。
- OpenAI-compatible HTTP 调用、结构化响应、失败重试和确定性评价兜底已经存在。

上述结果仅证明当前测试集合通过，不代表上一版功能完整兑现。

### 1.2 必须重新打开的审计项

执行开始时创建或更新 `docs/audit/personalized-practice-audit.md`，使用 `open | in_progress | verified | accepted_external` 四种状态。以下审计项初始状态全部为 `open`：

| ID         | 严重度 | 当前证据                                                             | 必须结果                                                           |
| ---------- | ------ | -------------------------------------------------------------------- | ------------------------------------------------------------------ |
| V3-AUD-001 | P0     | `ProblemUpdate` 接受 status，PUT 可将 guided case 直接设为 published | 所有结构化病例只能经过独立 publish endpoint 和审核 digest 门禁发布 |
| V3-AUD-002 | P0     | 任意 teacher 可调用 authoring 读取其他作者隐藏事实和 rubric          | authoring 仅作者；审核专家使用隔离的只读 review view               |
| V3-AUD-003 | P0     | API 编排器没有提交医学审核动作，直接发布必然冲突                     | 保存、提交审核、查看状态、发布形成可操作闭环                       |
| V3-AUD-004 | P0     | 审核详情只显示标题和意见框                                           | 审核专家可完整审阅病例、量表、练习蓝图、digest 和历史记录          |
| V3-AUD-005 | P0     | Demo 自定义病例可直接发布，没有独立审核状态机                        | Demo 与 API 使用相同状态、权限、digest 和不可变记录语义            |
| V3-AUD-006 | P1     | 班级只有后端 CRUD，没有教师页面                                      | 教师可创建、改名、归档、按 external ID 加入和移除学生              |
| V3-AUD-007 | P1     | ClassMember 不参与学生病例可见性，legacy class_ids 未同步            | 两种数据源并集可见，迁移和登录同步均幂等                           |
| V3-AUD-008 | P1     | 病例分析和学生档案页面是占位页                                       | 总览、病例和学生三级学情真实可下钻                                 |
| V3-AUD-009 | P1     | 分析测试未覆盖完整统计矩阵和一万条性能门                             | 固定统计口径、权限和性能全部有自动测试                             |
| V3-AUD-010 | P1     | DemoMessage 始终读取 CAP facts，attempt version 固定为 1             | 所有 Demo attempt 使用自身病例版本、事实和量表                     |
| V3-AUD-011 | P1     | “呼吸困难”等普通病史问题被当作安全攻击拦截                           | 只拦截真实提示注入，正常问诊继续事实释放                           |
| V3-AUD-012 | P1     | 前端 branches 78.09%，且覆盖范围不含新增教师模块                     | branches 至少 80%，所有新增 service/mapper 纳入覆盖                |
| V3-AUD-013 | P1     | E2E 只完整覆盖学生首轮病例                                           | 覆盖审核发布、克隆、重练、AI失败和个性化闭环                       |
| V3-AUD-014 | P1     | 0004 未补 author FK、兼容回填和全部组合索引                          | 0005 在空库和旧库路径上完整修复                                    |
| V3-AUD-015 | P1     | 根说明、功能说明和原审计报告存在过时声明                             | 文档与实际接口、限制、测试结果一致                                 |

P0 全部 verified 前不得开始班级和学情 UI 收口；V3-AUD-001 至 V3-AUD-015 全部 verified 前不得创建 0006。

### 1.3 审计证据格式

每项记录必须包含审计 ID、严重度、状态、复现路径、复现命令、风险说明、修复摘要、验证命令和实际输出摘要。不得仅凭代码存在或总测试通过将审计项标记 verified。

## 2. 第一阶段完成定义

第一阶段完成必须同时满足：

1. 审核发布无法通过 PUT、Demo helper 或其他旁路绕过。
2. 隐藏事实、参考路径、rubric criteria 和练习蓝图只对作者及有权限的审核专家开放。
3. 教师能在小程序中完成保存、提交审核、查看退回意见、重新编辑、重新提交和发布。
4. 审核专家能查看完整版本内容并执行批准或退回，作者不能自审。
5. Demo 和 API 在病例作者、审核状态、不可变记录、克隆和发布门禁上行为一致。
6. 班级管理和 legacy 数据兼容可用，跨教师资源返回 404。
7. 学情总览、病例详情、学生档案均为真实数据页面，并符合固定统计口径。
8. Demo 自定义病例不会读取 CAP 的隐藏事实或量表。
9. 正常临床病史提问不会被误判为提示注入。
10. 第一阶段自动质量门全部通过。

## 3. 第一阶段实施规格

### 3.1 结构化病例发布安全

- `ProblemUpdate.status` 对 guided case 不再生效。请求中出现非空 status 时返回 422 `VALIDATION_ERROR`；普通 question 保持原行为。
- guided case 的 `status` 只能由 publish/reject 等明确状态接口修改。
- `POST /problems/{id}/publish` 同时校验当前用户为作者、审核状态 approved、存在当前 problem/version 的批准记录、digest 一致、病例定义及量表通过严格 schema。
- 校验失败不改变 published_at；digest 不一致时审核状态重置为 `not_submitted`。
- 已发布 guided case 对所有 PUT 拒绝 409 `STATE_CONFLICT`；修改只能 clone 新版本。
- `clone-version` 复制他人内容时只允许源为 approved published；不能复制他人草稿。
- 克隆产生新 author、新 version、draft、not_submitted，不复制审核记录。

### 3.2 authoring 与审核视图隔离

- `GET /problems/{id}/authoring`：只允许该版本作者访问。
- 新增 `GET /problems/{id}/medical-review-view`：只允许 `permissions.medical_review`。
- review view 返回公开 metadata、完整 CaseDefinition、CaseRubric、practice blueprints、当前 digest、作者摘要、版本关系、审核状态和历史记录。
- 普通教师访问他人 authoring 或 review view 返回 404，避免暴露资源存在性。
- 审核权限不自动获得教师班级或学生分析权限。

### 3.3 医学审核状态机

```text
create / clone / edit
        ↓
not_submitted
        ↓ submit
pending
   ↙          ↘
rejected     approved
   ↓ edit       ↓ publish
not_submitted  published
```

- 只有作者能提交审核。
- pending 时作者不能修改正文；需由审核专家退回。
- rejected 后修改受审核内容，状态重置为 not_submitted。
- approved 后内容不可修改，只能发布或 clone。
- 作者自审返回 409 `STATE_CONFLICT`。
- rejected 必须填写至少 5 个字符的意见；approved 意见允许为空。
- MedicalReview 没有更新和删除接口。
- digest 覆盖 title、description、specialty、difficulty、estimated_minutes、target、target_ids、case_definition、rubric、capability_tags 和 schema version。

### 3.4 教师编排器与审核页

编排器按状态显示固定动作：

- draft/not_submitted：保存草稿、提交医学审核。
- pending：只读预览和状态，禁用编辑与发布。
- rejected：显示最新意见，允许编辑、保存和重新提交。
- approved：只读预览和发布。
- published：显示版本和“创建新版本”。

保存成功后以服务端 ID、slug、version、review status 和 digest 更新本地状态。提交审核和发布使用独立动作并防重复点击。

审核列表支持 pending、approved、rejected 和数量；详情分区展示元数据、学生开场、隐藏事实、参考路径、六维 criteria、practice blueprints、digest、版本关系和历史意见。批准前显示确认说明；退回必须填写有效意见。

### 3.5 Demo 审核对齐

- demo_teacher 是作者，demo_reviewer 具有 medical_review 权限且不能成为同一病例作者。
- 自定义草稿初始 not_submitted；teacher 提交后 reviewer 队列可见。
- reviewer 审核后写不可变记录和 digest；teacher 只能发布 approved 且 digest 一致的版本。
- 修改 rejected 草稿重置状态；approved/published 版本只能 clone。
- Demo reset 同时恢复病例、审核、attempt、assessment、learning plan 和 notification 演示数据。

### 3.6 班级模型兼容与 0005 迁移

新增 `backend/alembic/versions/20260823_0005_classes_review_hardening.py`：

- 检查并补齐 `problems.author_id -> users.id` 外键。
- 补齐 `classes(teacher_id, status)`、`class_members(class_id, student_id)`、`problems(content_type, status)`、`medical_reviews(problem_id, decision, created_at)` 索引。
- 读取 active classes，以 class code 匹配学生 legacy `class_ids`，幂等插入 ClassMember。
- legacy code 没有对应 class 时不自动创建班级，不丢弃 legacy 值，并记录迁移摘要。
- 空库、0004 旧库和部分同步库均可重复安全升级。
- downgrade 只移除 0005 新增对象，不删除班级、成员或 legacy 数据。

访问控制统一调用 `student_class_codes(db, student)`，取规范化成员 code 与 legacy class_ids 并集。禁止不同 service 自行实现合并。

### 3.7 班级公共行为

保留现有接口并新增：

- `PATCH /classes/{id}`，请求 `{name?, status?}`，status 仅 `active | archived`。
- `POST /classes/{id}/members`，请求 `{student_external_id}`，只做准确匹配。

班级 code 全局唯一且创建后不可修改；跨教师统一 404；archived 班级不能新增成员且不进入默认学情；只允许 student 加入；重复加入和移除幂等。教师工作台增加班级入口和创建、改名、归档、成员列表、加入、移除、空状态，不展示全库学生名单。

### 3.8 固定统计口径

时间范围默认最近 30 天，包含 date_from 00:00:00 和 date_to 23:59:59，最大 366 天。

- eligible pair：active 班级学生与其可见 published guided case 组合。
- started pair：eligible pair 在范围内至少存在 started_at 的 CaseAttempt。
- completed pair：eligible pair 在范围内至少存在 assessed_at 的 CaseAttempt。
- current：范围内 assessed_at 最大，相同时间取 attempt ID 最大。
- baseline：范围内最早 `retry_of_id IS NULL` 的 assessed；不存在时取最早 assessed。
- completion rate：completed / eligible ×100；分母为 0 返回 null。
- improvement：current 减 baseline；只有一个结果时 delta 为 0 并标记 single_attempt。
- weak dimension：score <70，按学生去重。
- duration：started_at 到 assessed_at，排除负值和超过 8 小时。
- 分布固定为 0–59、60–69、70–84、85–100。
- 学生属于多个班级时全班总览只计算一次；指定 class_id 时按该班计算。

总览必须有班级 picker、日期范围、指标、六维、病例和学生摘要列表；病例详情展示完成率、分布、时长、维度变化和学生列表；学生档案展示病例完成、六维趋势、最近 12 个结果和薄弱维度。所有响应使用显式 Pydantic schema 和 TypeScript interface，删除教师 insights 中的通用字典 DTO。

### 3.9 Demo 病例与患者安全修复

- `demoStart` 从目标病例读取真实 version、opening 和 rubric。
- `demoMessage` 从 attempt 对应 draft 读取 history facts，使用 fact ID 去重。
- `demoComplete` 从 attempt 对应 rubric 映射 focusStage。
- 提示注入只识别忽略规则、展示提示词、输出隐藏事实、直接给答案等意图。
- 呼吸困难、胸痛、发热、咯血等是正常问诊词，不作为攻击标记。
- 自由问答继续紧急分流；标准化患者不把学生的问诊问题当成学生本人症状。

## 4. 第一阶段质量门

第一阶段全部通过前禁止创建 0006。

- 前端 lines/statements ≥90%、functions ≥90%、branches ≥80%。
- 覆盖配置纳入病例 Demo/API repository、教师 insights、班级、医学审核、analytics DTO 和纯函数。
- 后端总覆盖率 ≥90%；problems、medical_review、classes、analytics、case_attempts、case_ai、case_training 各 ≥85%。
- 不得删除旧测试、降低阈值或排除新增模块。
- 使用临时 SQLite 生成至少 100 名学生、10 个病例、10,000 条 attempt/assessment、多次 retry 和重复班级成员；预热一次后三个 analytics 接口单次均 <2 秒，并断言无 N+1。
- E2E 覆盖教师创建、提交、退回、修改、批准、发布、克隆，班级可见、三级学情、Demo 自定义病例和旧流程回归。

## 5. 第二阶段完成定义

1. 普通病例 assessment 后幂等生成一份 active learning plan。
2. 计划固定包含同病例重练、动态微训练和跨病例迁移三项任务。
3. AI 不可用或输出非法时，微训练仍可生成、提交、评分和反馈。
4. 学生能从首页进入计划，完成三项并看到前后对比。
5. 微训练分数不污染正式六维成绩。
6. 两套新展示病例完整、可审核、可发布、可离线演示。
7. 教师可查看计划进度但不能代答或改分。
8. 站内通知可读、可全部标记已读且不重复。
9. Demo reset 可稳定恢复比赛演示起点。
10. 第二阶段自动质量门全部通过。

## 6. 第二阶段数据模型与迁移

新增 `backend/alembic/versions/20260823_0006_personalized_practice.py`。所有 JSON 字段定义严格 Pydantic 和 TypeScript 类型。

### 6.1 病例蓝图扩展

`problems` 增加 `capability_tags: JSON, not null, default []`，元素只能为六维 ID。CaseDefinition schema version 升为 2，兼容读取 version 1，新保存统一写 version 2，并增加 `practice_blueprints`。

PracticeBlueprint 固定字段：id、dimension_id、stage_id、learner_level、public_instruction、allowed_variants、fixed_facts、fallback_prompt、answer_schema、criteria。answer_schema 仅 `short_text | evidence_grid | decision_cards`。criteria 权重合计 100，criteria、fixed facts 和答案只对作者、审核专家和服务端开放。

### 6.2 LearningPlan

- id、student_id FK、source_assessment_id FK unique。
- status：`active | completed | superseded`。
- target_dimension_ids：1–2 个合法维度且有序。
- due_at：created_at 加 7 天。
- generation_mode 固定 deterministic；计划选择不交给 AI。
- model_name、prompt_version、fallback_used、failure_reason、created_at、completed_at、superseded_at。
- 同一 source assessment 只有一份计划；同一学生最多一份 active。

### 6.3 LearningTask

- id、plan_id、position 1–3，`(plan_id, position)` unique。
- task_type：`focused_retry | micro_drill | cross_case_transfer`。
- dimension_id、stage_id、problem_id、source_attempt_id。
- status：`pending | in_progress | completed`。
- public_definition、private_rubric、blueprint_id、blueprint_digest、started_at、completed_at。
- 学生响应永不返回 private_rubric。

### 6.4 LearningTaskAttempt

- id、task_id unique、student_id、status `in_progress | assessed`。
- answer、score 0–100、evidence、feedback、next_step。
- model_name、prompt_version、latency_ms、fallback_used、failure_reason、created_at、assessed_at。
- focused retry 和 cross-case 不创建该记录，而是创建关联 CaseAttempt。

### 6.5 StudentNotification

- id、student_id。
- type：`learning_plan_ready | learning_plan_due | learning_plan_completed`。
- entity_type 固定 learning_plan、entity_id、title、body、dedupe_key unique、read_at、created_at。
- 创建计划写 ready；距离 due_at 小于 24 小时时由学生首页同步动作幂等写 due；完成写 completed。
- 不建设后台定时器或微信消息服务。

### 6.6 CaseAttempt 关联

`case_attempts` 增加 nullable `learning_task_id` FK 和唯一约束。focused retry 使用来源 retry_of_id 并从 focus stage 开始；cross case 从 history 开始。task-linked assessment 完成后更新 task 和 plan，不能递归生成新计划。

## 7. 固定推荐算法

### 7.1 目标维度

按 score 升序；同分依次为 information_gathering、problem_representation、differential_diagnosis、evidence_reasoning、test_selection、management_safety。存在低于70时取最低两个；只有一个低于70时第二项取总体第二低；全部 ≥70 时只取最低一个巩固。

### 7.2 三项任务

1. focused_retry：来源病例、最低维度对应阶段，继承阶段前答案。
2. micro_drill：两个目标时用第二目标，否则用第一目标；从 approved published 病例匹配 blueprint，优先排除来源病例。
3. cross_case_transfer：排除来源 slug，只选 published、approved、digest 有效且 tag 命中最低维度的病例；优先同难度，其次 basic；按学生 assessed 次数和 problem ID 排序。

没有迁移病例时第三项替换为第二个 micro_drill，并记录 replacement reason。

### 7.3 计划状态

- 同 source assessment 重复请求返回原计划。
- 新普通 assessment 将旧 active 计划设为 superseded 后建新计划。
- task-linked assessment 只更新当前计划。
- 三项完成后 complete 接口幂等设置 completed。
- 任务按 position 解锁，不能跳过或手工完成。

## 8. AI 动态微训练

### 8.1 输入输出

AI 输入仅包含目标维度、阶段、学习层级、approved blueprint、允许变化范围和去标识化薄弱反馈，不发送 nickname、external ID、班级或无关历史。

输出严格为：

```json
{
  "title": "微训练标题",
  "context": "合成教学情境",
  "instruction": "学生任务",
  "answer_schema": "short_text | evidence_grid | decision_cards",
  "display_hints": ["不包含答案的提示"]
}
```

AI 不生成或修改评分 criteria。public definition 由输出与 blueprint 公开字段组合，private rubric 始终来自 approved blueprint。

### 8.2 安全校验和兜底

依次校验 JSON/Pydantic、answer_schema、长度上限、答案与 criteria 泄露、隐藏 ID、审核 digest、药物剂量、个体处方、真实患者指令和核心事实边界。首次失败后携带简短原因重试一次；再次失败、超时、断网或 disabled 使用 fallback_prompt。

### 8.3 微训练评分

- 按 answer_schema 校验答案。
- criterion 按固定 weight 累加，critical 缺失时上限 69。
- evidence 逐字来自学生答案，最长 160 字，最多 3 条。
- AI 只改写 feedback 和 next_step；引用非法则保留确定性反馈。
- 提交幂等，重复提交返回现有结果，不覆盖答案。

### 8.4 AI 审计

沿用 AICallLog，增加 task ID、blueprint ID 和 digest。任务名增加 `practice_generation`、`practice_feedback`；prompt version 固定 `practice-v1`。真实成功记录配置模型，fallback 记录 `deterministic-fallback`。

## 9. 两套跨病例展示内容

### 9.1 急性胸痛

- slug：`acute-chest-pain-undergraduate-showcase`。
- 专科：心血管内科/急诊教学；difficulty basic。
- tags：differential_diagnosis、evidence_reasoning、management_safety。
- 覆盖起病、疼痛特征、伴随表现、危险因素、生命体征、心电图和必要实验室结果。
- 鉴别包括急性冠脉综合征、主动脉夹层、肺栓塞和非心源性胸痛。
- 处置评价强调危险分层、监护、急诊评估和避免延误，不含药物剂量。

### 9.2 右下腹痛

- slug：`right-lower-quadrant-pain-undergraduate-showcase`。
- 专科：普通外科/急诊教学；difficulty basic。
- tags：problem_representation、evidence_reasoning、test_selection。
- 覆盖疼痛迁移、消化道伴随症状、发热、查体和基础检查。
- 鉴别包括急性阑尾炎、胃肠炎、泌尿系疾病和适用人群的妇科原因。
- 检查评价强调目的、优先级、辐射与适用性，不给真实患者处方。

两套病例均包含五阶段、隐藏事实、触发词、参考路径、至少四项鉴别、检查、处置、安全、六维量表、tags、至少两个 blueprints 和 fallback。Demo seed 创建 demo_teacher 作者和 demo_reviewer approved 工程记录；界面注明不代表仓库外医学专家签署。

## 10. 公共接口合同

### 10.1 审计整改接口

- `POST /problems/{id}/medical-review/submit`：作者；pending 幂等，approved/published 409。
- `GET /problems/{id}/medical-review-view`：medical_review 权限，返回完整只读审核视图。
- `PATCH /classes/{id}`：请求 `{name?, status?}`。
- `POST /classes/{id}/members`：请求 `{"student_external_id":"demo_student"}`。
- 原三个 analytics 接口补齐班级、日期、列表和下钻数据。

### 10.2 个性化接口

- `GET /learning/profile`：正式六维、最近完整病例、练习掌握度、active plan、未读数。
- `POST /attempts/{id}/learning-plan`：本人 assessed attempt，幂等返回计划。
- `GET /learning-plans/current`：无 active 返回 404。
- `GET /learning-plans/{id}`：本人计划、三项公开任务、进度和来源摘要。
- `POST /learning-tasks/{id}/start`：按任务返回判别联合。
- `GET /learning-task-attempts/{id}`：本人公开题面、答案和反馈。
- `POST /learning-task-attempts/{id}/submit`：返回 score、原文 evidence、feedback、next_step。
- `POST /learning-plans/{id}/complete`：三项未完成返回 409，完成后幂等。

start 返回：

```json
{
  "mode": "case_attempt",
  "task": { "id": 1, "task_type": "focused_retry" },
  "attempt": { "id": 99, "current_stage": "differential" }
}
```

或：

```json
{
  "mode": "micro_drill",
  "task": { "id": 2, "task_type": "micro_drill" },
  "attempt": {
    "id": 100,
    "status": "in_progress",
    "public_definition": {
      "title": "证据推理微训练",
      "context": "合成教学情境",
      "instruction": "完成支持与反对证据归纳",
      "answer_schema": "evidence_grid"
    }
  }
}
```

### 10.3 通知与错误码

- `GET /notifications?unread_only=&limit=`，limit 1–100。
- `POST /notifications/{id}/read`。
- `POST /notifications/read-all`。

统一 detail：400 `INVALID_DATE_RANGE`、403 `ROLE_REQUIRED`、404 `RESOURCE_NOT_FOUND`、409 `STATE_CONFLICT`、422 `VALIDATION_ERROR`。不得响应堆栈、SQL、模型原文、隐藏事实、criteria、API key 或 digest。

## 11. 前端信息架构

### 11.1 学生首页

学生登录进入学习仪表盘，顺序为当前能力画像、今日训练、站内提醒、待完成病例、最近报告、问答辅助。无 assessment 时引导 CAP；有 assessment 无 active plan 时显示生成计划。

### 11.2 计划、微训练和复盘

- 计划页显示来源病例、推荐原因、目标维度、7 天时间和三项进度。
- 任务按 position 解锁；刷新和重复点击不重复创建 attempt。
- 微训练按 short_text、evidence_grid、decision_cards 渲染结构化输入。
- 提交后锁定，显示掌握度、学生原文证据、反馈和下一步。
- 复盘分开显示正式六维变化、同病例 delta、微训练掌握度和跨病例结果。
- 未完成新的完整病例 assessment 时，正式能力不因微训练变化。

### 11.3 教师和比赛展示

教师学生档案增加计划状态、目标维度、任务进度、练习掌握度和跨病例结果，只有读取权限。

Demo reset 提供“全新演示”和“个性化闭环演示”两个固定数据集。所有按钮防重复；网络失败保留输入；AI 超时显示切换教学模板。适配 375×667、390×844、430×932 三档视口，验证键盘、长证据、底部安全区和报告滚动。

## 12. 测试矩阵

### 12.1 发布与权限

1. guided PUT published 返回 422，数据库不变。
2. 普通 question 发布不回归。
3. 非作者 authoring 404，作者成功。
4. reviewer review view 成功，普通 teacher 404。
5. 非专家 403、作者自审 409。
6. digest 任一字段变化后 publish 409。
7. approved 发布和重复发布幂等。
8. published PUT 409，clone 后旧 attempt 不变。
9. 他人 draft 不可 clone，approved published 可复制为自己的 draft。

### 12.2 Demo、班级和分析

1. Demo 提交、退回、批准、发布与 API 状态一致且记录不可覆盖。
2. 自定义病例只释放自身 facts，version 和 focus 正确。
3. class code、归档、成员、跨教师、external ID 和角色验证。
4. legacy、ClassMember 和并集可见性。
5. 0005 空库、旧库、部分同步库迁移。
6. analytics 覆盖无数据、未 assessed、retry、多班去重、三种 target、同时间决胜、提升、异常时长、范围边界和跨教师。
7. 一万条性能作为独立测试在最终验收运行。

### 12.3 学习计划与 AI

1. 两个低分、一个低分、全部达标和同分决胜。
2. 同来源幂等、新普通 assessment supersede、task assessment 不递归。
3. 顺序解锁、越级、重复提交和 complete。
4. 迁移病例选择和无病例替换。
5. AI enabled、disabled、首次非法后成功、两次非法、超时、连接错误、非2xx。
6. criteria、答案、隐藏 ID、剂量和注入泄露拦截。
7. deterministic score、critical cap、权重边界和原文 evidence。
8. AI feedback 非法引用时保留 fallback。
9. 审计记录完整。

### 12.4 构建隐私与 E2E

API 构建搜索三套病例隐藏原句、reference reasoning、rubric keywords、blueprint fixed facts、digest、API key 和 Demo 完整 draft，均不得命中。

E2E 固定覆盖：旧问答批阅；教师提交—reviewer退回—修改—批准—发布；版本克隆；班级和三级学情；学生低分初评—计划—重练—动态微训练—跨病例—复盘；AI 非法响应 fallback；Demo reset。禁止跳过测试或用固定等待掩盖失败。

## 13. 六周实施顺序

### 第 1 周：安全门禁和真实审计

- 建立 V3 审计并复现全部缺口。
- 修复 PUT 旁路、authoring 越权、clone 权限和 digest。
- 补编排器审核动作、完整审核视图和状态机测试。
- 修复 Demo 事实、版本、量表和注入分类。

### 第 2 周：班级、学情和第一质量门

- 创建验证 0005。
- 完成班级管理和 membership 并集。
- 完成三级学情和显式 DTO。
- 通过统计、性能、权限、覆盖率和 E2E。
- V3-AUD-001 至 015 全部 verified 后冻结第一阶段接口。

### 第 3 周：个性化领域模型

- 创建验证 0006。
- 完成 plan/task/task attempt/notification 模型和状态机。
- 实现推荐、幂等、顺序和 CaseAttempt 关联。
- 完成领域和 API 合同测试。

### 第 4 周：动态微训练和跨病例内容

- 扩展 CaseDefinition v2 和蓝图编辑/审核视图。
- 完成生成、校验、重试、fallback、评分和审计。
- 完成急性胸痛、右下腹痛病例、蓝图和 Demo seed。
- 完成医学内容工程检查并标注外部签署边界。

### 第 5 周：展示闭环

- 完成学生仪表盘、计划、微训练、复盘和通知。
- 完成教师学生档案计划进度。
- 完成 Demo/API 对齐、reset、动效、弱网和安全区。

### 第 6 周：冻结验收

- 运行迁移、覆盖率、性能、构建、隐私扫描和全量 E2E。
- 完成三档尺寸验收。
- 同步全部技术与功能文档。
- 修复失败，不增加新的产品分支。

## 14. 验证命令

```powershell
npm run format:check
npm run lint
npm run type-check
npm run test:coverage
npm run build:mp-weixin
npm run build:h5
npm run backend:check
npm run test:e2e
npm run check:all
git diff --check
git status --short
```

迁移和性能至少执行：

```powershell
npm run backend:migrate
Set-Location backend
python -m alembic current
python -m alembic heads
python -m pytest tests/test_migrations.py -q
python -m pytest tests/test_analytics_performance.py -q
Set-Location ..
```

测试文件名发生调整时保持验证内容不变，并在最终报告列出真实命令。

## 15. 文档同步

实现完成后同步根 `README.md`、`docs/features.md`、`docs/api.md`、`docs/database.md`、`docs/security.md`、`docs/architecture.md`、`docs/audit/personalized-practice-audit.md`、`.env.example` 和 `backend/.env.example`。不得写真实密钥。旧审计保留历史价值，但首页标明已由 V3 审计取代，不能继续宣称证据不足的项目完成。

## 16. 最终验收

- 教师 5 分钟内生成、编辑、保存并提交；reviewer 完整审阅并退回或批准；批准后发布且不可修改。
- 学生完成初评后立即得到三项计划；无 AI、超时、非法 JSON 和断网时仍完成。
- 复盘明确区分正式能力与微训练掌握度；迁移使用不同 approved 病例。
- Demo reset 后 8 分钟内展示低分初评、推荐、微训练、跨病例和前后对比。
- 三套病例、审核、通知、教师下钻不依赖真实模型。
- 前后端覆盖率、性能、双端构建、全量 E2E、迁移、权限和隐私扫描全部通过。
- 文档与实现一致，无未决标记和虚假完成声明。

## 17. 最终交付报告模板

```markdown
已完成审计整改与个性化跨病例训练更新。

### 审计整改

- 列出 V3-AUD-001 至 V3-AUD-015 最终状态和关键证据。

### 数据与接口

- 列出 0005、0006 实际迁移结果、新增接口和兼容说明。

### 个性化训练

- 列出计划、三项任务、动态微训练、跨病例、通知和复盘实现。
- 说明正式能力与练习掌握度隔离结果。

### AI 与医学安全

- 列出 client mock、一次重试、fallback、泄露检查和审计结果。
- 明确工程演示审核不等同于仓库外医学专家签署。

### 验证

- 列出实际测试数量、覆盖率、性能耗时、构建、E2E、迁移和隐私扫描。

### 外部事项

- 只列真实 AI 凭据、微信合法域名、生产部署和仓库外医学签署。
```

第一阶段审计项、第二阶段状态机、迁移、隐私扫描或全量质量门仍失败时，不得宣称整体更新完成。
