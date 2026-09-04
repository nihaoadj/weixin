# T06-02 仓库侧秘密扫描交付记录

任务编号／阶段：T06-02／S0-S1 仓库侧扫描与自测。执行工作树：`C:\Users\adj\.codex\worktrees\f581\wxprogrom7.15`。本记录只覆盖可在本地完成的秘密扫描，不代表历史凭据已撤销、生产环境已安全或 T06 已全部验收。

## 基线、范围与保护情况

- 起始 Git HEAD：`b96bab910dc5ee43410fa55c5b856cc4d3f3415d`。
- T06-01 基线文档在本轮文字修订前的 SHA-256：`00B0F4F8F28091D965E561C8CB4F337AFC3F8F847C76DCDBF6882DA3F868A1DB`。修订后 SHA-256：`5B0544846E9444B605F9B0FA5180AAB58B2098C78A5CD681F4DAAC238F8727E9`。
- 工作树在开始时已有大量前后端、OpenAPI、页面、测试和迁移改动，以及已删除的 `docs/update/README.md`。本轮未恢复、覆盖、提交、推送、合并或删除这些既有改动；未编辑 `package.json`、锁文件、CI、T01 文件、业务实现或权限配置。
- 本轮只新增/修改以下任务范围文件：
  - `scripts/security-secrets.mjs`：扫描器下载、校验、执行、结果脱敏和自测。
  - `config/gitleaks-security.toml`：继承 Gitleaks 默认规则，增加项目变量赋值的精确规则；没有路径、规则类别或历史发现白名单。
  - `docs/update_plan/deliveries/T06-baseline.md`：将 R-01 改为“实现事实、授权政策待决”，将 R-02 改为“非生产 demo 行为、是否为漏洞取决于演示账户政策”。
  - `docs/update_plan/deliveries/T06-secrets.md`：本交付记录。
- 严格遵守 T01 前置：未运行后端测试、E2E、`check:all`、迁移、seed，也未连接或读写任何业务数据库。未读取、输出或轮换真实凭据。

## 扫描器来源、锁定与输出边界

使用成熟的 Gitleaks `v8.30.1`。版本、发布包和校验值固定在脚本中；来源为 [官方 v8.30.1 release](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)，校验清单为 [官方 checksums 文件](https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt)。支持 Windows/Linux x64/arm64：

| 平台包                               | 官方 SHA-256（脚本固定值）                                         | 本轮状态               |
| ------------------------------------ | ------------------------------------------------------------------ | ---------------------- |
| `gitleaks_8.30.1_windows_x64.zip`    | `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e` | 已下载并校验；本机使用 |
| `gitleaks_8.30.1_windows_arm64.zip`  | `b95f5e4f5c425cedca7ee203d9afd29597e692c4924a12ed42f970537c72cc0f` | 固定，未在本机下载     |
| `gitleaks_8.30.1_linux_x64.tar.gz`   | `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` | 固定，未在本机下载     |
| `gitleaks_8.30.1_linux_arm64.tar.gz` | `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080` | 固定，未在本机下载     |

本机下载包位于 OS 临时工具缓存 `wxprogrom-security-tools/gitleaks-8.30.1`，实测大小 8,438,883 bytes，SHA-256 为 `D29144DEFF3A68AA93CED33DDDF84B7FDC26070ADD4AA0F4513094C8332AFC4E`（大小写差异不影响校验）。下载使用临时 `.partial` 文件，校验成功后才改名并解压；解压目录和归档不进入仓库。

每次扫描把 Gitleaks JSON 报告写入独立 OS 临时目录；扫描结束在 `finally` 中删除报告目录。扫描器 stdout/stderr 不转发给调用者，包装器只输出：`scope`、规则 ID、相对位置、起始行和由 scope/规则/位置/扫描指纹重新计算的 16 位脱敏指纹。不会输出 `Secret`、`Match`、`Line`、prompt、源码行或完整报告。自测样本在工作树下带随机后缀的临时目录创建，并在 `finally` 删除；本轮结束后未发现残留目录。

## 规则与能力

