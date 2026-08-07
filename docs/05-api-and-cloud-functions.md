# 05. API 与云函数设计

## 1. 统一约定

小程序调用普通云函数时，也应采用稳定的 API 契约，不让页面依赖数据库文档结构。

### 1.1 请求元数据

```ts
interface RequestMeta {
  requestId: string;       // 客户端生成，用于链路追踪
  idempotencyKey?: string; // 创建/提交类操作必填
  clientVersion: string;
  schemaVersion: '1';
}
```

客户端不得提交可信身份字段：`openid`、`userId`、`role`、`organizationId`（若作为筛选条件也必须由服务端验证 scope）。

### 1.2 标准响应

成功：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "requestId": "req_...",
    "serverTime": "2026-08-07T10:00:00.000Z",
    "nextCursor": null
  }
}
```

失败：

```json
{
  "ok": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "无权执行此操作",
    "retryable": false,
    "fieldErrors": []
  },
  "meta": {"requestId": "req_..."}
}
```

生产响应不返回堆栈、数据库错误、模型原始异常或内部路径。

## 2. 服务端请求管线

每个函数统一执行：

1. 生成/接受 requestId 并创建结构化日志上下文；
2. 从 CloudBase/微信可信上下文解析 openid；
3. 映射内部 `userId`，检查账号状态；
4. 对输入做 schema 校验和长度限制；
5. 从数据库加载角色与 scope；
6. 校验资源归属和状态机；
7. 对创建/提交操作检查幂等键；
8. 在事务或条件更新中执行用例；
9. 写最小化审计日志；
10. 返回 DTO，过滤敏感字段。

## 3. API 清单

### 3.1 身份与同意

| 用例 | 入参 | 返回 | 权限 |
| --- | --- | --- | --- |
| `authMe` | 可选资料完善字段 | 用户、角色 scopes、同意状态 | 已登录 |
| `consentUpdate` | consentType、policyVersion、decision | 最新同意状态 | 本人 |
| `profileUpdate` | 昵称/头像等允许字段 | 用户 DTO | 本人 |
| `dataSubjectRequestCreate` | type、scope | 工单 ID | 本人 |

`authMe` 首次调用可创建最小用户记录，但绝不接受客户端指定教师角色。

### 3.2 题目与作业

| 用例 | 关键入参 | 返回 | 权限 |
| --- | --- | --- | --- |
| `assignmentListForStudent` | cursor、status、limit | 可见作业摘要 | 学生本人 scope |
| `questionGet` | assignmentId | 固定版本题目 DTO | 被分配的学生/范围教师 |
| `questionDraftSave` | questionId?、expectedVersion?、内容 | 草稿与版本 | 教师课程 scope |
| `questionSubmitReview` | questionId、expectedVersion | 新状态 | 所有者教师 |
| `questionApprove` | questionId、decision | 审核结果 | 医学审核员 |
| `assignmentPublish` | questionVersionId、targets、时间、幂等键 | assignmentId | 教师课程 scope |
| `assignmentCancel` | assignmentId、expectedVersion | 状态 | 发布者/管理员 |

### 3.3 对话与 AI

#### `conversationStart`

```json
{
  "meta": {"requestId": "req_...", "idempotencyKey": "start-...", "clientVersion": "1.0.0", "schemaVersion": "1"},
  "assignmentId": "assign_..."
}
```

服务端检查发布时间、目标学生、作答次数和同意状态，返回 `conversationId` 与题目快照摘要。

#### `messageSend`

```json
{
  "meta": {"requestId": "req_...", "idempotencyKey": "msg-client-uuid", "clientVersion": "1.0.0", "schemaVersion": "1"},
  "conversationId": "conv_...",
  "content": "学生输入",
  "expectedVersion": 5
}
```

返回：

```json
{
  "ok": true,
  "data": {
    "userMessage": {"messageId": "msg_6", "seq": 6},
    "assistantMessage": {
      "messageId": "msg_7",
      "seq": 7,
      "content": "...",
      "aiGenerated": true,
      "citations": [],
      "safety": {"riskLevel": "low", "action": "normal"}
    },
    "conversationVersion": 7
  },
  "meta": {"requestId": "req_...", "serverTime": "..."}
}
```

同一会话同一时刻默认只允许一个进行中的模型生成；重复键返回首次结果。

#### `conversationComplete`

检查会话所有权、最少消息数、状态和幂等键。创建/更新 submission draft 并触发报告生成。若采用异步生成，返回 `reportStatus=generating`，客户端轮询状态或接收订阅通知。

### 3.4 提交与批阅

| 用例 | 说明 |
| --- | --- |
| `submissionSubmit` | 将草稿正式提交，幂等；服务端冻结会话版本 |
| `submissionListForTeacher` | 按 scope、状态、作业、班级分页，不返回无关正文 |
| `submissionGet` | 返回题目快照、对话、AI 报告和当前批阅 DTO |
| `reviewSaveDraft` | 保存教师草稿，携带 `expectedVersion` |
| `reviewPublish` | 发布评分/反馈，事务更新 submission 并写审计 |
| `reviewRequestRevision` | 退回修改，明确原因和新截止时间 |

`reviewPublish` 评分允许 0，校验应使用明确的数值范围而不是真值判断。

### 3.5 管理

- `adminTeacherInviteCreate`
- `adminRoleGrant` / `adminRoleRevoke`
- `adminMembershipUpdate`
- `adminAuditSearch`
- `adminSafetyEventReview`
- `adminKnowledgeSourcePublish`

管理用例需二次鉴权、强审计；高风险操作可要求 MFA/重新验证。

## 4. 权限矩阵

| 资源/操作 | 学生 | 教师 | 医学审核员 | 管理员 |
| --- | --- | --- | --- | --- |
| 查看自己作业/对话 | 是 | 仅教学 scope | 否 | 按职责 |
| 查看学生提交 | 自己 | 所属课程/班级 | 抽检授权范围 | 受控 |
| 创建题目 | 否 | 是 | 可 | 可 |
| 审核医学内容 | 否 | 无独立审核权限 | 是 | 不默认拥有 |
| 发布作业 | 否 | 教学 scope | 否 | 可 |
| 批阅 | 否 | 教学 scope | 可抽检、不默认改分 | 不默认拥有 |
| 授予教师角色 | 否 | 否 | 否 | 是 |
| 查看审计 | 自己相关记录摘要 | 自己 scope | 安全 scope | 按权限 |

任何“管理员拥有一切”也应拆分权限，避免日常账号可查看全部敏感对话。

## 5. 分页、排序和过滤

- 使用基于 `(sortValue, id)` 的不透明 cursor，不使用深页 offset；
- `limit` 默认 20，最大 100；
- 排序字段白名单，不接受任意字段；
- 所有列表自动附加服务端 scope 条件；
- cursor 包含查询版本/过滤摘要，篡改或条件不一致返回 `INVALID_CURSOR`；
- 列表返回摘要 DTO，正文由详情接口按需加载。

## 6. 错误码

| 错误码 | 含义 | 是否重试 |
| --- | --- | --- |
| `UNAUTHENTICATED` | 登录上下文无效 | 重新登录后 |
| `FORBIDDEN` | 角色/scope/资源不允许 | 否 |
| `VALIDATION_FAILED` | 字段格式、长度、枚举错误 | 修改输入 |
| `NOT_FOUND` | 资源不存在或为防枚举统一隐藏 | 否 |
| `CONFLICT` | expectedVersion 不一致 | 刷新后人工合并 |
| `IDEMPOTENCY_CONFLICT` | 同一键对应不同请求 | 换正确键/排查客户端 |
| `RATE_LIMITED` | 超出用户/课程/模型预算 | 按 `retryAfter` |
| `AI_UNAVAILABLE` | 模型超时/服务失败 | 有限重试或稍后 |
| `AI_OUTPUT_INVALID` | 输出不满足 schema/安全策略 | 系统处理，不显示伪造结果 |
| `CONSENT_REQUIRED` | 缺少必要同意 | 完成同意流程 |
| `SAFETY_ESCALATION` | 触发紧急/高风险处置 | 按安全 UI 引导 |
| `INTERNAL_ERROR` | 未分类服务端错误 | 有限重试并携 requestId 报障 |

## 7. 幂等与重试

- `conversationStart`、`messageSend`、`submissionSubmit`、`reviewPublish`、`assignmentPublish` 必须幂等；
- 服务端保存 `idempotencyKey + actor + useCase + requestHash`；
- 网络超时后客户端可用相同键重试；
- 只对明确 retryable 的错误做指数退避和随机抖动；
- 不自动重试权限、校验、冲突和安全拒绝；
- AI 供应商重试也复用内部 trace，避免重复计费/重复消息。

## 8. 从现有云函数迁移

| 现有函数 | 问题 | 迁移动作 |
| --- | --- | --- |
| `login` | 使用客户端 code/role | 替换为 `authMe`，可信上下文取身份；角色独立授予 |
| `getReport` | 客户端 openid/role，列表与详情混合 | 拆 submission list/get，统一 scope 和 DTO |
| `submitReport` | 学生提交与教师批阅混合、主键错位 | 拆 submissionSubmit/reviewPublish，统一 submissionId |
| `init` | 创建集合/索引不可重复、无版本迁移 | 改为版本化 migration，支持 dry-run 和幂等 |

旧函数在迁移期只能由兼容层调用，并记录弃用指标；客户端切换完毕后下线，不能长期双写。
