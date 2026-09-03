# S2 第二轮统筹验收

日期：2026-08-30。范围：T03/T04 第一轮整改后的候选。**结论：已确认多项修复，但两项任务仍未完整通过；不集成候选，不进入 S3。** 本记录保留第一轮 [验收记录](S2-review-01.md)，不覆盖缺陷历史。

## 当前事实与修复确认

- T03 仍在 `C:/Users/adj/.codex/worktrees/66ca/wxprogrom7.15`；T04 仍在 `C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15`。本轮只读取、执行候选检查；原工作区只更新验收文档，未集成生产代码、未提交/推送/合并。
- AI 评分的上一轮合成攻击样例已修复：空学生答案、每维 AI 候选 score=100/evidence=空，规则总分为 0，合并候选后仍为 0。该独立纯领域探针退出码 0，无数据库/网络调用。
- T03 原来的五类违规探针全部被拒绝：domain 导入 Vue、非静态 dynamic import、括号 uni.request、domain 导入页面、循环 re-export。命中数分别为 1/1/1/1/2，独立探针退出码 0。
- identity application 已改用 SessionStoragePort，具体 key/schema/迁移归入适配层。旧服务和聚合入口、测试路径已按交付迁移；生成 OpenAPI 仍在约定位置。
- pilot E2E 使用该次提交响应的 report ID 选择教师报告卡，并验证同一 ID 的批阅响应；没有任意 first 或隐藏记录。
- T04 默认 gateway 已脱离旧 legacy hook，模型/schema 的实际定义迁入所属模块；但下列门禁及并发证据仍不满足验收要求。

## 剩余阻断（均可本地修复）

| ID         | 级别/任务 | 可复现事实                                                                                                                                                                                                                                 | 完成标准                                                                                                                                                                              |
| ---------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R02-FE     | P1 / T03  | `platformIoMembers` 只列同步 storage API；页面 `uni.setStorage({key:'user',data:'x'})` 无违规。`export type Bad = import('vue').Ref<string>` 位于 domain 也无违规，因为缺少 ImportTypeNode 处理。                                          | 同步/异步存储 API 及其别名均受平台限制；import-type 依赖进入规则和循环图。增加精确正负断言，不能仅针对前次五个字符串修补。                                                            |
| R02-FE-SFC | P1 / T03  | SFC 的 script block 仍用正则抽取，只识别内联内容；外置 script 的 src 没有建立依赖。shared 中直接 fetch 也未被 IO 规则捕获。                                                                                                                | Vue 认可的外置 script 需解析或明确拒绝；浏览器 fetch/XMLHttpRequest 等 IO 边界要有明确规则和测试，纯 shared 不得隐含网络 IO。                                                         |
| R02-BE     | P1 / T04  | 以真实 DependencyIndex 运行四个新探针均无违规：API 参数 `handle: DbSession` 执行 handle.commit；domain 导入 app.core.config.settings；shared 导入 reports.infrastructure；`from importlib import import_module as load` 动态加载内部实现。 | 根据 Session 注解/别名和依赖来源识别 SQL；真实 app.core/config 分类不可漏掉；shared/platform 反向依赖应受约束；动态加载别名需受检。自测须使用真实索引而非只测试孤立字符串。           |
| R02-TYPE   | P1 / T04  | `backend/mypy.ini:4` 为 follow_imports=skip。公开合同不在 55 个显式目标内，调用不存在的 TrainingCasePort 方法仍检查成功。将同一 55 个目标的 follow_imports 改为 normal，出现 7 个实际错误。                                                | 检查真实公开 port/合同，不以 skip 将导入类型退化为 Any；修复 public.py 与 learning use_cases 的错误，并用不存在的方法/错误参数负例证明类型门禁有效。                                  |
| R02-RACE   | P1 / T04  | `_prepare_assessed_source` 在测试线程启动前已调用 complete 创建 assessment。两个线程都命中已有结果，注入的双人 Barrier 不执行。统筹在原测试外加内存观测，REVIEW_BARRIER_CALLS=0，期望 2 的断言失败。                                       | 准备已完成阶段但尚未评估的 attempt，启动前断言 assessment 数为0；两个独立 Session 同时进入创建路径，证明 barrier 两次参与，最终 assessment/audit/相关副作用计数一致，并复验失败重试。 |

