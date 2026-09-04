# T02 基础阶段交付（T02-01～T02-03）

状态：**仓库内基础交付完成；T02 后续静态门禁、截图、CI 汇总和远程治理待统筹在 T01 及各领域命令落地后继续。**

## 任务、基线与范围

- 任务编号／版本／负责人：T02／foundation／2026-08-30／当前执行者。
- 工作树：`C:\Users\adj\.codex\worktrees\4c45\wxprogrom7.15`。
- 起始 Git HEAD：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`。
- 完成步骤与验收 ID：T02-01（环境/忽略规则基础）、T02-02（前端格式及脚本静态检查）、T02-03（契约生成与只读漂移）；对应 CI-01/02/03 的仓库内基础证据已记录，目标 Python 3.12 与远程部分仍待后续。
- 本阶段未提交、未 push、未 merge，也未访问原目录 `D:\CODE\weixin\wxprogrom7.15`。
- 开工时已有大量前后端、契约、迁移及文档改动；本阶段保留这些改动，包括 `docs/update/README.md` 的删除状态。已修改的两个前端文件本来就处于工作区修改状态，仅施加本任务要求的格式差异。
- 首次改动前的既有文件原文和 SHA-256 已保存于独立临时目录：`C:\Users\adj\AppData\Local\Temp\t02-foundation-backup-20260830160451`。该目录不属于仓库。

## 文件指纹与改动清单

| 文件                                            | 改动前 SHA-256                                                     | 当前 SHA-256                                                       | 本阶段内容                                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| `package.json`                                  | `09D56489D8184DBB0A844B42F7EEF1449B332E9F3EABB042B9E148C1B7FE4C1E` | `5E88C937757C21E012B99A5BFC04D646885F0F9CA931EE3FB043FDDC77B1BD79` | 契约脚本改为跨平台 Node 编排；`check:all` 补入 `contract:check`。                      |
| `.gitignore`                                    | `5ED9821FB6258A9A2C267981C7EF6B253B0E52DD3F548AB296938F3EBBCB2F10` | `6FDE86A82A5D36E2625A81857918C53438D254DE533D2D60727C4E574934E6D1` | 补充通用 `.venv*`、Python 缓存、构建和项目内临时契约目录；不匹配源码目录。             |
| `scripts/contract.mjs`                          | 不存在                                                             | `747B6CA9E5679BB8A95BEAC436C121E3CDB100890E03367B3107DF4C945214F2` | 新增显式写入生成、临时目录只读检查、产物清单、环境去敏、根 Prettier 配置和行尾归一化。 |
| `backend/scripts/export_openapi.py`             | `49723BE42EA6EFA2B79483B8B73650EA365D6ED8387E96284596E957940DA970` | `BD5F6EB1EF5DD0A47946E5D73B556565BD88BE5C6922DC42E3845E95DC87C334` | 在导入 `app` 前强制内存 SQLite、关闭种子/AI/微信并清除凭据环境变量。                   |
| `backend/scripts/export_contract_fixtures.py`   | `CECA8433FEB298B9C7B420F4F185FC6373CBE082C6CA9E1434ECE893FF0B43F7` | `DD26CC7F8E11540DE015CC514F13A89EF95711CC401111A5BCEA7F3018115F11` | 增加 `--output`，允许安全写入临时目录；仅生成合成 fixture。                            |
| `src/pages/report/report.vue`                   | `609CFF000462DB58BB00EDF368C233551417B14E68E13C0A2B947771812CD012` | `F0EBE3203C269FB32E3C38CA704CBD1F7AE031203A862E42B6F82779EE74C4A9` | 修复已知 CSS 格式缺陷；无业务语义改动。                                                |
| `src/services/ai.ts`                            | `D84509B34B69D81AC79166C1DC90E274FD35DEA4CB5AD05E9ED73EE06298C25A` | `1D20E4E559EABE4AA270358222B76891F331BA13C62B680675EE7C51E6ECAC77` | 修复已知 Prettier 换行缺陷；无业务语义改动。                                           |
| `backend/scripts/seed_test_data.py`             | `DA33AEF8B88CF19A88F0DA21FE7FEA943E9C5594BCB282650C87CBA4A661B4EA` | 未修改                                                             | 已知导入排序/格式检查通过，不制造无关重写。                                            |
| `docs/update_plan/deliveries/T02-foundation.md` | 不存在                                                             | 本交付生成                                                         | 本记录；无原文可覆盖。                                                                 |

## 环境矩阵

| 项目          | 目标/CI 意图                        | 本机观察                                     | 结论                                      |
| ------------- | ----------------------------------- | -------------------------------------------- | ----------------------------------------- |
| Node.js       | `.nvmrc` 为 `22.13.0`               | `v24.14.0`                                   | 仅完成兼容性观察，不能代替 Node 22 验收。 |
| npm           | `packageManager` 为 `npm@11.9.0`    | `11.9.0`                                     | 版本一致。                                |
| Python        | CI `actions/setup-python` 为 `3.12` | `3.13.12`                                    | 未宣称 Python 3.12 通过；需目标环境复验。 |
| Python 锁文件 | 带哈希 `requirements*.txt`          | 文件头记录由 Python 3.13 的 pip-compile 生成 | 本阶段未手改或重生成锁文件。              |

`npm ci --legacy-peer-deps` 在本机完成；依赖锁文件未改变。Node 24 的结果只作为安装和前端检查记录，不冒充目标 Node 22／Python 3.12 的完整验收。

## 实现说明

1. `contract:generate` 通过 `scripts/contract.mjs generate` 显式写入仓库或 `--output-dir` 指定目录，统一生成 OpenAPI、生成 TypeScript DTO 和合成 fixture。
2. `contract:check` 在系统临时目录重新生成三类产物，用仓库根 `.prettierrc.json` 明确格式化配置；比较前将 CRLF/LF 统一为 LF，检查缺失、额外和内容过期，并在结束时清理临时目录。它不调用 `git diff`，也不写入仓库快照。
3. Node 子进程会移除 `DATABASE_URL`、AI/JWT/OpenAI/微信变量及 `_KEY`、`_SECRET`、`_TOKEN` 后缀变量。Python `export_openapi.py` 在导入 FastAPI `app` 之前再次执行同等保护，因此直接运行导出器也不会继承业务数据库路径或服务凭据。
4. OpenAPI 导出使用 `sqlite:///:memory:`、关闭 `SEED_SHOWCASE_CASE`/AI/Demo auth/微信配置；不会启动 lifespan、连接业务库或调用外部服务。fixture 导出只使用确定性的 Pydantic 模型和合成病例。
5. 补充 `.gitignore` 的窄范围环境/缓存/构建/临时契约目录规则；没有匹配源码目录或隐藏业务文件。
6. 没有修改 schema、路由、mapper、API/Demo 业务行为或数据库迁移；`docs/openapi.json`、生成 TS 和 fixture 的既有工作区内容由统筹/T01 保留，检查只读验证它们。

