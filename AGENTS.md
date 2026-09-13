# 项目协作约束

## T24 微信单端迁移与前端验收优先级

T01–T25 已收缩为 [阶段概述](docs/update_plan/01-25-summary.md)。微信小程序是唯一产品目标；T25 已按用户授权直接删除 H5 构建、Playwright 与 H5 专属实现。未完成的小程序验证必须保留为待验收项，历史 H5 证据也不得转换为小程序证据。后续功能性更新从 T26 开始。

小程序构建、逻辑测试、开发者工具交互测试、实际渲染审阅必须分别报告。H5 全绿、组件 DOM 测试、SDK 连接成功、页面 data 正确或截图文件存在，都不能证明小程序页面渲染通过。每项可见变更必须在正确 Demo 开发目录完成普通编译，检查**受影响页面与最小相关流程**的实际文字/控件可见性、滚动、固定栏、遮挡、长内容、空/错误状态及相关点击输入返回流程，并检查本次截图。不得因一次局部修改自动重跑全站、跨角色或完整 PBL 回归；全量核心回归仅在发布候选、跨模块/共享导航或构建改动、用户明确要求，或已有证据表明局部影响已外溢时执行。环境缺失、未登录、基础库未就绪或未覆盖状态记为失败/待验收，不得静默跳过。开发者工具自动化不能通过直接修改 data 或调用业务方法冒充用户操作。

工具自动化仅允许本地受控开发项目，不清理工具数据、不关闭安全校验、不记录原始 console/data/请求响应中的敏感内容。真实微信登录、API 授权、AI 与 Demo 证据分别记录。用户要求本次暂不执行真机验证；结论限定为开发者工具环境，不声称真实设备或生产已验证。后续发布仍按发布条件处理。

## T22 已批准的教师工作区职责调整

用户已批准 T22：教师一级导航继续为“待办、学情、内容、PBL”；PBL 诊断建议以“内容”为唯一列表入口，PBL 正式任务结果与补充反馈以“学情”为唯一列表入口，PBL 工作区只保留课堂创建、运行、关闭和逐学生阶段看板。“内容”默认诊断建议，“学情”默认 PBL 跟进；旧 PBL section 与独立 analytics 路径兼容跳转但不再渲染重复页面。T22 只覆盖 T21 的页面归属，不改变固定诊断快照、形成性反馈、同一操作反馈并发布、两轮正式任务、系统自动判定、权限和隐私边界。阶段事实见 [T01–T25 概述](docs/update_plan/01-25-summary.md)；微信真机、真实教学和生产环境仍未验证。

## T21 已批准的教师 PBL 闭环目标

用户已批准 T21：教师 PBL 工作区重组为“待处理、课堂、跟进”，教师可向学生发送形成性反馈，并可在同一明确操作中反馈并发布正式任务；学生主动提交继续使用固定摘要快照，不向教师开放未提交自主研讨、完整聊天或未审核个人练习。T21 不增加师生实时聊天，正式题仍须教师采用发布，系统自动判定仍按 T14 执行。阶段事实和待验收项见 [T01–T25 概述](docs/update_plan/01-25-summary.md)。

## T20 已批准的产品规则调整

用户已批准 T20：自主研讨默认私有且可无班级创建，四阶段完成后由学生预览并提交一个有效班级；课堂仍按原规则对教师可见。未审核 AI 题允许学生个人练习，必须明确标记、服务端校验并独立保存，不计正式成绩、知识点稳定状态或 T14 正式达标；正式题仍须教师采用发布。此例外优先于下文将所有自主诊断自动送教师及禁止任何未审核练习的旧表述。阶段事实和待验收项见 [T01–T25 概述](docs/update_plan/01-25-summary.md)。

本文件是本仓库人和自动化代理的最小工程约束。它只描述当前已核实的边界和检查路由；计划中的目录、命令或流程不得当作已经落地。

## 先读什么

