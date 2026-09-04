# T10 执行清单

## P0：计划门禁

- 格式、相对链接、尾随空白和工程 self-check 通过。
- 记录 `7eeb46b` 后的工作区状态，保护用户改动并排除临时产物。

出口：计划已锁定，尚未修改运行时代码。

## P1：边界收口

- 建立 PBL repository、classroom scope、content publication 和 UoW ports/records。
- 移除 application/API/public 的 ORM、Session 和数据库调用，更新 composition root。
- 运行后端边界 self-test 和正式检查。

出口：当前 7 个边界错误归零，无新增 allowlist。

## P2：数据和幂等

- 实现 0016、`pbl_messages` 和 JSON 历史 backfill。
- 覆盖重复消息、revision 竞争、suggestion 状态保护和采用发布原子性。

出口：T01 安全/迁移及 PBL repository/use-case 测试通过。

## P3：三 adapter 合同

- 完成脱敏 request builder、严格 parser、Bot/Workflow SDK 事件映射和普通 API 映射。
- 完成配置矩阵、失败类别和同 fixture 等价测试，不进行真实网络调用。

出口：Mock 测试通过，无 fallback 或敏感字段泄漏。

## P4：API 与前端

- 补齐 schema、分页/详情、教师课堂管理和学生分析展示。
- 同步 API/Demo、生成契约与 mapper。

出口：契约、类型、前端边界和组件行为测试通过。

## P5：闭环验收

- 运行完整后端、数据库安全/迁移、格式/Lint/类型/边界、微信/H5 构建和本地 Mock E2E。
- delivery 记录退出码、权限/敏感信息、未执行真实 Coze 的原因和回退。

出口：仅在全部仓库门禁通过后标记“仓库内完成、真实 Coze 外部联调未验证”；提交或推送另需用户授权。