## 已执行验证

| 命令或故障注入                                                                                                                                  | 退出码／结果 | 证据摘要                                                                                              |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| `npm ci --legacy-peer-deps`                                                                                                                     | 0            | 锁定 Node 依赖安装完成；本机 Node 24，非目标环境验收。                                                |
| `npm run format:check`                                                                                                                          | 0            | 全仓 Prettier 通过。                                                                                  |
| `npm run lint`                                                                                                                                  | 0            | ESLint 无错误。                                                                                       |
| `npm run type-check`                                                                                                                            | 0            | `vue-tsc` 与 Node `tsc` 均通过。                                                                      |
| `python -m ruff check backend/scripts/export_openapi.py backend/scripts/export_contract_fixtures.py backend/scripts/seed_test_data.py`          | 0            | Python 导出/fixture/seed 脚本检查通过。                                                               |
| `python -m ruff format --check backend/scripts/export_openapi.py backend/scripts/export_contract_fixtures.py backend/scripts/seed_test_data.py` | 0            | 格式检查通过；seed 脚本无写入。                                                                       |
| `git check-ignore` 针对 `.venv`、Python 缓存、`dist`/`build`、coverage、Playwright 和 `.contract-tmp`                                           | 0            | 规则命中预期生成物；源码路径未被忽略。                                                                |
| `npm run check`                                                                                                                                 | 0            | 前端 19 个测试文件、79 个测试通过，行覆盖率 96.91%；微信小程序和 H5 构建完成。仍是本机 Node 24 结果。 |
| `npm run contract:generate -- --output-dir <系统临时目录>`                                                                                      | 0            | 三类产物均在指定目录生成；未写仓库。                                                                  |
| `npm run contract:generate -- --output-dir <临时目录>`（继承合成 DB/AI/微信环境）                                                               | 0            | Node 子进程去敏生效；未创建合成数据库目录，运行日志不含合成凭据。                                     |
| `npm run contract:check`                                                                                                                        | 0            | 当前工作区契约内容一致；检查前后三个仓库快照 SHA-256 不变。                                           |
| 两个独立临时输出逐文件 SHA-256 比较                                                                                                             | 相同         | 证明绝对临时路径不会进入产物内容。                                                                    |
| 临时产物改为 CRLF 后 `node scripts/contract.mjs check --snapshot-dir <目录>`                                                                    | 0            | 证明 Windows 行尾差异被安全归一化。                                                                   |
| 临时生成 TS 追加一行注释后检查                                                                                                                  | 1            | 篡改产物被拒绝。                                                                                      |
| 临时移走 fixture 后检查                                                                                                                         | 1            | 缺失产物被拒绝。                                                                                      |
| 直接运行 `python backend/scripts/export_openapi.py <临时输出>`，同时继承合成业务 DB/key/secret 环境                                             | 0            | 未创建合成业务数据库目录，输出不含合成凭据。                                                          |

