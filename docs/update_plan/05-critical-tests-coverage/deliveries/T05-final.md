# T05 最终收尾：关键业务回归与职责覆盖率

任务编号／阶段：S3 / T05。  
执行日期：2026-08-31。  
工作树：`C:\Users\adj\.codex\worktrees\0413\wxprogrom7.15`（独立 worktree）。  
基线 HEAD：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`。  
状态：**已接收至主工作区；行为测试和全部关键职责组通过，全量覆盖率门槛仍未关闭。** 本文早期数值保留为执行历史，当前结论以末尾“主工作区最终接收与复验”为准。

## 范围、已有改动与安全边界

- 已按顺序阅读根 `AGENTS.md`、工程规范技能、计划 README/T05、S2 验收、T05 baseline/prep 以及架构、数据层、数据库和安全文档；工程规范自检 `python .agents/skills/wx-engineering-standards/scripts/self_check.py` 退出码为 0。
- 启动前记录了 `git status --short`、HEAD 和目标 SHA-256。worktree 原本有大量 S1/S2 的已修改和未跟踪文件（首次与结束时均为 198 项），包括 `docs/update/README.md` 删除；本任务未还原、清理、提交、推送或修改它们。
- 临时独立备份目录：`C:\Users\adj\AppData\Local\Temp\wx-t05-s3-a6bd4d1037df43309a6d22bbc9157898`。其中保存了首次选定目标和随后发现的生产缺陷文件的 preimage。新增文件没有 preimage。
- 仅修改测试、测试/验证脚本、覆盖率配置、此交付记录，以及一处由失败合同直接证明的最小生产修复。未修改 `package.json`、锁文件、CI、OpenAPI 生成物、迁移、生产配置或 T07 文档。为恢复本 worktree 缺失依赖曾运行 `npm ci --legacy-peer-deps`；未产生清单或锁文件差异。

## 修改与 SHA-256

| 目标                                                            | 修改前                                                             | 修改后                                                             | 说明                                                                                      |
| --------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `src/features/identity/infrastructure/remoteAuth.spec.ts`       | `BE3F6443AC41D6DF97B502DD59603AB1F7BC2C87DFBEDC619ECB607DDBB69AFA` | `16FF5F9C7BC81E8FE5EE0871583D053A1C4A0AF25A26A3B992318FC059CD94D7` | 微信身份映射、失败与会话行为。                                                            |
| `backend/app/modules/qa/infrastructure/medical_chat_gateway.py` | `226D17C310661C65F91C724AAC8F80425E7F1C0B3AC6DDC82D69BCAB73473A92` | `D6EFCEB1E153B27E96820339197BF2F2AB0411D1817E2AF8C3BB986C5536CB69` | `choices: []` 不再触发 `IndexError`，改为既有的空响应 fallback；非列表仍归类为无效 JSON。 |
| `src/features/identity/application/session.spec.ts`             | 新增                                                               | `A5B2C7C415319573DD85B3859805D75E6B44A87FA990A8C0BB05B7E8E9A4878D` | API cache 先失效、再写入身份及 session port。                                             |
| `src/platform/storage/storage.spec.ts`                          | 未单独保存 preimage                                                | `2437529590FACDC22877F02A4E35BC11213A606A676C8534154F214DCA554FCD` | 覆盖受管 storage key 查询。                                                               |
| `backend/tests/test_auth.py`                                    | 未单独保存 preimage                                                | `6B11D079105F9F518FC9E48A5BE9CE9B4631C42625009083E48FB2CF3E57FEA6` | provider 状态、坏身份 DTO、传输异常脱敏。                                                 |
| `backend/tests/test_case_ai.py`                                 | 未单独保存 preimage                                                | `979F0C19E12E683537B692EDDA7712F7B9C1E201CAAFCA9D1ACA01BB5A318249` | AI 配置、超时、空内容、schema 失败。                                                      |
| `backend/tests/test_t05_ai_adapter_safety.py`                   | 新增                                                               | `92F63F2CE1CBA6498EC3A30568FB18C134B1B574F3BD2B801ADB817C8BEF7E1F` | 医学/病例/练习 AI fallback、注入与隐藏字段。                                              |
| `backend/tests/test_t05_state_policies.py`                      | 新增                                                               | `373FBEBEC4880806A8D7942330BBB33DCFD9223ADE990AB7BC83ADAD7665F36D` | 内容、训练、学习状态政策和越权/非法状态。                                                 |
| `backend/tests/test_t05_learning_application.py`                | 新增                                                               | `74ABBA47752FA16D8116DF3622EF24EF7224D49100C16A66E8F16E9F4D0D48E8` | 学习计划、锁、幂等、冲突恢复。                                                            |
| `backend/tests/test_t05_content_application.py`                 | 新增                                                               | `2F37FB6A0EA5060A2737B2819A7A04BB38DF8967A4D3F668B28B7763D9C7FB65` | 病例草稿/审核/发布、digest、clone 与审阅权限。                                            |
| `config/critical-coverage.json`                                 | 新增                                                               | `51ED2388698289BCE87C7629BE49909895681A8761D47487245BD3362605671B` | 实际关键文件级职责清单和阈值。                                                            |
| `scripts/critical-coverage.mjs`                                 | 新增                                                               | `CDB9C542A4D4F01718DCF71252D437BF0465009DE82E57172E6BFE3D99B49D67` | 拒绝缺失文件、缺失 coverage record、空组及低于职责门槛。                                  |

首次备份也包含未改动的 `vitest.config.ts`、`backend/pyproject.toml`、报告草稿、T04 及既有 AI 特征测试，供回退/审阅比较。`storage.spec.ts`、`test_auth.py`、`test_case_ai.py` 是补测时才纳入修改的既有文件，未在最初批次留下独立 preimage；这是记录纪律缺口，不能把当前内容当作其修改前证据。

## 当次执行证据

| 命令                                                                                                                                                                                                                         | 结果                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run check`                                                                                                                                                                                                              | 退出 0；format、lint、typecheck、21 个前端 test files / 96 tests、H5 与 MP-Weixin 构建均通过。Vitest 总覆盖率：lines/statements 96.86%、branches 86.10%、functions 93.89%。               |
| `npx vitest run --coverage --coverage.reporter=json --coverage.reporter=text`                                                                                                                                                | 退出 0；21 files / 96 tests。随后前端职责校验退出 0。                                                                                                                                     |
| `node scripts/critical-coverage.mjs --frontend coverage/coverage-final.json`                                                                                                                                                 | 退出 0；identity-session 98.86/85.71/100，http-cache 100/98.15/100，storage-migration 100/93.75/100，report-training-use-cases 100/97.37/100（lines/branches/functions，门槛 90/85/90）。 |
| `cd backend; python -m pytest tests/test_auth.py tests/test_case_ai.py tests/test_t05_ai_adapter_safety.py tests/test_t05_state_policies.py tests/test_t05_learning_application.py tests/test_t05_content_application.py -q` | 退出 0；43 passed。使用 T01 `conftest.py` 的受管随机 SQLite fixture；42 条已知 SQLite FK-drop-order warning。                                                                             |
| `cd backend; python -m pytest --cov=app --cov-branch --cov-report=json:coverage/t05-backend.json -q`                                                                                                                         | 退出 0；119 passed；全局 lines 88.77%（仅供参考，不作为关键组通行依据）。                                                                                                                 |
| `node scripts/critical-coverage.mjs --backend backend/coverage/t05-backend.json`                                                                                                                                             | 退出 1；identity 98.68/93.75、medical-ai 99.40/100、content 95.81/90.91、training 91.16/87.80 均通过；learning lines 82.97%（门槛 90）失败。                                              |
| `npm run backend:check`                                                                                                                                                                                                      | 退出 0；ruff、mypy、119 passed；非分支全局 coverage 91.11%。                                                                                                                              |
| `npm run contract:check`                                                                                                                                                                                                     | 退出 0；临时目录生成并比较，无源码/快照写入。                                                                                                                                             |
| `node scripts/critical-coverage.mjs --self-test`、`git diff --check`                                                                                                                                                         | 均退出 0。self-test 仅在系统临时目录创建并删除自己的随机目录。                                                                                                                            |

