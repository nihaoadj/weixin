# 教学内容编辑与交互动效 · 2026-08-31

## 设计决策

本轮面向教师创建普通问题、编排结构化病例，以及从教学内容/报告列表进入详情的流程。沿用上一轮教学记录单语言，不重做身份、数据合同和医学审核流程。

视觉角色沿用六个项目色：Paper `#f6f8f6` 为工作台底色，Surface `#fbfdfd` 为编辑纸面，Ink `#102a43` 为标题，Clinical `#0a6b66` 为主操作，Wash `#e4f1ee` 为选中范围，Safety `#9a5618` 为审核提醒。正文和辅助文字复用现有语义令牌，不引入新字体或远程资源。

标题使用系统中文无衬线的 24–28px/粗体；分区标题 18px；字段与正文约 16px；提示 13–14px。层次来自版面、字号和内容分区，而非一层层圆角容器。保留输入和按钮的小圆角，帮助辨认可操作区域。

| 页面          | 主阅读顺序                                   | 宽屏布局             | 本轮辨识点                                     |
| ------------- | -------------------------------------------- | -------------------- | ---------------------------------------------- |
| 新建/编辑问题 | 页面身份 → 题目内容 → 发布范围 → 保存待审核  | 内容主栏 + 范围侧栏  | 题目是主体，范围是独立决策；保存不暗示直接发布 |
| 病例创建      | 教学设定 → 生成草稿 → 五步核验               | 设定主栏 + 流程说明  | 生成是起点，不把 AI 草稿表现成成品             |
| 病例编排      | 当前步骤名称 → 学生/教师可见字段 → 上/下一步 | 有名称的进度与编辑区 | 五步是真实流程，不用无语义装饰编号             |
| 问题列表      | 类型/范围/时间 → 标题/内容 → 独立操作栏      | 紧凑纵向列表         | 阅读区整体可点，拒绝/编辑/发布不触发详情       |

## 动效约束

