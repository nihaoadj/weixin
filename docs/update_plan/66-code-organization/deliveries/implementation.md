# T66 实施与验证记录

状态：S0–S3文件组织修复与验证、S4保护核对完成；临时清理受工具策略阻塞。全局函数覆盖率为已有未达标项；不宣称完整CI门禁通过。以[计划](../README.md)和[代码与目录组织规范](../../../code-organization-standard.md)为依据。

## 起始证据

2026-10-04，在仓库根目录执行：

| 命令或检查                                   | 退出码 | 结果                                                         |
| -------------------------------------------- | -----: | ------------------------------------------------------------ |
| `git status --short` 状态统计及现存文件基线  |      0 | 1,556 条状态记录；1,875 个现存文件哈希；暂存区条目哈希已保存 |
| `node scripts/frontend-boundaries.mjs`       |      0 | 211 个实现文件，通过                                         |
| `python backend/scripts/check_boundaries.py` |      0 | 9 个模块，通过                                               |

S0计划格式/链接/空白及`python scripts/check-project-skills.py`与`--self-test`均退出0，随后实施运行路径迁移。

## 完成的修复

- 复核网络来源等级，降低单一来源条文的“原则”标记，更新uni-app官方工程链接，保存[GitHub API当日快照](../../../references/code-organization-sources-20261004.json)。可选目录树仍不作为强制行业标准。
- 33份业务专属视图、展示帮助函数及邻近测试归入content/analytics/learning/pbl的`presentation`；2份跨模块测试移入`src/test/integration`；7份独立HTML移入`docs/examples/pelican`。42条映射见计划，HTML字节不改。跨业务教师工作区与通用UI保留原归属。
- Demo知识目录映射归content，装配根注入读取函数，learning不再读content内部JSON。身份导航守卫使用最小注入接口，避免展示直接依赖领域层，也避免经public引入类型循环。
- 删除3条失效后端豁免，两个维护脚本改用canonical bootstrap种子入口；去掉import节点后，两个脚本与编辑前AST相同，未执行种子或迁移真实数据库。
- 新增目录检查与自检，增强生成JSON依赖检查，允许合法功能视图组合，覆盖范围随视图迁移；`npm run check`与CI接入结构门禁。补Python缩进、ZIP属性和明确的本地产物忽略规则。Lint/格式化跳过历史证据、归档及原始设计输入，活动源码继续检查。
- 仅通过Prettier修复5个已有源码/测试/合同文件的格式，生成契约4产物保持原内容。T64原文按最近两轮完整计划规则归档，2份文件的大小与SHA-256逐项验证，原待验不变。

具体保留理由、兼容入口消费者与退出条件见[审计](../../../code-organization-audit.md)。未升级依赖、未改变API/数据库/页面注册合同，未提交或推送。

## 最终验证

以下命令从仓库根执行，基线coverage从隔离副本执行。完整本地日志保存在受忽略的`output/local/t66/`，核心结论在本页保存，供不持有本地日志的读者复核。

| 命令/验证                                                                                                                     |  退出码 | 实际结果                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------- | ------: | ---------------------------------------------------------------------------------- |
| `npm run structure:self-test`                                                                                                 |       0 | 文件组织14项；前端正例与37个越界负例；后端边界自检                                 |
| `npm run structure:check`                                                                                                     |       0 | 文件分类/大小写/失效豁免/工具反向依赖；前端212个实现+4个JSON资源；后端9模块        |
| `npm run lint`                                                                                                                |       0 | 活动代码通过，历史源码快照不参与活动代码扫描                                       |
| `npm run type-check`                                                                                                          |       0 | Vue/TypeScript检查通过                                                             |
| `npm run format:check`                                                                                                        |       0 | 最终全仓适用格式检查通过                                                           |
| `npm run contract:check`                                                                                                      |       0 | 4产物与隔离生成结果一致，生成物未手改                                              |
| `python -m ruff check scripts/check-code-organization.py backend/scripts/run_e2e_server.py backend/scripts/seed_test_data.py` |       0 | 新检查器与维护脚本通过                                                             |
| `node node_modules/vitest/vitest.mjs run src/bootstrap/demoContentSamples.spec.ts --maxWorkers=4`                             |       0 | 首轮失败文件独立3/3通过                                                            |
| `npm run test:coverage -- --maxWorkers=4`                                                                                     |       1 | 112文件、620测试全通过；函数覆盖率77.20%低于既定80%阈值，其余三项通过              |
| 恢复迁移前配置的副本`vitest run --coverage --maxWorkers=4`                                                                    |       1 | 112文件、619测试全通过；函数77.12%，同一阈值失败                                   |
| `VITE_APP_MODE=demo`下`npm run build:mp-weixin`                                                                               |       0 | Demo生产构建通过                                                                   |
| `VITE_APP_MODE=api`、本地API地址下同构建命令                                                                                  |       0 | API生产构建通过；未连接真实API                                                     |
| `VITE_APP_MODE=demo`下`npm run dev:mp-weixin`                                                                                 | 已ready | 最终开发编译到`dist/dev/mp-weixin`；仅停止本次启动的watcher                        |
| `node scripts/wechat/check-wxss.mjs --project dist/dev/mp-weixin`                                                             |       0 | 70份原生WXSS语法通过                                                               |
| wechatide `simulator_refresh`（指定开发目录）                                                                                 |       0 | 普通刷新成功                                                                       |
| `npm run test:mp:doctor`（本终端CLI路径/客户端）                                                                              |       0 | SDK3.17.2、URL校验开启；只证明环境就绪                                             |
| 开发/生产JSON组件引用核对                                                                                                     |       0 | 各83条`usingComponents`的JS/JSON/WXML目标均存在                                    |
| 本次当前Markdown本地链接                                                                                                      |       0 | 所查文档目标存在，包含归档后当前入口；不重开历史链接验收                           |
| [工作区保护核对](worktree-protection.json)                                                                                    |       0 | 1,875份起始现存文件按修改授权核对；1,787份非本次范围文件不变；暂存区原条目字节不变 |

