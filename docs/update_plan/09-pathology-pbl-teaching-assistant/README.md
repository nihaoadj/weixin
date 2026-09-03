# T09 病理学 PBL 教学助手

状态：**实施中；真实 Coze 外部联调未验证。** 本目录区分当前事实、锁定目标和验收证据，计划不能当作已完成实现。

## 最小闭环

面向医学本科生的病理学总论 PBL 课堂，首版目录覆盖细胞损伤与适应、炎症、修复、循环障碍、肿瘤。教师为自己拥有的班级创建活动课堂；所属学生进入后与 AI 多轮交流。AI 在证据不足时只追问，在证据充分时判断知识薄弱点和诊断思路问题，并把相关开放讨论题送入教师队列。

学生和教师都可查看自己的薄弱分析；仅教师可查看、编辑、拒绝或显式“采用并发布”建议题。AI 绝不自动发布。

## 已锁定提供方边界

- 业务只依赖 `PblInferenceGateway`；Coze Bot、Coze Workflow、普通 OpenAI-compatible API 是相互隔离的 adapter。
- `PBL_AI_PROVIDER=coze|openai_compatible` 与 `COZE_INVOCATION_MODE=bot|workflow` 均须显式配置。生产环境只接受 `coze`；普通 API 仅开发/测试，不可作为 Coze 完成证据。
- 禁止跨提供方或跨模式自动 fallback。失败返回受控的 `unavailable`，不伪造分析或建议题。
- Coze 使用固定版本的官方 Python SDK；本轮只在 SDK 边界注入 Mock/fixture，不发起真实网络调用。

## 当前事实

- 已有通用医学问答和教师手工出题；尚无 PBL 课堂、结构化诊断、教师建议队列、Coze adapter 或建议题来源关系。
- 当前通用 AI 使用 OpenAI-compatible HTTP 适配器，不能证明 Coze 接入或 PBL 闭环已经完成。

## 文档索引

| 文档                                                                 | 用途                                   |
| -------------------------------------------------------------------- | -------------------------------------- |
| [01-product-requirements.md](01-product-requirements.md)             | 用户流程、可见范围、病理目录与完成定义 |
| [02-interface-data-contracts.md](02-interface-data-contracts.md)     | HTTP、数据、权限、发布事务合同         |
| [03-implementation-tasks.md](03-implementation-tasks.md)             | 实施顺序与模块边界                     |
| [04-verification-rollback.md](04-verification-rollback.md)           | Mock 验收、发布限制与回退              |
| [05-ai-provider-adapter-design.md](05-ai-provider-adapter-design.md) | 端口、adapter、配置矩阵和错误映射      |
| [06-coze-resource-contract.md](06-coze-resource-contract.md)         | Bot/Workflow Coze 资源和 fixture 合同  |
| [deliveries/template.md](deliveries/template.md)                     | T09 交付证据模板                       |
| [deliveries/current-audit.md](deliveries/current-audit.md)           | 更新前仓库核查                         |

## 非目标

不进行真实 Coze 调用、生产部署、真实学生资料外发或真实数据库迁移；不自动评分、自动发布或替代教师作医学判断。
