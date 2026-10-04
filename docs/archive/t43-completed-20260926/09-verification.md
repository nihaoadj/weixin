# 09 验证矩阵

状态：A01–A27 验收矩阵尚未整体通过；当前缺口与执行顺序见[第11册](11-remaining-work-handoff.md)，命令与退出码见[实施进度](deliveries/implementation-progress.md)。本册下方带日期的结果是历史快照，不能覆盖第11册的当前状态。单层通过不得将整组写为 Pass。

2026-09-25 工具状态更正：此前 doctor 失败是 Codex 执行进程未设置 `WECHATIDE_CLI_PATH`，不是工具未安装。使用 `D:\codeapp\微信web开发者工具\wechatide.cmd` 后，打开/复用项目窗口、模拟器刷新、doctor 均通过（SDK `3.16.3`）；学生身份入口 tap 也成功。该证据只关闭工具连接/启动问题，不代表 T43 学生任务包或教师报告流程已完成实际交互验收。

## 2026-09-24 历史复核快照（已被 2026-09-25 续跑结果取代）

以下只更新仓库内复验状态，不代表 A01–A24 端到端全通过：最近完整 `npm run backend:check` 的 Ruff 与 pytest 退出 0，315 passed、88.26% 覆盖率，达到 85% 门槛；随后新增一个病例边界用例且定向 pytest 通过，但暂停时全量后端复跑被中断，当前完整结果应在续工时重跑。最新 `npm test -- --run` 72 files / 355 passed；`npm run test:coverage` 的 72 files / 355 tests 全通过，但命令退出 1，因为全局 lines/statements 60.46%、functions 60.30%（要求 85%），branches 77.62%（要求 80%）；`npm run backend:test:safety` 14 passed；`npm run backend:test:migrations` 22 passed；`npm run lint`、`npm run type-check`、前后端边界、`npm run contract:check`、`npm run build:mp-weixin` 均退出 0。T43 定向前端覆盖病例目标维度缺失/临时读取错误重放的测试文件 3 tests passed；后端病例完成但同轮其他 active 任务仍未完成的 API 测试 1 passed；最终报告 builder 故障回滚/同请求重试用例此前定向通过。具体时间、警告和边界见[实施进度记录](deliveries/implementation-progress.md)。`npm run security:secrets` 退出 1，结果只列 `miniprogram/pages/student/chat/` 历史范围的 3 项 `generic-api-key` 指纹，本轮未读取/编辑这些历史源码；责任人复核前该门禁保持 Fail。

### 2026-09-25 收尾续跑结果

用户要求本次暂时收尾后，`npm run backend:check` 已安全中止：Ruff 通过，pytest 汇总前 Ctrl-C，退出码 1；没有可报告的全量测试数或 coverage。明日从全量后端检查重新开始。其他 2026-09-24 快照仍是最近完整证据，不应误读为包含 2026-09-24 后新增的病例边界用例。

Demo watcher 在最后代码变更后重新以显式 `VITE_APP_MODE=demo` 启动成功，并输出 `Build complete. Watching for changes...`；生产目录 `npm run build:mp-weixin` 退出 0。`npm run test:mp:doctor` 因缺少 `WECHATIDE_CLI_PATH` 退出 1，按根规则限定的常见安装根只读搜索未发现 `wechatide.cmd`，且当前会话无 Developer Tools 内部交互/截图工具。因此本轮没有执行规定目录内普通编译后的真实 tap/input/scroll，也没有截图审阅；小程序交互与渲染均为 **Unverified**，不能将 watcher/build 视为通过。`python backend/scripts/transition_t43_packages.py --database .\unopened-t43-fixture.sqlite --apply` 在连接文件前按策略拒绝并退出非零；没有创建或迁移数据库。真实 Coze、医学审核签署、受管开发库备份恢复、PostgreSQL/生产与真机同样未验收。历史迁移按第07册只读审计策略，不属于待转换项。

### 2026-09-25 继续实施复核

