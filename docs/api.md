# API 设计

## 结构化病例训练

- `GET /problems`、`GET /problems/{id}`：学生只获得公开病例 metadata 和 opening。
- `GET /problems/{id}/authoring`、`POST /problems/case-drafts/generate`、`POST /problems/{id}/clone-version`：仅病例作者可用的编排接口。
- `POST /problems/{id}/attempts`、`GET /attempts/{id}`、`POST /attempts/{id}/messages`：开始/恢复训练与虚拟患者对话。
- `POST /attempts/{id}/stages/{stage}/submit`、`POST /attempts/{id}/complete`、`GET /attempts/{id}/assessment`：服务器控制的阶段提交与六维报告。

所有 attempt 和 assessment 仅可由所属学生读取；重练通过 start 请求中的 `retry_of_id` 启动。

后端使用 FastAPI，启动后可访问自动文档：

```text
http://127.0.0.1:8000/docs
```

## 第二阶段接口

- `GET/POST /classes`：教师查看或创建负责班级；`GET /classes/{id}/students` 查看成员。
- `PATCH /classes/{id}`：作者教师改名或归档；归档后不能新增成员。
- `POST /classes/{id}/members`：按 `student_external_id` 精确加入；`POST/DELETE /classes/{id}/members/{student_id}`：兼容数字 ID 的幂等加入/移除，跨教师范围返回 404。
- `GET /problems/review-queue?status=pending`、`GET /problems/{id}/medical-review-view`：仅 `medical_review` 权限可访问，后者返回完整只读审核内容。
- `POST /problems/{id}/medical-review/submit`：病例作者提交审核；`POST /problems/{id}/medical-review`：审核专家批准或退回。
- `GET /problems/{id}/medical-reviews`：作者或审核专家读取不可变审核记录。
- `GET /analytics/overview`、`/analytics/cases/{id}`、`/analytics/students/{id}`：只统计班级范围内的结构化病例 CaseAssessment，支持 `class_id/date_from/date_to`。

结构化病例发布前必须有 approved 审核，审核记录保存版本和 case definition/rubric SHA-256 摘要。

## 认证

开发阶段使用 Demo 登录：

```http
POST /auth/demo-login
```

请求：

```json
{
  "role": "student",
  "external_id": "demo_student",
  "nickname": "学生体验账号",
  "avatar_url": ""
}
```

响应：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "role": "student",
    "nickname": "学生体验账号"
  }
}
```

后续请求使用：

```http
Authorization: Bearer <access_token>
```

微信小程序 API 模式使用服务端微信登录：

```http
POST /auth/wechat-login
```

请求只携带 `wx.login` 返回的一次性 `code`、昵称和头像。服务端使用仅存在于后端环境变量中的 `WECHAT_APP_SECRET` 调用 `code2Session`；小程序不保存或传输 AppSecret。已有账号的角色由服务端保留，新账号默认为学生，教师首次登录必须命中 `WECHAT_TEACHER_OPENIDS` 白名单。

## 个性化跨病例训练

- `GET /learning/profile`：返回正式六维、最近完整病例、练习掌握度、当前计划和未读数。
- `POST /attempts/{id}/learning-plan`：对本人已评估的完整病例幂等生成计划；新普通评估会 supersede 旧 active 计划。
- `GET /learning-plans/current`、`GET /learning-plans/{id}`：返回来源摘要、目标维度和三项公开任务，不返回 private rubric、fixed facts 或 digest。
- `POST /learning-tasks/{id}/start`：按 position 解锁；focused retry/cross case 返回 CaseAttempt，micro drill 返回 LearningTaskAttempt。
- `GET /learning-task-attempts/{id}`、`POST /learning-task-attempts/{id}/submit`：读取或提交微训练，提交幂等并返回原文 evidence、反馈和下一步。
- `POST /learning-plans/{id}/complete`：三项均完成后幂等完成计划，否则返回 409。
- `GET /notifications?unread_only=&limit=`、`POST /notifications/{id}/read`、`POST /notifications/read-all`：仅应用内通知，不接微信订阅消息。

错误 detail 使用 `RESOURCE_NOT_FOUND`、`STATE_CONFLICT`、`ROLE_REQUIRED`、`INVALID_DATE_RANGE` 等稳定码，不返回堆栈、SQL、模型原文、API key 或隐藏事实。

## AI 问答

```http
POST /v1/medical-chat
```

请求：

```json
{
  "prompt": "肺炎如何鉴别诊断",
  "mode": "医学常识",
  "messages": []
}
```

当 `AI_ENABLED=true` 且服务端 AI 配置完整时，后端调用配置的 OpenAI-compatible `chat/completions` 地址并最多重试一次；未配置、超时或响应不合法时使用确定性教学反馈。模型密钥永不进入小程序。

响应：

```json
{
  "content": "演示反馈：建议从定义、常见表现、鉴别要点和处理原则四部分梳理。医学内容仅用于教学。"
}
```

## 对话

```http
GET /conversations
POST /conversations
GET /conversations/{conversation_id}
```

## 报告

```http
GET /reports
POST /reports
POST /reports/{report_id}/submit
POST /reports/{report_id}/review
```

报告状态：

```text
draft → pending_review → reviewed
```

`POST /reports` 可同时提交 `analysis.errors`、`analysis.strengths` 和 `analysis.general_suggestions`；服务端持久化这些形成性反馈并在 `GET /reports` 和报告详情中返回。报告内容只允许所属学生创建，教师只能批阅已提交报告。

## 题目

```http
GET /problems
POST /problems
POST /problems/{problem_id}/publish
```

学生只能看到 `published` 题目。教师可以创建和发布题目。
