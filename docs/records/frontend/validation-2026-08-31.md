# 前端设计与微信同步验收记录

日期：2026-08-31。工作区：`D:\CODE\weixin\wxprogrom7.15`。Git 基线：`b96bab9`，但开始时即存在大量未提交/未跟踪的业务重构，不能把相对 HEAD 的全部差异算作本轮修改。

设计方案与当前/未来边界见 [前端设计](../../frontend/design.md)。本记录不替代 T01–T07 的独立验收。

## 1. 范围与已有改动保护

本轮修改的是视觉/交互层、必要的微信启动兼容及其测试：

- `App.vue`、`uni.scss`、登录与学生学习/问答页面、共享图标/状态/学生导航。
- 教师工作区、报告/问题列表、`components/teacher/TeacherWorkspaceNav.vue` 与 `TeacherOverview.vue`。
- 教师报告详情及 `ReportTranscript.vue`、`ReportReference.vue`、`ReportFeedback.vue`；从嵌套气泡改为连续文档与人工评价区。
- `keyboard.ts`、`nativeFieldA11y.ts` 及对应测试，保证 uni-app H5 自定义控件的实际键盘/输入语义。
- `main.ts` 的启动顺序与 `platform/contracts/validationRuntime.ts`，避免微信 Zod 动态编译崩溃。
- 现有 E2E 的文案/导航选择器、经过审阅的视觉基线、设计与开发说明。

未 reset、clean、回退、提交或推送；未恢复已删除的 `docs/update/README.md`。其他后端、feature 分层、计划文档及生成契约的既有改动保留。未修改用户安装的 skill 文件来迁就格式检查。

## 2. 同步诊断与修复证据

### 当前事实

微信开发者工具加载 `dist/dev/mp-weixin`；生产命令写入 `dist/build/mp-weixin`。仅执行 `build:mp-weixin` 不会更新工具正在显示的 dev 目录。已恢复 `npm run dev:mp-weixin` 持续编译，输出目录与实际导入项目一致。

同步后仍出现启动异常，堆栈指向 Zod `Doc.compile` / `generateFastpass`，并伴随 `Function.prototype.apply` 类型错误；后续模块未定义是启动失败的连带现象。现改为在 `main.ts` 第一项导入中执行 `z.config({ jitless: true })`。已检查生成 `app.js`，配置引入早于业务模块和 schema 构造。

这不是关闭验证：新增用例证明动态 `Function` 不被调用，嵌套契约、会话角色、空 token 等非法输入仍被拒绝。模式仍由原装配点决定，不因 API 失败切换 Demo。

另发现小程序对共用 `100dvh` 声明的表现不符合预期，会让教师底栏回到内容中部。现仅 H5 输出动态视口声明，小程序使用 `100vh`；真实开发者工具截图确认导航在底部。

开发者工具普通编译/热重载需要等待完整启动。新增组件时短暂的空白、旧页面残留不能作为最终界面证据；最终截图均在页面加载完成后获取。没有清空工具数据、关闭安全检查或开启服务端口。