此结果取代上面的“续工必须重跑”状态；上段保留为真实历史中断记录。全量 `npm run backend:check` 现已退出 0：Ruff 通过，316 passed，backend coverage 88.26%。`npm run test:coverage` 退出 1，78 个测试文件/371 项均通过，但全局 coverage 为 lines/statements 66.63%、functions 60.20%、branches 76.45%，低于仓库 85%/85%/80% 门槛。`npm run lint`、`npm run type-check`、`node scripts/frontend-boundaries.mjs` 和 `git diff --check` 退出 0。新增 6 个前端行为测试文件共 16 项断言通过，覆盖整包审阅/发布、题库筛选竞态及副本生命周期、v7/v6 路由、课堂进度与报告返回、学生任务包分组/提交后统一报告、学情详情范围与分页。筛选竞态测试先复现缺陷，再确认修复后旧响应不会覆盖新筛选状态。

`npm run contract:check` 与 `npm run build:mp-weixin` 在本轮前已对最后一次运行时代码变更通过；本轮其后仅新增测试与文档，不改 OpenAPI/schema 或运行时代码。显式 Demo watcher 持续运行且见到 `Build complete. Watching for changes...`，但没有可用的微信开发者工具 CLI/内部交互通道，未执行指定开发目录普通编译、tap/input/scroll 或内部截图，页面渲染验收仍 **Unverified**。安全扫描仍有 3 个历史指纹等待责任人复核。未应用迁移或连接受管/真实数据库，未调用真实 Coze，医学专家、PostgreSQL/生产与真机验收均未做。全量命令、退出码和解除条件见[实施进度记录](deliveries/implementation-progress.md)。

### 2026-09-25 后续：病例资源目标与来源绑定

本轮后端只改评分资源安全与草稿保存逻辑，不改 HTTP DTO、OpenAPI、数据库 schema 或页面。新增断言覆盖：审核 digest 随 knowledge link 变化；无关联目标的病例不得出现在 focused_retry/micro_drill 资源列表或经 PUT 绑定；同目标但非诊断 session 绑定的另一病例也拒绝；正确病例返回完整两轮。微训练 PUT 保存审核蓝图中的 objective/options/criteria，客户端不能替代 rubric。

| 命令                                                         | 退出码 | 结果                                     |
| ------------------------------------------------------------ | -----: | ---------------------------------------- |
| `npm run backend:test:safety`                                |      0 | 14 passed。                              |
| `npm run backend:test:migrations`                            |      0 | 22 passed；没有应用到真实数据库。        |
| `npm run backend:test -- tests/test_t43_package_draft.py -q` |      0 | 14 passed。                              |
| `npm run backend:check`                                      |      0 | Ruff 通过；318 passed，coverage 88.70%。 |

旧审核 digest 不含节点关系，现保留原始行但 fail closed，新的课堂评分用途需正式复审；未自动重签。前端上次全量 coverage 83 files/411 tests 全通过但 gate exit 1（71.44%/60.71%/76.51%）；DevTools CLI、开发目录普通编译/真实交互/截图、安全历史指纹复核、受管库演练及 Coze/医学专家/生产/真机仍未验收。当前 Demo 没有可复验的微训练资源选择 fixture，A23/W1/W3 保持开放。

### 2026-09-25 后续：Demo 推理微训练

Demo 90004 增加两轮合成推理蓝图，教师资源查询/保存保留审核 rubric；学生用文本完成微训练，未满足 70 分时只激活该目标第二轮，第二轮完成后与病例目标一起形成课堂终态报告。未改 API DTO、OpenAPI、数据库或迁移。`npx vitest run src/features/learning/infrastructure/demoLearningRepository.classroomPackages.spec.ts` 退出 0（3 tests passed）。本次未运行全量前端 coverage；Developer Tools 普通编译与实际交互仍待 `WECHATIDE_CLI_PATH` 可用后按最小路径验收，Demo 的合成评分不能证明真实医学审核。

## 测试场景

