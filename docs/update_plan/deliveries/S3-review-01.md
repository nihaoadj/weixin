# S3 第一轮统筹审核

日期：2026-08-31。范围：T05、T06、T07 的 S3 独立 Worktree 候选。结论：**T05 退回完善；T06 功能增量可接受但交付格式未过；T07 可接收为 S2 事实同步候选，最终文档仍须跟随 T05/T06/T02 收尾。S3 未通过，不进入最终 CI 集成，不代表生产发布批准。**

本轮仅审核、独立运行检查并更新统筹证据，没有修复执行者代码、重启执行者、集成候选、提交、推送、合并或部署。沿用项目 `wx-engineering-standards` 的审核路由。主工作区仍保留全部既有未提交/未跟踪改动及 `docs/update/README.md` 删除状态。

## 范围与基线

| 任务                       | 候选 Worktree                                      | 相对 S2 的增量                                                    | 本轮判定                                         |
| -------------------------- | -------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------ |
| T05 关键业务与覆盖率收尾   | `C:/Users/adj/.codex/worktrees/0413/wxprogrom7.15` | 13 文件：测试、覆盖率配置/脚本、一个 AI 空 choices 修复和交付记录 | 未完成；须解决下列 R1-01～R1-05                  |
| T06 安全与发布证据收尾     | `C:/Users/adj/.codex/worktrees/9e54/wxprogrom7.15` | 5 文件：生产判定、seed 条件、安全回归、扫描自测和交付记录         | 本地功能复验通过；R1-05 格式未过，外部事项仍阻断 |
| T07 工程规范与事实文档收尾 | `C:/Users/adj/.codex/worktrees/b01c/wxprogrom7.15` | 14 文件：权威文档、AGENTS、skill、自检与交付                      | 当前阶段文档候选可接收；不是最终 S3 文档验收     |

三个候选 HEAD 均沿用 `b96bab910dc5ee43410fa55c5b856cc4d3f3415d`，但实际基线是带 S1/S2 改动的工作树。用 S2 `workspace-manifest.json` 逐文件比较，三项增量所对应的主工作区文件都仍匹配 S2 hash；新增目标在主工作区不存在。没有发现 package、锁文件、CI、迁移或生成契约的越界改动。T05 三个未单独备份的既有测试文件可以由这份冻结 hash 加当前主工作区原像核实，不能仅凭 Git HEAD 恢复。

本轮外部证据目录：`C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc`。`scope.json` 保存候选与基线指纹，T05/T06/T07 子目录保存相对主工作区的逐文件 diff。复验报告与负例只写入该系统临时目录；临时目录不是永久 CI 制品，后续集成应保存脱敏证据及新版本指纹。

## 必须处理的问题

### R1-01 / P1：覆盖率计数缺失时错误放行

位置：T05 `scripts/critical-coverage.mjs:99–116`，自测位于 `:122–144`。

校验器只验证 `value.total` 是有限数，未验证 `value.covered`。后端报告保留 `num_statements`、`num_branches`，删除 `covered_lines`、`covered_branches` 后，累计结果成为 NaN；`NaN < minimum` 为假，五个职责组全部输出 `lines=NaN% branches=NaN%`，进程仍退出 **0**。缺损报告会被误认为门禁通过。

独立复现通过真实 CLI 读取临时合成报告，不改源码或阈值：完整合成报告退出 0；零覆盖和缺记录报告退出 1；缺 covered 字段报告错误退出 0。证据为 `valid-control.json/log`、`zero-coverage.json/log`、`missing-record.json/log`、`missing-covered.json/log`。

现有 `--self-test` 虽创建了 config，却没有调用 `check()`；低阈值和缺文件断言只是自测内部重新编写的条件，不能保护真实校验入口。

完成标准：验证 covered、total、threshold 的类型、有限性及合法范围，拒绝缺字段、负值、covered 大于 total、无效阈值；计算结果也须有限。前后端正负例应经过同一实际校验函数或 CLI，覆盖边界值、缺源码/记录、空组、零分支和低覆盖，全部异常必须非零退出。不得仅增加又一套自测内判断。

### R1-02 / P1：前端全部业务覆盖率范围仍不完整

位置：T05 `vitest.config.ts:18–24`。这是 T05-05 应完成但本轮没有修改的既有配置，不属于新引入的运行时回归。

include 仍只匹配若干目录的 `.ts`，没有纳入 Vue script、pages、components 和 App。本轮实际覆盖率 JSON 中 **0 个 Vue 文件**，候选 `src` 中有 **34 个 Vue 文件**。因此 96.86% lines 只能说明已配置范围，不能证明任务书要求的“全部手写业务代码”达到 85/80/85 门槛。页面里的加载、重试、提交和角色流程不会因为无人测试而拉低该指标。

完成标准：补齐 SFC 编译/source map 与覆盖率 include，对页面、组件和 composable 内手写业务落实统计；纯类型/生成物/资产排除要有理由。未被测试导入的业务实现也必须出现在报告中；使用未导入样例证明范围防护。按完整范围补测试并达到既定阈值，不整包排除页面来维持高数字。

### R1-03 / P1：后端分支门槛未落实，learning 两项指标均未达标