- 总体规则、任务阶段与交付格式：[docs/update_plan/README.md](docs/update_plan/README.md)。该目录是计划和证据索引，不是当前实现的替代说明。
- 当前架构和目录边界：[docs/architecture.md](docs/architecture.md)。
- 数据访问、API/Demo、契约、缓存和错误边界：[docs/data-layer.md](docs/data-layer.md)。
- 开发命令与现有说明：[docs/operations/development.md](docs/operations/development.md)。其中与测试安全、路径或命令有关的旧说明须以本文件的“当前安全前置条件”和 T01/T02 后续事实更新为准。
- 数据库及迁移限制：[docs/backend/database.md](docs/backend/database.md)。
- 权限、敏感数据、AI 与凭据处置：[docs/governance/security.md](docs/governance/security.md)。
- 环境和发布条件：[docs/operations/deployment.md](docs/operations/deployment.md)。
- 重大数据层取舍：[docs/adr/0001-data-layer-contracts.md](docs/adr/0001-data-layer-contracts.md)。
- 已归档的 T01–T25 产品、工程和验证阶段概述：[docs/update_plan/01-25-summary.md](docs/update_plan/01-25-summary.md)。

改动涉及的领域要先阅读对应权威文档，而不是一次复制整套文档。目录内新增局部 `AGENTS.md` 仅能补充确有差异的规则，不能放宽本文件。

## 更新分流：功能性代码变更与直接维护

只有会**实质改变运行时代码功能或工程运行边界**的更新，才必须先写 UpdatePlan 再修改代码。工程规则、文档和不改变既有功能的小型维护不应为了流程而新建计划目录。

### 功能性代码变更：先计划、后实施

以下任一情况属于功能性代码变更，必须按以下顺序执行；不得先改运行时代码再补计划：

- 新增、删除或改变用户可完成的业务流程、领域规则、可持久化状态、错误恢复语义或跨页面导航结果。
- 改动 API/schema、公开模块接口、`src/bootstrap/wiring.ts`、API/Demo 分界、数据读写、缓存/会话、授权或数据范围。
- 改动数据库、迁移、生成契约、AI 提供方/合同、凭据或敏感数据处理。
- 结构性重构、依赖、构建或 CI 改动会改变应用运行行为、模块边界或发布/验证边界。

1. **核查当前事实**：阅读本文件和相关权威文档，执行只读 `git status`，记录当前分支、既有未提交改动、公开接口、API/Demo、权限、数据、迁移、AI 和生成物影响。
2. **建立 UpdatePlan**：在 `docs/update_plan/` 下按 `NN-short-name/` 新建或更新本次更新的独立目录；至少写明当前事实、目标与非目标、接口/数据/模块设计、实施顺序、测试验收、外部阻塞和回退。大型更新还须提供 `deliveries/template.md`。
3. **计划门禁**：对 UpdatePlan 执行格式、相对链接、尾随空白及工程 skill self-check。计划必须区分“已核实事实”和“待实现目标”，且足以让执行者无需自行补产品或架构决策。
4. **按计划实施**：只有计划门禁通过后才能修改运行时代码；按文档顺序逐项实施，保持模块公开边界、API/Demo 隔离、生成契约流程、权限与敏感数据约束。发现会改变既定范围的新事实时，先修订 UpdatePlan 再继续。
5. **分阶段验证**：每完成一个阶段，运行与风险匹配的最小检查；API/schema、模型/迁移、AI、身份或跨模块改动必须执行对应的契约、数据库安全、迁移、权限和边界测试。不得以跳过或降级门禁伪造通过。
6. **交付与提交**：在 UpdatePlan 的 `deliveries/` 中记录命令、时间、退出码、未执行项、风险和回退。提交前检查暂存范围、秘密和生成物；只有用户明确授权才可提交或推送。提交不能把“仓库内完成”误写为“真实外部服务或生产已验证”。

如果发现已经存在本应走本流程的**功能性代码**，只能先创建补充 UpdatePlan 和当前差距审计，再继续修改；补写计划不能倒推为先前实现已通过门禁。

### 直接维护：无需 UpdatePlan

下列正常小更新可直接实施，不建 UpdatePlan、不做计划门禁、不写 `deliveries/`：

- 纯 Markdown、计划/交付记录、`AGENTS.md`、项目 Skill、注释、链接、格式或措辞更新。
- 不改变业务流程、状态、数据、路由结果、公开接口或 API/Demo 行为的局部样式、文案、可访问性、布局、默认视觉选中项和展示层修复。
- 不影响应用运行行为的测试文字/断言整理、类型/格式整理、开发工具配置或脚本维护。

