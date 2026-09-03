# S2 第一轮统筹验收：退回整改

日期：2026-08-30。范围：T03、T04 初次交付。结论：**两项均未通过验收，不集成，不进入 S3 综合交付。已在原任务、原 Worktree 以 Luna Max 派发整改。**

## 基线与保护

- 原工作区为 `D:/CODE/weixin/wxprogrom7.15`，仍是 S1 集成基线和用户既有未提交修改；本轮未复制任何 T03/T04 生产代码进入原工作区。
- T03：`01a05207-d1c4-7d21-b4e8-94c5fc0e3fb6`，Worktree `C:/Users/adj/.codex/worktrees/66ca/wxprogrom7.15`。
- T04：`01a05208-03d7-7711-91a9-a614eac82887`，Worktree `C:/Users/adj/.codex/worktrees/4507/wxprogrom7.15`。
- 先检查原工作区 `git status`，读取项目 skill、架构、数据层、数据库、安全文档及两个子任务交付；只读探针没有在生产源码中插入违规文件，没有打开业务数据库，没有真实 AI/微信调用。
- 未 reset、clean、提交、推送、合并，未恢复 `docs/update/README.md`。原工作区本轮仅更新计划/验收文档。

## 阻断发现

| ID  | 级别/归属          | 已观察到的事实                                                                                                                                                                                                                                                                  | 复验通过标准                                                                                                                                                                 |
| --- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R01 | P0 / T04、T05、T06 | `training/domain/state.py:177` 的 `apply_ai_candidates` 用 AI score 覆盖确定性 score/weighted_score。六维非 critical rubric、空答案、空 evidence、候选分数 100 的纯领域样例使总分从 0 变 100。原 S1 的 `services/case_training.py` 同样有此逻辑，是继承缺陷，不是本次新增回归。 | AI 任意候选不能改变规则维度分、权重和总分；空/伪造/有效 evidence、高/负分均有独立负向测试。作为安全修复单列，保留接口字段，不改变生成合同。                                  |
| R02 | P1 / T03           | 正式边界检查和自测通过，但外部 Vue 导入、非静态动态导入、括号形式 uni.request、domain 导入页面、循环 re-export 的五种违规样例全部通过。正则解析且未建循环图，外部导入被直接跳过。                                                                                               | AST/SFC 解析及来源解析覆盖静态/相对/alias/type-only/re-export/dynamic，识别平台 IO 的替代写法；非法层间依赖和循环可被独立样例阻断，例外精确声明。                            |
| R03 | P1 / T04           | `_check_source` 放过 application 相对导入 infrastructure、`from app import models`、API `session.commit()`、application 导入 platform transaction、domain 导入 application 五类违规。忽略 `ImportFrom.level` 和导入符号，API 只检查名为 db 的变量，无完整循环检测。             | 解析模块与符号的真实来源、相对导入/重导出/TYPE_CHECKING，检查全量生产图、反向依赖和循环；SQL/提交检查不依赖变量名；每种违规逐项断言。                                        |
| R04 | P1 / T03           | identity application 仍导入具体 storage key/schema，并通过 `applicationPlatformRoots` 白名单放行；兼容入口以未具名“仓库外消费者”为保留理由，coverage 排除整个旧 services/data 包，其中仍有函数和聚合逻辑。                                                                      | 存储格式/迁移实现归 adapter，应用依赖窄 port；迁移现有测试，清理无实际消费者旧入口；所有剩余手写逻辑计入覆盖，保留入口写明具体消费者和解除条件。                             |
| R05 | P1 / T04           | 生产 wiring 默认装配 LegacyAssessmentGateway，它先回调旧 services；learning 穿透 training.application，模型/schema 仍中央聚合；BE-06 以顺序重复调用充当并发证据，严格类型检查未完成。                                                                                           | 生产使用新 gateway，测试通过注入 port；跨模块经公开合同，模型/注册职责完整映射；独立 session/屏障的竞争与失败恢复测试通过；真实类型检查覆盖核心并修复错误，不靠 Any/ignore。 |
| R06 | P1 / T03、T04      | T03 完整 API E2E 自报 7/8；T04 官方契约/E2E 缺本地 Node 依赖；T03 将 S1 的秘密扫描沿用为重构后证据。                                                                                                                                                                            | 精确选择本次提交的报告并验证批阅，不能任意 first/隐藏数据；恢复锁定依赖后跑官方契约；重扫最终工作树/构建物。环境安装和测试失败不能当作外部阻塞宣布完成。                     |