类型正常检查发现的具体位置：`training/public.py:248/249` 对 object 调用 float；`learning/application/use_cases.py:108/110` 将 CaseAttemptContract 赋给 LearningTaskAttemptRecord；同文件 241/244/245 行 CaseProblemContract 与 ProblemLike 的只读/可写协议不匹配。工具输出为 `Found 7 errors in 2 files (checked 55 source files)`。这不是缺少 package script 或外部环境造成的阻塞。

## 统筹实际复验

| 候选/命令                                      | 退出码                | 结果                                                                        |
| ---------------------------------------------- | --------------------- | --------------------------------------------------------------------------- |
| T03 边界 --self-test / 正式检查                | 各 0                  | targeted-negative=7；117 implementation files                               |
| T03 独立上一轮五类负向探针                     | 0                     | 五类全部拒绝；不代表新探针也通过                                            |
| T03 `npm run check`                            | 0                     | 格式、Lint、类型、93/93、微信/H5 构建通过；行96.55%、分支86.26%、函数92.11% |
| T03 `npm run contract:check`                   | 0                     | 系统临时目录生成比较通过                                                    |
| T03 `npm run test:e2e`                         | 0                     | 8/8；独立端口 API 18221 / H5 41821，T01 受管临时 SQLite                     |
| T03 `npm run test:e2e:demo`                    | 0                     | 1/1；独立 Demo 端口41822                                                    |
| T03 工作树、dist/build 秘密扫描                | 各 0                  | 两项均 findings=0；未重复读取历史秘密                                       |
| T04 边界 --self-test / 正式检查                | 各 0                  | 原自测通过；新的独立探针暴露漏检                                            |
| T04 原 `python scripts/type_check.py`          | 0                     | 报告55文件无问题；下列 normal 模式证明该结论不覆盖真实公开合同              |
| T04 `npm run backend:test:safety`              | 0                     | 14/14；46.79秒，13个既有外键排序警告                                        |
| T04 `npm run backend:test:migrations`          | 0                     | 2/2；16.15秒，1个既有警告                                                   |
| T04 `npm run contract:check`                   | 0                     | 官方逐字节比较通过，无需手改生成物                                          |
| T04 评分不变量独立探针                         | 0                     | 0 → 0，上一轮 P0 样例修复                                                   |
| T04 正常 follow-imports 类型检查（同一55目标） | 1（子进程真实退出码） | 7个错误；外层诊断脚本退出0仅用于完整打印结果                                |
| T04 TrainingCasePort 错误方法探针              | skip=0 / normal=1     | normal 正确拒绝不存在的方法，skip 错误放过                                  |
| T04 原 assessment 竞争测试加屏障观测           | 1                     | 原测试体成功，但实际 barrier调用0次；额外验证断言失败，不是产品API回归      |

竞争探针通过 pytest.main 的内存插件包装 StaticAssessmentGateway.assess，仅在 `_barrier is not None` 时计数；没有修改源码或 fixture。失败资源按 T01 规则保留在 `C:/Users/adj/AppData/Local/Temp/medical-qa-pytest-rgqdpvt9`，未手工清理。插件追加断言产生的 Pluggy warning 属于诊断探针，不是业务错误。

T03 E2E 使用其 Worktree 中继承的 S1 后端，不是 T03+T04 已集成版本；因此不能代替后续组合回归。微信真机、目标 Node22/Python3.12、远程CI/分支保护、历史凭据撤销和医学审核仍未验证。

## 后续与影响

后端完整复跑现已结束：`npm run backend:check` 退出码 0，Ruff 通过、78/78 测试、覆盖率 89.53%、耗时 78.92 秒，77 个既有外键排序警告。该结果没有解除本记录的屏障未触发和类型/边界漏检；普通测试绿灯不能替代有效的负向验证。

已将本轮具体复现输入、错误位置和通过标准分别发回两个原任务，仍由 Luna Max 在原 Worktree 整改，不创建重复任务。T03 仅需补余下门禁形式，T04 聚焦真实竞争、公开合同类型及依赖来源；不要重做已通过的 AI 安全修复和业务流程。

继续在两个原 Worktree 修复以上有限整改项，保留本轮通过证据和修改前 hash；重跑受影响的正负检查与完整回归后再提交统筹验收。T03/T04 未全部接收前，不接入假称完备的总门禁，不宣布生产可发布。

原工作区无本轮生产代码或数据变更，不涉及数据库回退。计划文档变更仅需检查格式、链接和差异；不恢复已删除旧文档。各项业务测试都经过 T01 受管 fixture，没有对开发库、共享库或生产库清表。
