# 后端模块、路由与数据责任映射

状态：T04 与 R05 已纳入 S2 仓库内组合验收；本文记录当前代码事实，不等于远程 CI、生产发布或产品权限政策已获批准，也不改变数据库 schema 或公开 API。

## 依赖方向

```text
HTTP router (app/modules/*/api)
        │ actor + command
        ▼
module public/application ───────► module domain
        │                              ▲
        │ ports                        │ pure policy/state
        ▼                              │
module infrastructure ───────────────┘
        ▲
        │ explicit composition
module wiring + platform UoW
```

路由只负责请求/响应 schema、actor 适配、用例调用和公开 view 映射。`wiring.py` 是显式装配入口；它创建 repository、外部 gateway 和 request-scoped UoW，不向业务层提供 service locator。通用结构化 AI transport 位于 `app/platform/ai.py`，由模块 infrastructure 通过显式 import 使用。`domain` 和 `application` 不导入 FastAPI、SQLAlchemy、Pydantic 请求 schema、httpx 或旧 `app.services`。R05 要求其他模块的 `api` 仅能由本模块 `api` 或 `wiring` 导入；其余跨模块调用使用 `public.py` 合同。`backend/scripts/check_boundaries.py` 及 `config/backend-boundaries.json` 对此做 AST 正负检查。

## 路由与业务模块

| 业务模块  | 当前路由入口与 operation 范围                                                                                                                          | 应用/领域职责                                                                          | 基础设施与公开入口                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| identity  | `app/modules/identity/api/auth.py`：`/auth/demo-login`、`/auth/wechat-login`                                                                           | 演示/微信账号政策、角色收敛、账号更新                                                  | `SqlAlchemyUserRepository`、`WechatHttpGateway`、`JwtTokenIssuer`；`identity/public.py`、`identity/wiring.py`        |
| qa        | `app/modules/qa/api/`：conversations、student_questions、`/v1/medical-chat`；`content/api/problems.py` 仅调用 qa public/application 的题目 thread 合同 | 对话/题目线程隔离、摘要分页、医学安全分流                                              | conversation/question repository、medical chat gateway/audit；`qa/public.py`、`qa/wiring.py`                         |
| reports   | `app/modules/reports/api/reports.py` 全部 `/reports`                                                                                                   | 草稿→待批阅→已批阅状态、学生所有权、教师可见性、reviewer 记录                          | `SqlAlchemyReportRepository`；`reports/public.py`、`reports/wiring.py`                                               |
| content   | `app/modules/content/api/problems.py` 的题目/病例 CRUD、clone、publish/reject/draft；`content/api/medical_review.py` 全部                              | 作者所有权、公开可见性、病例完整性、审核 digest 与发布规则                             | `SqlAlchemyProblemRepository`、visibility/draft adapters；`content/public.py`、`content/wiring.py`                   |
| training  | `app/modules/training/api/case_attempts.py`：attempt、message、stage submit、complete、assessment                                                      | 病例阶段状态机、确定性评分、AI 受限合并、重试/assessment 幂等                          | `SqlAlchemyTrainingRepository`、patient/assessment AI gateway；`training/public.py`、`training/wiring.py`            |
| learning  | `app/modules/learning/api/personalized.py` 全部学习计划、任务、通知、profile                                                                           | 计划选取/生成、任务解锁、微训练评分、通知幂等；消费 `training.public.TrainingCasePort` | `SqlAlchemyLearningRepository`、practice generator、case-attempt adapter；`learning/public.py`、`learning/wiring.py` |
| classroom | `app/modules/classroom/api/classes.py` 全部 `/classes`                                                                                                 | 教师所有权、班级状态、成员增删                                                         | `SqlAlchemyClassroomRepository`；`classroom/public.py`、`classroom/wiring.py`                                        |
| analytics | `app/modules/analytics/api/analytics.py` 全部 `/analytics`                                                                                             | 日期、班级/作者范围、当前/基线 attempt 选择和统计 read model                           | `SqlAlchemyAnalyticsReader` 只读跨表查询；`analytics/public.py`、`analytics/wiring.py`                               |
| pbl       | `app/modules/pbl/api/routes.py`：学生统一研讨、课堂、参与消息、诊断队列、建议发布、两轮结果、学生学情报告和汇总                                        | 统一会话、固定沟通方式、schema v4 阶段证据、建议审核发布编排、结果与学情只读           | `SqlAlchemyPblRepository`、Coze/开发 gateway；`pbl/public.py`、`pbl/wiring.py`                                       |

`/problems` 是 HTTP 聚合入口：题目本体和审核走 content，题目线程走 qa；两个应用合同在路由层按 operation 分开，互不穿透 infrastructure。

## 表所有权与读例外

