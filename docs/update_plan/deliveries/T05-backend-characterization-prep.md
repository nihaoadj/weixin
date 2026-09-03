# T05 增量：后端 characterization 就绪与 remoteAuth 分支

记录范围：本次仅交付 T05 重构前后样板的静态后端准备，以及 `remoteAuth` 剩余关键分支的前端可运行测试。  
工作树：`C:\Users\adj\.codex\worktrees\c9b6\wxprogrom7.15`。  
状态：前端增量已验证；后端 characterization 仅静态准备，等待 T01 正式交接后运行。  
根报告：未修改统筹方已集成／修订的既有报告，仅新增本增量记录。

## 文件保护与增量清单

在修改前已将 `src/services/remoteAuth.spec.ts` 复制到独立临时目录，并记录原 SHA-256：

- 备份：`C:\Users\adj\AppData\Local\Temp\t05-increment-dfb01d240af946baaea6bfd20286779e\remoteAuth.spec.ts`
- 修改前 SHA-256：`F66833F1555513FE8954A96D10FA6AC1E37E096B95F71134EA241D2B134B1BB0`

新增文件在本次开始前不存在，因此没有原 hash：

- `backend/tests/test_characterization.py`
- `docs/update_plan/deliveries/T05-backend-characterization-prep.md`

本次修改仅涉及上述两个新增文件和 `src/services/remoteAuth.spec.ts`；未修改实现、package/lock、coverage/CI、E2E 或现有统筹报告。

## remoteAuth 可运行增量

在 `src/services/remoteAuth.spec.ts` 新增以下完整测试名：

| 测试名                                                                                        | 观察合同                                                                                |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `syncDemoLoginWithBackend is a no-op in Demo mode and preserves an existing token`            | Demo 模式不发 HTTP，请求前已有 token 保持不变并返回空权限。                             |
| `syncDemoLoginWithBackend preserves an existing token when the API request fails`             | API 网络失败返回 `NETWORK_ERROR`，旧 token 不被清理。                                   |
| `syncWechatLoginWithBackend rejects outside API mode without invoking the WeChat SDK or HTTP` | 非 API 模式抛出“微信登录仅适用于 API 模式”，不调用 `uni.login` 或 HTTP，旧 token 保持。 |

执行环境：Windows PowerShell；Node `v24.14.0`；npm `11.9.0`；Vitest `3.2.6`。命令与真实结果：

```powershell
npx vitest run src/services/remoteAuth.spec.ts
```

退出码 `0`；1 个测试文件、10 个测试通过、0 个失败；Vitest 报告时长 1.34 秒。此前已有的微信成功／无 code／取消／坏 DTO／缺 user／教师返回学生旧 token 分支仍保留并同文件执行。

## 后端 characterization 静态样板

新增 `backend/tests/test_characterization.py`，只依赖 T01 应提供的两个 fixture：

