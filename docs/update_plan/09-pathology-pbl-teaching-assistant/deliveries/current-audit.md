# T09 当前实现核查（2026-09-03）

状态：**未完成**。本记录是对当前工作树的只读代码核查，不是 T09 实施交付，也没有调用真实 Coze、运行数据库迁移或生产环境。

## 对照结论

| 最小要求                            | 当前仓库证据                                                                                                                                                                                           | 判定                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| 学生在 PBL 课堂向 AI 提问并多轮交流 | `src/pages/student/chat/chat.vue` 支持自由问答、有限历史、保存/续聊和主题选择；但没有绑定教师/班级的 PBL session，调用的是普通医学问答。                                                               | 部分完成               |
| AI 判断知识点掌握不足               | `backend/app/modules/qa/api/medical_schemas.py` 响应只有 `content`；`MedicalChatResult` 没有薄弱点字段。                                                                                               | 未完成                 |
| AI 判断诊断思路问题                 | `medical_chat_gateway.py` 的 system prompt 只要求通用教学回答；没有诊断推理阶段/问题类型 schema。`src/utils/report.ts` 只是客户端关键词启发式。                                                        | 未完成                 |
| AI 通过交流形成针对性追问           | `requestLearningAssistant` 的 `followUpPrompts` 固定为空，候选主题只是回显输入主题；学生页实际调用 `requestMedicalAssistant`。                                                                         | 未完成                 |
| 针对薄弱处生成建议题                | 现有 learning practice generator 服务于训练评估后的个性化练习，不接收自由问答的结构化诊断，也不产生教师建议队列。                                                                                      | 未完成                 |
| 薄弱处和建议题发送给教师            | 没有相关表、repository、API 或教师页面。学生可另行生成/提交报告，但报告不是自动教师队列且内容来自客户端规则。                                                                                          | 未完成                 |
| 教师直接采用 AI 问题并发布          | 现有 content/教师页面支持手工创建和发布正式题目；没有 AI suggestion ID、导入/采用动作、来源关系或采用幂等。                                                                                            | 部分完成（仅手工基础） |
| 后端使用 Coze 预训练大模型          | `backend/app/core/config.py` 只有通用 `AI_*`；`medical_chat_gateway.py` 和 `app/platform/ai.py` 直接调用 OpenAI-compatible `/chat/completions`；仓库检索不到 Coze adapter/config/test，且默认禁用 AI。 | 未完成                 |
| 授权、隐私与安全闭环                | 当前通用问答已有登录、历史上限、急症分流、服务端密钥与脱敏 AI audit 基础；但尚无教师建议队列的数据范围和 Coze 数据处理证据。                                                                           | 部分完成               |

## 关键缺口

1. 缺少课堂上下文：conversation 只有 student 和可选 topic codes，不能可靠确定接收教师。
2. 缺少结构化模型合同：现有端点只有字符串回答，无法持久化或验证知识薄弱点、推理问题和建议题。
3. 缺少教师交付链：没有建议队列、教师授权查询、采用状态、正式题目来源关系和幂等发布。
4. 缺少 Coze 适配：通用兼容端点不能证明所需供应商、资源版本、鉴权、错误语义或结构化输出已接入。
5. 缺少端到端证据：现有测试覆盖普通问答失败/fallback和手工题目发布，但没有 PBL-01～PBL-07 的组合测试。

## 核查方式

- 阅读根 `AGENTS.md`、`docs/update_plan/README.md`、架构、数据层、安全、后端模块和前端公开接口文档。
- 使用 `rg` 检索 Coze、AI 配置、医学聊天、结构化学习输出、薄弱点、教师题目创建/发布和测试。
- 阅读学生聊天页、qa 前后端 adapter/application/schema、AI gateway、报告规则和 content 发布用例。

## 本次文档验证证据

- 编辑前 `git status --short`：退出码 0；确认工作树已有大量修改/未跟踪内容，根 `AGENTS.md` 与 `docs/update_plan/` 也属于既有未跟踪范围。本次未 reset、clean、恢复、删除、提交或覆盖无关文件。
- `python .agents/skills/wx-engineering-standards/scripts/self_check.py`：编辑前后均退出码 0；技能结构、链接和“当前事实/计划目标”标签检查通过。
- 目标文件存在性与尾随空白检查：退出码 0。
- 首次 `npx prettier --check`：退出码 1，发现 4 个新增 Markdown 文件需格式化；随后仅对这 4 个新增文件运行 `npx prettier --write`，退出码 0；最终对本次 8 个目标 Markdown 文件运行 `npx prettier --check`，退出码 0。
- T09 索引目标、文件存在性和尾随空白联合复验：退出码 0。
- 编辑前 SHA-256：`AGENTS.md` 为 `8EA7D8E76A8F02259ACF61DD087ED827572AC77CBEBFA49CCF340C7003F7DC53`，`docs/update_plan/README.md` 为 `BD44967A734365B7B8EF8599D245671059ABDB5E7405F45956C2BC4680327995`；用于区分本次最小追加与既有未跟踪内容。

未运行后端测试、迁移、契约生成或 E2E：本次只修改 Markdown/协作约束，且没有更改公开 API、schema、数据库或运行时代码。解除条件是后续实施 T09 代码后按 [验证与回退](../04-verification-rollback.md) 执行相应检查。

## 安全、影响与回退

- 本次没有外发学生数据、读取或写入真实凭据、调用 Coze、变更权限、修改数据库或生成契约。
- 当前普通问答、API/Demo 和教师手工发布行为未被运行时代码更改。
- 如需回退本次文档变更，仅移除 T09 文档目录并撤销根 `AGENTS.md` 与总计划索引中对应新增段落；无数据影响。
