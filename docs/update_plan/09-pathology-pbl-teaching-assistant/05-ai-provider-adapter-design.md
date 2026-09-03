# T09 AI 提供方适配设计

`PblInferenceGateway` 是 application 唯一依赖，输入/输出均为 PBL 自有 record。三个独立实现是 `CozeBotGateway`、`CozeWorkflowGateway`、`OpenAICompatibleGateway`；Bot/Workflow 共享官方 SDK 客户端工厂、流事件解析和结构化校验，但分别映射协议。普通 API 独立使用 HTTP client，不能继承 Coze 类。

| 环境             | provider            | 资源                                                   | 结果               |
| ---------------- | ------------------- | ------------------------------------------------------ | ------------------ |
| production       | `coze`              | `bot` + Bot ID，或 `workflow` + Workflow ID 和关联资源 | 允许               |
| development/test | `coze`              | 同上                                                   | 允许，仅 Mock 覆盖 |
| development/test | `openai_compatible` | base URL、key、model                                   | 允许，仅开发测试   |
| production       | `openai_compatible` | 任意                                                   | 启动失败           |

PBL 启用时，缺少 provider、timeout、模式、令牌或资源均失败；禁止 provider/mode fallback。超时、限流、SDK/HTTP 异常、流中断、空内容、非 JSON、schema 错误均映射为 `unavailable`，不写建议题。元数据只含 provider/mode、资源安全标识、prompt 版本、耗时、失败分类，不含 token 或全文。
