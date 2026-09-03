# T08-06 测试、发布与回退

## 必测场景

- 自由问答、已选主题问答、题目继承主题和切换主题。
- 助手回答收藏、无主题时选择知识点、私人备注长度与隔离。
- 结束小测的 1/3 题抽取、跳过、正确、错误、重复提交与答案不提前泄漏。
- 调度 `again/hard/good/easy`、UTC 到期、最大间隔、客观/自评统计分离。
- 病例、微训练、教师标记的阈值与幂等复习项。
- 教师卡生命周期、审核、班级范围、系统卡不可编辑。
- 学生所有权、教师班级隔离、小样本聚合抑制、日志脱敏。
- API 与 Demo 模式闭环，以及网络失败不回退 Demo。

## 验证路由

- 结构与文档：受影响链接、路径、命令及 `git diff --check`。
- 前端：相关 Vitest、`node scripts/frontend-boundaries.mjs`、`npm run type-check`、`npm run build:h5`、`npm run build:mp-weixin`。
- 后端：先 `npm run backend:test:safety`、`npm run backend:test:migrations`，再执行相关 pytest、`python backend/scripts/check_boundaries.py`。
- API/schema：有意审阅差异后运行 `npm run contract:generate`，随后 `npm run contract:check`。
- 端到端：分别验证 API 与 Demo 主闭环；截图更新必须人工审阅。

## 数据影响与回退

迁移只增加 T08 表与索引，不自动回填历史对话。回退时关闭问答学习上下文、小测和复习入口，停止新增证据；保留新增表数据以便以后恢复。downgrade 仅删除本轮新增表和索引，不修改既有对话、报告、病例或学习计划。生产迁移、回填、外部模型调用和远程发布均需单独授权。