- 按下反馈立即开始，70ms 短过渡，释放后 180ms 回稳；普通按钮位移 1px，阅读型卡片缩放至 0.992。只改变 transform/opacity，不触发布局动画。
- uni 按钮使用 `hover-start-time=0`、`hover-stay-time=80` 的明确触摸反馈。保持原生 touchcancel 处理；不捕获全局触摸，不阻止纵向滚动。
- H5 页面内容用 200ms 透明度入场；不移动页面根节点，避免固定栏随包含块改变定位。病例步骤内容可用 6px 短位移。没有倒计时、自动滚动或长循环装饰。
- 微信页面转场仍由原生导航完成。`navigateTo.animationType/animationDuration` 仅为 App 参数，不能称为微信/H5 转场配置。依据：[uni-app 路由官方说明](https://uniapp.dcloud.net.cn/api/router.html)。
- 同目标导航仅在原调用未完成时合并；成功/失败释放，不增加定时等待。失败显示可重试提示。列表本地分页不再假等待 250ms。
- 教师报告与问题详情加载时保留文档形状占位；失败可重试，不以空白或静默降级冒充完成。
- `prefers-reduced-motion: reduce` 关闭入场和位移过渡，保留静态按下反馈。

设计与工程依据：`frontend-design`、`frontend-ui-engineering`；复核使用 [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)。UI 工程 skill 指向的 accessibility-checklist 在本仓库不存在，因此以现有可访问性 helper、指南及实际键盘/浏览器验证补充，未假定其已读取。

## 验收记录

当前状态：仓库内实现、设计复审和双端构建完成；微信开发者工具的开发输出已重新同步。新版目标页的开发者工具实拍仍需窗口保持前台后补，不以 H5 截图冒充微信实拍。

### 设计复审结论

- 首轮问题页的题型和范围仍像居中的小胶囊，病例生成按钮也过于孤立。第二轮将题型改为三等列，范围改为有说明和勾选标记的全宽选择行；病例页增加编辑纸面与五步核对轨道，按钮归入明确操作区。
- 五步结构只用于真实编排顺序：病例概况、阶段与事实、参考推理、评价量表、预览核对。步骤切换后立即对齐步骤标题并移动键盘焦点，不添加等待动画，也不允许前跳绕过校验。
- 学生公开信息、教师/审核专用字段在页面上有文字标识，不只依赖颜色。动态生成的 H5 原生输入框经实际 DOM 检查后补齐 `aria-labelledby` 和稳定 `name`。
- 列表阅读区与拒绝/编辑/发布操作区分离；列表分页移除伪造的 250ms loading。问题和报告详情保留文档形状加载占位，降低点击后的空白跳变。
- 最终 Web Interface Guidelines 复核未发现本轮文件中的 `transition: all`、无替代焦点的 `outline: none`、禁用缩放、未命名按钮或仅颜色表达选中状态。表单离页未保存确认没有在本轮扩大实现，仍是后续可单独定义的产品策略。

### 浏览器与动效证据

- Playwright CLI 在 320、390、768、1024、1440px 检查新建问题和病例创建页：10 个组合均无横向溢出；最终可见输入和按钮均有可访问名称。
- 病例生成后重新检查动态 DOM：6 个首步原生字段未命名数为 0，`name` 为 `case-title`、`case-specialty`、`case-duration`、`case-description`、`case-patient-intro`、`case-chief-complaint`。
- 问题页 Tab 顺序依次覆盖 3 个题型、标题、说明和 3 个发布范围选择；病例从第 1 步切换到第 2 步后，活动标记为“事实”，步骤标题位于视口顶部约 44px 且获得焦点。
- 阅读卡按下为 `scale(0.992)`/70ms，松开并移出后恢复 `transform:none` 且无残留 `is-pressed`；快速双击只增加 1 层页面栈。700ms 采样 118 帧，最大帧间隔 7ms（本机 H5 证据，不外推为所有设备性能）。
- `prefers-reduced-motion: reduce` 下按压 transition 为 0s、页面入场 animation 为 none。最终新浏览器会话控制台为 0 error、0 warning。
- 截图位于 `output/playwright/editor-motion/`：`problem-final-390.png`、`case-final-390.png`、`case-final-1440.png`、`case-step1-390.png`、`case-step2-390.png`、`problem-detail-390.png`。CLI 原始动效 trace 已移到系统临时目录 `C:/Users/adj/AppData/Local/Temp/codex-motion-trace-20260831-1125`，避免生成的脚本资源污染项目 Lint。

### 命令证据

| 命令                                                                   | 结果                                                                                                                |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `python .agents/skills/wx-engineering-standards/scripts/self_check.py` | 退出码 0，skill 结构、链接与状态标签通过                                                                            |
| `npm run lint`                                                         | 退出码 0                                                                                                            |
| `npm run type-check`                                                   | 退出码 0                                                                                                            |
| `npm test`                                                             | 退出码 0；33 个文件、139 个测试通过；保留既有 App 无 render 的 Vitest warning                                       |
| `node scripts/frontend-boundaries.mjs`                                 | 退出码 0；129 个实现文件通过                                                                                        |
| `npm run build:mp-weixin`                                              | 退出码 0；仅有上游 Zod PURE 注释位置 warning                                                                        |
| `npm run build:h5`                                                     | 退出码 0；同一上游 warning                                                                                          |
| `npm run test:e2e`                                                     | 退出码 0；API 模式 8 个通过；launcher 仅使用有所有权标记的临时 SQLite，真实 AI/微信凭据禁用                         |
| `npm run test:e2e:demo`                                                | 退出码 0；Demo 模式 5 个通过，无 API 回退                                                                           |
| `git diff --check`                                                     | 退出码 0                                                                                                            |
| `npm run format:check`                                                 | 退出码 1；只剩 6 个用户安装 skill 文件不符合仓库 Prettier，未改写安装内容；本轮源码、测试、文档和截图 YAML 已格式化 |

微信同步事实：`dev:mp-weixin` 原 watcher 已停止，开发目录一度停在 11:28；已重新启动并于 2026-08-31 11:45 左右输出 `DONE Build complete. Watching for changes...`，导入路径仍为 `dist/dev/mp-weixin`。生产构建目录没有复制覆盖开发目录，也没有清理开发者工具数据。

范围保护：保留已有未提交/未跟踪工程改动；只编辑本轮前端、相关测试和此记录。没有提交、清理或还原工作树。

接口与安全：沿用 feature public API；没有修改 OpenAPI、后端、角色/范围授权、API/Demo 装配、存储键或数据库迁移。没有真实 AI/微信服务调用。

未执行/外部项：没有运行后端全量 pytest、迁移安全回归、远程 CI、真机或生产发布，因为本轮没有修改后端/迁移/契约，且这些事项不属于普通前端 UI 授权。微信开发者工具最后一次目标页截图因窗口未保持前台而由安全保护取消；解除条件是窗口保持前台后执行普通编译并打开“问题编写”或“病例编排”。

回退：按本轮文件差异逐块撤销编辑页、列表和动效补丁；不要整体恢复当前 dirty 文件或旧 HEAD。无需数据库回滚；重新运行双端构建并等待 dev watcher 完成后在微信工具普通编译。
