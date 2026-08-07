# 11. 开发指南

## 1. 当前状态说明

当前仓库没有 lockfile，依赖目录也未安装，因此现有 `npm run build -- --noEmit` 会因为找不到 `tsc` 而失败。第一阶段应先整理依赖和单一源码，再把以下命令固化到 CI。

## 2. 本地准备

建议统一：

- Node.js：使用 `.nvmrc`/`.node-version` 固定团队版本，并确保与 CloudBase 支持的运行时策略兼容；
- npm：随 Node 固定版本；
- 微信开发者工具：团队固定一个稳定版并记录基础库兼容范围；
- CloudBase：开发者只获取 dev 环境最小权限；
- Git hooks：只做快速检查，完整门禁由 CI 执行。

仓库完成依赖整理后，标准命令应为：

```powershell
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

不要依赖全局安装的 `tsc`、Lint 或部署 CLI。

## 3. 源码规则

### 3.1 TypeScript 唯一源码

- 业务逻辑只编辑 `.ts`；
- 构建生成的 `.js` 放独立输出目录或明确忽略，不能与 `.ts` 同目录手工维护；
- 若微信开发者工具负责 TypeScript 编译，CI 也必须执行等价 typecheck/build；
- `strict` 保持开启；新增代码禁止无理由 `any` 和非空断言；
- 客户端、云函数、共享 contract 使用同一枚举和 schema 来源。

### 3.2 页面分层

页面只负责：生命周期、绑定事件、渲染状态、调用 service。

```ts
// page: 不直接访问数据库、模型或拼授权字段
const result = await conversationService.sendMessage({
  conversationId: this.data.conversationId,
  content,
  idempotencyKey: clientMessageId,
});
```

`services/` 负责 API 与 DTO；`stores/` 负责少量跨页状态；`models/`/contracts 负责类型；纯函数放 `utils/`。禁止在 WXML 对复杂业务状态做多层计算。

### 3.3 云函数分层

```text
handler → validation/auth → use-case → repository/provider → response mapper
```

- handler 不写大段业务逻辑；
- use-case 不依赖微信 event 结构；
- repository 统一过滤 scope 和软删除；
- provider 隔离模型供应商；
- 错误统一映射为公开错误码；
- 日志只记录结构化元数据。

## 4. 命名与类型

- 业务 ID：`userId`、`questionId`、`conversationId`、`submissionId`，不要统称 `id`；
- 状态：内部英文枚举，UI 单独映射中文；
- 时间：`createdAt/updatedAt/submittedAt`，服务端 UTC；
- 布尔值：`is/has/can/should` 前缀；
- DTO：`QuestionSummaryDto`、`SubmissionDetailDto`；数据库文档类型不直接返回客户端；
- 输入 schema 限制长度、数组数量、枚举和额外字段；
- 分数使用 number，明确 0–100，不能通过真值判断存在性。

## 5. 配置

建议服务端配置结构：

```ts
interface AppConfig {
  environment: 'dev' | 'staging' | 'prod';
  cloudEnvId: string;
  ai: {
    provider: string;
    modelId: string;
    timeoutMs: number;
    maxInputChars: number;
    dailyBudget: number;
  };
  safetyPolicyVersion: string;
}
```

规则：

- 配置启动时 schema 校验；
- 密钥只从服务端密钥管理/环境读取；
- `.env.example` 只列变量名和说明，不放真实值；
- 小程序包不保存模型 endpoint、密钥或管理 API；
- 生产配置变更有审批、审计和回滚版本。

## 6. 数据库开发

- 所有 schema 变更创建 migration ID；
- migration 支持 dry-run、校验和重复执行保护；
- 禁止直接在线手改生产文档作为常规发布方式；
- 本地 seed 只使用合成数据，并标记 `source=seed`；
- 查询必须有 scope、limit、确定性排序和索引；
- 列表不返回消息正文/大字段；
- 写操作使用服务端时间、幂等和必要事务/乐观锁。

## 7. 错误处理

客户端：

- 根据错误码展示可操作文案；
- 网络/可重试错误保留草稿和幂等键；
- `FORBIDDEN` 不提示资源是否存在；
- 显示 requestId 供客服定位，不显示堆栈；
- loading 在 `finally` 关闭，避免重复点击。

服务端：

- 区分校验、认证、权限、冲突、外部依赖和内部错误；
- catch 未知错误后记录受控上下文，返回 `INTERNAL_ERROR`；
- 不把 `error.message` 原样回传；
- AI 失败不能伪造成正常分数/回复。

## 8. 日志

允许记录：requestId、actor hash、资源业务 ID、action、状态、耗时、错误码、模型版本、token/费用。

禁止记录：API key、Authorization、session、openid 明文、完整对话、真实病历标识、完整模型提示、数据库连接串。

开发调试需要正文时使用合成数据；生产敏感日志临时提升必须有审批、时间限制和销毁计划。

## 9. Git 与评审

- 分支名清晰描述任务；小提交、单一意图；
- PR 描述包含问题、方案、风险、测试、截图、数据/API/合规影响和回滚；
- 不提交 IDE 私有配置、构建缓存、依赖目录、密钥和真实数据；
- 修改权限、模型、安全、隐私、migration 时指定对应 Code Owner；
- 评审者重点检查“服务端是否重新校验”，不能只看 UI 是否隐藏；
- 发现仓库已有无关改动时不覆盖、不重置，限定修改范围。

## 10. 新接口开发模板

1. 在 contract 定义输入、输出、错误码和 schema；
2. 写权限与状态机测试；
3. 实现 use-case；
4. repository 使用业务 ID 和 scope；
5. handler 接入可信身份、幂等、日志和响应 mapper；
6. 客户端 service 解析 DTO，不接触数据库字段；
7. 增加集成/E2E 和观测指标；
8. 更新 API、数据模型和发布文档。

## 11. AI 功能开发模板

1. 定义用例边界、风险等级和失败降级；
2. 确认数据能否发送给供应商并做脱敏；
3. 定义结构化输出 schema；
4. 版本化提示词和审核知识来源；
5. 通过 AI Gateway provider 调用；
6. 输入前风险分级、输出后 schema/引用/安全校验；
7. 记录模型/提示/知识/策略版本与最小 trace；
8. 加入黄金集、红队集和成本测试；
9. 医学审核、灰度和回滚配置；
10. UI 显示 AI 标识、边界、引用和反馈入口。

## 12. 小程序专项规范

- 页面与组件 JSON 明确：组件必须 `"component": true`；
- 所有跳转目标存在并在 `app.json` 注册；
- 静态资源只保留 `miniprogram/resource` 或明确的 assets 目录，引用校验进 CI；
- 页面卸载时取消可取消的请求/计时器；
- 列表使用稳定业务 ID 作为 `wx:key`，不用 index；
- 控制 `setData` 大小，不整段反复发送长消息数组；长对话做分页/增量更新；
- 本地存储 key 带 schemaVersion 和 userId namespace；退出登录清除敏感缓存；
- 授权拒绝、弱网、切后台、低版本基础库都要有可恢复体验。

## 13. 文档维护

- 架构或技术栈变化写 ADR；
- 新集合/状态同步更新数据模型；
- 新接口同步更新 API 文档和契约；
- 新模型/提示词/安全策略更新 AI 文档、评测版本和回滚说明；
- 每个季度或重大监管变化后复核合规链接；
- 文档中的“建议”被团队批准后，应改为明确 owner、日期和实施状态。
