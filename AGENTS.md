# 项目协作约束

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
- 病理学 PBL 教学助手的最低产品要求、接口/数据目标与当前差距：[docs/update_plan/09-pathology-pbl-teaching-assistant/README.md](docs/update_plan/09-pathology-pbl-teaching-assistant/README.md)。
- PBL 参与级自动阶段、两轮巩固和系统判定的当前实现与证据：[docs/update_plan/14-pbl-automatic-mastery-loop/README.md](docs/update_plan/14-pbl-automatic-mastery-loop/README.md)。
- 学生 PBL 学情报告、评价历史和改善轨迹的当前实现与证据：[docs/update_plan/15-pbl-student-learning-report/README.md](docs/update_plan/15-pbl-student-learning-report/README.md)。
- 学生/教师四项导航、页面标题和训练资源归类的当前实现与证据：[docs/update_plan/16-frontend-information-architecture/README.md](docs/update_plan/16-frontend-information-architecture/README.md)。

改动涉及的领域要先阅读对应权威文档，而不是一次复制整套文档。目录内新增局部 `AGENTS.md` 仅能补充确有差异的规则，不能放宽本文件。

## 每次更新的强制步骤

所有功能、修复、重构、依赖、迁移、契约或工程规则更新都必须按以下顺序执行；不得先改运行时代码再补计划：

1. **核查当前事实**：阅读本文件和相关权威文档，执行只读 `git status`，记录当前分支、既有未提交改动、公开接口、API/Demo、权限、数据、迁移、AI 和生成物影响。
2. **建立 UpdatePlan**：在 `docs/update_plan/` 下按 `NN-short-name/` 新建或更新本次更新的独立目录；至少写明当前事实、目标与非目标、接口/数据/模块设计、实施顺序、测试验收、外部阻塞和回退。大型更新还须提供 `deliveries/template.md`。
3. **计划门禁**：对 UpdatePlan 执行格式、相对链接、尾随空白及工程 skill self-check。计划必须区分“已核实事实”和“待实现目标”，且足以让执行者无需自行补产品或架构决策。
4. **按计划实施**：只有计划门禁通过后才能修改运行时代码；按文档顺序逐项实施，保持模块公开边界、API/Demo 隔离、生成契约流程、权限与敏感数据约束。发现会改变既定范围的新事实时，先修订 UpdatePlan 再继续。
5. **分阶段验证**：每完成一个阶段，运行与风险匹配的最小检查；API/schema、模型/迁移、AI、身份或跨模块改动必须执行对应的契约、数据库安全、迁移、权限和边界测试。不得以跳过或降级门禁伪造通过。
6. **交付与提交**：在 UpdatePlan 的 `deliveries/` 中记录命令、时间、退出码、未执行项、风险和回退。提交前检查暂存范围、秘密和生成物；只有用户明确授权才可提交或推送。提交不能把“仓库内完成”误写为“真实外部服务或生产已验证”。

如果更新前已经存在未按本流程实施的代码，只能先创建补充 UpdatePlan 和当前差距审计，再继续修改；补写计划不能倒推为先前实现已通过门禁。

## 当前已核实的边界

- 技术栈为 uni-app、Vue 3、TypeScript、Vite；后端为 FastAPI、SQLAlchemy、Alembic 和 SQLite。PostgreSQL 是后续生产目标，尚非已验证的即插即用事实。
- `VITE_APP_MODE=demo|api` 在启动时选择运行模式。API 失败必须显式报错，禁止自动回退到 Demo 或混写两套数据。
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

- 前端 UI：格式、Lint、类型检查和相关组件/用例；跨端行为再做对应构建。
- 前端业务、存储或身份：另检查 API/Demo 分界、运行时校验、会话隔离与相关契约。
- 后端领域、API/schema、模型/迁移、权限/AI/敏感数据：使用 T01 受管 fixture，并按已落地命令和领域测试矩阵验证。API/schema 改动还要审阅生成契约链；模型/迁移改动还要记录 upgrade、downgrade、保留与回退范围。
- 依赖、构建、CI 或跨模块重构：由实际脚本、边界检查和完整回归证据决定。`backend:test:safety`、`backend:test:migrations`、`scripts/frontend-boundaries.mjs`、`backend/scripts/check_boundaries.py` 均已存在；后两项尚未包装为 `package.json` 的 `frontend:boundaries`/`backend:boundaries` script，须按文档直接运行。远程 CI、分支保护及 Node 22/Python 3.12 复验仍是外部或统筹验收事项。

任何未运行的检查要说明原因、风险和解除条件；不得通过跳过、吞错、关闭权限、放宽覆盖率或移动生成文件来伪造通过。

## 交付自检

交付说明应至少列出：范围和已有改动保护情况、公开接口/合同及 API-Demo 影响、数据或迁移影响、已执行命令及退出码、未执行项与原因、安全/权限检查、回退方式。涉及计划任务时，将证据写入对应计划目录的 `deliveries/Txx.md`；T01–T07 的共享阶段证据位于 `docs/update_plan/01-07-engineering-governance/deliveries/`，并明确“当前事实”“待实现目标”“仓库内证据”和“外部阻塞”。

本文件不创建全局设置、不替代 CI，也不自动批准外部操作。