直接维护仍必须先阅读适用规则并执行只读 `git status`，保护既有改动；按“按改动选择验证”运行最小相关检查，并在回复或提交说明中记录改动范围、命令与退出码。若修改会改变功能、数据、权限、合同、路由结果或运行边界，或无法可靠判断，改按“功能性代码变更”执行。Demo 同步与开发者工具验收是否适用，按其独立规则判断，不以是否建立 UpdatePlan 代替。

## 当前已核实的边界

- 技术栈为 uni-app、Vue 3、TypeScript、Vite；后端为 FastAPI、SQLAlchemy、Alembic 和 SQLite。PostgreSQL 是后续生产目标，尚非已验证的即插即用事实。
- `VITE_APP_MODE=demo|api` 在启动时选择运行模式。API 失败必须显式报错，禁止自动回退到 Demo 或混写两套数据。
- **微信开发者工具重新编译**：面向开发者工具加载与手工体验的所有小程序重新编译，一律运行 `npm run dev:mp-weixin`，并仅导入 `D:\\CODE\\weixin\\wxprogrom7.15\\dist\\dev\\mp-weixin`。保持 watcher 运行至完整构建结束后，再在工具内执行普通编译；`npm run build:mp-weixin` 只输出 `dist/build/mp-weixin` 供生产构建检查，不能替代或刷新开发者工具目录。
- **Demo 同步与微信开发者工具验收（用户强制）**：每次影响可被 Demo 体验的运行时代码、页面/组件、用户流程、可见状态或文案、feature public API、Demo seed/store/adapter、API/Demo 装配、前端数据读写或导航的更新，都必须同步维护 Demo，使其呈现同一界面合同、关键状态和受影响流程；Demo 不得伪造服务端授权、真实 AI、生产数据或安全结论。该验收与是否需要 UpdatePlan 独立：小型前端维护可直接更新，但仍须在适用时同步并验收 Demo。交付前必须在启动 watcher 的终端显式设置 `VITE_APP_MODE=demo` 后运行 `npm run dev:mp-weixin`（PowerShell：`$env:VITE_APP_MODE='demo'; npm run dev:mp-weixin`），等待 `Build complete. Watching for changes...`，并在微信开发者工具**仅加载** `D:\\CODE\\weixin\\wxprogrom7.15\\dist\\dev\\mp-weixin`、执行一次普通编译，手工走完与改动相关的 Demo 最小流程。默认只执行与改动直接相关的脚本和截图；不得把完整核心回归作为每次修改后的默认动作。自动化截图只能使用开发者工具内部截图通道后台执行，不得依赖系统截屏、抢占前台窗口、鼠标或键盘。H5 Demo E2E、`npm run build:mp-weixin`、生产目录、热更新提示或历史截图均不能替代该验收；不得手改 `dist`、复制生产目录、清理工具数据或关闭安全校验。交付必须记录模式、命令、开发目录、普通编译、角色/入口、验证流程、失败项与解除条件；取证不得包含 token、完整学生回答、隐藏病例或其他敏感信息。纯文档、计划、delivery、工程规则或项目 Skill 的孤立修订可免除此项，但不得以文档名掩盖运行时代码变化。
- **前端视觉层次**：避免以多个大尺寸圆角、阴影“气泡”卡片切割页面区域。优先用语义化标题层级、字号与字重、留白、轻量分隔线、色彩层级和顺序关系组织内容；卡片只用于承载独立操作、可聚焦对象或需要明确边界的关键信息。
- 页面只能经 `src/features/*/public.ts`、用例、领域 port、adapter 和显式 mapper 使用领域数据；不得在页面直接调用 `uni.request`、拼接后端地址或读写 storage key。`src/bootstrap/wiring.ts` 是唯一 API/Demo 装配点；`src/services` 与业务 `src/data` 运行时目录已删除，只有生成的 OpenAPI 类型仍保留在 `src/data/contracts/`。
- `docs/openapi.json` 与 `src/data/contracts/openapi.generated.ts` 是生成物，禁止手改。schema 或路由变更须同步 OpenAPI、生成类型、mapper 和契约测试。
- 客户端不得保存或输出服务端秘密；微信 AppSecret、AI key、JWT secret 只可存在于后端受管环境。日志不得记录 token、提示词、完整学生回答、病例隐藏字段或真实敏感数据。
- 授权、角色和数据范围必须由后端校验；学生 DTO 不得泄露隐藏事实、参考推理、评分 criteria 或审核内部字段。
- 本工作区已有未提交和未跟踪改动。先查看 `git status`，仅编辑本次范围；不 reset、clean、恢复、覆盖、代为提交或删除他人文件。特别不得恢复已删除的 `docs/update/README.md`。

