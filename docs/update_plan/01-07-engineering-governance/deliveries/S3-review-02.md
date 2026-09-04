# S3 第二轮审核与 T06 接收

日期：2026-08-31。结论：**T06 本地代码及交付格式已接收并集成；T05 首轮返修仍不合格，已继续下发 R2。S3 未通过，T02 最终 CI 接线暂缓。**

用户在首轮返修分发后要求继续。本轮沿用项目工程 skill，先核对原 Worktree 的完成状态、交付内容与指纹，再执行主工作区受保护同步。没有创建重复任务、降低门槛、提交、推送、合并或生产操作；保留既有改动和 `docs/update/README.md` 删除状态。

## T05：部分进展与第二轮返修

任务：`01a0535e-8b4a-7d13-bc41-caa6dd80d4ad`，Worktree：`C:/Users/adj/.codex/worktrees/0413/wxprogrom7.15`。R1 回合已结束，但执行者仍明确交付“部分完成”。不能用回合结束代替任务完成。

| 项目  | 已观察进展                                                                                         | 尚未关闭                                                                                                    |
| ----- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| R1-01 | 计数/阈值有限性检查已补；自测开始调用真实 `check()`。本轮 type-check 和 checker self-test 均退出 0 | 新增发现：全量及关键组完全零计数也会以 N/A 放行，见 R2-01                                                   |
| R1-02 | Vitest 加入 SFC 插件及 App/pages/components 覆盖率范围                                             | 执行者 R1 报告完整范围行覆盖率 49.82%，未达到 85%；本轮未重跑其正在返修的全量前端，不把该数字当作下一版结果 |
| R1-03 | 配置已有独立全量/关键阈值，新增生成临时报表再校验的 `scripts/t05-verify.mjs`                       | 后端全量 branch、learning 门槛和稳定两轮全绿仍缺证据。执行者中止的全量测试不计通过                          |
| R1-04 | 测试已改成首次 in_progress、写冲突、回滚再读 assessed，并新增无赢家的 409 用例                     | 尚需目标故障注入证明；fake port 恢复不冒充真实双 Session 竞争                                               |
| R1-05 | 最终文档已进行格式处理                                                                             | R1 表格中的未转义竖线导致命令/状态列错位；历史与最新证据需继续整理，不能仅凭 Prettier 宣称内容正确          |

R1 指纹清单为 `C:/Users/adj/AppData/Local/Temp/wx-t05-r1-20260831-004227/postimage.json`；其中 checker 为 `F7711666EC8FA14E1E6AFCC2283AAAA372C8BF23BFB15E4830309355D92CB5AA`。该记录定位本次被审阅版本；T05 已继续编辑，不宣称该指纹永久代表候选最新状态。

### R2-01 / P1：零行计数不能作为不适用指标放行

位置：R1 版本 `scripts/critical-coverage.mjs` 的 `checkGroup()`、`checkOverall()`。

现在两处都会将所有 `total === 0` 的指标返回为 N/A，不区分无分支文件与完全没有可执行行统计的关键职责。统筹为配置里的真实关键源文件生成 `s: {}`、`f: {}`、`b: {}` 报告，实际执行 CLI；全量与 identity、HTTP cache、storage、report/training 组均输出 `lines=N/A branches=N/A functions=N/A`，进程错误退出 **0**。因此“文件存在且在报告中”仍不足以证明门禁有效，R1-01 暂不能关闭。

复现证据：`C:/Users/adj/AppData/Local/Temp/wx-s3-r2-review-732j0g9o/empty-counts.json`、`empty-counts.log`。命令为在 T05 Worktree 执行 `node scripts/critical-coverage.mjs --frontend <上述 empty-counts.json 的绝对路径>`。

返修标准：全量及包含可执行实现的关键职责不得接受零行计数；正常没有分支或函数的指标可以按真实适用性处理，但不能豁免整个空实现组。前后端正负例必须通过真实 checker/CLI，同时保留缺计数、低阈值、缺源码/报表和正常无分支文件的断言。

### 已发送的 R2 指令

继续使用 **Terra High**，同任务新回合 `01a05398-88b9-74c2-a760-dc0e57b59217`；发送后 `wait_threads` 已确认 `active`、`inProgress`。

- 保留 R1-01～05 全部标准，先修 N/A 放行和验证入口，再持续补真实 SFC 业务与后端分支；不减阈值、不扩大排除、不构造假执行命中。
- runner 在失败时也要输出临时证据目录，正确传递退出码，并验证 Windows 空格路径。修文档表格及具体场景到测试名映射。
- 工具返回 `session_id` 时用 `write_stdin` 继续读取；`functions.exec` 返回 cell ID 时使用 `functions.wait`，不要把 30 秒等待窗口当作测试失败而杀掉进程。统筹此前完整后端测试已以会话方式等待 101.75 秒完成；本轮主工作区 29 项测试也通过会话等待完成。
- 全量前端 85/80/85、前端关键 90/85/90；全量后端行/分支 85/80、后端关键 90/85 均需新证据。补故障注入、稳定两轮验证和最终指纹后再交付。
- package/锁文件/CI、其他 Worktree、生产政策和迁移仍不在其修改范围。T05 未通过之前不集成它的部分门禁到主工作区。

