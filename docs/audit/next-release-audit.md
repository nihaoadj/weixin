# 发布前审计摘要

审计日期：2026-08-28  
详细对比见 [初始版本功能与安全对比](./initial-version-comparison.md)，V3 证据见 [个性化训练审计](./personalized-practice-audit.md)。

## 已验证

- 初始远程版本的页面、报告、题目、教师批阅和日志能力均已在新前端/后端找到对应闭环。
- 病例作者编辑隔离、审核详情只读、审批/退回、digest 发布校验、clone version 和 Demo/API 双状态机已覆盖。
- 班级创建/改名/归档、外部 ID 加成员、legacy `class_ids` 兼容、教师 owner 隔离已覆盖。
- 总览、病例、学生学情分析支持日期范围与下钻；10,000 次 attempt 性能测试验证查询数量与耗时上限。
- API 构建不包含 Demo 病例隐藏事实、参考答案、rubric 或旧模型密钥；学生响应不包含内部字段。
- Alembic 可从 0004 升级到 head，并从 head 回滚到 0004；0005/0006/0007 均未修改 0001–0004。

## 仍需外部确认

- 旧远程历史中的模型 API key 必须在平台侧撤销/轮换，并核查账单和访问日志；仅从当前工作树删除不等于完成处置。
- 当前 `project.config.json` / `src/manifest.json` 的 AppID 与旧仓库 AppID 不同，需项目负责人确认是否为有意切换；不能在未确认时自动替换。
- 旧微信云数据库/云函数数据没有自动迁移到 FastAPI 数据库，需要单独的数据导入、脱敏和验数方案。
- 配置真实微信 AppSecret、教师白名单、HTTPS 合法域名、生产 JWT/数据库/AI 网关，并完成医学专家签署与上线联调。

## 复核命令

```text
npm run check
npm run backend:check
npm run test:e2e
cd backend && python -m pytest tests/test_migrations.py -q
git diff --check
```