参考资料：[Zod 编译配置](https://zod.dev/compile)、[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)。问题判断同时以本地堆栈、编译输出和实拍为证据。

## 3. 设计验收结果

### 教师导航

- 手机主导航固定在底部，桌面在左侧；报告、问题和工作台不再在一张长页中叠放。
- 报告为默认入口；进入问题后有独立标题、顶部创建操作与状态筛选。
- 空状态不再重复“新建问题 / 生成病例”操作。
- H5 320/768/1024/1440 测得无横向溢出。滚动问题列表时，页面外层 `scrollTop=0`，内部列表滚动，主导航位置不变，工具栏吸附在页眉下。
- API 回归覆盖创建问题、批阅报告、管理班级、医学审核等下钻与返回路径；当前工作区以 query 保留。

### 报告批阅

- 最终辅助文字色为 `#5E7382`；计算得到在 Paper 底色上的对比度 4.63:1、Surface 上为 4.84:1，替换原来在 Paper 上仅 4.32:1 的色值。该检查针对这组令牌，不冒充全站无障碍认证。

- 页眉以学生与提交信息识别报告；不再将 AI 分数放在最大卡片中。
- 原文为完整的编号记录，保留角色、时间与换行；正文内嵌套 `.card` 数量为 0。
- AI 摘要、优势、待补充和一般建议分级呈现；人工评价区用无圆角的浅底分区和青色顶线定位。
- 手机连续阅读后填写；桌面在右侧对照填写。评分必填、反馈选填且仍限 1000 字。
- 已批阅报告可更新；失败保留输入；提交中禁用重复提交。字段错误与保存错误分别在对应位置展示。
- 320/768/1024/1440 无横向溢出；提交栏左右边界与应用壳一致，未超过 1080px 外壳。
- 实际 H5 输入获得可访问名称；Enter 触发缺失评分提示，`aria-invalid=true`，Tab 从评分移到反馈。修正后的独立页面错误监听结果为空。

## 4. 截图证据

截图来自 Demo 或受管测试数据；没有真实 AI/微信服务调用。微信截图是 OS 级实拍，不用 H5 截图冒充。

| 证据                 | 文件                                                                                                      |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| 微信批阅页布局实拍   | [teacher-review-wechat.png](../output/playwright/second-pass/teacher-review-wechat.png)                   |
| 微信批阅页教师反馈区 | [teacher-review-feedback-wechat.png](../output/playwright/second-pass/teacher-review-feedback-wechat.png) |
| H5 手机批阅首屏      | [teacher-review-390.png](../output/playwright/second-pass/teacher-review-390.png)                         |
| H5 手机输入/焦点状态 | [teacher-review-feedback-390.png](../output/playwright/second-pass/teacher-review-feedback-390.png)       |
| H5 桌面对照批阅      | [teacher-review-1440.png](../output/playwright/second-pass/teacher-review-1440.png)                       |
| 教师问题长列表滚动   | [teacher-problems-scrolled-390.png](../output/playwright/second-pass/teacher-problems-scrolled-390.png)   |
| 桌面教师工作区       | [teacher-problems-1440.png](../output/playwright/second-pass/teacher-problems-1440.png)                   |

微信原始临时截图：`C:\Users\adj\AppData\Local\Temp\codex-shot-2026-08-31_10-42-52.png`、`codex-shot-2026-08-31_10-45-58.png`，复制到上述证据路径时没有裁切/调色/编辑。

H5 布局与键盘复验使用 `output/playwright/second-pass/check-report-review.pw`；问题滚动复验使用 `check-teacher-layout.pw`。这些是 Playwright CLI 的原始函数输入，不是应用源码或新的 Playwright test spec。运行目录为该文件所在目录：

```powershell
npx --yes --package @playwright/cli playwright-cli -s=ui-sync run-code --filename check-report-review.pw
```

该脚本要求浏览器已经通过 UI 登录并打开对应 Demo 报告。它会填入示例评分/反馈验证布局，之后清空，不执行保存。主工程师已查看关键手机/桌面/微信图像，而非只检查文件是否生成。

## 5. 命令与退出码

微信截图记录最终布局，获取时间早于最后一次小幅辅助文字加深；这次色值调整已在 H5 复拍及两个构建中验证。再次系统实拍因前台窗口不匹配而安全取消，没有继续点击或拍摄其他应用。

共享样式还复核了 [学生问答页](../output/playwright/second-pass/chat-390.png)：输入区与底部导航保持在视口内，可访问名称已到达真实输入控件，禁用操作有显式禁用语义。

除 CLI 脚本外均在仓库根运行。以下为本轮最终结果，均为本地证据。

| 命令/检查                                                              | 退出码 | 结果                                                          |
| ---------------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| `python .agents/skills/wx-engineering-standards/scripts/self_check.py` | 0      | 项目 skill 路由检查通过                                       |
| 针对本轮源文件、测试和文档的 `npx prettier --check …`                  | 0      | 本次编辑内容格式通过                                          |
| `npm run lint`                                                         | 0      | 无错误/警告                                                   |
| `npm run type-check`                                                   | 0      | Vue 与 Node TypeScript 检查通过                               |
| `npm test`                                                             | 0      | 29 个文件，126 个测试通过                                     |
| `node scripts/frontend-boundaries.mjs`                                 | 0      | 127 个实现文件边界通过                                        |
| `npm run contract:check`                                               | 0      | 临时目录生成比对通过，未改写契约快照                          |
| `npm run build:mp-weixin`                                              | 0      | 最终小程序生产构建通过                                        |
| `npm run build:h5`                                                     | 0      | 最终 H5 生产构建通过                                          |
| `npm run test:e2e`                                                     | 0      | 8 个 API/浏览器用例通过                                       |
| `npm run test:e2e:demo`                                                | 0      | 5 个 Demo/视觉用例通过                                        |
| Playwright CLI 报告多宽度/键盘复验                                     | 0      | 四个宽度无溢出、输入命名、错误与 Tab 顺序通过，新增页面错误 0 |
| `npm run format:check`                                                 | 1      | 仅 6 个现有 skill 文件格式不符，见下文                        |

完整格式检查剩余：`frontend-ui-engineering/SKILL.md`、`playwright/SKILL.md`、`playwright/agents/openai.yaml`、`screenshot/SKILL.md`、`screenshot/agents/openai.yaml`、`web-design-guidelines/SKILL.md`，均在 `.agents/skills/`。本次不重写安装包内容、不忽略检查来伪装全仓通过。

中间失败均已区分原因并复验：登录/工作区视觉快照因设计变化不匹配，查看实际图后才更新基线；Lint 曾与 E2E 清理输出目录并发冲突，已串行复跑；H5 键盘验收发现标准事件与 uni 包装事件的差异，修正后追加单测与浏览器复验；微信组件样式中的属性选择器及旧文本选择属性已改为兼容写法。

构建仍有 Zod 上游 PURE 注释提示；单测有 App 无 render/template 的既有测试警告；微信仍可出现开发工具/基础库的 SharedArrayBuffer、getSystemInfo、热重载和 worker 提示。这些没有通过关闭日志或吞错隐藏，不宣称所有控制台警告为零。

## 6. 接口、数据、安全与未执行项

- 公开业务 API、DTO、schema 和后端授权不变。页面仍经 feature public API 读写，不新增 `uni.request`、storage key 或后端地址拼装。
- API/Demo 仍互斥；Demo 流程测试确认没有核心业务 API 请求。启动兼容只改变 Zod 执行方式，不降低验证约束。
- 无生产/开发数据库迁移、真实微信登录、真实 AI、推送、部署、密钥或全局设置操作。API E2E 仅使用现有 launcher 创建的带所有权标记的随机临时 SQLite，并关闭真实 AI/微信调用。
- 没有修改后端实现/迁移，因此未跑全量后端、依赖审计、远程 CI 或完整 `check:all`；本记录不代替这些门槛。
- 未新增完整覆盖率达标声明；执行的是全量现有前端单测与定向新增交互测试，没有放宽覆盖率阈值。
- H5 浏览器与微信开发者工具不是真机。iOS/Android 软键盘、真实读屏与长期性能未验收；需在对应设备使用测试账号复验。缺失的 skill 扩展无障碍 checklist 没有被当作已执行的审计。

## 7. 回退与交接

如需回退，只审阅并撤销本轮目标文件中的 UI/启动适配差异及其测试/截图，保留开始时存在的业务分层改动；禁止整文件 `checkout` 或整库 reset。撤销纯 UI 不涉及数据回退。若撤销 Zod 启动适配，当前微信动态编译故障会重新出现，应先准备兼容方案。

开发者工具继续导入 `dist/dev/mp-weixin`，保持 `npm run dev:mp-weixin` 运行；源码改变后等待编译完整结束。生产构建仍在另一个目录，详见 [开发说明](../../operations/development.md#微信开发者工具源码与构建目录同步)。

状态：本轮 UI 与本地跨端验收完成；真机/完整读屏及远程 CI 是明确的后续验收，不混同为已通过。