## T06：独立核对与受保护集成

任务：`01a0535e-d9b7-7a63-87ef-ac5182be2275`，Worktree：`C:/Users/adj/.codex/worktrees/9e54/wxprogrom7.15`。R1 文档返修已结束。

核对 `C:/Users/adj/AppData/Local/Temp/wx-t06-r1-05-0db7b50075184f44b962dabcddd9b6dc` 中的 preimage/postimage manifest、备份文件与候选实际字节：

- 最终文档 preimage 与第一轮统筹 `scope.json` 一致；postimage 五个文件都与实际候选和独立备份匹配。
- 四个代码/测试/扫描文件均保持首轮审阅版本，本次只修文档；候选 Prettier 和 `git diff --check` 再验退出 0。
- 主工作区三个既有目标写入前仍匹配首轮冻结 root hash；另外两个新目标不存在。全部五项先校验后备份，再逐项复查并同步，未整目录覆盖。

集成备份：`C:/Users/adj/AppData/Local/Temp/wx-integrate-t06-s3-ge4c57z_`，`manifest.json` 保存五个路径及 before/after SHA-256；preimage 子目录保存三个既有文件。同步后五项主工作区指纹全部与候选一致。

| 已接收文件                                 | 作用                                                          |
| ------------------------------------------ | ------------------------------------------------------------- |
| `backend/app/core/config.py`               | 统一归一化 `Settings.is_production`                           |
| `backend/app/main.py`                      | JWT 与启动 seed 共用生产态判定，避免大小写/空白绕过 seed 限制 |
| `backend/tests/test_t06_security.py`       | 生产 Demo/seed 边界及 AI 审计字段检查                         |
| `scripts/security-secrets.mjs`             | 扫描自测增加短占位符不误报断言                                |
| `docs/update_plan/deliveries/T06-final.md` | 格式合格的交付、统筹复验证据边界与外部阻断记录                |

### 主工作区集成后验证

| 命令/检查                                                                                                                                                                 | 退出码与结果                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 在 backend 执行 `python -m pytest tests/test_t06_security.py tests/test_auth.py tests/test_second_phase.py tests/test_access_control.py tests/test_database_safety.py -q` | 0；29 passed，49.16 秒；28 个既有 SQLite FK-drop-order warning |
| `python -m ruff check backend/app/core/config.py backend/app/main.py backend/tests/test_t06_security.py`                                                                  | 0                                                              |
| `node scripts/security-secrets.mjs --self-test`                                                                                                                           | 0；1 个合成命中                                                |
| `node scripts/security-secrets.mjs --scope=worktree`                                                                                                                      | 0；findings=0                                                  |
| `npx prettier --check scripts/security-secrets.mjs docs/update_plan/deliveries/T06-final.md`                                                                              | 0                                                              |
| `git diff --check`、五项集成指纹核对                                                                                                                                      | 各 0                                                           |

这里关闭的是 T06 仓库侧增量和 R1-05 格式问题，**不是 SEC-01/03/09 外部发布事项**。历史三条凭据撤销/审计、教师报告 `submitted_global` 政策、平台/医学/真实服务证据继续阻断生产发布。

## 合同、数据、安全与回退

- 本次没有改变 HTTP/schema、生成 OpenAPI/类型、API/Demo 数据合同、数据库 schema/迁移或权限范围；不调用真实 AI/微信。pytest 在 T01 导入前受管临时 SQLite 上运行，没有连接开发/共享/生产数据库。
- 未执行全量后端、E2E、构建、契约生成或依赖审计：本次新增集成只涉及此前审阅过的生产态/seed 判断、扫描自测及定向安全测试，按范围完成主工作区复验。全量组合回归仍留待 T05/T07/T02 形成最终组合候选；不引用本轮结果宣布 S3 全绿。
- 回退前核对当前目标 hash，仅从集成备份按文件恢复本次三个既有文件；两个新增文件仅在确认未被后续任务接管时精确移除。不得 reset/clean、目录覆盖、恢复旧删除文档或执行数据库 downgrade。安全回退不能被当作允许弱 JWT/生产 seed 的发布授权。
- 本轮统筹另新增本文并更新执行索引。索引 preimage 位于 `C:/Users/adj/AppData/Local/Temp/wx-s3-r2-review-732j0g9o/execution-status.preimage.md`，SHA-256 为 `48CF7D6742BC7836A1782FBD5A5E5D98F81836BDE34D015B447F535AFFC74A79`。

## 下一步

T05 原任务继续 R2；T06 不再重复返修已关闭的格式项。T07 保留阶段文档候选，等待 T05/T06/T02 最终事实统一更新；T02 仍不修改共享门禁文件。统筹继续按“审阅指纹、负例复验、受保护同步、组合回归”接收后续成果，不能把多个独立 Worktree 的单项通过当成最终工程验收。
