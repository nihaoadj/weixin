# 依赖安全基线

## 病例训练数据隔离

学生病例接口使用显式响应结构：隐藏事实、参考推理、评分 criteria 和 `revealed_fact_ids` 均不会返回。attempt、提交和 assessment 始终按 `student_id` 查询；教师 authoring 接口要求教师角色。AI 审计日志只记录调用元数据，不记录密钥、完整 prompt 或学生完整回答。

## 当前实现与外部阻断

本地可用的依赖/秘密检查为 `npm run audit:prod`、`npm run audit:all`、`npm run backend:audit`、`npm run security:secrets` 和 `npm run security:secrets:self-test`。远程 CI 是否已强制执行它们、分支保护是否已配置，均未由本工作树证明；不能写作当前完成事实。后端 requirements 文件使用哈希安装；审计命令读取 `backend/requirements.txt`。

当前客户端不处理真实患者身份数据，不加载不受信任的 ZIP/JPEG 文件，也不向用户暴露 Vite 开发服务器。生产部署只发布构建后的静态资源与微信小程序包。

## 凭据泄露处置（外部阻断）

远程仓库初始提交 `2a9ad32` 的旧版聊天页曾把一个看似真实的模型 API key 写入客户端源码（TypeScript 和生成的 JavaScript 各一处）。当前工作树已不再包含该值，但 Git 历史仍可读取，因此该 key 必须按已泄露处理：由外部管理员撤销/轮换，并提供调用账单和访问审计证据。当前没有这些外部证据；历史清理也需要另行评估远程仓库协作者影响，不能仅靠删除当前文件视为完成。

旧版同时暴露了 AppID 和云环境 ID；这些是项目标识，不等同于 AppSecret，但仍应核对云数据库权限和合法域名。当前实现不再把模型密钥放在小程序端，微信 AppSecret 仅由后端环境变量读取。

## 依赖升级约束

- `@dcloudio/*` 必须以同一发布批次升级；不得单独升级其中一个运行时或编译包。
- 当前 DCloud 插件的 peer 元数据仍声明 Vite 5.2.8；S2 证据记录了在当前锁文件环境的类型检查、H5 和微信小程序构建。安装使用 `npm ci --legacy-peer-deps`；目标 Node 22/Python 3.12 与远程环境复验仍待统筹/平台验收。每次 DCloud 或 Vite 升级必须重新完成双端构建与 API/Demo 回归。
- low/moderate 告警不得通过 allowlist 隐藏；它们记录在依赖升级报告中，并在下次依赖批次升级时复查。

# 已实现的代码边界

- permissions 由服务端 seed/allowlist 决定，LoginRequest 不接受客户端权限；`demo_reviewer` 才有 `medical_review`。
- 班级、审核和分析接口按教师 owner 隔离，跨范围统一 404；审核专家不会自动获得班级分析数据。
- 学生响应仍不包含 hidden facts/reference/rubric；分析只读取结构化 CaseAssessment，不读取自由问答 Report.ai_score。
- 发布前校验审核状态；审核记录保存病例版本和 SHA-256 digest，便于发现审核后内容变化。
- 微信登录的角色由服务端已有账号或 `WECHAT_TEACHER_OPENIDS` 白名单决定，客户端不能通过请求字段提升为教师。
- 生产启动会拒绝默认或过短的 `JWT_SECRET`；密钥缺失时不允许带着可预测签名密钥运行。

# V3 安全边界补充

- 学生接口只返回公开病例 metadata、public definition、学生自己的答案/反馈；`private_rubric`、`fixed_facts`、reference reasoning、blueprint digest 和模型 prompt 不出现在学生 DTO。
- 学生题目响应不返回定向发布的学生/班级 ID、作者 ID、能力标签或审核内部字段。
- 微训练输入只使用维度、阶段、审核蓝图公开字段和去标识化薄弱反馈；不发送 nickname、external ID、班级或无关历史。
- 动态题面经过 Pydantic、答案 schema、长度、注入、剂量/处方和隐藏 ID 校验；失败重试一次后使用固定 fallback。
- 服务端固定 criteria 决定总分，AI 只能改写反馈；evidence 必须逐字来自学生答案并限制为最多三条、每条 160 字。
- 站内通知只读写当前学生记录，不建设后台定时器或微信消息服务。

## 不得冒充已完成的事项

真实微信登录与真机/合法域名、真实 AI 提供方、生产配置与部署、医学内容审核，以及教师报告范围是否要从当前 `submitted_global` 收窄，均需要外部授权或证据。T06 仓库侧扫描、测试与本地构建物证据已经接收，但历史凭据撤销、访问审计及上述外部条件仍未核实，不得推断为完成。

# T09：生产 PBL 仅使用 Coze，显式 Bot/Workflow 模式；普通 OpenAI-compatible 仅开发/测试。输入最多 20 条去标识化历史，日志/DTO 不得含 token、完整 prompt、完整学生回答、供应商 DTO 或教师建议题。

# T11：开发环境可在被 Git 忽略且未跟踪的 `backend/.env` 中选择 `PBL_AI_PROVIDER=openai_compatible`。该文件只由服务端读取；测试和 OpenAPI 导出会隔离 AI 环境变量，自动化回归使用 Mock。生产环境仍拒绝 openai-compatible 并要求显式 Coze 调用模式。不得在示例、文档、日志、生成物或客户端保存实际密钥。