## 病理学 PBL 教学助手最低产品约束

- 本项目必须完成以下闭环，不能以普通聊天、通用学习报告或教师手工出题替代：学生在病理学 PBL 课堂讨论中向 AI 提交不理解的问题；AI 通过多轮追问判断学生掌握不足的知识点和诊断思路问题；系统把结构化薄弱处及针对薄弱处生成的问题持久化并发送到有权查看该学生/班级的教师工作台；教师能够审阅、必要时编辑，并通过一次明确的“采用并发布”操作将 AI 建议题发布给目标学生。
- “发送给教师”必须是服务端持久化、可授权查询且可追踪状态的教师待办/建议队列，不得只停留在学生页面、浏览器内存、Demo storage、聊天文本或需学生另行复制粘贴的报告中。“直接采用”允许教师先编辑，但必须保留 AI 建议到正式题目的来源关系并保证采用/发布幂等；AI 不得绕过教师动作自动发布医学教学内容。
- AI 输出必须使用经运行时 schema 校验的结构化合同，至少区分 `knowledge_gaps`、`reasoning_issues`、`recommended_questions`、面向学生的回复/追问及安全提示；自由文本或客户端关键词规则不能作为完成证据。模型失败或确定性 fallback 必须显式标记，不能生成或上报虚假的已诊断薄弱点。
- 每个学生参与记录独立按 `problem_framing → hypothesis → evidence → synthesis → completed` 推进。schema v3 阶段证据必须来自当前阶段开始后的学生消息，服务端只允许相邻推进；完成后锁定新消息。教师阶段 PATCH 仅保留 deprecated 冲突响应。
- 教师采用发布时必须预创建两轮已审核等价变式。系统按版本化逐项规则自动判定结果：知识再测必须为 100，推理微训练和病例目标维度必须至少为 70，证据缺失按未达标处理；首轮失败只激活失败目标的第二轮，第二轮失败进入 `needs_reinforcement + automation_exhausted`。教师结果区只读，verify POST 仅保留 deprecated 冲突响应。
- 后端大模型生产提供方固定为 **Coze 平台上已配置的预训练大模型/智能体或工作流**。`PBL_AI_PROVIDER=coze` 时必须显式选择 `COZE_INVOCATION_MODE=bot|workflow`；所有 Coze token、bot/app/workflow 标识和调用只存在于后端受管环境并通过专用 gateway/adapter 隔离，客户端不得直连 Coze。`openai_compatible` 仅可用于开发/测试，生产必须拒绝它；不得仅凭普通 `/chat/completions` 适配器或 `AI_*` 配置宣称已完成 Coze 接入。提供方/模式禁止自动 fallback，具体 Coze 协议须以接入时采用的官方合同和固定版本为准，并由契约测试覆盖。
- 该闭环必须遵守 API/Demo 隔离、教师班级/学生数据范围、最小必要外发、去标识化、日志不记录完整对话/提示词/学生回答、医学安全分流和人工审核要求。Demo 只能演示同一界面合同，不能作为 API 模式、真实 Coze 调用或教师授权闭环的验收证据。
- 仓库内 T14 闭环已实现并保留本地 API/Demo、权限、迁移、provider 合同和敏感数据负向证据，详见上述 T14 文档。真实 Coze schema v3 联调、微信真机、医学专家审核和生产部署仍是外部验收项；完成前只能声明“仓库内完成”，不能声明生产教学闭环已验证。
- T15 在 T14 主线上增加学生只读“学情”总览与单课详情，并以 `(plan_id, cycle_number)` 唯一的评价历史展示两轮改善轨迹。报告只组合本人讨论、本人计划和课堂共同训练，不计算综合分、不调用 AI 总结、不暴露其他学生诊断或教学私有字段；真实生产回填和真机仍属外部验收。
- T16 将学生一级导航固定为“课堂、学习、学情、答疑”，将病例、知识和练习归入学习二级资源页；教师四工作区显示为“待办、学情、内容、PBL”，内部 query key 保持不变。一级页面以原生栏为唯一可见页面标题，正文不得再次堆叠同义 Hero；二级路径与旧链接继续兼容。