| 表                                                                                                                 | 写入责任模块                                        | 允许的跨模块读取                                                                           |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `users`                                                                                                            | identity                                            | classroom、qa、reports、training、learning 通过各自 repository 读取所需 actor/owner 字段   |
| `conversations`, `messages`                                                                                        | qa                                                  | reports 读取报告关联的对话摘要/消息                                                        |
| `reports`                                                                                                          | reports                                             | analytics 不读完整内容；其他模块不写                                                       |
| `problems`, `medical_reviews`                                                                                      | content                                             | training/learning 读取经过 record/port 的公开病例及 rubric；analytics 只读统计字段         |
| `question_threads`, `question_thread_messages`                                                                     | qa                                                  | content API 仅通过 qa application 取得线程 view                                            |
| `case_attempts`, `case_attempt_messages`, `stage_submissions`, `case_assessments`                                  | training                                            | learning 通过 `CaseAttemptPort`/source record 读取；analytics 通过只读 reader              |
| `ai_call_logs`                                                                                                     | 发起 AI 用例的 training、learning、qa audit adapter | analytics 不读取提示词或回答；表中只写模型、版本、耗时、fallback、失败类别和关联 ID        |
| `learning_plans`, `learning_tasks`, `learning_task_attempts`, `learning_plan_evaluations`, `student_notifications` | learning                                            | pbl 通过 `PblLearningPort` 读取本人计划和评价；analytics 仅通过 reader 读取计划/掌握度摘要 |
| `classes`, `class_members`                                                                                         | classroom                                           | content/training/learning/analytics 通过明确查询 adapter 取得班级可见性所需字段            |
| `pbl_sessions`, `pbl_participations`, `pbl_messages`, `pbl_diagnostic_snapshots`, `pbl_question_suggestions`       | pbl                                                 | content/learning 仅通过公开发布和学习 port 协作；教师查询由 PBL owner 范围控制             |

canonical ORM 模型分别位于各模块 `infrastructure/models.py`，由 `app/bootstrap/model_registry.py` 唯一注册；`app/models/*` 仅为历史导入兼容 re-export。模型文件没有因分包复制或移动而改变表结构。T04 没有新增 Alembic revision，也没有改变表、列、索引、relationship 或既有迁移；工作区继承的 `20260830_0009_report_reviewer_auth_provider.py` 未修改。

## Actor、UoW 与错误合同

- HTTP 依赖把 `User` 收敛为不可变 `app.shared.actor.Actor`。应用用例再次检查角色、owner、资源范围和状态，不能只信任 router dependency。
- `SqlAlchemyUnitOfWork` 绑定请求 Session。repository 只查询、`add`、`flush`/`refresh`；应用用例是唯一 commit/rollback 拥有者。commit 异常会 rollback；冲突由应用映射为稳定错误。
- `AppError(code, message, status_code)` 在 `app/errors.py` 统一映射为现有错误响应；常见代码为 `AUTH_REQUIRED`(401)、`ROLE_REQUIRED`/`FORBIDDEN`(403)、`RESOURCE_NOT_FOUND`(404)、`VALIDATION_ERROR`(422)、`STATE_CONFLICT`(409)、`SERVICE_ERROR`(5xx)。核心层不抛 HTTPException。
- training assessment 与其 AI audit 在同一事务中写入；learning practice generation 与其 audit/plan/notification 也在同一事务中写入；医学问答的非急症回答与 audit 同事务。audit 写入或提交失败会 rollback 并返回 503；急症安全分流不写 audit、不调用外部 AI。外部 AI 只做有界重试，失败使用确定性 fallback。
- training 完成后由路由通过 bootstrap composition root 调用 learning application；training 结果先提交，learning side effect 再提交。learning 只看到 `TrainingCasePort` 与 source/assessment contract；重试通过 source/task 唯一键和既有记录收敛，不回滚已成功的训练评估，也不递归创建计划。

## 兼容入口与待移除条件

`app/api/*.py`、`app/models/*`、`app/schemas/*` 和 `app/services/{case_training,personalized,analytics,medical_ai,case_ai,access_control,medical_review,problem_view}.py` 仅是窄兼容门面或历史 mapper；生产路由不依赖旧业务实现。`app/bootstrap/seed.py` 是 showcase seed 的实际拥有者，`app/bootstrap/test_seed.py` 是开发/测试数据编排的实际拥有者，`app/services/case_seed.py` 与 `app/services/test_seed.py` 仅为旧 seed 调用方转发。`training/infrastructure/legacy_hook.py` 已删除，生产默认直接装配 `CaseAiGateway`；assessment gateway 只通过 `training.wiring` 的显式可选 port 注入测试实现。无生产动态 import 例外。

## 未决产品政策

报告教师可见范围继续使用当前行为 `ReportPolicy.teacher_scope = "submitted_global"`：教师可查看所有非 draft 的已提交报告。是否收窄到本人班级尚未由产品确认；T04 只建立策略接口和测试接缝，没有自行扩大或收紧权限。
