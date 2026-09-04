# 工程更新最终汇总交付

日期：2026-08-31。状态：**T05、T06、T07 的剩余候选已在主工作区完成受保护的文件级接收和组合复验；本轮代码工作树成果已经汇总到主工作区。** 这不等于 Git 提交、远程合并或生产发布，也不把未达到的覆盖率和外部条件写成通过。

## 接收范围与保护证据

- 本次从 T05 Worktree 接收 17 个文件，从 T07 Worktree 接收 14 个文件；T06 的 5 个文件已在前一轮接收。候选与冻结 postimage、主工作区与冻结 preimage 均逐文件通过 SHA-256 门禁后才复制。
- 本次 31 文件的主工作区 preimage、来源、候选 after 和统筹调整后的最终 SHA-256 位于 `C:/Users/adj/AppData/Local/Temp/wx-final-integration-20260831-011742/final-manifest.json`；文档收口前置副本位于 `C:/Users/adj/AppData/Local/Temp/wx-final-integration-docs-20260831-012900`。T06 备份位于 `C:/Users/adj/AppData/Local/Temp/wx-integrate-t06-s3-ge4c57z_`。
- 保留原有未提交和未跟踪改动、0009 迁移及 `docs/update/README.md` 删除状态。未使用 reset、clean、目录覆盖，未提交、推送或执行 Git merge。
- T05 覆盖率检查器 self-test 暴露出跨盘 Windows 临时绝对路径无法映射的问题；统筹只让后端报告支持绝对路径，未调整覆盖率范围或阈值。修复后 self-test 通过。

## 当前交付结果

| 领域               | 主工作区结果                                                                                      | 结论                           |
| ------------------ | ------------------------------------------------------------------------------------------------- | ------------------------------ |
| T01 测试数据库隔离 | 127 项后端全量测试使用受管随机临时 SQLite 通过                                                    | 已接收，未接触未知或开发数据库 |
| T02 基础门禁与契约 | Lint、类型、契约只读检查通过；package/CI 最终统一接线未做                                         | 基础可用，治理项保留           |
| T03/T04 前后端分层 | 前后端边界 self-test 与实际扫描通过                                                               | 已接收                         |
| T05 行为与覆盖率   | 前端 103 项、后端定向 48 项、后端全量 127 项、API E2E 8 项、Demo E2E 1 项通过；全部关键职责组达标 | 行为通过；全量覆盖率门槛未关闭 |
| T06 安全           | 扫描器 self-test、工作树、H5 与 MP-Weixin 构建物均 0 命中                                         | 本地仓库侧已接收；外部阻断仍在 |
| T07 规范与 skill   | 权威文档、根 AGENTS、项目 skill 已接收；skill 自检和格式检查通过                                  | 已接收                         |

## 本次主工作区验收

| 检查                                                     | 结果                                                                                                                              |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `npm run lint`、`npm run type-check`                     | 退出 0                                                                                                                            |
| `npm run test -- --reporter=dot`                         | 退出 0；23 files / 103 tests。存在一条 App 无 render/template 的 Vue 测试警告                                                     |
| T05 后端 6 文件定向 pytest                               | 退出 0；48 passed；47 条已知 SQLite FK drop-order warning                                                                         |
| 后端全量 branch coverage pytest                          | 退出 0；127 passed；126 条同类 warning；报告在 `C:/Users/adj/AppData/Local/Temp/wx-final-acceptance-20260831-012100/backend.json` |
| `python -m ruff check .`、`python scripts/type_check.py` | 退出 0；严格类型检查 64 个源文件                                                                                                  |
| 前后端边界脚本 self-test 与实际扫描                      | 退出 0；前端 117 个实现文件、后端 8 个模块                                                                                        |
| `npm run contract:check`                                 | 退出 0；在系统临时目录生成并比较，没有改写生成物                                                                                  |
| `npm run build:mp-weixin`、`npm run build:h5`            | 退出 0；仅有依赖注释位置的 Rollup 警告                                                                                            |
| API / Demo E2E                                           | 退出 0；8 passed / 1 passed，使用独立端口和受管 E2E 数据库                                                                        |
| 秘密扫描 self-test、工作树、两份构建物                   | 退出 0；实际扫描均 0 findings                                                                                                     |
| 工程 skill 自检、限定 Prettier、`git diff --check`       | 退出 0                                                                                                                            |

## 真实未关闭项

- 前端将全部页面与组件纳入统计后，103 项测试均通过，但全量 lines/statements 为 51.84%（检查器按 statement/line 计数显示 51.85%），低于 85%；branches 83.80%、functions 87.17%。报告在 `C:/Users/adj/AppData/Local/Temp/wx-final-acceptance-20260831-012100/frontend/coverage-final.json`。
- 后端全量行/statement 为 91.90%，分支 73.66%，分支低于 80%。所有关键组已经达标：identity 98.68/93.75、medical-ai 99.40/100、content 95.81/90.91、training 91.16/87.80、learning 96.28/87.50（lines/branches）。
- `package.json` 尚未提供 `frontend:boundaries`、`backend:boundaries`、critical coverage 和后端严格类型的统一别名，也未把这些门禁接入最终 CI；当前按文档直接调用实际脚本。
- 远程 CI/分支保护、目标 Node 22/Python 3.12 环境、跨平台截图基线、历史凭据撤销和访问审计、生产配置与备份恢复、微信真机/合法域名、真实 AI、医学审核和教师报告范围政策仍需外部证据或决定。生产发布继续阻断。

## 数据、合同与回退

本次没有 schema、OpenAPI、迁移或持久化数据变更。唯一生产代码增量是医学 AI adapter 对空 `choices` 和非法结构使用已有 fallback，避免 `IndexError`；API/Demo 选择方式和公开合同未改变。回退时先核对 integration manifest 中的 after hash，再逐文件使用对应 preimage；新增文件逐项删除。不得对整个 dirty 工作区执行 reset/clean。

历史审核记录继续保留，数值代表当时快照；本文件和 [执行状态](../execution-status.md) 是当前汇总依据。