## 当前安全前置条件

- **T01 已在本地验收。** 后端 pytest 在导入应用前创建带所有权 marker 的随机临时 SQLite，并显式覆盖 `DATABASE_URL`；清表前后校验规范路径、marker、token、数据库文件和链接边界。`npm run backend:test:safety`、`npm run backend:test:migrations`、`npm run backend:test`、`npm run backend:check` 及根/`backend` pytest 入口均可使用。修改 `conftest.py`、`testing_resources.py`、engine 初始化、迁移或 E2E 启动器后，先复跑安全和迁移检查；不得绕过 fixture 直接对未知 engine 清表。
- `npm run backend:migrate` 会对当前后端数据库 URL 应用迁移；仅在已确认的受管开发/测试数据库、已说明数据影响与回退条件时运行，绝不对未知、共享或生产数据库试探性执行。
- `python backend/scripts/seed_test_data.py`/`python scripts/seed_test_data.py` 只能面向已确认的非生产受管数据库；它会先升级迁移。不要把它当作测试隔离机制。
- `npm run contract:generate` 会写入 OpenAPI、生成类型和 fixture，只在有意同步契约且可审阅差异时运行。`npm run contract:check` 已改为在系统临时目录生成并逐字节比较当前快照（忽略 CRLF/LF 差异），不会改写源码或快照；接口/schema 变更后两者都要按职责使用。
- 纯 Markdown 或本文件级改动只需验证受影响链接、路径与命令描述；不因文档改动运行数据库迁移、后端测试或 E2E。
- 生产、远程推送/合并、密钥轮换、外部账号、真实 AI/微信调用和全局 Codex 设置均不属于普通代码改动的默认授权范围。

## 按改动选择验证

- 前端 UI：格式、Lint、类型检查和相关组件/用例；跨端行为再做对应构建，并按“Demo 同步与微信开发者工具验收”完成 Demo 开发目录、工具普通编译和相关手工流程。
- 前端业务、存储或身份：另检查 API/Demo 分界、运行时校验、会话隔离与相关契约；同步维护 Demo 并完成开发者工具 Demo 验收。
- 后端领域、API/schema、模型/迁移、权限/AI/敏感数据：使用 T01 受管 fixture，并按已落地命令和领域测试矩阵验证。API/schema 改动还要审阅生成契约链；模型/迁移改动还要记录 upgrade、downgrade、保留与回退范围。
- 依赖、构建、CI 或跨模块重构：由实际脚本、边界检查和完整回归证据决定。`backend:test:safety`、`backend:test:migrations`、`scripts/frontend-boundaries.mjs`、`backend/scripts/check_boundaries.py` 均已存在；后两项尚未包装为 `package.json` 的 `frontend:boundaries`/`backend:boundaries` script，须按文档直接运行。远程 CI、分支保护及 Node 22/Python 3.12 复验仍是外部或统筹验收事项。

任何未运行的检查要说明原因、风险和解除条件；不得通过跳过、吞错、关闭权限、放宽覆盖率或移动生成文件来伪造通过。

## 交付自检

交付说明应至少列出：范围和已有改动保护情况、公开接口/合同及 API-Demo 影响、Demo seed/store/adapter 同步情况、`VITE_APP_MODE=demo` watcher 与开发者工具普通编译/流程证据（适用时）、数据或迁移影响、已执行命令及退出码、未执行项与原因、安全/权限检查、回退方式。T26 起的计划将证据写入自身 `deliveries/`；T01–T25 的历史阶段已收缩为 [阶段概述](docs/update_plan/01-25-summary.md)，仍须区分“当前事实”“待实现目标”“仓库内证据”和“外部阻塞”。

本文件不创建全局设置、不替代 CI，也不自动批准外部操作。
