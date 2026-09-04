# S2 第三轮审阅记录

日期：2026-08-30。范围：T03/T04 第二轮整改后的两个独立 Worktree。**本轮已复验关闭上一轮五项阻断；另确认一项 P2 测试缺陷，T04 尚不能完整接收。未集成候选，未进入 S3。**

本次为审阅，不修改执行者的业务代码、测试或门禁，不自动派发下一轮开发。前两轮记录保留：[第一轮](S2-review-01.md)、[第二轮](S2-review-02.md)。

## 当前发现

### R03-TEST：微训练竞争测试混淆 attempt ID 与 assessment ID（P2）

- 位置：T04 Worktree 的 `backend/tests/test_t04_concurrency.py:338`。
- `LearningApplication.ensure_for_assessment(actor, attempt_id)` 的第二个参数是训练 attempt ID；测试却传入 `_assessment_id`。普通空库测试中两个自增 ID 恰好相同，所以四项竞争/重试测试全部通过。
- 独立复现：在原测试的 `_prepare_assessed_source` 执行前，通过 `_prepare_completed_source(client, 'review_unassessed_attempt')` 创建另一个学生的已完成但未评估 attempt，再执行原准备逻辑和原测试体。真实数据库此时目标 `attempt=2`、`assessment=1`；原第 338 行抛出 `RESOURCE_NOT_FOUND`，退出码 1，尚未进入微训练竞争屏障。
- 影响：测试依赖不成立的跨表 ID 相等假设；增加种子或改变准备数据即可导致误失败，不能作为稳定的微训练竞争回归证据。本轮搜索到的生产调用方使用 attempt ID，**没有据此认定生产接口存在同样错误**。
- 完成标准：第 338 行传入 `_attempt_id`；准备数据明确保证目标 attempt ID 与 assessment ID 不相同。保留两个独立 Session、屏障参与两次、返回同一任务 attempt、最终只有一条任务 attempt 的断言；复跑四项竞争/重试测试和后端完整检查。无需重做已通过的分层或评分实现。

复现仅使用 pytest 的内存 hook 包装准备函数，未改源码；测试依旧由 T01 fixture 管理。失败资源依规则保留在 `C:/Users/adj/AppData/Local/Temp/medical-qa-pytest-vgoyfx5k`，未手动清理。

## 上一轮问题关闭证据

| 上轮问题   | 本轮独立复验                                                                                                                                          |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| R02-FE     | domain 中 `import('vue').Ref` 和页面异步 `uni.setStorage` 均分别命中一条违规。                                                                        |
| R02-FE-SFC | 正常 Vue 外置 script 指向 feature infrastructure 被拒绝；shared 的 `fetch('/api')` 被拒绝。SFC 已通过 Vue compiler 解析。                             |
| R02-BE     | 真实源码索引加虚拟探针：别名 Session 参数 commit、domain 导入 app.core.config、shared 反向导入 infrastructure、import_module 别名四类均分别命中违规。 |
| R02-TYPE   | follow_imports=normal；公开合同进入显式目标；63 个源文件类型检查通过，不存在的方法和错误参数负例均被拒绝。                                            |
| R02-RACE   | assessment 测试改为先准备未评估 attempt；独立内存观测得到 `REVIEW_BARRIER_CALLS=2`，原四项竞争/重试测试全部通过。                                     |

## 本轮实际执行

T03：`C:/Users/adj/.codex/worktrees/66ca/wxprogrom7.15`。T04：`C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15`。后端直接 Python 命令在其 `backend` 目录执行。