| 编号 | 场景                    | 必须断言                                                                                                                          |
| ---- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| A01  | 同学生同课堂多候选      | 一包一plan，多项任务；不同课堂同节点不合并                                                                                        |
| A02  | 发布双击/并发/超时重试  | 同键同payload同回执，异payload409，无重复通知                                                                                     |
| A03  | 编辑与发布并发          | 版本/摘要冲突409，发布内容等于教师确认版本                                                                                        |
| A04  | 发布后修改/增加任务     | 全部拒绝；题库修改不影响冻结包                                                                                                    |
| A05  | 目标覆盖缺失            | 缺目标或第二轮变式不能发布                                                                                                        |
| A06  | 无薄弱点                | 证据充分可完成，验证题覆盖目标，无虚构finding/补充卡                                                                              |
| A07  | AI失败/越界/私人续问    | 无虚假诊断/任务/报告/教师可见事件                                                                                                 |
| A08  | 未发布/首轮部分完成     | 逐学生列表能筛选、分页、返回；巩固无最终报告，逾期不记0；终态缺报告明确标记且不可进入假详情                                       |
| A09  | 首轮全部通过            | 一份improved报告，第二轮inactive不影响完成                                                                                        |
| A10  | 首轮失败后二轮通过/失败 | 只激活失败目标；最终分别improved/needs_reinforcement                                                                              |
| A11  | 病例回调失败重试        | assessment不重复，任务最终只完成一次，不递归建计划                                                                                |
| A12  | 独立病例                | 学生反馈保留，不产生教师报告/正式待办/结果统计                                                                                    |
| A13  | 统计去重与日期          | 只计已完成 T43 最终报告；上海边界、空窗、同目标多题不重复计数；旧计划和独立病例排除                                               |
| A14  | 权限                    | 篡改student/class/session/package/report/bank ID均不越权；学生无答案泄漏                                                          |
| A15  | 私人内容                | teacher DTO/报告/题库无私人续问、原始回答及其他学生诊断                                                                           |
| A16  | 题库入库编辑归档        | 仅教师动作、同源幂等、本人隔离、版本不覆盖、归档不删历史                                                                          |
| A17  | 医学审核                | 教学确认不等于批准，摘要改变失效，专家权限不可提升为班级权限                                                                      |
| A18  | 历史迁移                | 空升级降级、非空拒降级；历史审计重复运行结果稳定且零写入；`--apply` 在打开数据库前拒绝，不执行转换或备份恢复                      |
| A19  | 历史缺失/多计划         | 跳过转换、明确历史标识，不伪造0分或新报告                                                                                         |
| A20  | 班级归档/退出           | 停止新发布，既发任务本人可完成，原班有权教师可查历史                                                                              |
| A21  | 缓存与角色切换          | 旧GET不覆盖新用户/新班级，写后列表和统计刷新                                                                                      |
| A22  | 学情/PBL/内容导航       | 综合回学情，本课报告回PBL，题库回内容，旧深链可恢复                                                                               |
| A23  | API/Demo                | 同状态/字段/幂等规则，含任务顺序及 discussion 仅记证据、不计分的终态判定；API失败不回退Demo                                       |
| A24  | 故障注入                | 最终报告生成异常回滚该完成事务；病例外部已存事实可幂等重放                                                                        |
| A25  | 排除可选候选            | 完整两轮一并排除，来源行/题库外键保留；过期审核引用不阻塞排除，新绑定不落库，重新纳入再校验；仅 included 项进入医学提交与发布计划 |
| A26  | 目标覆盖边界            | 移除目标最后一组 retest/micro_drill 被拒绝；cycle 1/2 inclusion 不一致被拒绝                                                      |
| A27  | 恢复候选                | 草稿恢复原 pair 会递增版本、更新摘要并要求重新确认；已发布后恢复/编辑被拒绝                                                       |

## 此前局部测试记录（历史证据，由上方 2026-09-24 当前复核快照更新）

此前 `python -m pytest backend/tests/test_t43_classroom_case_callback.py::test_classroom_case_five_stage_api_completes_one_final_report -q` 退出 0、1 passed，只记录 A11 的一个正向 HTTP 子路径为部分证据，不足以关闭 A09/A10/A11/A24。更早的后端 309 项和前端 345 项全量结果也已被上方当前复核快照中的 314/353 结果更新。保留本段用于说明局部测试曾覆盖的范围，不得将其当作最新全量状态。

## 仓库内命令

补充合同断言：v7自主研讨无课堂目标也能合法完成且不创建教师资源；同candidate_key重试得到相同stable_key；发布确认记录与发布版本一致；analytics schema_version=2且旧病例端点拒绝结果查询；教学反馈省略不生成空记录。上述分别并入A07、A02、A03、A13和A02执行。

以下命令为实施者的验证路线，不表示均已运行。实际执行与退出码只以阶段交付记录为准；从根目录按阶段执行并记录实际时间/退出码：