- 默认规则：`[extend] useDefault = true`，不设置 broad allowlist；历史发现必须逐条处置，不能通过整类 key 或目录忽略。
- 项目专用规则 `t06-project-secret-assignment`：仅匹配 `AI_API_KEY`、`JWT_SECRET`、`WECHAT_APP_SECRET` 在同一行的非空 24 字符以上值；使用 `[ \t]` 避免跨行把下一项配置误识别为 secret。示例中的空值和短占位符不命中。
- `--scope=worktree` 扫描整个受管工作树，覆盖 tracked、modified、untracked/new 文件；`--scope=history` 使用 Gitleaks `detect` 扫描当前可得完整 Git 历史；`--scope=all` 合并两者，可额外接受 `--build-dir <仓库内目录>` 扫描 H5/小程序构建目录；构建目录必须位于仓库根内，拒绝路径穿越。
- 运行参数包含 `--redact 100`、`--no-banner`、`--log-level error`。发现时包装器以退出码 1 表示需处置；扫描器自身使用退出码 0 以确保报告落盘，包装器再依据脱敏发现数返回结果。

## 脱敏扫描结果

### 合成样本自测

`node scripts/security-secrets.mjs --self-test` 在临时文件写入合成 `AI_API_KEY` 值，命中 `t06-project-secret-assignment`，只输出 `security-secrets: self-test=pass findings=1`，退出码 0。样本内容未写入版本库、报告或聊天。

### 当前工作树

`node scripts/security-secrets.mjs --scope=worktree` 输出 `findings=0`，退出码 0。该结果包括本轮新增脚本、配置和交付文件，以及所有已有 untracked/modified 文件；不代表 Git 历史或未来构建物无发现。

### 当前可得 Git 历史

`node scripts/security-secrets.mjs --scope=history` 输出 3 条，退出码 1：

| scope   | rule              | location                                     | 脱敏 fingerprint   |
| ------- | ----------------- | -------------------------------------------- | ------------------ |
| history | `generic-api-key` | `miniprogram/pages/student/chat/chat.js:137` | `d778f15337798100` |
| history | `generic-api-key` | `miniprogram/pages/student/chat/chat.ts:141` | `8a3ca2c594c75a93` |
| history | `generic-api-key` | `miniprogram/pages/student/chat/chat.ts:147` | `f6d7abe6cb857ce9` |

这三项与 `docs/security.md` 记载的旧聊天页 TypeScript/生成 JavaScript 模型 key 位置相符；本任务没有读取匹配值，因此不能证明它们是否为同一凭据，也不能证明已撤销。历史凭据状态保持 **未知**，SEC-01 和生产发布继续阻塞。

`node scripts/security-secrets.mjs --scope=all` 合并结果仍为上述 3 条、退出码 1；本轮 `dist/` 不存在（只读检查为 false），未运行构建，也未执行指定构建目录扫描。构建后应由发布/CI 调用 `--scope=build --build-dir <实际构建目录>`，不得把构建物提交仓库。

## 命令与文件证据

| 命令                                                                                                                         | 结果                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `node --check scripts/security-secrets.mjs`                                                                                  | 退出码 0                                                                                   |
| `node scripts/security-secrets.mjs --self-test`                                                                              | 退出码 0；`self-test=pass findings=1`                                                      |
| `node scripts/security-secrets.mjs --scope=worktree`                                                                         | 退出码 0；`findings=0`                                                                     |
| `node scripts/security-secrets.mjs --scope=history`                                                                          | 退出码 1；3 条历史发现（上表）                                                             |
| `node scripts/security-secrets.mjs --scope=all`                                                                              | 退出码 1；3 条历史发现（工作树 0）                                                         |
| `git diff --check -- docs/update_plan/deliveries/T06-baseline.md scripts/security-secrets.mjs config/gitleaks-security.toml` | 退出码 0                                                                                   |
| `npx eslint scripts/security-secrets.mjs`                                                                                    | 未形成有效门禁：退出码 2，当前未安装的 `@eslint/js` 导致配置加载失败；未因此修改仓库或依赖 |

任务范围文件 SHA-256（交付时复算）：

| 文件                                          | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| `docs/update_plan/deliveries/T06-baseline.md` | `5B0544846E9444B605F9B0FA5180AAB58B2098C78A5CD681F4DAAC238F8727E9` |
| `scripts/security-secrets.mjs`                | `C076FEC2AA2479BFB305D27DFD2386095AECED39FBD79065E706C30ADD6DA1CB` |
| `config/gitleaks-security.toml`               | `A84D01CDC46F33833C69410B0386D1A89640A9896BF8B9FC8A21DA55BF5F4B68` |

