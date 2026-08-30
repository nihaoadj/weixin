# 数据库设计

## 结构化病例迁移

`20260823_0002_structured_cases` 为 `problems` 增加内容类型、版本和 JSON 病例字段，并创建 `case_attempts`、`case_attempt_messages`、`stage_submissions`、`case_assessments`、`ai_call_logs`。迁移按 inspector 检查对象，兼容初始迁移已按最新 metadata 建表的空库。

## 当前选择

开发阶段使用 SQLite：

```text
backend/data/dev.db
```

这个文件是本地开发数据，不进入 Git。

## 为什么先用 SQLite

- 不需要单独安装数据库服务
- 适合 Demo、开发和测试
- FastAPI + SQLAlchemy 支持成熟
- 后续可以迁移到 PostgreSQL

## 核心表

```text
users
conversations
messages
reports
classes
class_members
medical_reviews
case_attempts
case_assessments
learning_plans
learning_tasks
learning_task_attempts
student_notifications
problems
```

## users

保存用户身份。

```text
id
external_id
role
nickname
avatar_url
created_at
```

开发阶段 `external_id` 使用 `demo_student`、`demo_teacher`。正式阶段映射微信 openid 或统一账号 ID；角色和权限由服务端维护。

## conversations / messages

对话和消息拆表，方便查询、分页和审计。

```text
conversations: id, client_id, student_id, created_at, updated_at
messages: id, conversation_id, role, content, created_at
```

## reports

报告有明确状态流：

```text
draft
pending_review
reviewed
```

字段：

```text
conversation_id
student_id
status
ai_score
ai_summary
ai_analysis
teacher_score
teacher_feedback
created_at
updated_at
```

## problems

题目表：

```text
type
title
description
target
target_label
target_ids
status
content_type
slug
specialty
difficulty
estimated_minutes
version
parent_problem_id
author_id
medical_review_status
capability_tags
case_definition
rubric
created_at
published_at
```

班级和定向发布已由第二阶段迁移实现：

```text
classes
class_members
problems.target/target_ids
```

## 生产迁移

上线前建议迁移到 PostgreSQL。保持 SQLAlchemy 模型和 Alembic 迁移后，数据库连接只需要从：

```text
sqlite:///./data/dev.db
```

切换为：

```text
postgresql+psycopg://user:password@host:5432/dbname
```

# 迁移链与兼容性

`20260823_0004_classes_review_analytics.py` 在 0003 基础上只做加法；`20260823_0005_classes_review_hardening.py` 补充 author FK、兼容回填和组合索引。审核记录没有更新/删除接口；旧 `class_ids` 保留并与 `class_members` 兼容合并。后续迁移链为 `0006_personalized_practice`、`0007_report_analysis`。

## 个性化训练迁移

`20260823_0006_personalized_practice.py` 新增 `problems.capability_tags`、`case_attempts.learning_task_id`、AI 蓝图审计字段，以及：

```text
learning_plans
learning_tasks
learning_task_attempts
student_notifications
```

计划以 `source_assessment_id` 唯一，学生最多一个 active 计划；任务以 `(plan_id, position)` 唯一，微训练 attempt 以 `task_id` 唯一。降级只移除 0006 对象和新增字段，不删除 legacy class_ids、班级或病例内容。`0007` 为 reports 增加 `ai_analysis`，回滚只移除该列。

迁移测试覆盖空库/0004 旧库升级、legacy class_ids 回填以及从 head 回滚到 0004；SQLite 回滚会先清理早期动态建表遗留索引。

## 摘要分页索引

`20260830_0008_data_layer_indexes.py` 接在 0007 后，为 conversations/reports 增加 `(updated_at, id)` 和 `(student_id, updated_at, id)` 索引。升级和降级均检查索引存在性，降级只移除这四个索引，不删除业务记录。会话消息更新显式更新父会话时间，确保分页排序反映最近活动。
