# 目标信息架构

## 目标目录

```text
docs/
├── README.md                         # 唯一总入口：当前文档、归档、计划
├── architecture.md                   # 当前跨模块架构
├── data-layer.md                     # 当前数据层规则
├── product/
│   └── features.md
├── frontend/
│   ├── README.md
│   ├── design.md
│   └── public-interfaces.md
├── backend/
│   ├── README.md
│   ├── api.md
│   ├── database.md
│   └── module-map.md
├── operations/
│   ├── README.md
│   ├── development.md
│   ├── deployment.md
│   └── dependency-upgrade.md
├── governance/
│   └── security.md
├── records/
│   ├── frontend/
│   │   ├── editor-motion-2026-08-31.md
│   │   └── validation-2026-08-31.md
│   └── architecture/
│       └── cloud-demo-to-fastapi-migration.md
├── adr/
└── update_plan/
    ├── README.md                     # 全部计划索引与新计划规则
    ├── 01-... 至 13-.../             # 每轮独立计划与本轮交付
    └── 01-07-engineering-governance/ # 共享总任务书、阶段状态与交付证据
```

## 阅读路径

| 读者与目的       | 首先阅读                                                      | 按需进入               |
| ---------------- | ------------------------------------------------------------- | ---------------------- |
| 所有开发者       | `docs/README.md`、`AGENTS.md`                                 | 当前任务关联的权威文档 |
| 前端开发         | `docs/frontend/README.md`、`architecture.md`、`data-layer.md` | 设计与公开接口         |
| 后端开发         | `docs/backend/README.md`、`architecture.md`、`data-layer.md`  | API、数据库与模块图    |
| 运行与发布       | `docs/operations/README.md`、`governance/security.md`         | 依赖维护与部署说明     |
| 追溯早期工程治理 | `docs/update_plan/01-07-engineering-governance/README.md`     | T01–T07 与阶段证据     |
| 当前产品更新     | `docs/update_plan/README.md`                                  | T01–T13 独立计划       |

## 命名约束

- 当前文档使用职责名称，不在文件名中混入一次性验收日期。
- 归档材料保留原始内容，在文件名附加日期或语境以避免和当前规则混淆。
- 计划目录沿用 `NN-short-name/`，计划本身、设计、任务、验证和 `deliveries/` 放在同一目录。
- 所有入口页说明“当前事实”和“阶段记录”的区别；记录不用于替代权威文档。
