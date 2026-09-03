# S2 第四轮修复与复验

日期：2026-08-30。用户明确要求统筹指挥修复后，已在原 T04 任务（Luna Max）派发 R03-TEST 的限定修复。没有创建重复任务，也未扩大为业务改造。

**结论：R03-TEST 已修复并通过统筹复验，关闭该 P2 缺陷。T03/T04 当前已知审阅问题已关闭，候选可进入组合集成验证；尚未集成或完成 S3。**

## 修复内容与独立证据

- 修复位于 `C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15/backend/tests/test_t04_concurrency.py`：计划准备传入正确的 attempt ID；先创建另一个合成学生未评估的 attempt，使目标 attempt 与 assessment 的 ID 不同，并增加关联和未评估状态断言。
- 保留两个独立 Session、竞争屏障、相同返回 ID、最终一条任务 attempt 的断言。测试和临时数据库仍由 T01 fixture 管理，没有迁移或清理开发/共享/生产数据库。
- 统筹通过 pytest 内存 hook 观察目标准备函数和 `BarrierTaskRepository.mark_task_started`，四项竞争/重试测试退出码 0：`REVIEW_MICRO_IDS [(2, 1)] BARRIER_CALLS 2`，4 passed，3.60秒，3个既有外键排序警告。该独立探针没有修改源文件。
- 执行者完整检查证据：`npm run backend:check` 修正后退出码 0，Ruff + 78 passed，覆盖率89.56%，84.05秒；首次检查因新增断言超行长退出1，已修正排版，未跳过规则。详细历史在 T04 Worktree 的 `docs/update_plan/deliveries/T04.md`。

统筹独立执行 `npm run backend:check` 退出码 0：Ruff 通过，78 passed，覆盖率89.56%（5286 statements / 552 miss），87.20秒，77个既有外键排序警告。独立观测后唯一后续测试代码调整为长断言排版；最终快照见下表。

## 范围核验与回退

统筹派发后的 243 个后端源码、测试、脚本、迁移、配置及共享契约文件 SHA-256 清单保存在 `C:/Users/adj/AppData/Local/Temp/wx-review-r03-u21f7qvx/before.json`。最终核验只有目标测试文件的内容变化，扫描范围内无新增源文件，检查退出码0；该清单不包含 Markdown，执行者另更新了自己的 T04 交付记录。候选 `git diff --check` 退出码0。

| 文件                                    | 修复前 SHA-256                                                     | 修复后 SHA-256                                                     |
| --------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `backend/tests/test_t04_concurrency.py` | `D0C3908A9802F332B173AD45A733C6FE15BDB8EB906FD6D4D5983046BE342D5B` | `00F77CD10C7CC07E5EF8B3A57B3198C35BDB2981AE4D40F97F3192B9EED9EA1C` |

执行者两文件 preimage 备份位于 `C:/Users/adj/AppData/Local/Temp/wxprogrom7.15-T04-increment-20260830-r03`。如需撤回本轮测试修复，应先核对当前 hash，再仅恢复对应文件；不 reset/clean，不回滚业务数据，不覆盖其他候选改动。

## 验收边界与下一步

- 本轮只修复测试及证据，不改变 API/schema、生成契约、API/Demo 模式、权限或业务行为；不改变 fixture、engine 或迁移。
- 因相关实现未改，本轮不重复运行安全/迁移、契约、前端、E2E 和秘密扫描；前轮通过证据见 [第三轮审阅](S2-review-03.md)，不将历史结果标记为本轮重跑。
- R03-TEST 完成后可解除 T04 当前已知候选阻断；不代表整个项目或生产发布验收完成。T03/T04 仍在独立 Worktree，尚未集成原工作区；下一阶段应按基线 hash 保护已有改动、顺序集成，再运行组合 E2E 和全套门禁，并完成 T02/T05/T06/T07 的最终任务。
- 历史凭据撤销、远程 CI/分支保护、目标运行时、微信真机与医学审核仍未验证，仍为发布条件。没有调用外部 AI/微信，没有提交、推送、合并或部署。
- 原工作区仅更新统筹验收和计划状态文档，保留所有已有未提交/未跟踪改动与 `docs/update/README.md` 删除状态。
