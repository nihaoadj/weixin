# 开发、验证与发布

## 更新分流

改变业务流程、持久化状态、导航结果、公开接口、数据/会话、授权、AI、数据库或运行/发布边界，先建立或更新`docs/update_plan/NN-short-name/`计划。纯文档、规则、注释、格式/类型整理和不改变行为的样式、文案、布局维护直接实施；不能确定影响时按功能变更处理。Demo同步与微信验收另按改动适用。

功能变更按以下顺序执行：

1. 查看`git status`，核对源码和相关合同，确定范围与已有改动。
2. 计划写明当前事实、目标/非目标、模块/接口/数据设计、实施顺序、验收、阻塞和回退；大型更新提供[交付模板](update_plan/delivery-template.md)。
3. 通过格式、链接、尾随空白及项目技能自检后再改运行代码；实施必需的产品/架构决策先解决。
4. 按阶段实施与验证，范围变化先修订计划。既有功能缺少计划时先补差距审计，不追认历史门禁。
5. 功能交付在`deliveries/`记录命令、时间、退出码、证据、未执行项和回退；直接维护在回复记录检查结果。提交前核对范围、秘密及生成物，提交/推送须明确授权。

## 数据库与生成物

迁移、seed、回填、清理和测试资源所有权见[数据库](database.md)。`backend:migrate`和`backend:dev`会迁移当前URL，seed也先升级；仅对已核实的受管非生产目标运行。测试安全检查不是实际库恢复证据。

schema/路由变化同步OpenAPI、生成类型、mapper和运行时校验：`npm run contract:generate`写入生成物，审阅差异后运行`npm run contract:check`（临时生成并比较，不改源码）。知识目录变化还运行`python backend/scripts/export_pathology_catalog.py`；它使用隔离临时库导出，不恢复静态fallback。

## 按改动选择验证

阶段内连续修改后集中检查受影响范围；通过结果在代码/范围未变化时有效。失败先定向修复和复测，不降低覆盖率、安全或发布门槛。全量测试仅在某次更新全部完成后进行，用于集成/发布节点、影响外溢或用户明确要求。

| 改动                       | 检查范围                                                                                                        |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 文档/规则/技能             | 格式、本地链接及引用路径/命令、`git diff --check`；技能另跑self-check及`--self-test`                            |
| UI/交互                    | 受影响Lint、类型与行为检查，同步Demo并执行[微信最小流程验收](wechat.md)                                         |
| 前端数据/身份/导航         | API/Demo、校验、会话、缓存与授权合同；结构变化跑前端边界脚本                                                    |
| 后端/API/权限/AI           | 受管fixture下的领域、合同、权限及敏感数据检查；模块变化跑后端边界脚本                                           |
| 模型/迁移/测试资源生命周期 | 安全与迁移专项、upgrade/downgrade及数据保留；修改conftest、testing_resources、engine或启动器后先跑安全/迁移检查 |
| 依赖/构建/CI/跨模块重构    | 对应边界、构建和集成检查；远程CI及目标环境需各自证据                                                            |

分别报告逻辑、构建、工具交互、渲染与外部验收；Demo不证明服务端授权、真实AI、医学审核或生产。

## 收尾与人工待验

仅做必要验证，复用未受改动影响的通过结果，不因观察同一状态或等待用户重复检查。微信工具/环境阻塞按[微信验收](wechat.md#阻塞与人工交接)登记[人工台账](manual-acceptance.md)后继续推进，不阻断计划最终收尾。交付注明待验编号及发布影响；用户方便时补验并更新原条目，不自动重开整个计划。实际缺陷和必要测试失败仍阻断收尾；计划收尾不等于全部验收通过或正式发布。

## 常用命令

命令定义以`package.json`和脚本为准，按上表选择，不默认执行全套。

| 用途                 | 命令                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| 安装                 | `npm ci --legacy-peer-deps`、`npm run backend:install`                                   |
| 前端静态/逻辑        | `npm run type-check`、`npm run lint`、`npm run test`                                     |
| 格式                 | `npm run format:check`                                                                   |
| 目录与边界           | `npm run structure:check`；检查器回归用`npm run structure:self-test`                     |
| 后端安全/迁移/全量   | `npm run backend:test:safety`、`npm run backend:test:migrations`、`npm run backend:test` |
| 后端静态及覆盖率全量 | `npm run backend:check`                                                                  |
| 技能结构             | `python scripts/check-project-skills.py`；支持`--self-test`                              |
| 生产小程序构建       | `npm run build:mp-weixin`                                                                |

`npm run check:all`包含契约、后端和依赖审计，不包含微信工具E2E。

目录检查组合文件分类、Git路径大小写与前后端依赖边界；`npm run check`及CI前端节点执行该门禁。仅新增本地可重建产物使用受忽略的`output/local/`或`artifacts/`，现有交付证据按[证据目录说明](../output/README.md)保留。独立HTML示例归`docs/examples/pelican/`，根`index.html`仍是构建入口。

## 本地运行与发布

API开发使用`VITE_APP_MODE=api`及`VITE_API_BASE_URL=http://127.0.0.1:8000`，确认数据库后运行`npm run backend:dev`。Demo无需后端，watcher/工具操作见[微信验收](wechat.md)。

生产API使用微信HTTPS合法域名，发布前按[安全](security.md)配置身份与AI，按[数据库](database.md)执行备份、迁移和恢复验证。PostgreSQL兼容仍待验收。

## 依赖维护

`@dcloudio/*`成组保持一致，以lockfile为准；legacy-peer-deps处理现有Vite peer冲突，不能替代审计。Python从requirements*.in用pip-compile生成带hash、allow-unsafe的锁，不手改txt。

更新依赖执行相关构建/契约、前端生产及完整依赖审计、`npm run backend:audit`、`npm run security:secrets`及其self-test。高危/严重漏洞阻断发布；低/中风险记录适用性与处置，不过滤结果或复用旧审计数字。
