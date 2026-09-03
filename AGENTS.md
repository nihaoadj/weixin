# 项目协作约束

本文件是本仓库人和自动化代理的最小工程约束。它只描述当前已核实的边界和检查路由；计划中的目录、命令或流程不得当作已经落地。

## 先读什么

- 总体规则、任务阶段与交付格式：[docs/update_plan/README.md](docs/update_plan/README.md)。该目录是计划和证据索引，不是当前实现的替代说明。
- 当前架构和目录边界：[docs/architecture.md](docs/architecture.md)。
- 数据访问、API/Demo、契约、缓存和错误边界：[docs/data-layer.md](docs/data-layer.md)。
- 开发命令与现有说明：[docs/development.md](docs/development.md)。其中与测试安全、路径或命令有关的旧说明须以本文件的“当前安全前置条件”和 T01/T02 后续事实更新为准。
- 数据库及迁移限制：[docs/database.md](docs/database.md)。
- 权限、敏感数据、AI 与凭据处置：[docs/security.md](docs/security.md)。
- 环境和发布条件：[docs/deployment.md](docs/deployment.md)。
- 重大数据层取舍：[docs/adr/0001-data-layer-contracts.md](docs/adr/0001-data-layer-contracts.md)。
- 病理学 PBL 教学助手的最低产品要求、接口/数据目标与当前差距：[docs/update_plan/09-pathology-pbl-teaching-assistant/README.md](docs/update_plan/09-pathology-pbl-teaching-assistant/README.md)。

改动涉及的领域要先阅读对应权威文档，而不是一次复制整套文档。目录内新增局部 `AGENTS.md` 仅能补充确有差异的规则，不能放宽本文件。

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
- 后端大模型生产提供方固定为 **Coze 平台上已配置的预训练大模型/智能体或工作流**。`PBL_AI_PROVIDER=coze` 时必须显式选择 `COZE_INVOCATION_MODE=bot|workflow`；所有 Coze token、bot/app/workflow 标识和调用只存在于后端受管环境并通过专用 gateway/adapter 隔离，客户端不得直连 Coze。`openai_compatible` 仅可用于开发/测试，生产必须拒绝它；不得仅凭普通 `/chat/completions` 适配器或 `AI_*` 配置宣称已完成 Coze 接入。提供方/模式禁止自动 fallback，具体 Coze 协议须以接入时采用的官方合同和固定版本为准，并由契约测试覆盖。
- 该闭环必须遵守 API/Demo 隔离、教师班级/学生数据范围、最小必要外发、去标识化、日志不记录完整对话/提示词/学生回答、医学安全分流和人工审核要求。Demo 只能演示同一界面合同，不能作为 API 模式、真实 Coze 调用或教师授权闭环的验收证据。
- 完成声明至少需要 API 模式端到端证据：学生对话与追问、结构化薄弱点/诊断思路问题、教师队列可见性和跨班级拒绝、建议题一键采用发布及重复提交幂等、学生端可见、Coze 成功/超时/无效响应/回退、敏感数据负向断言。当前核查结论为“未完成”，详见上述 T09 文档；只有代码、迁移、生成契约、测试及交付证据全部验收后才能更新此状态。

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

交付说明应至少列出：范围和已有改动保护情况、公开接口/合同及 API-Demo 影响、数据或迁移影响、已执行命令及退出码、未执行项与原因、安全/权限检查、回退方式。涉及计划任务时，将证据写入 `docs/update_plan/deliveries/Txx.md`，并明确“当前事实”“待实现目标”“仓库内证据”和“外部阻塞”。

本文件不创建全局设置、不替代 CI，也不自动批准外部操作。
