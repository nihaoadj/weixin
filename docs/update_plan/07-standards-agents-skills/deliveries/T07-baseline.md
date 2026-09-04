# T07 基线记录（T07-01 / S0）

状态：**S0 基线已交付，等待统筹在重构与命令实际落地后安排后续阶段；T07 整体未完成。**

## 任务书与快照完整性确认

- 工作树：`C:\Users\adj\.codex\worktrees\f82d\wxprogrom7.15`
- 禁止触碰的原目录：`D:\CODE\weixin\wxprogrom7.15`（本阶段未访问、未修改）。
- 起始 Git HEAD：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`。
- 任务书实际位置为 `docs/update_plan/07-standards-agents-skills.md`；总任务书为 `docs/update_plan/README.md`。二者以及 development、architecture、data-layer、database、deployment、security、文档索引和 ADR 0001 均可读取。
- 起始工作区（新增本交付前）有 65 项已跟踪的修改/删除和 4 项未跟踪内容；其中 `docs/update/README.md` 已被删除，保留删除状态，绝不恢复。计划中提及的未跟踪 `20260830_0009_report_reviewer_auth_provider.py` 当前存在。
- 本阶段允许的两个目标文件在写入前均不存在：`AGENTS.md`、`docs/update_plan/deliveries/T07-baseline.md`。故没有被覆盖的原内容；无需保存原文件副本。

### 输入内容指纹（SHA-256）

| 输入                                             | SHA-256                                                            |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `docs/update_plan/README.md`                     | `D703930A61E62A6EC29F920C8096F2A7AABAD1E9B5800EB662C544B5423ECA67` |
| `docs/update_plan/07-standards-agents-skills.md` | `F3AEC5E734819D98219033544773217E57B3EB43D0D491FC054D758A40658ED7` |
| `docs/development.md`                            | `F51359B2D5D7B55130C17A93FBECAE5FB9AD8BCCE88CCEF59BBD862BCDDAB5A8` |
| `docs/architecture.md`                           | `F3C1D1B120FA28FE77387F5A621980CC0973DBEF197FE0ECFDF5D6CED0567413` |
| `docs/data-layer.md`                             | `A8F23076EFAFB8038DE99A7C8F9F50B777E66C1715D7C2D5675D270E8DD94F01` |
| `docs/security.md`                               | `24EE860076007767C6E9AEAE8EB3AEC66DE8BB6C880049CDE3186394994BF424` |
| `docs/database.md`                               | `B4B7C26EEE1C7AB210AE926A094760B35F846620939F986C90EA59C18FE08BA2` |
| `docs/deployment.md`                             | `4B93DC6B6F31E3F5020B76CB842137935A76D00374ECE45F02964D919CE7A713` |
| `docs/adr/0001-data-layer-contracts.md`          | `39549B1705DF9C97061A395886723D7DB291DA0ECA528F625A5FE684AFB755AF` |
| `package.json`                                   | `09D56489D8184DBB0A844B42F7EEF1449B332E9F3EABB042B9E148C1B7FE4C1E` |

## 本次交付

- 新增根 `AGENTS.md`：以链接路由权威文档，保护已有改动、测试数据库、API/Demo 和服务端秘密边界；明确当前命令的安全前置条件及计划命令尚未落地的事实。
- 新增本记录：固定冲突、职责、后续输入与可验收条件。
- 未修改正式主文档，未创建项目 skill，未安装插件，未运行后端测试、E2E、数据库迁移或 seed，未 commit/push/merge。

## 规范冲突与待澄清清单

| ID   | 当前观察                                                                                                        | 冲突或风险                                                                                                | 归属与后续处理                                                      |
| ---- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| C-01 | 根 README 的“当前更新状态”仍引用已删除的 `docs/update/README.md`，并称迁移仅到 `0007`。                         | 文件系统已有 `0008`，且工作区有未跟踪 `0009`；不能将已删除文档恢复为事实来源。                            | T07-02 在集成已落地迁移后修正文档索引/状态。                        |
| C-02 | `docs/development.md` 仍将 Demo 数据、远程入口写为 `repository.ts`/`repositoryAsync.ts`。                       | 与 `docs/data-layer.md` 的 `src/data`、Repository、adapter、mapper、compatibility facade 描述不一致。     | T03 提供真实路径/公开接口映射；T07-02 统一说明。                    |
| C-03 | development、deployment、backend README 展示直接 pytest 路线。                                                  | 当前测试仍多处对应用 engine 直接 `drop_all`/`create_all`，默认配置指向开发 SQLite；T01 前可伤及开发数据。 | T01 交付受管 fixture 和安全入口；T07-02/03 更新命令。               |
| C-04 | `contract:check` 当前调用会写入的 `contract:generate`。                                                         | 与总任务书中“目标为临时生成后只读比较”的目标合同不一致。                                                  | T02 落地只读检查；T07 只能在证据出现后更新为“当前”。                |
| C-05 | `docs/database.md` 以仅切换 URL 表述 PostgreSQL 生产迁移。                                                      | T01/T07 任务书明确 PostgreSQL 兼容性未实测，不能承诺即插即用。                                            | T01 提供迁移矩阵，T06/T07 在有证据后修正表述。                      |
| C-06 | 开发/部署安装说明分别使用 `npm install`、`npm ci --legacy-peer-deps`，Python 安装入口也分散。                   | 不能证明可重复环境；运行目录与锁定版本说明尚未统一。                                                      | T02 确定锁定工具链与 CI；T07-02 只引用已验证命令。                  |
| C-07 | 总任务书列出 `backend:test:safety`、`backend:test:migrations`、`frontend:boundaries`、`backend:boundaries` 等。 | 它们是待新增目标，不是当前 `package.json` scripts。                                                       | T01–T04/T02 实现并交付证据前，AGENTS/skill 不得要求或声称已可执行。 |
| C-08 | architecture 以“生产 PostgreSQL/服务端 AI 网关/对象存储（按需）”显示于总体图。                                  | 容易被误读为已部署调用链；任务书要求区分概念路线与实际依赖。                                              | T03/T04 给出现状/目标模块与依赖图；T07-02 纠偏。                    |

## 权威文档职责与当前引用策略

| 权威位置                                   | 负责的事实                                              | T07 基线如何使用                                                |
| ------------------------------------------ | ------------------------------------------------------- | --------------------------------------------------------------- |
| `docs/architecture.md`                     | 模块职责、目录/层边界、装配和架构图                     | 用于目录与依赖判断；现状/目标需待 T03/T04 映射后澄清。          |
| `docs/data-layer.md`                       | DTO、领域记录、展示转换、API/Demo、缓存、存储、错误合同 | 作为前端数据边界和契约生成规则的唯一说明。                      |
| `docs/development.md`                      | 可复现开发、工具、命令和提交要求                        | 当前存在过时路径/不安全测试命令，暂由 AGENTS 安全前置条件约束。 |
| `docs/database.md`                         | 实际迁移链、开发/测试库边界、保留和恢复限制             | 需 T01 以实际 Alembic 图和隔离证据刷新。                        |
| `docs/deployment.md`                       | 环境、构建、平台和发布前提                              | 不替代测试安全与真实 CI 工具链证据。                            |
| `docs/security.md`                         | 权限、敏感数据、AI 和历史凭据处置状态                   | 是秘密、DTO、日志及发布安全的权威边界。                         |
| `docs/adr/0001-data-layer-contracts.md`    | 重大数据层决策和取舍                                    | 用于兼容门面、显式模式、DTO/领域分离的理由。                    |
| `docs/update_plan/`                        | 本轮任务、阶段、验收和交付证据                          | 仅计划/证据，不能替代当前代码事实。                             |
| 根 `AGENTS.md`                             | 最小项目级约束、必读入口、检查路由                      | 本次新增；只链接权威来源，不复制易失效细节。                    |
| `.agents/skills/wx-engineering-standards/` | 按改动类型执行的流程                                    | 待 T07-04；尚未创建，不可作为当前前提。                         |

## 后续文档和 skill 更新所需输入

| 提供方   | T07 必须收到的事实输入                                                                    | 用于的后续验收                                               |
| -------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| T01      | 受管测试资源模型、所有受支持入口、DB-01～DB-09 结果、迁移矩阵、真实安全命令及失败诊断     | DOC-02、DOC-05、DOC-07；替换不安全 pytest 示例。             |
| T02      | 锁定的 Node/Python 工具链、实际 package scripts、CI 门禁/平台、契约只读比较与生成流程证据 | DOC-02、DOC-09；命令表和安装/检查说明。                      |
| T03      | 前端八业务模块中的实际模块字典、目录迁移表、公开接口、依赖边界命令和 API/Demo 兼容策略    | DOC-01、DOC-04、DOC-08；architecture/data-layer/skill 路由。 |
| T04      | 后端模块、层/事务/依赖规则、路由/schema/use case/model 映射、OpenAPI 与 Alembic 实际 head | DOC-01、DOC-05、DOC-08；后端边界与迁移说明。                 |
| T05      | 关键行为矩阵、覆盖率范围/门槛、测试入口与跨端/E2E 证据                                    | DOC-04、DOC-05、DOC-07；按改动选择验证。                     |
| T06      | 权限/威胁矩阵、秘密扫描入口和结果、外部凭据/发布阻塞的脱敏状态                            | DOC-04、DOC-08、DOC-09；安全/发布限定。                      |
| 统筹集成 | 已合并或可审阅的真实路径、命令、文档事实及冲突裁决                                        | T07-02～07；防止把计划写成现状。                             |

## T07 后续验收前置与接收者复验

1. T01–T06 将各自实际命令、路径、接口与未验证项写入对应交付记录，统筹解决本记录 C-01～C-08 的归属。
2. T07 仅据这些证据更新正式 development、architecture、data-layer、database、deployment、安全文档与文档索引；每一处目标命令须先确认存在且可执行。
3. 使用 `skill-creator` 创建仓库内 `.agents/skills/wx-engineering-standards/`，不得修改用户全局 settings 或把未安装插件设为依赖。
4. 在干净副本验证 DOC-01～DOC-09：链接/路径/元数据、文档任务的轻量检查、登录和 schema 样例、已有改动保护、失败/缺工具报告及跨域违规指引。
5. 最终 `deliveries/T07.md` 应记录命令、时间、退出码、覆盖率范围、证据路径、外部阻塞和回退信息；本基线不以文件存在代替这些验证。

## 回退与影响

本次只新增两个 Markdown 文件。回退时仅移除这两个新增文件，不恢复 `docs/update/README.md`，不修改用户数据、数据库、全局设置或既有工作区改动。
