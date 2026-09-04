# S2 组合集成与验收

日期：2026-08-30。当前状态：T03/T04、INT-01 和 R05 边界修复均已按增量集成并完成主工作区组合验收。最终证据见 [S2 分层迁移组合验收](S2-acceptance.md)；本文件保留首轮失败和修复派发过程。

## 集成保护

- 原工作区：`D:/CODE/weixin/wxprogrom7.15`；HEAD 保持 `b96bab910dc5ee43410fa55c5b856cc4d3f3415d`，没有提交、推送、合并提交或部署。
- T03 来源：`C:/Users/adj/.codex/worktrees/66ca/wxprogrom7.15`；T04 来源：`C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15`。
- 集成备份：`C:/Users/adj/AppData/Local/Temp/wx-integrate-s2-fwgc8nm1`。`root-before.json` 记录294个原工作区路径，`backup/` 保存存在文件的副本，`plan.json` 记录每项来源、before/after SHA-256；全部写入前先核对当前内容，完成后核对范围外文件没有变化。
- 共396项增量：T04修改43、新增160；T03修改38、新增94、删除59；另顺序合并2份共享文档。59次删除仅针对已有迁移映射、通过before hash校验的精确旧前端文件；没有递归删除。`docs/update/README.md` 仍保持用户原有删除状态，0009迁移保持原样。
- `docs/architecture.md` 的前端/后端职责及同一统计说明段落合并；ADR保留两方完整补充，而非覆盖其中一方。`docs/update_plan/README.md` 与执行状态不从旧Worktree复制。
- 集成后只对受影响的4份Markdown和 `config/backend-boundaries.json` 统一Prettier排版；首次 `npm run check` 因该JSON排版退出1，修正后完整通过，未更改规则内容。
- `post-integration/manifest.json` 和 `post-integration/files/` 保存547项路径的集成后快照，用于限定后续回归修复增量；不以HEAD代替包含用户改动的实际基线。

## 首轮组合检查

| 检查                              | 退出码／结果                                                                   |
| --------------------------------- | ------------------------------------------------------------------------------ |
| 前端边界 self-test / 正式检查     | 各0；26个负向命中，117个实现文件                                               |
| 后端边界 self-test / 正式检查     | 各0；8模块、4层，正负检查通过                                                  |
| 后端严格类型 / 错误调用负例       | 各0；63源文件，错误方法与参数被拒绝                                            |
| `npm run backend:test:safety`     | 0；14 passed，50.18秒，13个既有外键排序警告                                    |
| `npm run backend:test:migrations` | 0；2 passed，16.77秒，1个既有警告                                              |
| `npm run check`（排版修正后）     | 0；格式、Lint、类型、93测试、微信/H5构建通过；行96.55%、分支86.26%、函数92.11% |
| `npm run contract:check`          | 0；临时生成与既有快照比较通过，没有改写生成物                                  |
| `npm run backend:check`           | 0；Ruff、78 passed，覆盖率89.56%，92.95秒，77个既有警告                        |
| 工作树及 `dist/build` 秘密扫描    | 各0；均findings=0；不重复读取历史秘密值                                        |
| API组合E2E                        | 1；7 passed / 1 failed，47.8秒；API端口18321、H5端口41921                      |
| Demo E2E（另行执行）              | 0；1 passed，20.2秒；端口41922，无API请求                                      |

API测试失败后未继续同一链条的Demo命令；统筹单独执行Demo，失败制品先复制到备份的 `e2e-initial-failure/`，避免后一次测试覆盖。所有后端/E2E数据由T01受管临时资源创建，未使用开发数据库，未调用真实AI或微信。

## INT-01：病例草稿生成行为丢失（已关闭）

`e2e/review-and-class-flow.spec.ts:62` 保留原断言：输入“急性胸痛”，预期既有主题模板标题“急性胸痛：危险分层与证据推理”，组合版本返回“急性胸痛：结构化临床推理”。其他7项API E2E和Demo均通过。

进一步源码对比发现，`content/infrastructure/draft_generator.py` 无条件使用通用确定性草稿，删除teacher关联；`content/application/use_cases.py` 不再进行草稿生成审计。集成前的 `services/case_ai.py.generate_draft` 会通过结构化模型调用处理成功路径，失败/disabled使用 `showcase_draft(topic)` 的主题模板，并保存 `case_draft` AI审计与提交。该退化不是仅修改E2E标题期望就能解决的问题。

原 T04（Luna Max）恢复模型成功、disabled/错误 fallback、主题模板、审计和事务失败路径；统筹冻结 payload 比较四主题一致，独立 API/真实数据库事务探针合计 9 passed。第五轮审阅发现的跨模块 API 依赖和边界漏检由 R05（Terra High）修复并独立验收。有限增量同步主工作区后，API E2E 8/8、Demo E2E 1/1、后端 84/84 和前端 93/93 均通过，原断言未放宽。

## 后续、发布限制与回退

- S2 组合基线已经冻结；T02/T05/T06/T07 最终工作以 [S2 验收](S2-acceptance.md) 为起点。原执行目录保留前序交付现场，后续使用新隔离 Worktree，不整目录覆盖原执行者工作。
- `frontend:boundaries` / `backend:boundaries` 的底层脚本已集成并验证；npm统一入口、CI/关键覆盖率及权威规范文档收尾仍需T02/T05/T07完成，当前不可宣称全套门禁已接入。
- 远程CI/分支保护、目标Node22/Python3.12、微信真机、历史凭据撤销与医学审核仍未验证；源码/构建物扫描为零不解除这些发布条件。
- 如需撤回集成，先比较当前文件与本轮postimage，只有内容仍匹配的文件才按 `plan.json` 和 `backup/` 逐项恢复；新文件只在确认未被其他任务修改或接管后精确删除，不reset/clean，不恢复用户此前删除的旧文档。不涉及数据库降级或业务数据回退。