`npm run check` 后 Vitest 的默认 coverage reporter 会清除 JSON artifact；因此曾出现一次随后单独运行的 frontend checker 因 `coverage-final.json` 缺失退出 1。这是执行顺序问题，不是测试失败；已用上表的显式 JSON 重跑修复并通过。最早的环境失败是 worktree 不含 `node_modules`，`npm run test:coverage` 无法找到 Vite；安装受锁定依赖后重跑通过。

## 业务合同、权限与数据影响

- 身份/会话：验证 API token/cache 清理顺序、持久化 session 写入、坏 DTO、provider 状态和传输错误不泄漏原始异常；微信条件编译由 H5/MP 构建验证，未把 Vitest 的编译目标布尔值当作端侧登录证据。
- AI：所有 provider 均是 monkeypatch/fake，受测试 socket guard 限制，没有调用真实 AI 或微信。覆盖 disabled、缺配置、timeout、HTTP 状态、坏 JSON/结构、空响应、有界重试、急症 fallback、prompt injection、隐藏事实/rubric 不外泄。
- 内容/病例审核：覆盖草稿/审核/发布的不可变性、过期 digest、clone 冲突、学生不可审自己及 owner/approved 限制；训练与学习覆盖非法状态、锁、幂等和冲突恢复。
- 数据库：未创建未知 engine，未直接 `drop_all`，未运行开发迁移或 seed。DB 清理只由 T01 受管 fixture 内部执行，其路径/marker/token 边界由 `conftest.py` 控制。没有迁移和持久化数据改动。
- 合同：未更改路由、schema、OpenAPI 或生成类型；`contract:check` 通过。