- npm run lint
- npm run type-check
- npm test
- npm run test:coverage
- node scripts/frontend-boundaries.mjs
- python backend/scripts/check_boundaries.py
- npm run backend:test:safety
- npm run backend:test:migrations
- npm run backend:test
- npm run backend:check
- npm run contract:generate（有意写生成物后审查差异）
- npm run contract:check
- npm run build:mp-weixin
- npm run security:secrets

格式检查只针对本次范围，避免格式化他人变更。定向pytest通过仓库受管fixture入口运行，禁止直接使用未知engine。全量失败须列出失败项、基线证据和影响，不能以“旧失败”直接声明全量通过。

## Demo 与开发者工具

使用 [微信验收规范](../../wechat.md)。显式设置VITE_APP_MODE=demo后运行npm run dev:mp-weixin，保持到Build complete. Watching for changes...，仅加载D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin。wechatide.cmd打开项目并simulator_refresh普通编译，test:mp:doctor获取SDKVersion。

顺序完成：教师诊断打开 → 编辑首/二轮 → 保存 → 入库 → 题库编辑归档 → 返回发布 → 学生学习一课堂一条 → 完成首轮与必要第二轮 → 教师课堂进度 → 巩固报告 → 学情学生综合 → 返回保持筛选。另用独立Demo账号/种子走无薄弱点与首轮达标。测试fixture预置状态可以用于不同场景，不能通过setData或业务方法冒充步骤内用户操作。

实际审阅：长标题、两轮长题、错误重试、空题库/无报告、窄屏和默认宽度、键盘输入、滚动到底、固定栏与返回。截图仅simulator_screenshot内部通道，同页同状态一张代表图，必要上下区域或新状态另取，逐张记录审阅结论。不能运行系统鼠标键盘或旧App.* WebSocket。

## 接收标准

逻辑测试、小程序构建、工具连接、真实交互和渲染分别记录。跨模块闭环不得只有静态字符串断言。需要真实交互但选择器无法定位，记录失败步骤和解除条件；真实登录、Coze、医学签署、PostgreSQL、生产和真机仍属于外部待验收，不能以Demo代替。

## 2026-09-25 后续页面复核（局部证据，不关闭矩阵）

又运行全部 12 个 T43 后端专项测试文件，52 passed（51 项 SQLAlchemy FK 排序警告）；之前 7 文件/36 passed 是先行子集结果。6 个 Demo/API feature adapter 文件另有 13 项通过。学生任务与教师学情详情两个页面行为文件共 8 项通过。新测复验提交不确定后的冻结 payload/同请求标识重试、刷新后允许安全修改、日期范围切换后丢弃旧分页结果，以及教师身份切换后清除旧详情并舍弃旧请求。`npm run lint`、`npm run type-check`、前端边界检查（203 implementation files）和 `git diff --check` 退出 0。此后又运行全量前端 `npm run test:coverage`：78 files / 375 tests 全通过，但 coverage gate 退出 1（lines/statements 66.71%、functions 60.41%、branches 76.53%，门槛 85%/85%/80%），不得调低门槛。后端仅 T43 专项定向复测，未重新运行完整 `backend:check`。

最新显式 Demo watcher 完成 `dist/dev/mp-weixin` 编译，产物包含新任务恢复动作和教师会话校验/账号变更阻断逻辑；`npm run test:mp:doctor` 退出 1，因未配置 `WECHATIDE_CLI_PATH`。没有开发者工具普通编译、tap/input/scroll 或内部截图，相关可见行为仍 Unverified。仅有编译产物检查不等于页面呈现验收。其他角色切换、全局矩阵、API/Demo 同态与外部条件仍按第11册未关闭项处理。

## 2026-09-25 续跑：题库身份隔离与最终前端复测（局部证据）

题库页面行为测试确认：教师角色守卫拒绝时列表/详情不触发 API；详情页教师账号切换时清空旧数据、使旧 GET 回包失效。配合课堂包提交恢复、学情日期分页竞态与身份变更用例，三个页面行为文件共 14 项通过。此证据只覆盖这些交互断言，不关闭 A16/A21 全矩阵。

最新完整前端 Vitest：78 files / 377 tests passed；`npm run test:coverage` 仍以 exit 1 结束，lines/statements 66.77%、functions 60.47%、branches 76.61%，未达到 85%/85%/80%。Lint、type-check、frontend-boundaries、`contract:check`、微信生产构建均 exit 0。显式 Demo watcher 生成 `dist/dev/mp-weixin` 并检查对应 WXJS 中的提交恢复及身份阻断文案；`test:mp:doctor` exit 1（未配置 `WECHATIDE_CLI_PATH`），因此没有普通编译后的真实 tap/input/scroll、页面渲染审阅或 DevTools 截图。不得把 WXML/WXJS 产物检查记为可见交互通过。