### 初次失败及处置

初次全仓Lint退出1，是`output/`内历史源码快照进入活动代码扫描；将证据目录排除后通过，未改写/删除证据。初次格式检查退出1，5个活动源码格式问题已备份原字节并由Prettier修复。

初次契约检查退出1，是本次新增的`data/`格式化忽略误匹配`src/data/`，隔离生成的TypeScript因此未格式化。改为仅根`/data/`后重验退出0，4份生成物原字节保持；不能将首次失败写成API或预存契约漂移。

首轮覆盖率运行620项中618通过，Demo初始化一项5秒超时、随后API存储断言失败；该轮同时存在构建负载。停止构建竞争、使用4 workers而保持原超时/断言/覆盖门槛后，独立3项和全量620项通过。没有通过加长测试超时、删用例或忽略存储断言取得通过。

覆盖率仍退出1，因此恢复起始412份src与5份配置到隔离副本，已有快照优先、其余当前文件哈希与基线一致；使用相同依赖与并发、各阶段对应的覆盖配置重验。语句/分支/函数/行从85.48/81.21/77.12/85.48提升到85.50/81.27/77.20/85.50，说明函数阈值不足继承自起始工作区。未降低80%阈值，未缩小迁移视图的覆盖扫描范围。

微信首次doctor退出1提示运行时未到达模拟器；第二次普通刷新后doctor退出0。目录迁移无视觉设计变化，本次仅做生成引用、语法、普通编译与工具环境检查，不新增截图或恢复历史按钮待验。

## 保护与范围限制

[保护清单](worktree-protection.json)保存原/现文件哈希、迁移路径、暂存区哈希和已删除路径保持统计；HTML7份与T64归档2份字节相同，132个起始已删除路径仍缺失。已有暂存、未暂存、未跟踪及删除状态均按本次范围保护，既有`output/`未清理，仅修复T64交付记录指向已归档计划的一处链接，证据正文与结论不改。

最后尝试清理本次临时产物：先核对两个绝对目录位于`.contract-tmp/`、junction目标为本仓库`node_modules`，再依次删除junction、隔离副本、基线及8个迁移帮助脚本。执行工具在启动PowerShell前返回`Rejected ... blocked by policy`，未提供更具体理由，所有删除均未发生。未改用其他执行方式绕过该拒绝。`.contract-tmp/t66-baseline-frontend/`、`.contract-tmp/t66-filesystem-baseline/`及8个`t66-*.py`仍在受忽略目录中；隔离副本的`node_modules`是指向共享依赖的junction，后续清理应先移除链接本身。仅停止了本次启动的watcher；没有停止用户原有进程。此项是清理未完成，不是活动源码或业务验证失败。

函数覆盖率低于80%仍使全局coverage/完整CI门禁失败；Vite7.3.6与uni插件精确peer5.2.8差异仍待独立依赖评估。远程CI、干净环境安装、真实API、PostgreSQL及真机未执行。既有MA-T64-001等人工待验保持，不把本次文件组织检查扩充为这些环境的验收通过。
