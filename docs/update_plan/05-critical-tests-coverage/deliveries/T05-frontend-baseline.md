# T05 前端特征测试基线

状态：前端最小基线已验证；后端安全基线待 T01 验收后交接。

本阶段只修改前端测试和 T05 交付记录，未修改业务实现、`package.json`、coverage 配置、后端文件或 E2E。未运行 `pytest`、`backend:test`、`backend:check`、`check:all` 或任何 E2E。

## 修改与保护记录

原内容备份目录：`C:\Users\adj\AppData\Local\Temp\t05-frontend-baseline-df03c06239b244869ea104c47c3d191d`。

| 修改前文件                                    | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| `docs/update_plan/deliveries/T05-baseline.md` | `637E74377B37370943A140A90BC99964B489B68483E03DF418C6DA3E47B388E8` |
| `src/services/remoteAuth.spec.ts`             | `3F86D5AD9613A5851B8B8FF249AC9AF1442C46BA4273C43642DE3458729E3E3A` |
| `src/services/apiClient.cache.spec.ts`        | `991964795CDA4FFC1344CF20B913165D3EB0C9C54462F823C7BB12F4D9C3AAF0` |

新增文件 `src/data/usecases/reportDraft.spec.ts` 在修改前不存在。未对原始目录执行读写。

审阅加强前，当前 WIP 的 `src/services/apiClient.cache.spec.ts` 另行备份于 `C:\Users\adj\AppData\Local\Temp\t05-frontend-baseline-review-8cacd0569e4046718d559c22c59e1647\apiClient.cache.spec.ts`，SHA-256 为 `50C2A91B40E45E43FFE4CB6E6CC081D6EA65AD8EC88C3CCFADC950BA0919B26B`。

## 已新增的行为覆盖

| 责任           | 测试文件与完整测试名                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 通过的可观察断言                                                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 微信认证       | `src/services/remoteAuth.spec.ts::syncWechatLoginWithBackend saves a complete successful WeChat identity only after a valid response`                                                                                                                                                                                                                                                                                                                                                                      | 完整成功响应才保存 token，并返回完整 session identity。                                                                                                                             |
| 微信失败原子性 | `src/services/remoteAuth.spec.ts::{syncWechatLoginWithBackend preserves the existing token when WeChat returns no code,syncWechatLoginWithBackend preserves the existing token when WeChat login is cancelled,syncWechatLoginWithBackend preserves the existing token when the response DTO is invalid,syncWechatLoginWithBackend preserves the existing token when the response has no user,syncWechatLoginWithBackend rejects a student response for a teacher request without replacing the old token}` | 每种失败都没有覆盖旧 token；教师入口拒绝学生 response。                                                                                                                             |
| 会话／缓存     | `src/services/apiClient.cache.spec.ts::{rejects a delayed successful response from an old session without replacing the newer token,handles concurrent 401 responses with one session-expiry navigation,evicts the oldest cache entry when the 128-entry cache limit is exceeded}`                                                                                                                                                                                                                         | 旧成功响应为 `STALE_SESSION`；两条 401 请求分别拒绝为 `AUTH_REQUIRED`（含 401）和 `STALE_SESSION`，token 已清除且只导航一次；插入第 129 个条目淘汰最旧条目，第 127 项仍为缓存命中。 |
| 报告编排       | `src/data/usecases/reportDraft.spec.ts::{persists the conversation before persisting the draft with the resolved conversation id,propagates a second-step failure after the conversation has been persisted and does not retry either step}`                                                                                                                                                                                                                                                               | 先会话后报告；第二步失败会原样传出，且不重试。                                                                                                                                      |

## 执行证据

环境：Windows PowerShell，Node `v24.14.0`，npm `11.9.0`，Vitest `3.2.6`。

`npm ci` 退出码非零：锁文件中的 `@dcloudio/vite-plugin-uni` peer 要求 Vite `5.2.8`，但项目锁定 Vite `7.3.6`，出现 `ERESOLVE`。未修改锁文件。`npm ci --legacy-peer-deps` 成功安装锁文件依赖。

```powershell
npx vitest run src/services/remoteAuth.spec.ts src/services/apiClient.cache.spec.ts src/data/usecases/reportDraft.spec.ts
```

真实退出码：`0`。结果：3 个测试文件通过，18 个测试通过，0 个失败；Vitest 报告总时长 18.66 秒。

审阅加强后额外执行：

```powershell
npx vitest run src/services/apiClient.cache.spec.ts
```

真实退出码：`0`。结果：1 个测试文件通过，9 个测试通过，0 个失败；Vitest 报告总时长 2.22 秒。

## 未验证与后续

- 后端、迁移、性能、完整 coverage、H5 E2E、Demo E2E、微信构建与真机验收均未执行，仍受 T01/T02 和设备条件约束。
- 报告第二步失败当前的行为是“会话已持久化、错误传播、不自动重试／补偿”；这项测试记录的是现有可观察合同，未判断其是否需要产品层补偿策略。
- 等待 T01 提供并验收受管临时数据库、fixture、迁移入口及 E2E 独占资源后，再继续后端业务基线。