后台/外部仍待办：A01–A24 按层闭环证据、前端全局 coverage 门槛、历史 secret-scan 指纹由安全责任人复核、受管非生产开发库的报告修复 dry-run/备份恢复、真实 Coze/医学专家/PostgreSQL/生产/真机。

同日再运行 `npm run security:secrets` 仍 exit 1，只有 `miniprogram/pages/student/chat/` 的 3 个历史 `generic-api-key` 指纹；未读取/输出匹配值，也未更改文件。它仍是安全门禁未关闭项，需责任人复核。

## 2026-09-25 续跑：T43 API adapter 合同测试与全量覆盖率

新增/扩展三个 learning adapter 测试文件，17 项通过，覆盖教师整包状态/双轮资源、草稿保存、医学提交、发布幂等字段、题库来源、学生包/稳定提交/病例上下文和终态报告冻结字段；教师报告 adapter 覆盖 owned class/session/student query、分页与身份不一致拒绝。全量 Vitest 79 files / 390 tests 均通过。

该次全量 `npm run test:coverage` exit 1：lines/statements 68.11%、functions 61.71%、branches 76.90%，要求为 85%/85%/80%。`coverage/lcov.info` 显示两个 T43 核心 adapter：`classroomPackages.ts` 99.28% lines / 100% functions / 90.91% branches，`classroomFinalReports.ts` 100% / 100% / 100%。单文件进步不能替代全局门禁。

Lint 与 type-check 在新增测试后均 exit 0。此增量只有测试文件变更，无需据此重做 API contract、生产构建或 Demo 编译；之前同运行时代码的 contract/build/Demo 证据仍有效。

## 2026-09-25 后续续跑：教师整包审阅异步上下文隔离

在教师诊断详情切换课堂期间，已发起但尚未完成的旧请求不得将另一位学生/课堂的包内容、失败信息、忙碌状态或题库操作提示写入当前页面。组件现以诊断快照/会话/学生/班级变更递增页面代次，另外以任务包 ID、版本和 digest 校验保存、取回最新版、医学提交、发布、题库预览/入库的延迟响应。服务端已受理的题库写入不可客户端取消，但切换上下文后不显示旧操作完成提示，也不改当前页面。

| 命令                                                                                                                                                                  |                     退出码 | 结果                                                                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------: | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `npx vitest run src/components/teacher/TeacherClassroomPackageReview.behavior.spec.ts src/pages/teacher/pbl-diagnostic-detail/pbl-diagnostic-detail.behavior.spec.ts` |                          0 | 2 files / 13 tests passed；教师整包审阅 11 项，诊断路由 2 项。新增用例曾在旧实现下复现 5 种陈旧保存/刷新/审核/发布响应污染。                 |
| `npm run test:coverage`                                                                                                                                               |                          1 | 79 files / 397 tests 全通过；lines/statements 68.38%、functions 62.12%、branches 76.93%，未达 85%/85%/80% 全局门槛。                         |
| `npm run lint` / `npm run type-check` / `node scripts/frontend-boundaries.mjs`                                                                                        |                  0 / 0 / 0 | ESLint、Vue/TypeScript、203 个前端实现文件边界检查通过。                                                                                     |
| `npx --no-install prettier --check src/components/teacher/TeacherClassroomPackageReview.vue src/components/teacher/TeacherClassroomPackageReview.behavior.spec.ts`    |                          0 | 本次组件与行为测试格式通过。                                                                                                                 |
| `npm run build:mp-weixin`                                                                                                                                             |                          0 | 生产构建通过；未作为 DevTools 可见验收。                                                                                                     |
| `$env:VITE_APP_MODE='demo'; npm run dev:mp-weixin`                                                                                                                    | watcher 构建成功，随后停止 | 明确 Demo 模式，`dist/dev/mp-weixin` 输出 `Build complete. Watching for changes...`；仅检查生成组件中出现当前任务包身份校验，不手改 `dist`。 |
| `npm run test:mp:doctor`                                                                                                                                              |                          1 | 缺少 `WECHATIDE_CLI_PATH`；没有 DevTools 普通编译、真实 tap/input/scroll、渲染截图审阅。                                                     |

