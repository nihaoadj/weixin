# 病理学知识库设计

本目录是 `pathology-general-v4` 的跨代理设计入口。运行时唯一权威源是数据库；这里记录合同、审查结论和维护流程，不作为代码 fallback，也不允许页面从 Markdown 推断关系。

当前基线包含 5 个模块、30 个稳定知识点、30 份学习材料、34 条有向学习前置边和 14 个公开来源。每个节点和每条边均为 `evidence_status=source_supported`，但仍为 `medical_review_status=pending_expert_review`；这表示“有列明来源支持”，不表示“已由授权病理学专家签署”。

## 阅读顺序

1. [目录与节点](catalog-v4.md)：稳定编码、模块和节点职责。
2. [依赖审计](dependency-audit-v4.md)：34 条运行时边、方向和已纠正关系。
3. [来源登记](sources.md)：来源身份、范围与局限。
4. [维护流程](maintenance.md)：迁移、审核、验证和回退规则。

## 权威边界

- `knowledge_catalogs` 决定唯一 active 版本；多个或零个 active 目录均返回显式 503。
- `knowledge_modules`、`knowledge_points`、`knowledge_study_materials`、`knowledge_dependencies`、`knowledge_sources` 及两个来源关联表保存目录事实。
- 当前 5/30/34/14 数量由 v4 版本清单和迁移测试固定，不是仓储的永久上限；未来目录扩展仍须满足来源、材料、端点和无环校验。
- `/knowledge/tree` 和 `/knowledge/points/{code}` 通过同一仓储读取；`prerequisite_codes` 只是 `knowledge_dependencies` 的兼容投影。
- PBL 允许知识点、诊断结果校验、学习证据、普通问答、内容绑定和统计标签都使用同一个 `KnowledgeCatalogPort`。
- Demo JSON 由隔离临时数据库迁移到 head 后导出，不由静态 Python 节点表生成。
- `card_blueprints.py` 只用于开发环境把练习卡写入 `knowledge_card_contributions`；它不是知识点或依赖目录。

## 箭头语义

`A → B` 只表示“学习 B 前建议掌握 A”。它可能是机制基础、结构组成、分类框架或结局定义；并不统一表示 A 导致 B，更不表示必然进展。边的 `relation_kind`、`rationale` 和 `limitation` 必须共同展示或可查询。

没有画边只表示 v4 未把该关系选作“建议学习前置”，不表示两个概念在医学上无关；图谱也不是完整疾病因果网。模块归属和根节点连线只用于目录层级，不作为医学机制边入库。

## 当前外部阻塞

- 尚无课程负责人或病理学专家签署，因此不能将 v4 称为“已医学审核”。
- 尚未在真实 PostgreSQL、生产迁移、真实教学和微信真机完成外部验证。
- 来源失效、教材版本变化或专家异议必须通过前向迁移修订，不直接改生产表。
