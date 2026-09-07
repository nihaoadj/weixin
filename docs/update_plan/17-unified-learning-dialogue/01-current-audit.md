# 当前事实与差距

核查日期：2026-09-07。

## 当前事实

- 当前分支 `dev`，起始 HEAD `c35190a`，相对 `github/dev` ahead 4。
- 工作区已有未提交和未跟踪改动，包含 PBL、自由答疑、学生导航、教师 PBL 队列和共享聊天组件；T17 必须增量保护这些内容。
- PBL 由 `features/pbl` 和后端 `modules/pbl` 拥有，消息驱动参与级四阶段、schema v3 诊断、教师建议队列和两轮学习计划。
- 自由答疑由 `features/qa` 调用 `/v1/medical-chat` 取得非结构化文本；页面另行保存 conversation、生成客户端分析报告并可手工加入复习。
- PBL session 当前只由教师为班级创建；学生没有公开的有效班级摘要接口，也不能主动创建 PBL session。
- `pbl_sessions` 已允许 `case_id` 为空；`pbl_participations` 当前没有沟通方式字段。
- 生产 PBL provider 固定为 Coze，普通 OpenAI-compatible 仅允许开发/测试；API/Demo 由 bootstrap 唯一选择。
- 学生主导航当前为课堂、学习、学情、答疑四项，旧 chat、conversation 和 report 路径已有历史调用方。

## 当前差距

- 两条对话链拥有不同消息、AI、报告和学习结果，不能仅通过页面复用实现统一闭环。
- 自由提问缺少班级 owner、稳定知识目标和学生理解证据，不能直接进入教师建议队列。
- 现有 schema v3 没有声明沟通方式，provider 可能无法证明采用了 direct/guided 策略。
- 旧 conversation 缺少 PBL 阶段证据窗口和诊断版本，自动迁移会伪造事实。

## 影响审计

- 公开接口：新增学生班级与统一研讨接口；旧 QA/PBL 接口兼容保留并标记 deprecated。
- 数据：需要新增 Alembic 0020 和模型约束；不改旧 conversation/report 数据。
- AI：Coze Bot/Workflow、开发 provider、Mock 和运行时 schema 同步升级。
- 权限：学生主动会话只能由本人和班级 owner 教师访问；跨范围统一拒绝。
- 生成物：OpenAPI、生成 TypeScript 和契约 fixture 必须经生成流程更新。
- API/Demo：两种模式实现同一公开合同；失败不得跨模式 fallback。
