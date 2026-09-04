# 当前事实与缺口

## 已核实事实

- 本地 `dev` 基线为 `7eeb46b`；T01～T09 已作为阶段性提交保存，未推送。
- PBL 已有独立目录、0015 迁移、学生/教师路由、三种 provider adapter、前端 API/Demo adapter、学生页和教师队列入口。
- T09 记录的 provider fixture、迁移、安全、类型、契约和局部 Ruff 曾通过；真实 Coze 未调用。
- `python backend/scripts/check_boundaries.py` 当前失败：PBL application 直接依赖 SQLAlchemy/基础设施和 classroom 内部模型；content `public.py` 导入基础设施实现；PBL API 直接查询数据库。

## 必须收口的缺口

1. application 仅依赖 PBL port/record/UoW；SQLAlchemy 查询与 ORM 全部下沉 infrastructure repository。
2. content `QuestionPublicationPort` 是纯公开协议，实现在 content infrastructure/wiring；采用发布使用同一 request-scoped UoW，PBL 不导入 content ORM。
3. Coze Bot/Workflow 必须按固定 SDK 的真实事件类型映射，支持 conversation 续用、interrupt、超时/限流分类、严格 schema 和去标识输入；普通 API 仅开发/测试。
4. HTTP schema 需补明确 response model、分页/详情、教师建课和关闭、版本并发、学生字段裁剪；页面不得依赖供应商字段。
5. 教师前端缺少课堂创建/关闭和完整诊断详情；学生入口、加载/空/失败、键盘和跨端路径需要集中验收。
6. 缺少权限、重复消息、revision 竞争、建议 supersede、重复采用、三 adapter 等价及本地 Mock E2E 的完整证据。

## 进一步核查结论

- `QuestionPublicationPort` 当前是 content `public.py` 中的 SQLAlchemy 具体实现，而不是稳定协议；其构造函数暴露 `Session`。
- PBL API 直接返回 ORM 并在教师队列中调用 `db.query()`，路由缺少显式 `response_model`；教师诊断详情和稳定分页尚不存在。
- participation 把所有消息写入 JSON 数组，应用层先读取再追加，无法用数据库唯一约束抵御并发的相同 `client_message_id`。
- Bot/Workflow adapter 只拼接任意 `content` 字段，没有区分官方 completed、delta、interrupt/error 事件；没有创建/恢复 Coze conversation，也没有发送目录和最多 20 条脱敏历史。
- Workflow 目前可能把 app ID 当作 bot ID 参数传入，配置层也没有阻止 app ID 与 bot ID 同时出现。
- 学生页没有呈现具体薄弱点和推理问题；教师页缺少课堂创建、列表和关闭操作。

以上均是计划输入，不是已完成状态。静态边界检查的 7 个错误是 T10 首个硬门禁。