## 未关闭项、回退与外部阻塞

1. **T05 关键门槛未关闭：** `learning-plan-state-machine` 关键职责组 82.97% lines，低于 90%。保留真实阈值而未降低/排除源文件；下一执行者应补 `backend/app/modules/learning/application/use_cases.py` 的未覆盖错误、重复/回滚和边界路径，并重跑 branch coverage + checker。
2. 本次没有重跑 H5 API E2E、Demo E2E 或真机/微信开发者工具测试。S2 的 8/8、1/1 与构建事实仅为历史交接资料，不冒充本次证据；若要关闭 T05，须在唯一端口和 T01 受管数据库下重新执行适用 E2E，端侧真机仍需要外部环境。
3. 未单独调用 `backend:test:safety` / `backend:test:migrations` 脚本；完整 pytest 已包含其相关测试文件，但若修改 fixture/engine/migration，仍需按 T01 入口专门重跑。
4. 回退：删除新增测试、配置、脚本和本记录；将 `medical_chat_gateway.py` 从上述独立 preimage 恢复，并逐个审阅/恢复已有测试的本任务 hunks。不得对该 dirty worktree 使用 `reset --hard`、`clean` 或批量恢复。

等待统筹审阅；在 learning 门槛和适用 E2E 获得新的通过证据前，不应标记 T05 为完成。

## S3 审核返修 R1（2026-08-31）

本轮基线仍为 `b96bab910dc5ee43410fa55c5b856cc4d3f3415d`，开始与修改前的独立 manifest 为
`C:\Users\adj\AppData\Local\Temp\wx-t05-r1-20260831-004227\preimage.json`。本轮没有覆盖首轮
备份、没有修改主工作区、`package.json`、锁文件、CI、迁移、生成物或生产配置。

| 审核项               | 本轮事实与具体测试                                                                                                                                                                                                                                                                                                                                                                                               | 状态                                                                                                                                                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1-01 检查器         | `scripts/critical-coverage.mjs --self-test` 现经真实 `check()` 运行 frontend/backend 完整报告、刚好达标、略低、缺记录/源码、空组、零适用分支、缺指标、坏阈值、缺 covered 和 covered > total。计数、阈值和百分比均要求有限合法值；不再把 `NaN` 当作通过。                                                                                                                                                         | 已关闭（self-test exit 0）。                                                                                                                                                                                          |
| R1-02 SFC 范围       | `vitest.config.ts` 使用锁定树中已有的 Vue SFC 编译插件，`coverage.all=true` 并纳入 `App.vue`、全部 components 与 pages。复跑显示此前未计入的 34 个 SFC 全部在 JSON/report 中，当前全量 lines/statements 为 **49.82%**、branches 83.61%、functions 86.65%。                                                                                                                                                       | **未关闭**：全量 lines < 85，尚需逐页/组件行为测试；未用排除或假执行掩盖。                                                                                                                                            |
| R1-03 后端独立门槛   | config 已声明 frontend 全量 85/80/85、backend 全量 85/80，关键组仍是 90/85；checker 同时校验全量与组。`scripts/t05-verify.mjs --frontend / --backend / --all` 以临时报告运行测试后再调用 checker，跨 Windows/Linux 传递子进程退出码，不依赖旧 JSON。                                                                                                                                                             | **未关闭**：后端上轮真实分母仍为 lines 4989/5476=91.11%、branches 536/748=71.66%；learning 268/323=82.97%、62/88=70.45%。本轮全量 branch run 被本机执行宿主在 30 秒时中断并已停止其精确 PID，未将不完整输出记为证据。 |
| R1-04 微训练竞争恢复 | `test_learning_application_recovers_a_racing_micro_start_and_assessment` 现在首次返回 `in_progress`，`assess_micro_task` 真实抛出 `PersistenceConflict`，rollback 后第二次读取返回 assessed winner；断言赢家原答案不被覆盖、两次 rollback。`test_learning_application_reports_conflict_when_racing_assessment_cannot_be_recovered` 断言无 winner 时 409、无 commit、原答案/状态不变。定向 pytest：**5 passed**。 | 已修正测试有效性；真实双 session submit conflict 仍受当前无乐观版本/条件更新约束，不能冒充为已证明的数据库竞争恢复。                                                                                                  |
| R1-05 格式           | 本文件最后修改后需执行限定 Prettier，结果追加到冻结记录。                                                                                                                                                                                                                                                                                                                                                        | 待最后冻结。                                                                                                                                                                                                          |

