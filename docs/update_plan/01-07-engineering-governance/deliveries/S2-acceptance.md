# S2 分层迁移组合验收

日期：2026-08-30。结论：**S2 仓库内组合验收通过，可以进入 S3 综合交付；不等于生产发布已获批准。**

本轮验收覆盖 T03 前端分层、T04 后端分层、INT-01 病例草稿行为修复和 R05 后端跨模块 API 边界修复。原工作区 HEAD 仍为 `b96bab910dc5ee43410fa55c5b856cc4d3f3415d`，没有提交、推送、合并或部署；保留开工前及各领域未提交/未跟踪改动、0009 迁移和 `docs/update/README.md` 的删除状态。

## 候选审阅与缺陷关闭

- R04 恢复病例草稿的模型成功、disabled/错误 fallback、胸痛/肺炎/右下腹/未知主题完整模板、AI audit 和 application UoW 回滚。统筹以冻结文件逐对象比较四主题 payload，并通过真实 API、数据库 audit、audit flush 异常和 commit flush 异常探针。
- 第五轮审阅发现 `content/infrastructure` 依赖 `training.api.schemas`，同时边界检查遗漏跨模块 API 目标。R05 将 provider schema 收归 content，删除无效 allowlist，并让非 `api/wiring` 来源导入其他模块 API 稳定失败；`*.public` 合同继续通过。
- R05 独立 preimage 位于 `C:/Users/adj/AppData/Local/Temp/wxprogrom7.15-T04-increment-20260830-r05-boundary`。`preimage.json` SHA-256 为 `9C9FF3946153859111A777F6819852ECCBE3FB9320CB35E168CB2CA33804387A`，五个备份文件逐项与声明 hash 一致。
- 候选 Worktree 独立复验：边界 self-test/正式检查、64 文件严格类型及负例、四份 provider/HTTP schema 等价、额外字段拒绝、契约检查、compileall 和 9 项 API/事务探针均退出 0；`backend:check` 退出 0，84 passed，覆盖率 89.84%。

## 受保护同步

- R04/R05 主增量备份：`C:/Users/adj/AppData/Local/Temp/wx-integrate-r04-r05-bswilvf3`。第一次同步 14 个目标，包含 10 个既有文件和 4 个新文件；所有既有文件在写入前均与 S2 首轮 `post-integration/manifest.json` 冻结 hash 一致。
- 组合静态复验发现同步清单漏列 `backend/scripts/check_boundaries.py`，因此旧 self-test 仍只有 17 项。统筹没有接受该结果，使用 `C:/Users/adj/AppData/Local/Temp/wx-integrate-r05-boundary-script-de3b2xbl` 单文件备份后补充同步；修改前 hash `8F1B5A09E2E08C7DDDE77C593D37CDE5E4F714B76451B8F3F01A191898D5FA95` 与冻结快照一致，修改后为 `9216E4EC6B3DAFD7ACE49C33B6C69AD12313F60313839A075674206653E0A8C8`。
- 仅对 `config/backend-boundaries.json` 和 `docs/update_plan/deliveries/T04.md` 执行 Prettier；没有修改规则语义、迁移、前端、E2E 断言、package/lock 或 CI。
- S2 最终工作树清单位于 `C:/Users/adj/AppData/Local/Temp/wx-s2-accepted-_i3un1gp/workspace-manifest.json`，清单 hash 和缺失路径列表保存在同目录 `workspace-metadata.json`；另保留完整 `git status`，供 S3 新 Worktree 与后续增量核对。

## 主工作区最终证据

