# 目标接口、数据与 Coze 边界

> T09 锁定更新：新实现独立于 `qa`，使用 `pbl/{api,application,domain,infrastructure,public.py,wiring.py}`。路由固定为教师 `/classes/{class_id}/pbl-sessions`、学生 `/student/pbl-sessions`、教师队列 `/teacher/pbl-diagnostics` 和 `/teacher/pbl-question-suggestions`。会话、参与、追加诊断快照、建议题与 `content.problem_origins` 均独立持久化；学生 DTO 删除建议题和供应商内部信息。

状态：本文件描述待实现合同，不表示这些路由、表或配置当前存在。最终命名可在实施设计中调整，但不得删除产品语义。

## 模块与依赖方向

建议由 `qa` 拥有学生多轮教学诊断，由 `content` 拥有正式题目，由 `classroom` 提供教师/班级范围合同。跨模块调用只能经 `public.py`/稳定 port 或 bootstrap wiring；页面仍只调用 `src/features/*/public.ts`。

```text
student PBL UI
  → qa public/application
  → Coze gateway (backend only)
  → structured diagnostic snapshot + suggested-question queue
  → teacher PBL queue UI
  → qa adopt application
  → content public contract creates/publishes official problem
  → existing student question feed
```

## 建议的 HTTP 合同

- `POST /pbl/sessions`：教师建立课堂会话并绑定自己负责的班级/学生与病理学主题。
- `POST /pbl/sessions/{id}/messages`：学生提交消息；返回教学回复、可选追问、结构化诊断状态和安全状态。
- `GET /teacher/pbl/diagnostics`、`GET /teacher/pbl/diagnostics/{id}`：教师按授权范围读取薄弱点和建议题。
- `PATCH /teacher/pbl/question-suggestions/{id}`：教师编辑建议题草稿。
- `POST /teacher/pbl/question-suggestions/{id}/adopt-and-publish`：幂等创建并发布正式题目，返回建议状态和 `problem_id`。

任何 schema/路由落地都必须通过生成流程同步 `docs/openapi.json`、`src/data/contracts/openapi.generated.ts`、前端 Zod mapper 和契约测试；禁止手改生成物。

## 建议的结构化返回

```json
{
  "answer": "面向学生的教学回复",
  "follow_up_question": "证据不足时的下一条追问",
  "diagnostic_status": "probing",
  "knowledge_gaps": [],
  "reasoning_issues": [],
  "recommended_questions": [],
  "safety_notice": null,
  "fallback_used": false
}
```

`diagnostic_status` 至少包含 `probing|ready|insufficient_evidence|unavailable`。服务端必须对白名单枚举、长度、数量、知识点编码、建议题字段和关联 ID 做 Pydantic 校验；Coze 返回不能直接透传到客户端或数据库。

## 最小持久化语义

- PBL 会话：关联现有 conversation、student、teacher/class、病理学主题和状态，保证诊断结果能被正确路由。
- 诊断快照：保存规范化薄弱点、诊断思路问题、生成版本、Coze 资源版本/调用元数据及状态；不重复保存 token、完整 prompt 或完整对话。
- 教师建议题：关联诊断快照和薄弱处，保存可编辑题目草稿、目标范围、`proposed|adopted|published|rejected|unavailable` 状态、正式 `problem_id` 与幂等键。
- 正式题目：继续由 `content` 模块和现有 `problems` 发布规则拥有；不得让 qa 直接写 content 表。

所有 schema 变化需新增 Alembic upgrade/downgrade，说明既有记录保留、唯一约束、并发行为和回退后的可读性。迁移只能在已确认的受管非生产资源上执行。

## Coze 接入约束

- 提供方固定为 Coze。使用后端专用 `Coze...Gateway` 把项目内请求/结果合同与 Coze 官方 API/SDK 的会话、智能体或工作流协议相互映射；不得让 application/domain 依赖供应商 DTO。
- 项目可定义 `COZE_*` 环境变量承载 API base URL、服务端 token、bot/app/workflow 标识、版本和超时；准确字段以实施时采用的 Coze 官方合同为准，并写入 `.env.example`，真实值不得入库。
- 学生身份、openid、昵称、班级、token 和与本次判断无关的历史不得发给 Coze。必要对话应去标识化、限定条数/长度，并记录批准的数据处理目的、地区、保留期和删除方式。
- Coze 超时、限流、非成功状态、流式中断、空响应、无效 JSON、schema 不符和内容安全失败必须有界处理。fallback 可提供安全教学提示或继续追问，但必须标记 `unavailable/fallback_used`，不得上报伪造薄弱点或自动生成可发布题。
- 审计只记录任务、模型/智能体/工作流版本、耗时、失败分类、fallback、用户/会话关联 ID；禁止记录 Coze token、完整 prompt、完整学生回答或完整模型输出。

## 权限与医学安全

- 学生只能写自己的课堂会话并读自己的回复；教师只能读取和处理自己负责范围内的队列。
- 采用发布时重新校验教师角色、班级 owner、建议状态和目标学生，而不是信任建议生成时的旧权限。
- PBL 输出只用于病理学教学，不替代临床诊断。急症描述先走确定性安全分流，不向模型请求个体诊断、处方或剂量。
- 教师发布是医学内容的人在回路审核点；Coze 结果不得绕过现有题目可见性和审核政策。
