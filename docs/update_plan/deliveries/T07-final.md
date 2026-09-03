# T07 最终规范同步（S3）

日期：2026-08-30。状态：**仓库内文档与项目 skill 已接收至主工作区并通过统筹复验；不等于外部发布批准。**

## 范围、基线与已有改动保护

- 工作树：`C:\Users\adj\.codex\worktrees\b01c\wxprogrom7.15`；开始 HEAD：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`。
- 开始前已记录完整 `git status`：存在大量既有跟踪修改/删除与未跟踪模块、脚本和文档；本交付只编辑权威 Markdown、根 `AGENTS.md` 和 `.agents/skills/wx-engineering-standards/`，没有恢复 `docs/update/README.md`，没有修改业务代码、测试、迁移、OpenAPI、package/lock 或 CI。
- 编辑前逐文件 SHA-256、独立原像与路径清单：`C:\Users\adj\AppData\Local\Temp\wxprogrom7.15-T07-final-preimage-20260830-1\manifest.json`。本记录在编辑前不存在。

| 编辑前文件                                                                                                 | SHA-256                                                            |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `AGENTS.md`                                                                                                | `8B67307DA71A64C63A2733CB5681ABEFB9427F8CE0A6A13E7AFC9CF1399F2B38` |
| `docs/{architecture,data-layer,development,database,security,deployment}.md`                               | 逐项见独立 manifest；其原像均在同一目录的同名相对路径              |
| `docs/adr/0001-data-layer-contracts.md`                                                                    | `54AEA852A12F36D1309FA9DA7A058064A75F89F6570732838D5311A762A5AAFD` |
| `docs/{backend-module-map,frontend-public-interfaces}.md`                                                  | 逐项见独立 manifest；其原像均在同一目录的同名相对路径              |
| `.agents/skills/wx-engineering-standards/{SKILL.md,references/delivery-template.md,scripts/self_check.py}` | 逐项见独立 manifest；其原像均在同一目录的同名相对路径              |

## 当前事实与来源

- [S2 验收](S2-acceptance.md) 是本次仓库内验收来源：前端以 feature/public、bootstrap、platform 分层；后端已有八个 `app/modules/<module>`；S2 同时验收 R05 跨模块 API 边界，且 `scripts/frontend-boundaries.mjs`、`backend/scripts/check_boundaries.py` 均为直接脚本，尚无 `frontend:boundaries`/`backend:boundaries` npm alias。
- `package.json`、`scripts/contract.mjs`、受管 pytest fixture、`testing_resources.py` 和 0009 migration 是命令、契约、测试隔离与迁移事实来源。`contract:check` 在系统临时目录比较；`contract:generate` 才写入三份生成物。pytest 在导入应用前取得带所有权 marker/token 的随机临时 SQLite。
- 0009 的 `down_revision` 为 0008；其 upgrade/downgrade 只涉及 `reports.reviewer_id`、`users.auth_provider` 及相应索引。PostgreSQL 仍是未验证的生产目标。
- T06 仓库侧安全交付已接收；仍保留以下外部阻断：远程 CI/分支保护、目标 Node 22/Python 3.12、历史凭据撤销/访问审计、生产配置、真实微信/AI、医学审核和教师报告范围政策均未在此工作树验收。

## 实施结果

- `AGENTS.md` 保留最小持续约束，改为真实的 feature/public、bootstrap、平台、模块与直接边界脚本路由；不再把边界检查写成计划目标。
- architecture、data-layer、development、database、deployment 与 ADR 删除旧 services/data、旧后端目录和“切 URL 即生产迁移”等冲突叙述，明确 API/Demo 装配、生成契约、受管测试资源和 0009 迁移边界。
- security、backend-module-map、frontend-public-interfaces 记录 S2/R05 当前代码边界，且不把远程或外部事项误写为完成。
- 项目 skill、reference 和 validator 现在检查权威路由、八个后端模块层、R05 标记与真实边界脚本；它不替代后端测试、S2 证据、远程 CI 或生产验收。

API/Demo、HTTP OpenAPI、数据库 schema/迁移、业务代码和公开 operation 均未改变；本次不需要生成契约、执行迁移或数据回退。

## 验证证据

| 命令/检查                                                              | 结果                                                                                                               |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `npx prettier --write <13 个目标 Markdown>`                            | 0；目标均已按 Prettier 格式化。                                                                                    |
| `python .agents/skills/wx-engineering-standards/scripts/self_check.py` | 0；结构、链接、状态标签、权威路由、八个模块层和 R05 标记通过。                                                     |
| `python backend/scripts/check_boundaries.py --self-test`               | 0；R05 API 边界的正负、alias、type-only、SQL、cycle 探针通过。                                                     |
| `node scripts/frontend-boundaries.mjs --self-test`                     | 1；当前工作树未安装本地 `typescript`，Node 无法加载该依赖。未安装或修改 package/lock；先按锁文件安装依赖后再复验。 |
| 相对链接、文档路径和 `package.json` script 引用检查                    | 0；所有编辑 Markdown 的本地相对链接、记录的路径及列出的 script 均存在。                                            |
| `npx prettier --check <13 个目标 Markdown>`                            | 0。                                                                                                                |
| `git diff --check`                                                     | 0。                                                                                                                |

纯文档/skill 同步不运行数据库迁移、后端回归、E2E 或真实外部调用。未运行项的风险是未在当前无依赖工作树独立复验前端边界；解除条件为在不改锁文件的前提下按已验证安装路线提供本地依赖后重跑该 self-test。

## 与并行任务的交接

- **T02**：可把已有直接边界脚本、契约检查与 S2 命令接入最终门禁；不得据本文宣称远程 CI、分支保护或目标版本环境已完成。
- **T05**：继续提供关键行为/覆盖率矩阵与稳定命令；本文没有把任何计划中的 critical script 或覆盖率政策写成当前实现。
- **T06**：仓库侧扫描与测试证据已经接收；凭据撤销、生产、真实服务、医学或报告范围仍需外部证据，不得推断为完成。

## 回退

先比较当前目标文件 SHA-256 与本交付完成后的记录，再只从上述 preimage 的同名相对路径逐文件恢复；删除本次新增的 `docs/update_plan/deliveries/T07-final.md`。不得 `reset`、`clean`、目录覆盖、恢复 `docs/update/README.md`、执行 downgrade 或更改用户既有工作。

## 主工作区接收结论（2026-08-31）

本任务 14 个文件已通过冻结 SHA-256 与主工作区 preimage 门禁后接收，清单位于
`C:/Users/adj/AppData/Local/Temp/wx-final-integration-20260831-011742/integration-manifest.json`。接收后工程 skill self-check、前后端边界 self-test/实际扫描、限定 Prettier 和链接路由复验通过；主工作区已安装依赖，因此此前 T07 Worktree 中未能运行的前端边界自测也已补跑通过。

T05、T06 当前事实已由统筹写入 [最终汇总交付](final-closeout.md)：T05 全部关键职责组通过但全量覆盖率仍有缺口，T06 仓库与构建物扫描通过但外部发布阻断未解除，T02 的 package/CI 统一接线仍未执行。本文较早的并行状态表述只保留为执行历史。
