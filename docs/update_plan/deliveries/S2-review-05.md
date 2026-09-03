# S2 第五轮候选修复审阅

日期：2026-08-30。审阅对象为原 T04 Worktree `C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15` 中用于关闭 INT-01 的 R04 病例草稿修复。原工作区没有同步本轮候选业务代码，没有提交、推送、合并或部署；已有未提交/未跟踪改动和 `docs/update/README.md` 的删除状态均保留。

**结论：R04 已恢复病例草稿的模型成功、确定性降级、主题模板、审计和回滚行为，但存在 1 项 P1 模块边界阻塞。INT-01 的行为修复可以保留，S2 尚不能验收或进入 S3。**

## P1：content infrastructure 依赖 training API 内部 schema，且边界门禁漏检

- `backend/app/modules/content/infrastructure/ai_schemas.py:8` 直接导入 `app.modules.training.api.schemas.CaseDraftGenerateResponse`，使 content 的外部 AI adapter 依赖另一个业务模块的 HTTP schema。`config/backend-boundaries.json:146-149` 又为这项依赖增加逐路径例外，而不是把草稿合同放回 content 自己的 API/provider schema 或稳定公开合同。
- 当前 `backend/scripts/check_boundaries.py:599-605` 只在跨模块目标角色为 `application/domain/infrastructure` 时报告内部导入，遗漏 `api`。统筹以空 `allowed_imports` 对合成 `content/infrastructure/probe.py` 执行真实 `_build_index()` 和 `_check_source()`；`from app.modules.training.api.schemas import CaseDraftGenerateResponse` 返回 `[]`。因此配置例外对现有门禁没有实际作用，删除例外后违规仍会被错误放行。
- 正式 `check_boundaries.py --self-test` 与仓库检查均退出码 0，但自测没有“模块 infrastructure 导入其他模块 api”负例。这证明当前通过结果存在覆盖盲区，不能作为 BE-01 的完成证据。
- 该依赖与 T04 的 `public.py` 公开合同职责、其他模块经公开合同协作的规则，以及 T04-08“合法图通过、禁止依赖能失败”的完成条件冲突。它会把 HTTP/Pydantic schema 的变更传播到 content infrastructure，也允许后续同类穿透在门禁中静默通过。

### 限定修复与完成标准

1. 由 content 自己定义病例草稿的 provider 校验 schema；可复用稳定的 content-owned/public 嵌套类型，但 `content/infrastructure` 不再导入或 re-export `training.api`。
2. 删除 `config/backend-boundaries.json` 中仅为 `content/infrastructure/ai_schemas.py -> training.api.schemas` 增加的例外；既有 AI audit 表的精确 ORM 例外不在本缺陷范围。
3. 扩充边界检查和 self-test：非 `api/wiring` 层导入其他业务模块 `api` 必须失败；合法的 `*.public` 合同继续通过。负例必须在没有 allowlist 的情况下稳定命中 `cross-module internal import`。
4. 修复不得改变 HTTP path/method、OpenAPI 字段、模型成功与 fallback payload、审计字段、事务归属、迁移或前端合同；不得复制第二套病例主题 payload。
5. 候选 Worktree 复跑边界 self-test/正式检查、严格类型及负例、病例草稿定向测试、`backend:check`、`contract:check`。统筹按 preimage 限定同步后，再在 T03/T04 组合版本重跑 API E2E；原胸痛标题断言必须通过。

## 已通过的行为与合同证据

- 统筹使用 S2 集成前冻结文件 `C:/Users/adj/AppData/Local/Temp/wx-integrate-s2-fwgc8nm1/pre-s2-expected-drafts.json`，对急性胸痛、右下腹痛、未知主题和社区获得性肺炎逐对象比较；`deterministic_case_draft(..., "undergraduate", ["识别危险信号", "说明证据"])` 四项均为 `True`。冻结文件 SHA-256 为 `A6E09E6396BDBA06066CAD472744901B41E2AF2AC58280C63837395DE23B2C77`。
- 独立 pytest 插件 `C:/Users/adj/AppData/Local/Temp/wx-integrate-s2-fwgc8nm1/verify-content-transaction.py` 复用 T01 受管 fixture，补充真实 API 模型成功及数据库 audit、audit flush 后异常回滚、commit flush 后异常回滚三项探针；与候选六项测试合计 9 passed，退出码 0，4.20 秒。失败响应为 503，失败事务后不存在残留 audit row；没有调用真实 AI、微信或未知数据库。
- 本轮统筹复跑：边界 self-test 17 项和正式 8 模块检查退出码 0；严格类型 64 个源文件和错误调用负例退出码 0；`npm run contract:check` 退出码 0并在系统临时目录完成比较。边界命令的“通过”受上述 P1 漏检限制，不能解除阻塞。
- 执行者交付记录报告定向后端 30 passed、全后端 84 passed、覆盖率 89.77%，以及 Ruff/compileall/契约/边界/类型通过。统筹本轮没有再次运行全后端、安全、迁移或组合 E2E；原因是当前静态边界缺陷已经阻止候选集成，且这些检查在限定修复后必须重新执行，不能把执行者历史结果标为本轮独立全量复验。

## 影响、回退与后续

- R04 没有改变 Alembic、数据库表列、API/Demo 分界或权限策略；只复用既有 `ai_call_logs`，失败路径回滚本次未提交 audit。现有教师报告范围和历史凭据发布阻断均未改变。
- R04 preimage 位于 `C:/Users/adj/AppData/Local/Temp/wxprogrom7.15-T04-increment-20260830-r04-content`。若限定修复失败，只按 preimage 和当前 hash 逐文件恢复；不使用 reset/clean，不目录覆盖，不执行迁移 downgrade。
- 原 T04 执行任务在代码与报告落盘后因 Codex 用量限制结束，没有产生可靠的最终任务消息；统筹已直接核对工作区文件和上述证据。解除 P1 后仍需将有限增量同步到原工作区并完成组合 E2E，才能关闭 INT-01 和冻结 S2 基线。
