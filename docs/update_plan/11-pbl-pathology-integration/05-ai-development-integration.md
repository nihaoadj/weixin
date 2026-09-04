# AI 开发接入与秘密保护

## 用户授权与待实现目标

开发普通模型使用 deepseek-v4-flash、基础地址 https://api.deepseek.com、POST /chat/completions。依据 [DeepSeek 官方合同](https://api-docs.deepseek.com/api/create-chat-completion/)。生产只允许显式 Coze；本轮 Coze 仅 Mock 合同检查，不真实调用。

用户提供的密钥只配置于未跟踪且已忽略的 backend/.env，本文件及所有文档、示例、源码、生成物均不得包含该值。使用 AI_* 和 PBL_OPENAI_* 独立后端变量，普通答疑与 PBL 配置为同一服务；开发 PBL provider 默认为 openai_compatible，PBL_MOCK_ENABLED=false。

先保证测试和契约导出不加载本地 .env，显式隔离 AI/PBL/Coze 变量，再创建本地配置。Settings 的直接测试构造不自动加载开发凭据；get_settings 仅正常服务入口按后端绝对路径加载环境文件。pytest/E2E/contract-export 使用受控环境。

PBL JSON 输出、thinking disabled、max_tokens=4096、服务端超时 25 秒、前端 35 秒。历史角色 student 转 user，最多二十条；提示词包含完整输出 schema、允许知识点和证据 ID。只发送公开病例上下文、匿名会话引用、去标识化有限历史。身份、班级名、秘密、隐藏事实、rubric 不外发。

失败区分 timeout/auth/rate_limit/http_error/invalid_json/invalid_contract/truncated；失败无 findings/recommendations。不自动切换提供方。日志仅存安全元数据，不存完整回答、请求、响应、提示词或 reasoning_content。

## 联调与验收

自动化仅 Mock。独立 live runner 用受管临时库和合成问题，首轮至多十二次调用，覆盖五主题和至少一条教师采用链；只记录计数、状态、耗时、schema 结果。密钥匹配扫描仅输出文件位置，不输出原文；检查文档、tracked/untracked 源文件及 staged 内容。本地 .env 不作为扫描输出或交付附件。