本增量没有改变 API/schema/迁移、权限或业务统计口径。完整 W8 仍开放：A01–A24 全链路和 API/Demo 同态未整体验收；coverage、安全历史指纹责任人复核、真实受管非生产库报告修复演练、真实 Coze/医学专家/PostgreSQL/生产/真机均未关闭。本次页面改动的 Demo 可编译，但 DevTools 页面交互为 **Unverified**，不能称小程序页面验收通过。

## 2026-09-25 最新续跑：教师工作区及报告入口身份隔离

继续按 W5 复核发现教师账号变化/教师权限失效时，工作区可能缓存上一账号班级与待办；PBL 诊断、课堂进度和单课报告路由也可能在 `requireRole` 拒绝后继续显示上一身份内容。现工作区按教师 `openid` 重置班级/待办和懒加载子页，并以请求代次阻止旧账号响应回写；权限失效时隐藏工作区。诊断、进度、报告页面拒绝访问时清空学生/报告/任务数据并递增请求代次，迟到成功/失败不再更新页面。整包审阅组件在上下文切换或卸载时同样作废待处理请求。发布确认弹窗现在逐项列出目标学生、课堂、首/二轮数量与第二轮条件、版本和完整摘要校验值。题库写请求已由教师明确确认并送达服务器后不能客户端取消；页面切换只抑制其陈旧 UI 回执，不回滚教师个人题库写入。

五个受影响页面行为套件共 23 项通过：`TeacherClassroomPackageReview` 12、教师工作区身份边界 2、诊断详情路由 3、课堂进度 4、单课报告路由 2。全量 `npm run test:coverage` 为 81 files / 405 tests 全通过，但 exit 1：lines/statements 69.90%、functions 61.24%、branches 76.63%，低于固定 85%/85%/80% 门槛。Lint、type-check、203 implementation files 边界、定向测试和 Prettier 通过；`npm run build:mp-weixin` exit 0。显式 Demo watcher 编译成功，编译产物可见教师失权提示和整包身份校验；`npm run test:mp:doctor` exit 1（未配置 `WECHATIDE_CLI_PATH`），无 DevTools 普通编译、tap/input/scroll 或内部截图。未修改 API/OpenAPI、schema、迁移或后端；没有访问真实数据库或 Coze。T43 端到端 A01–A24、全局 coverage、安全责任人、受管非生产数据库演练、真实服务/专家/生产/真机仍为未关闭项。

## 2026-09-25 续跑：学生端身份上下文隔离

W4/W5 学生流程复核发现学生账号/角色变化时，学习首页、课堂包详情、病例训练和学生病例分析页有保留旧身份状态或接收迟到异步回包的风险。现在四页均检查当前 session `openid + role`；变化/失权即清空任务、回答、病例/分析内容和相关加载/操作状态，递增页面上下文代次，后续旧请求成功/失败不会更新页面、导航或报告入口。病例分析继续限定为学生个人反馈，课堂任务包最终报告仍只由包终态加载。

新增/扩展四个页面行为套件共 12 项通过，实际用例包含账号切换后的旧课堂包 GET、病例 GET、病例分析 GET 与任务提交回包。全量 `npm run test:coverage` 为 83 files / 411 tests 全部通过，但退出 1：lines/statements 71.44%、functions 60.71%、branches 76.51%，仍低于 85%/85%/80% 门槛。`npm run lint`、`npm run type-check`、`node scripts/frontend-boundaries.mjs` 均 exit 0；`npm run build:mp-weixin` exit 0。显式 Demo watcher 已输出 `Build complete. Watching for changes...`，生成目录包含四个学生页面身份变化状态。`npm run test:mp:doctor` exit 1（缺少 `WECHATIDE_CLI_PATH`）；故 DevTools 普通编译、真实 tap/input/scroll、可见状态审阅与截图均 Unverified。本轮无 API/backend/schema/迁移变更，后端/contract 未重跑。

因此 A21 仅增加学生关键路径的仓库行为证据，不关闭角色/缓存完整矩阵；A22 的页面真实导航与返回交互也仍 Unverified。A01–A24 其余跨层场景、coverage gate、安全责任人复核、受管非生产库演练、真实 Coze/授权医学审核/PostgreSQL/生产/真机仍开放。