| Fixture  | T01 交接要求                                                                                                                                                                                               |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client` | 与 `db` 使用同一个受管临时数据库的 FastAPI `TestClient`；不连接应用默认开发库；为提交失败样板设置 `raise_server_exceptions=False`，使 500 响应可观察；生命周期结束关闭客户端。                             |
| `db`     | 与 `client` 相同临时资源的 SQLAlchemy `Session`；按测试隔离、可回滚、结束关闭；fixture 内部负责 schema/迁移和资源所有权。本文件不创建 engine、导入应用 engine、`create_all`、`drop_all` 或删除数据库文件。 |

文件中的测试及拟比较的当前行为：

1. `test_report_state_visibility_and_reviewer_audit`：学生 A 创建草稿；教师在草稿阶段批阅返回 `409/STATE_CONFLICT`；学生 B 获取 A 的报告返回 404；A 提交后变为 `pending_review`，重复提交为 `409/STATE_CONFLICT`；审核者完成批阅为 `reviewed` 并在响应中留下其 `reviewer_id`。没有断言教师报告班级范围，等待产品政策确认。
2. `test_report_commit_failure_rolls_back_the_draft_without_a_partial_row`：在已存在会话后通过 SQLAlchemy `before_commit` 一次性注入提交异常，期望 API 返回 500，随后受管 `db` 查询不到报告行；用于发现提交失败留下半条报告的缺陷。该测试依赖 T01 client 对服务端异常的可观察配置。
3. `test_publish_rejects_a_stale_review_digest_and_invalidates_approval`：使用受管 `db` 中的 `cap-undergraduate-showcase`，修改已审核病例标题后调用发布；期望 `409/STATE_CONFLICT`，病例仍保持 `published` 但 `medical_review_status` 变为 `not_submitted`，变更内容不被回滚。这是当前 digest 失效语义，不把它改写成新政策。
4. `test_repeated_completion_and_learning_plan_creation_are_sequentially_idempotent`：完成五阶段病例后重复 `/complete`、重复按 assessment 创建计划、重复启动首个 focused-retry 任务；期望 assessment、plan、`learning_plan_ready` 通知各仅一条，响应 ID／总分／任务 ID 稳定，第二次 start 返回相同 case attempt。测试名称明确为 sequentially；没有把顺序调用冒充真实并发。

训练样板使用固定的五阶段 payload（`history`、`problem_representation`、`differential`、`tests`、`management`），只断言稳定状态、ID、计数和错误码，不快照时间戳。真实并发完成／计划生成仍需 T01 提供两个独立 session 与屏障后另行补测。

## T01 fixture 就绪清单（后端尚未执行）

统筹方确认 T01 完成后，运行本文件前需逐项确认：

- [ ] pytest 导入应用配置和创建 engine 前已分配不可预测、独占的临时数据库；继承 `DATABASE_URL` 不会触碰开发库。
- [ ] `client` 与 `db` 绑定同一隔离资源，TestClient lifespan／依赖覆盖／Session 关闭顺序有证据。
- [ ] fixture 支持本文件通过 `db` 调用 `seed_showcase_case`，或 lifespan 已提供同等 `cap-undergraduate-showcase`；不得由本测试创建全局 engine 或清表。
- [ ] `raise_server_exceptions=False` 的 500 注入路径已被 T01 安全验证；异常后 session 可回滚，查询不会读到半写报告。
- [ ] `0009` 为有效 head，`users.auth_provider`、`reports.reviewer_id` 已在临时迁移矩阵中验证；报告审计样板可读取 reviewer 字段。
- [ ] 运行并发样板时提供独立 session／屏障和冲突诊断；当前文件的顺序幂等测试不替代并发验收。
- [ ] 教师报告班级范围、审核者学情访问范围由产品/T06 书面确认后，另增政策测试；本增量不锁死该语义。

T01 正式交接后，先执行安全入口，再单独执行本 characterization 文件：

```powershell
npm run backend:test:safety
npm run backend:test:migrations
cd backend
python -m pytest tests/test_characterization.py -q
```

上述命令当前均未执行；最后一条在 T01 fixture 未落地时预期无法安全运行，不能以默认 `dev.db` 替代。

## 未执行项与结论

- 本增量没有运行任何后端 pytest、`backend:test`、`backend:check`、E2E、`check:all`、迁移或默认开发库验证。
- 没有发现前端实现缺陷；新增 remoteAuth 测试均通过。
- 后端测试文件是可审阅的静态样板，不代表当前后端行为已验证；T01 fixture、迁移 head 和未决权限政策完成后才能产生后端执行证据。

## 统筹集成复验补充

上述表述是子任务交付时的历史事实。T01 集成后，统筹将提交失败用例接入 `capture_server_errors` 受管 marker，并在同一受管临时数据库上执行本文件：4/4 通过，退出码 0。`remoteAuth.spec.ts` 同步通过 10/10；前端全量现为 20 个文件、93/93。教师报告班级范围仍未决定，本基线没有锁死该政策；真实并发和最终关键模块独立门槛仍属于 T05 后续工作。
