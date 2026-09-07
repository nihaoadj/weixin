# 验证与回退

## 分阶段验证

- S0：scoped Prettier、相对链接、尾随空白、`git diff --check`、skill self-check。
- S1：`backend:test:safety`、`backend:test:migrations`、0020 专项权限/幂等测试。
- S2：PBL API、provider、状态机和两轮闭环测试；后端边界 self-test/检查。
- S3：`contract:generate` 后人工审阅生成差异，随后 `contract:check`。
- S4：前端边界 self-test/检查、format check、Lint、类型、单元测试、H5/微信构建及 API/Demo E2E。
- S5：后端完整检查、秘密扫描与最终 `git diff --check`。

不得通过跳过、放宽 schema、关闭权限或改写快照伪造通过。未执行真实 Coze、微信真机、生产迁移、部署和远程 CI，必须作为外部阻塞记录。

## 必须验收的场景

- 单班自动、多班显式选择、无班拒绝；跨学生/班级/教师统一拒绝。
- 重复创建、start 和消息返回同一结果；方式变更冲突。
- guided/direct 都只能引用当前阶段学生证据，并产生同构诊断和同一后续闭环。
- direct 不能仅依据首问直接 ready；必须回答后取得学生理解证据。
- completed 锁定新消息；旧 message ID 重试仍可读取既有结果。
- 旧 QA 数据不进入新诊断；旧深链可读、可安全续开。
- API 失败不切 Demo，Coze provider/mode 不 fallback，日志不含完整消息或 prompt。

## 回退

- 数据库迁移只在受管测试资源验证，不运行 `backend:migrate` 指向未知数据库。
- 后端先兼容发布再切前端；回退前端时旧接口继续可用。
- 0020 有业务新数据时拒绝 downgrade；需要回退数据库时从迁移前已验证备份恢复。
- 代码回退必须保留旧 conversation/report 与新增数据，不执行 reset、clean 或删除用户数据。
