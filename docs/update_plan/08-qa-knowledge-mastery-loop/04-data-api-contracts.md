# T08-04 数据、API 与合同

## 模块归属

| 模块 | 责任 |
| --- | --- |
| qa | 对话学习上下文、结构化问答响应、主题历史筛选 |
| content | 目录、系统/教师卡、审核、题目与病例知识关联 |
| learning | 小测、复习项、调度、知识状态与手动收藏 |
| reports | 教师批阅时保存复习知识点代码并通过公开合同提供证据 |
| analytics | 教师拥有班级的只读聚合 |

新增表由 Alembic `0010` 创建：`conversation_learning_contexts`、`problem_knowledge_links`、`knowledge_cards`、`knowledge_card_reviews`、`review_items`、`review_states`、`review_attempts`。

## 公开前端能力

- qa：`requestLearningAssistant`、`getConversationLearningContext`、`setConversationLearningContext`、`getTopicConversationSummaries`。
- content：`getKnowledgeTree`、`getKnowledgePoint`、`getKnowledgeCards` 及教师卡/审核操作。
- learning：`getReviewDashboard`、`getDueReviewQueue`、`createConversationExitQuiz`、`submitExitQuizAnswer`、`captureManualReviewItem`、`revealRecallCard`、`gradeObjectiveCard`、`rateRecallCard`、`dismissReviewItem`。
- analytics：`getClassKnowledgeOverview`。

页面只能经相应 feature `public.ts` 调用；API/Demo adapter 由 `src/bootstrap/wiring.ts` 装配。

## HTTP 合同

- `GET/PUT /conversations/{id}/learning-context`
- `GET /conversations?knowledge_point_code=...`
- `GET /knowledge/tree`、`GET /knowledge/points/{code}`、`GET /knowledge/cards`
- 教师知识卡 CRUD、提交审核、医学审核、停用接口
- `POST /conversations/{id}/exit-quiz`、`POST /learning/exit-quizzes/{id}/answers`
- `GET /learning/review-dashboard`、`GET /learning/reviews/due`
- `POST /learning/reviews/{id}/reveal|grade|rate`
- `GET/POST /learning/review-items`、`POST /learning/review-items/{id}/dismiss`
- `GET /analytics/classes/{class_id}/knowledge`

所有 schema/路由变更必须同步 `docs/openapi.json`、生成 TypeScript 类型、Zod mapper 与契约测试；生成物禁止手改。

## 授权与数据边界

- 学生只能读取和写入自己的对话上下文、复习状态和私人备注。
- 教师只能管理本人卡片与本人班级范围；审核者权限独立。
- 系统卡不可经教师接口修改。
- 学生 DTO 不返回卡片正确答案，直至完成提交或主动揭晓。
- 班级统计不返回私人备注、完整问答、完整学生答案或隐藏病例字段。