| 候选／命令                                                      | 退出码 | 结果                                                                                    |
| --------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------- |
| T03 `node scripts/frontend-boundaries.mjs --self-test`          | 0      | targeted-negative=26；正例无违规。                                                      |
| T03 `node scripts/frontend-boundaries.mjs`                      | 0      | 117 个实现文件。                                                                        |
| T03 独立四类历史失败探针                                        | 0      | 每类均拒绝；无源文件写入。                                                              |
| T03 `npm run check`                                             | 0      | 格式、Lint、类型、20 文件/93 测试、微信/H5 构建通过；行96.55%、分支86.26%、函数92.11%。 |
| T03 `npm run contract:check`                                    | 0      | 临时目录生成比较通过。                                                                  |
| T04 `python scripts/check_boundaries.py --self-test` / 正式检查 | 各0    | 正负探针通过；8 modules、4 layers。                                                     |
| T04 真实索引四类历史失败探针                                    | 0      | 每类均拒绝。                                                                            |
| T04 `python scripts/type_check.py`                              | 0      | 63 files，无类型错误。                                                                  |
| T04 `python scripts/type_check.py --negative`                   | 0      | 底层 mypy 拒绝错误调用，脚本核实两种诊断。                                              |
| T04 `npm run backend:test:safety`                               | 0      | 14 passed，42.30秒，13个既有外键排序警告。                                              |
| T04 `npm run backend:test:migrations`                           | 0      | 2 passed，18.58秒，1个既有警告。                                                        |
| T04 原四项竞争测试加独立屏障观测                                | 0      | 4 passed，3.30秒；assessment 屏障参与2次。                                              |
| T04 微训练竞争的不同 ID 准备数据探针                            | 1      | 目标 attempt=2、assessment=1；第338行 RESOURCE_NOT_FOUND。                              |
| T04 `npm run contract:check`                                    | 0      | 临时目录生成比较通过。                                                                  |
| 两个候选 `git diff --check`                                     | 各0    | 无空白错误。                                                                            |

T04 `npm run backend:check` 本轮退出码 0：Ruff 通过，78/78 测试通过，覆盖率 89.56%（5286 statements / 552 miss），耗时 80.87 秒，77 个既有外键排序警告。普通测试通过不能消除上述不同 ID 探针暴露的测试缺陷。

原工作区三份审阅/状态文档已通过 Prettier；项目 skill 的结构、链接和事实标签自检退出码 0，`git diff --check` 退出码 0。

## 审阅快照

以下 SHA-256 标识本轮实际审阅的关键文件，而非整个候选树快照。

| 候选／文件                                  | SHA-256                                                            |
| ------------------------------------------- | ------------------------------------------------------------------ |
| T03 `scripts/frontend-boundaries.mjs`       | `B86B8E82FDE5277D4B6187433DBDE17BB479D3B0A90E3AE8C6D91A6EE112DB19` |
| T03 `config/frontend-boundaries.json`       | `FCEA40F7AE80610C23EFBAF85A3779883D89A98204636BEAFEFB1C450B66413F` |
| T04 `backend/scripts/check_boundaries.py`   | `8F1B5A09E2E08C7DDDE77C593D37CDE5E4F714B76451B8F3F01A191898D5FA95` |
| T04 `backend/scripts/type_check.py`         | `9EB224D99FBA5D18E6BEA64B9195C20E0540282BBE6DE8E42680D57FC4DD6A16` |
| T04 `backend/mypy.ini`                      | `CC454705A3C4C916985210E2C886938448326537A4B6EEC1C798F59CA53CBC42` |
| T04 `backend/tests/test_t04_concurrency.py` | `D0C3908A9802F332B173AD45A733C6FE15BDB8EB906FD6D4D5983046BE342D5B` |

## 范围、限制与后续

- T03 本轮整改项通过，未发现新的前端阻断；不等于已完成组合版本验收。T04 剩余一项明确的 P2 测试修正，不能继续沿用上一轮“类型/边界/assessment屏障仍失败”的状态描述。
- 本轮未重跑 E2E：T03 最新整改集中于门禁脚本与配置，上一轮同一候选业务流程已有 API 8/8、Demo 1/1 证据。T03 与 T04 尚未集成，下一阶段仍须跑组合回归和接入总门禁；历史单侧 E2E 不能替代组合测试。
- 没有接口、schema、API/Demo 模式、权限策略、数据或迁移改动。无真实 AI/微信调用；没有迁移或清理开发库、共享库、生产库。安全与迁移检查只使用受管临时资源。
- 不重复扫描或读取历史秘密。历史凭据撤销、远程 CI/分支保护、目标 Node22/Python3.12、真机和医学审核仍未验证，属于发布限制。
- 原工作区仅新增本报告并更新计划状态链接；保留已有未提交/未跟踪改动及旧文档删除状态，未提交、推送、合并或替换候选实现。没有业务数据回退事项；文档如需回退，只撤回本轮审阅记录和状态更新。