R01 与当前安全规范“AI 只改反馈、规则决定总分”冲突，优先修复。历史凭据、教师报告范围、真实平台和医学审核等外部事项仍保留，不因本轮退回或修复而自动解除。

## 本轮实际执行证据

| 检查                                                                                      | 退出码 | 结果/解释                                                              |
| ----------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------- |
| 原工作区 `git status --short`、文档/源码只读检查                                          | 0      | 用户既有改动和旧文档删除状态保留                                       |
| 项目 skill `python -X utf8 .agents/skills/wx-engineering-standards/scripts/self_check.py` | 0      | 结构与链接自检通过，不代表业务验收通过                                 |
| T03 `node scripts/frontend-boundaries.mjs --self-test`                                    | 0      | 原自测 positive=0、negative=2                                          |
| T03 `node scripts/frontend-boundaries.mjs`                                                | 0      | 156 implementation files；下列负向探针证明存在漏检                     |
| T03 `npm run type-check`                                                                  | 0      | vue-tsc 和 Node 配置类型检查通过                                       |
| T03 内存负向探针（Node stdin，调用原 analyze/virtualEntries）                             | 0      | 5/5 输出 ACCEPTED_VIOLATION；0 仅表示探针执行成功，不表示门禁正确      |
| T04 内存负向探针（Python stdin，importlib 加载检查器并调用 _check_source）                | 0      | 5/5 输出 ACCEPTED_VIOLATION；没有调用 app 或数据库初始化               |
| T04 纯领域评分探针（Python stdin）                                                        | 0      | deterministic_total=0，after_ai_candidate_total=100；无真实网络/数据库 |

探针只使用合成输入。前端运行时以内存 data URL 加载去除 CLI 入口后的现有检查器，暴露其分析函数；后端只导入检查器或领域模块。所有违规样例均未写入仓库。

### 负向样例清单

前端：`import { ref } from 'vue'` 位于 domain；页面 `import(targetPath)`；页面 `uni['request']({url:'/x'})`；domain 导入 `@/pages/probe.vue`；`shared/a.ts` 与 `shared/b.ts` 互相 re-export。

后端：application 中 `from ..infrastructure.repository import Repository`；domain 中 `from app import models`；API 中 `def route(session): session.commit()`；application 中导入 `app.platform.transactions.SqlAlchemyUnitOfWork`；domain 中导入本模块 `application.ports.ReportRepository`。

评分：根据 `DIMENSION_SPECS` 创建六维 rubric，每维只有一个不存在于空答案的非 critical keyword；先执行 `deterministic_assessment`，再注入每维 score=100、evidence=空的 `AssessmentCandidate` 并调用 `apply_ai_candidates` 和 `summarize_dimensions`，观察总分变化。

## 下一步及交接

1. 已向 T03/T04 原任务派发上述有复现输入的整改要求，仍使用 `gpt-5.6-luna / max`；不创建重复任务。
2. T03 负责边界、存储分层、旧入口清理、coverage 和精确 E2E 报告选择；T04 优先修复 AI 评分，再修依赖、生产 gateway、类型和并发验证。
3. 执行者追加真实修复记录、增量 hash 和完整验收结果；不得覆盖第一轮缺陷历史或把先前报告直接改为全绿。
4. 统筹再独立复验违规探针、AI 评分不变量、安全/迁移、契约与全量回归。通过后按修改前 hash 逐文件集成，合并共享文档并接入边界脚本。
5. S2 通过后再推进 T05 关键覆盖率/T06 安全/T07 事实文档/T02 最终 CI；不提前把未实现命令写成可用。

## 未执行项与回退

本轮尚未重跑两个候选的全量测试、双端构建、E2E、扫描或数据库迁移，因为已发现足以拒绝交付的结构和安全缺陷；这些检查必须在整改版本上重新执行。子任务自报的 93/72 项通过仅作为其历史证据，不替代统筹复验。

原工作区没有集成生产代码，不涉及 API/Demo、数据库、schema 或数据回退。若需撤回本次文档更新，仅按其差异处理计划/验收记录；子任务仍在原独立 Worktree 保留代码及 preimage，禁止借此清除其他改动。