所有故障注入均在系统临时目录完成，没有污染仓库、业务库、真实服务或凭据。

## 未完成、阻塞与后续集成

- T01 的受管临时数据库、DB-01/DB-02 证据尚未正式交接；因此未运行 `npm run backend:test`、`npm run backend:check`、任何后端 pytest、迁移、seed 或 E2E。
- Python 3.12 专用环境、干净检出安装和对应 pip-audit 尚未在本机复现；解除条件是统筹提供/启用目标 Python 3.12 环境并按锁文件安装。
- mypy、后端格式/类型完整门禁、前后端边界、关键覆盖率和秘密扫描由 T02 后续/T03～T06 负责；本阶段没有接入不存在的目标脚本，也没有声称 T02 全部完成。
- Linux 截图基线、双平台视觉回归、Engineering gate 汇总、GitHub/Gitee 主仓库分支保护和远程规则未配置或核验；这些需要目标平台/账号权限，属于后续或外部阻塞。
- `package.json` 的脚本改动已保留在本 worktree，最终接入顺序由统筹决定；T01 schema 变化后应重新有意运行 `npm run contract:generate`，再运行只读 `npm run contract:check`。

## 后续集成清单（当前不宣称完成）

| 项目                                                             | 责任方                 | 接入条件                           | 当前状态                                   |
| ---------------------------------------------------------------- | ---------------------- | ---------------------------------- | ------------------------------------------ |
| Python 3.12 专用环境、`ruff format --check`、mypy 与后端完整检查 | T02／T04               | 受管环境和后端边界规则落地         | 待接入；本阶段不运行后端 pytest。          |
| `frontend:boundaries`、`backend:boundaries`、关键覆盖率命令      | T03／T04／T05          | 跨层规则和关键职责清单存在         | 目标命令尚未全部存在，未写入永久失败脚本。 |
| T06 `security-secrets.mjs` 及其 npm 门禁                         | T06 提供规则，T02 接线 | 扫描配置、自测和脱敏输出可审阅     | 待 T06 交付后接入 package/CI。             |
| Linux Chromium 视觉基线、API/Demo 分开制品和连续回归             | T02／T05               | 目标 CI 浏览器/字体/时区及人工审阅 | 未在本机宣称通过。                         |
| `Engineering gate` 汇总任务、取消/跳过/失败传播和 action 固定    | T02                    | 所有必要任务名称及依赖确定         | 未配置；当前 workflow 仅保留既有独立任务。 |
| GitHub/Gitee 主仓库、分支保护、审阅者和合并队列                  | 仓库管理员／统筹       | 外部账号权限和故意失败 PR 证据     | 外部阻塞，未执行远程变更。                 |

## 回退与接收者复验

- 回退只需从上述临时备份恢复六个既有文件，移除新增的 `scripts/contract.mjs` 和本交付记录；不恢复 `docs/update/README.md`，不触碰数据库或用户数据。当前未执行回退。
- 统筹可在本 worktree 复验：`npm run format:check`、`npm run lint`、`npm run type-check`、`npm run contract:check`；在 T01 完成后另行按安全前置运行后端和 E2E 门禁。