本轮范围内测试映射补充：AUTH 的 remote DTO/session/cache 守卫仍由
`remoteAuth.spec.ts`、`session.spec.ts`、`apiClient.cache.spec.ts` 覆盖；CONTENT owner/digest/发布幂等由
`test_t05_content_application.py` 覆盖；TRAIN 状态/AI fallback 由
`test_t05_state_policies.py` 与 `test_t05_ai_adapter_safety.py` 覆盖；LEARN 的锁、幂等、提交冲突恢复和
409 由 `test_t05_learning_application.py` 覆盖。职责源映射维持
`config/critical-coverage.json` 的 identity、medical-ai、content、training、learning 实际文件列表；首轮报告的
历史全量“88.77%”是 branch run 的综合显示，绝不作为 lines 指标。

本轮未验证项：尚未完成 34 个 SFC 的行为覆盖、全量 backend branch 80%、learning 90/85、两轮连续全绿、返修后的 API/Demo E2E 与真机验收；不将统筹上一轮 96/119/API 8/Demo 1 作为本轮通过证据。真实 AI/微信、未知数据库、开发迁移及 seed 均未调用。回退方式是按 manifest 逐文件恢复已存在目标、删除本轮新增脚本/测试；不得在该 dirty worktree 使用 reset/clean。

冻结清单：preimage 为 `C:\Users\adj\AppData\Local\Temp\wx-t05-r1-20260831-004227\preimage.json`，postimage 为 `C:\Users\adj\AppData\Local\Temp\wx-t05-r1-20260831-004227\postimage.json`。

## S3 审核返修 R2（2026-08-31）

本轮新增 preimage：`C:\Users\adj\AppData\Local\Temp\wx-t05-r2-20260831-005518\preimage.json`；
本轮新增目标的最终指纹记录在同目录 `postimage.json`（完成最后格式化后更新）。没有恢复
`docs/update/README.md`，也没有覆盖 R1 的备份或其他执行者文件。

| 项目               | R2 证据与当前判定                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1-01 / 空计数漏洞 | `scripts/critical-coverage.mjs` 的 `check()`/`checkGroup()`/`checkOverall()` 现在要求全量和关键组有可执行行计数；全空 `s/f/b` 不再以 N/A 通过。真实 CLI 读取统筹的 `empty-counts.json` 退出 1（`frontend all has no executable line coverage data`）；有行但零适用分支的正常文件仍在真实 self-test 通过。missing-covered 负例保持拒绝。                                                     |
| R1-02 / SFC        | `vitest.config.ts` 使用锁定依赖树中的 Vue compiler plugin，`coverage.all=true`，include `App.vue`、全部 `components/**/*.vue` 和 `pages/**/*.vue`。真实前端报告列出 34 个 SFC；新增 `ui.behavior.spec.ts`、`sfc.behavior.spec.ts` 共 7 个真实挂载/事件测试，均通过。当前全量 lines/statements **49.82%**、branches **83.61%**、functions **86.65%**（lines 仍低于 85，未排除 SFC/假命中）。 |
| R1-03 / backend    | 新增学习 application 的 4 组可观察行为测试；锁定的后台完整回归句柄 `C:\Users\adj\AppData\Local\Temp\wx-t05-r2-backend-run` 完成 120 passed、96.94s、综合 88.91%。其 branch JSON 经 checker 真实判定 backend all branches **72.06% < 80%**；追加用例后尚未形成新的完整 branch JSON，不能把旧结果升级为本轮通过。learning 仍需真实 90/85。                                                    |
| R1-04 / 竞争恢复   | `test_learning_application_recovers_a_racing_micro_start_and_assessment` 首次未评分、写入冲突、rollback、二次读取 assessed winner，并验证原答案不被覆盖；新增不可恢复 409。R2 定向 `test_t05_learning_application.py` **9 passed**。由于当前 SQL 写入没有乐观版本/条件更新，仍不把 fake-port 分支冒充真实双 session submit conflict。                                                       |
| R1-05 / 格式       | R2 最后修改后限定 Prettier：`scripts/critical-coverage.mjs`、`scripts/t05-verify.mjs`、`config/critical-coverage.json`、`vitest.config.ts`、本文件均通过；Python 使用 Ruff，不把 Prettier 对 Python 的 parser 错误算作格式通过。                                                                                                                                                            |

