# T09 Coze 资源与 Mock 合同

SDK 固定 `cozepy==0.20.0`，debug 日志关闭。Coze 仅后端调用；本轮不配置真实 token，不访问 Coze 网络。

Bot 必填 `COZE_BOT_ID`，Workflow 必填 `COZE_WORKFLOW_ID`，并依资源发布类型验证 `COZE_APP_ID` 或 `COZE_BOT_ID` 关联。两者传递匿名 conversation 与同一去标识 JSON：`schema_version`、session、topic、允许目录、当前问题和最多 20 条历史。不得发送真实身份、班级、token 或未裁剪病例。

模型完成文本必须为包含 `assistant_reply`、`diagnostic_status`、`follow_up_question`、`knowledge_gaps`、`reasoning_issues`、`recommended_questions` 的 JSON。fixture 是 SDK client 所见 conversation/delta/completed/interrupt/error 事件及期望领域结果，覆盖两模式成功、续聊、空内容、坏 JSON、schema、超时、限流与 SDK 异常；不含真实凭据或学生资料。