位置：T05 `config/critical-coverage.json`、`scripts/critical-coverage.mjs`、`backend/pyproject.toml`，以及 `backend/app/modules/learning/application/use_cases.py` 的补测范围。

119 项测试通过并不代表覆盖率验收通过。本轮直接读取完整 branch JSON 的真实计数：

| 指标                    | 实测                 | 目标 | 判定   |
| ----------------------- | -------------------- | ---- | ------ |
| 后端全量行              | 4989 / 5476 = 91.11% | 85%  | 通过   |
| 后端全量分支            | 536 / 748 = 71.66%   | 80%  | 未达标 |
| learning 关键职责组行   | 268 / 323 = 82.97%   | 90%  | 未达标 |
| learning 关键职责组分支 | 62 / 88 = 70.45%     | 85%  | 未达标 |

pytest 显示的 **88.77% 是行与分支的综合覆盖率**，不是全量行覆盖率或分支覆盖率；T05-final 把它标成 lines，应更正。现有 pytest `fail_under=85` 只挡综合指标，critical checker 只检查所列职责组，没有独立执行全量分支 80% 门槛。learning 的行指标首先抛错，掩盖了同组分支也不达标的事实。

完成标准：新增/完善可复用的测试加校验入口，分别强制全量行 85%、全量分支 80% 和关键组 90/85，不降低标准；补 learning 状态、异常、提交/回滚、通知和重复请求路径。T05 交付稳定直接命令，T02 再独占接入 npm/CI；不能只提供消费旧 JSON 的手工命令。报告应独立展示每项指标，不能把综合值改名为 lines。

### R1-04 / P2：微训练提交冲突恢复测试没有触发对应分支

位置：T05 `backend/tests/test_t05_learning_application.py:138–165`。

`test_learning_application_recovers_a_racing_micro_start_and_assessment` 中 `find_task_attempt` 始终返回 `status="assessed"`。`submit_micro_task` 直接走“已评分则返回”的幂等短路，从未执行配置的 `assess_micro_task` 异常；唯一一次 rollback 来自前面的 start。即使删除提交评分的冲突恢复代码，这条用例仍可能通过。本轮真实覆盖率也显示 `use_cases.py:154–159` 的提交冲突分支全部未覆盖。

完成标准：首次查询返回未评分状态，写操作真实抛出 `PersistenceConflict`，回滚后的再查询才返回另一请求已提交的评分；断言持久化结果、原答案没有被覆盖和正确回滚。另测竞争结果仍不可读时的 409。对目标守卫做临时副本故障注入，证明对应测试会失败；不以顺序重复请求代替竞争恢复证据。

### R1-05 / P2：最终交付文件使格式门禁失败

位置：T05、T06 各自的 `docs/update_plan/deliveries/T05-final.md`、`T06-final.md`。

两份最终文档均被本轮 `prettier --check` 拒绝，退出码 1。T05 记录的早先 `npm run check` 通过不能代表包含最终文档的交付树已经全绿；`git diff --check` 也不能代替 Prettier。源测试、critical JSON/脚本及 T06 扫描脚本的限定格式检查没有报错。

完成标准：两位执行者分别格式化自身交付文档，最后一次修改之后重跑受影响格式检查，更新最终文件 hash 和证据；不能删除文档或加入 ignore 来绕过门禁。

## 独立复验结果

环境：Windows，Node 24.14.0，Python 3.13.12。目标 Node 22/Python 3.12 和 Linux 截图仍由 T02/平台另验。