R2 稳定 runner 用法：`node scripts/t05-verify.mjs --frontend`、`--backend` 或 `--all`。它使用 Node 直接启动 Vitest/Python（无 shell 拼接），每侧生成自己的临时报告；子进程非零会保留并打印报告目录。前端 runner 本轮实际退出 1，原因是完整 SFC lines 49.82%，不是测试失败；后台 backend 报告由独立 `Start-Process` 句柄保留日志和 JSON。

R2 具体测试—职责映射：`src/components/ui/ui.behavior.spec.ts` 覆盖 UI 状态/动作/导航；
`src/components/sfc.behavior.spec.ts` 覆盖 App 启动与教师报告 loading/error/retry；
`backend/tests/test_t05_learning_application.py` 覆盖 case-linked assessment、非 micro 启动、缺 problem、冲突恢复、计划完成/回滚/服务失败、通知/到期提醒/缺资源；
原有 `test_t05_ai_adapter_safety.py`、`test_t05_content_application.py` 和 `test_t05_state_policies.py` 继续覆盖 AI 隐藏字段/fallback、病例审核 digest/owner、训练/学习 policy。

R2 尚未关闭：其余 32 个 SFC 的加载/空态/错误/重试/提交行为，全量前端 85/80/85，backend 全量 branch 80%，learning 90/85，两轮连续完整恢复树回归，以及返修后 API/Demo E2E、双端构建和真机。上述未关闭项是当前真实缺口，不是外部依赖伪装；真实 AI/微信、未知数据库、迁移、seed、package/lock/CI 仍未触碰。

## 主工作区最终接收与复验（2026-08-31）

统筹按冻结 SHA-256 接收本任务 17 个文件；清单和主工作区 preimage 位于
`C:/Users/adj/AppData/Local/Temp/wx-final-integration-20260831-011742/integration-manifest.json`。接收后发现覆盖率检查器的 backend self-test 在 Windows 跨盘临时路径下无法映射绝对路径，已让 backend loader 同时接受 coverage.py 的相对路径和合法绝对路径；阈值、范围与计数规则未改变，self-test 随后退出 0。

- 前端行为：23 files / 103 tests 通过；API E2E 8/8、Demo E2E 1/1、MP-Weixin 与 H5 构建通过。
- 后端行为：T05 定向 48 tests、全量 127 tests 通过；全部使用 T01 受管随机 SQLite。仍有已知 SQLite FK drop-order warning。
- 关键职责组全部达标。前端 identity 98.86/85.71/100、http 100/98.15/100、storage 100/93.75/100、report/training 100/97.37/100；后端 identity 98.68/93.75、medical-ai 99.40/100、content 95.81/90.91、training 91.16/87.80、learning 96.28/87.50。
- 全量门禁仍失败：前端 lines 51.85% < 85%；后端 branches 73.66% < 80%。完整报告位于 `C:/Users/adj/AppData/Local/Temp/wx-final-acceptance-20260831-012100/`，没有降低阈值或移除页面。
- Lint、前端类型、Ruff、后端严格类型、契约只读检查、前后端边界和本地秘密扫描通过。`package.json`/CI 的 critical 与边界统一别名仍由 T02 治理项承接。

因此 T05 的代码与测试成果已经交付到主工作区；其剩余工作是提高全量覆盖率和接入最终 CI，而不是再次接收本 Worktree。