| 检查                     | 退出码与结果                                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| 后端边界 self-test       | 0；20 个正负、alias、type-only、SQL、dynamic、cycle 探针通过，包含空 allowlist 的跨模块 API 负例和两类 public 正例 |
| 后端边界正式检查         | 0；8 modules、4 layers，通过真实来源追踪和循环检查                                                                 |
| 后端严格类型/负例        | 各 0；64 个 source files 无错误；缺失方法和参数错配被拒绝                                                          |
| provider/HTTP 合同探针   | 0；四份冻结 payload 在两套 schema 下序列化完全一致；未声明字段被拒绝                                               |
| 草稿 API/事务探针        | 0；9 passed，包含真实数据库 audit、audit/commit flush 后回滚                                                       |
| `npm run contract:check` | 0；在系统临时目录生成比较，未改 OpenAPI、生成类型或 fixture                                                        |
| `npm run backend:check`  | 0；Ruff + 84 passed，5473 statements / 556 miss，89.84%，86.02 秒                                                  |
| `npm run check`          | 0；格式、ESLint、Vue/TS 类型、20 文件 93 tests、微信和 H5 构建通过                                                 |
| 前端覆盖率               | statements/lines 96.55%、branches 86.25%、functions 92.11%                                                         |
| API 组合 E2E             | 0；8 passed，37.8 秒；端口 18331/41931；原 review-and-class-flow 回归通过                                          |
| Demo E2E                 | 0；1 passed，19.0 秒；端口 41932；确认无 API 请求                                                                  |
| 工作树/构建物秘密扫描    | 各 0；findings=0，扫描 `dist/build/h5` 与 `dist/build/mp-weixin`                                                   |
| `git diff --check`       | 0；无 whitespace error                                                                                             |

后端测试继续产生 83 个既有 SQLite 循环外键 drop 排序 warning；没有吞错或放宽门槛。E2E 后端由 T01 受管随机临时 SQLite 创建、迁移和清理，没有连接开发/共享/生产数据库；AI 被禁用，没有调用真实 AI 或微信。

## 合同、数据、安全和回退

- HTTP path/method、OpenAPI operation/字段/错误码、API/Demo 分界、数据库 schema/表列/迁移和权限策略未改变。R04/R05 不新增 Alembic revision，不需要 downgrade 或业务数据回滚。
- `CaseDraftModel` 仅用于 content provider 内部校验；响应仍由既有 HTTP response model 校验。AI audit 只保存模型、prompt version、耗时、fallback/失败类别和关联 ID，不保存 prompt、完整回答、隐藏病例事实或凭据。
- 回退时先核对当前 hash，仅按上述两个集成备份逐文件恢复既有文件；四个 R04 新文件只有在确认未被后续任务接管时才精确移除。不得 reset、clean、目录覆盖、恢复 `docs/update/README.md` 或执行迁移 downgrade。

## S3 下一步和并行边界

1. **T05 关键业务与覆盖率收尾**：基于当前 S2 验收树补齐关键模块独立门槛、缺失文件防护和最终行为矩阵；重点处理 learning/training 用例覆盖、身份会话和 AI 失败路径，不以总覆盖率替代关键职责验收。
2. **T06 安全与发布证据收尾**：复核新目录的权限/敏感数据流和构建扫描；历史三项凭据发现仍需外部管理员提供撤销/轮换和访问审计证据。教师报告范围政策、生产配置、真实微信/AI、医学审核仍是发布阻断或外部决策。
3. **T07 规范事实同步**：把 S2 已落地目录、真实命令和边界更新到架构、开发、安全、AGENTS 和项目 skill；删除计划式旧表述，但不把远程/生产事项写成已完成。
4. **T02 最终门禁和 CI**：由唯一负责人顺序修改 package、锁文件、CI 和共享质量配置，接入已存在的前后端边界、关键测试、安全扫描和契约检查；在目标 Node 22/Python 3.12 复验，并由平台管理员设置必需检查和分支保护。

T05、T06、T07 可从本 S2 验收树分别创建独立 Worktree 并行执行，但不得同时编辑 package/lock/CI。T02 可以先只读核对接线方案，最终共享文件修改必须在 T05/T06 提供稳定命令后由统筹顺序集成。各任务仍需独立 preimage、范围 hash 和交付记录；统筹逐项审阅后再形成 S3 组合版本。