| 检查与工作树          | 命令或操作                                                                                                                                                                | 结果                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| T05 前端全量          | `npx vitest run --coverage --coverage.reporter=json --coverage.reporter=text --coverage.reportsDirectory=C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/frontend`  | 0；21 文件、96 tests；配置范围内 lines 96.86%、branches 86.11%、functions 93.89%    |
| T05 前端关键          | `node scripts/critical-coverage.mjs --frontend C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/frontend/coverage-final.json`                                        | 0；四组通过，但不消除 R1-01/R1-02                                                   |
| T05 后端全量          | 在 backend 执行 `python -m pytest --cov=app --cov-branch --cov-report=json:C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/t05-backend.json -q`                     | 0；119 passed，101.75 秒；118 个既有 SQLite FK-drop-order warning；覆盖率见 R1-03   |
| T05 后端关键          | `node scripts/critical-coverage.mjs --backend C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/t05-backend.json`                                                     | 1；learning 行门槛失败                                                              |
| T05 checker 自测/负例 | `node scripts/critical-coverage.mjs --self-test`；真实 CLI 临时报表探针                                                                                                   | 自测 0；缺 covered 的真实负例错误退出 0，其余结果见 R1-01                           |
| T05 API E2E           | `E2E_API_PORT=18341`、`E2E_H5_PORT=41941` 下 `npm run test:e2e -- --output=C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/e2e-api`                                 | 0；8 passed，20.3 秒；包含 Windows 当前截图基线，不等于 Linux 验证                  |
| T05 Demo E2E          | `E2E_DEMO_H5_PORT=41942` 下 `npm run test:e2e:demo -- --output=C:/Users/adj/AppData/Local/Temp/wx-s3-review-uqh6nqhc/e2e-demo`                                            | 0；1 passed，5.7 秒；未发 API 请求                                                  |
| T06 安全回归          | 在 backend 执行 `python -m pytest tests/test_t06_security.py tests/test_auth.py tests/test_second_phase.py tests/test_access_control.py tests/test_database_safety.py -q` | 0；29 passed，51.17 秒；28 个既有 SQLite warning                                    |
| T06 秘密扫描          | `node scripts/security-secrets.mjs --self-test`、`--scope=worktree`；分别带 `--scope=build --build-dir dist/build/h5` 和 `dist/build/mp-weixin`                           | 全部 0；自测发现 1 个合成样本；工作树与两个现存构建目录 findings=0。本轮未重新构建  |
| T05/T06 Ruff          | 对各自修改的 Python 文件执行 `python -m ruff check <明确文件清单>`                                                                                                        | 各 0                                                                                |
| T05/T06 最终 Markdown | 限定文件 `prettier --check`                                                                                                                                               | 各 1；见 R1-05                                                                      |
| T07 文档/skill        | 13 个目标 Markdown 格式/本地链接；`python .agents/skills/wx-engineering-standards/scripts/self_check.py`；`git diff --check`                                              | 各 0；无失效相对链接                                                                |
| T07 后端边界自测      | `python backend/scripts/check_boundaries.py --self-test`                                                                                                                  | 0；20 项正负探针                                                                    |
| T07 前端边界          | 候选缺本地 TS 依赖；逐字节确认其前端源码、边界脚本与配置均同主工作区，在主工作区直接执行 self-test 与正式脚本                                                             | 各 0；26 个定向负例、117 个实现文件。这是同源码跨工作树复验，不宣称候选完成独立安装 |

一次扫描调用遗漏必需的 `--build-dir`，按设计退出 2；随后用上述两个显式目录重跑通过。没有忽略该错误。T05-final 原先“本轮没有 E2E”的证据缺口已由本次统筹复验补充，后续改动仍须按影响重跑。

## 安全、合同与验证限制

- 所有后端测试复用 T01 的导入前隔离 fixture，E2E 使用其 launcher-owned 随机临时 SQLite；没有对开发/共享/生产库清表、迁移或 seed。E2E 内的迁移只作用于其新建受管临时库。
- T05 空 choices 修复保持 fallback；T06 统一 production 大小写/空白判定，防止启动 seed 错把生产当作开发。没有发现这两处增量引入新的 HTTP/schema、数据库或 API/Demo 合同变化；本轮未重生成或重跑契约链，因为源 schema/路由及三个生成物指纹均未改。
- 本轮没有真实 AI/微信调用、凭据撤销/轮换、历史重写、依赖升级或远程平台操作。历史三条凭据发现沿用已交付记录；本次没有重新运行 history 扫描或依赖审计，不能把历史/昨日审计当成本轮新证据。
- 没有做 T05 计划要求的全部业务守卫故障注入、逐场景最新测试映射和连续两轮最终全绿；这些仍须由执行者补齐。T07 的阶段文档可以接收，但等 T05/T06/T02 命令与事实稳定后还须同步，不将当前直接脚本描述成已有 npm alias。
- 生产仍阻断于历史凭据处置、报告 `submitted_global` 政策决定、生产配置/备份、远程 CI/分支保护、目标工具链、微信真机/域名、真实服务与医学/供应商证据。本地代码接收不解除这些条件。

## 下一步返修与接收顺序

1. **T05 保持一个领域任务返修**：修 R1-01 校验器和真实自测，完善 R1-02 前端统计范围，补 R1-03/R1-04 后端行为及独立阈值；补具体测试名映射和必要故障注入。最后修交付格式并冻结 hash。保持 Terra High，不另拆多个小计划；package/lock/CI 仍交 T02。
2. **T06 限定收尾**：修 R1-05 格式，回传最终指纹；安全代码无本轮发现的功能返修项。外部阻断保持事实状态，不用白名单隐藏历史凭据。
3. **T07 等待最终事实**：当前候选可用于后续集成；T05/T06/T02 收敛后，由其统一更新真实命令、覆盖率适用范围和发布阻断。无需因纯文档重新跑数据库迁移。
4. **T02 暂缓最终接线**：待关键门禁本身不会错误放行、完整/关键覆盖率达标、交付格式通过后再启动共享文件修改。必须先形成包含三项增量的受保护组合候选，再运行组合回归；各 Worktree 独立通过不能替代组合验收。

以上是本轮审核给出的返修标准，**尚未在本轮发送执行消息或启动返修**。本次没有接收代码到主工作区。

## 统筹记录回退

本轮只新增本文并更新 `execution-status.md` 审核索引。该文件修改前原像在外部证据目录的 `execution-status.preimage.md`，SHA-256 为 `AA9828C406E11B8362CAC6A03E0A2D9727EAE207D5A9AEB44A24417422AB2E00`。后续如需回退，先确认没有他人接续修改，仅反转本轮文档差异；不得据此覆盖任何执行者的代码或恢复已删除旧文档。
