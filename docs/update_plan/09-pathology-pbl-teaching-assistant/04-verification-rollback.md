# 验证、发布与回退

> T09 锁定更新：本轮只以 Mock/fixture 验收 Coze Bot、Workflow 和开发/测试普通 API；不得进行真实 Coze 网络调用。必须验证生产拒绝普通 API、资源配置失败、无跨提供方 fallback、学生字段隔离、迁移和采用幂等。最终最多标记“仓库内完成、真实 Coze 外部联调未验证”。回退为 `PBL_AI_ENABLED=false`，绝不自动切换普通 API。

## 验收矩阵

| 场景         | 最低断言                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------- |
| 多轮追问     | 首轮信息不足返回 `probing` 和单一明确追问；后续消息沿用同一 PBL session，不重复当前 prompt。       |
| 知识薄弱点   | 结构化字段通过 schema；知识点存在于目录；依据摘要来自本会话且已去标识；置信不足时标记而非猜测。    |
| 诊断思路问题 | 能定位到明确推理阶段和问题类型；不得把缺少某关键词简单等同于推理错误。                             |
| 建议题       | 每题关联薄弱处并符合长度/题型/目标范围合同；空薄弱处不产题。                                       |
| 教师路由     | 正确教师可见；其他教师、其他班级、其他学生不可读取、编辑、采用或发布。                             |
| 采用发布     | 单击生成正式题并发布；重复请求/并发只有一个 `problem_id`；失败后状态一致且可重试。                 |
| 学生可见性   | 目标学生能看到正式题，非目标学生不可见；学生 DTO 不含教师依据、内部置信度或其他学生信息。          |
| Coze 成功    | 后端 adapter 正确映射已固定版本的官方合同并拒绝多余/非法字段；客户端构建不含 token/资源密钥。      |
| Coze 失败    | 超时、限流、HTTP 错误、流式中断、空响应、坏 JSON、schema 错误均有界；fallback 不伪造诊断或建议题。 |
| 安全分流     | 急症与个体诊疗请求优先确定性拦截；不调用 Coze 或发布相关问题。                                     |
| 脱敏审计     | 请求白名单和长度上限生效；日志/AI audit/异常响应不含 token、完整 prompt、完整学生回答或完整输出。  |
| API/Demo     | API 失败显式报错且不切 Demo；Demo 仅验证展示和交互合同，不计入真实 Coze 验收。                     |

## 建议验证入口

实施后按实际改动执行并记录退出码；不存在的测试命令不得提前写成已通过事实。

```text
python .agents/skills/wx-engineering-standards/scripts/self_check.py
node scripts/frontend-boundaries.mjs --self-test
node scripts/frontend-boundaries.mjs
python backend/scripts/check_boundaries.py --self-test
python backend/scripts/check_boundaries.py
npm run contract:generate
npm run contract:check
npm run type-check
npm test
npm run backend:test:safety
npm run backend:test:migrations
npm run backend:test
npm run test:e2e
```

`contract:generate` 会写文件，必须只在有意更新并审阅生成契约时运行。迁移测试使用 T01 launcher-owned 临时库；不得对未知、共享或生产数据库试探性执行迁移。

## 发布门槛

- 仓库内：代码、迁移、生成契约、PBL 单元/集成/E2E、边界和秘密扫描通过。
- 仓库外：Coze 账号和资源版本受管、token 轮换与最小权限、数据处理/保留/地区批准、HTTPS/微信合法域名、医学教师验收、目标平台复验有证据。
- 任一外部条件缺失时可标记“仓库内完成但外部阻塞”，不得宣布可生产发布。

## 回退原则

- 以服务端 feature flag 停止新 PBL 诊断和建议生成，同时保留既有课堂对话、正式题目及审计记录可读；不得自动切换其他模型提供方。
- 回退 Coze adapter 或 prompt/workflow 版本时保留版本标识，避免旧结果与新结果混写。
- 已采用并发布的正式题目由 content 模块原有生命周期管理，关闭 PBL 功能不得删除或偷偷下架它们。
- 数据库 downgrade 前确认新记录的保留/导出方式；若 downgrade 会丢失诊断或来源关系，必须先备份并明确数据影响。
- 前端可隐藏未完成入口，但 API 必须显式返回稳定的不可用状态；不能用 Demo 响应掩盖服务端故障。