未修改文件的参考哈希：`package.json` = `09D56489D8184DBB0A844B42F7EEF1449B332E9F3EABB042B9E148C1B7FE4C1E`，`package-lock.json` = `91D4DE0594F9CAA81CF264E25714E40428E3B20873B1F1F41882FBC7358A0252`，`backend/requirements.txt` = `A7DCFD2A3BD649650510E3F94B465278DE163823FBDA65DD7CCDD2FAAB1CC3B9`。这些哈希仅用于证明本轮未改包管理或 Python 依赖文件，不代表依赖审计已完成。

## 管理员操作单与下一阶段接线

1. **历史模型凭据（P0／SEC-01）**：凭据平台管理员依据三条脱敏位置/指纹定位对应历史 key，立即撤销并重新签发后端专用 key；检查调用账单、访问日志和异常用量。只回传工单号、时间、脱敏指纹和状态，不回传原始 key。若无法核实，保持发布阻塞；不由本任务重写远程历史。
2. **教师报告范围（P0／SEC-03）**：负责人确认 R-01 是班级/owner 限制还是经批准的共享审阅队列。政策确认后由 T04 实现或记录例外，T05 用跨教师负向用例复验；在决策和证据完成前不把当前行为宣传为安全隔离。
3. **Demo 身份（P1／SEC-04）**：负责人确认非生产 demo 是否允许任意合成身份选择角色；再决定固定 demo allowlist 或保留现行为并记录访问边界。生产仍必须提供 `ENABLE_DEMO_AUTH=false` 的负向证据。
4. **生产/平台（P0／SEC-07/09）**：发布管理员在批准环境验证强 JWT、seed 关闭、HTTPS/CORS、微信合法域名、受管数据库、AI endpoint/secret 来源、供应商数据处理协议和医学审核签署；只回传脱敏配置状态和证据链接。
5. **npm/CI 接线（交 T02）**：本轮没有编辑 `package.json` 或 CI。建议在依赖与门禁方案确认后新增：`security:secrets` 调用 `node scripts/security-secrets.mjs --scope=all`；独立自测调用 `node scripts/security-secrets.mjs --self-test`；双端构建完成后额外调用 `--scope=build --build-dir <构建目录>`。CI 必须保留退出码 1 为未处置发现，且不上传原始 JSON。

## 状态、回退与解除条件

状态：**T06-02 仓库侧扫描器、自测和脱敏基线完成；SEC-02 的工作树检查通过，历史发现未处置；T06 未闭环，生产发布阻塞。**

回退只需删除本轮新增的 `scripts/security-secrets.mjs`、`config/gitleaks-security.toml` 和本交付记录，并恢复 T06-baseline 的前一版本；不涉及数据库、迁移、API 合同或运行配置。不得以回退扫描器来恢复历史 key 或放宽秘密门禁。

解除发布阻塞至少需要：历史凭据撤销/轮换和调用审计证据；R-01 授权政策及对应代码/测试结论；生产平台与供应商/医学外部证据；T01 安全 fixture 完成后由 T02/T05 接入扫描、构建泄露检查和关键回归。

## 统筹集成复验补充

统筹发现原 `worktree` 扫描会把本机未跟踪且被忽略的 `.venv-*` 纳入扫描，并且 Windows 下 Gitleaks 目标路径处理不稳定。集成时改为使用 `git ls-files --cached --others --exclude-standard -z` 建立只含受管且未忽略文件的系统临时扫描区，同时拒绝符号链接；Gitleaks 改在目标目录内以相对路径运行。脚本还补齐 Node 全局的显式导入，以通过仓库 ESLint。

修正后统筹复验：语法检查通过；合成自测命中 1 项并退出 0；工作树 0 项并退出 0；双端构建后的 `dist` 0 项并退出 0；Git 历史仍准确报告同 3 项并按设计退出 1。交付正文中的旧脚本 hash、`dist` 不存在和 ESLint 无法执行等陈述仅代表子任务当时状态，以本补充和 `execution-status.md` 为当前事实。历史凭据撤销状态仍未知，发布阻断不变。
