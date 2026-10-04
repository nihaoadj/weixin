# 微信开发者工具验收

## 开发环境

在仓库根目录启动Demo watcher：

```powershell
$env:VITE_APP_MODE='demo'
npm run dev:mp-weixin
```

保持watcher运行至`Build complete. Watching for changes...`，工具仅加载`D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin`并普通编译。生产构建目录不能刷新开发目录；工具不会自动监听dist，自动化使用当前终端环境变量及受支持CLI：

```powershell
$env:WECHATIDE_CLI_PATH='D:\codeapp\微信web开发者工具\wechatide.cmd'
$env:WECHATIDE_CLIENT='Codex'
& $env:WECHATIDE_CLI_PATH -c $env:WECHATIDE_CLIENT open_project_window --project 'D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin' --window-mode liteMode
& $env:WECHATIDE_CLI_PATH -c $env:WECHATIDE_CLIENT simulator_refresh --project 'D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin'
npm run test:mp:doctor
```

CLI路径须指向实际安装的wechatide.cmd。doctor通过`automation_runtime_info --action systemInfo`检查项目、URL安全校验和SDKVersion，只证明环境就绪。报缺WECHATIDE_CLI_PATH时在同一终端设置，不改系统环境。

真实交互用`automation_element_action`的tap/input/scroll，截图用`simulator_screenshot`。9420是CLI/HTTP服务，不是App.* WebSocket；不使用`--auto-port`、`WECHAT_AUTO_PORT`、`ws://127.0.0.1:*`、Tool.getInfo或旧miniprogram-automator。旧automator脚本及停用npm入口已在T65清除，当前验收使用上述官方CLI；历史取证不作为新通过证据。不得手改dist、复制生产目录、清理工具数据或关闭安全校验替代编译。

## 选择验收范围

默认验证受影响页面与最小相关流程。完整核心回归仅用于发布候选、共享导航/应用壳/构建或跨模块数据/身份改动、影响外溢及用户明确要求。脚本以package.json为准，复用当前工具串行执行，不新开窗口、重登或抢占前台。

通过证据在代码、范围和相关环境未变化时复用；仅对失败项和新改动影响的部分复验。逻辑边界由合同/行为测试验证，微信只补必要的真实交互与渲染，不逐项重复逻辑用例。默认使用常规手机视口，不做320px专项或全机型矩阵。

截图只覆盖必要的当次可见状态，同页面同状态保留一张代表图。先以watcher、产物、WXML/元素属性和断言确认代码/状态，再用截图审阅视觉。旧图不证明新改动；不能连续截近似图等待编译或试探缓存。文件损坏、区域不全或真实编译/交互产生新状态时才补拍并记录原因，达到目标即停止。

## 交互与渲染

UI改动在watcher完成后增加原生WXSS语法检查（Windows开发环境，复用已安装微信工具，不安装额外编译器）：

```powershell
$env:WECHATIDE_CLI_PATH='D:\codeapp\微信web开发者工具\wechatide.cmd'
node scripts/wechat/check-wxss.mjs --project dist/dev/mp-weixin
```

该命令一次编译全部生成样式，失败直接给出具体文件、行和token；可用`--compiler`指定已安装的wcsc路径。Vite成功不能替代WXSS检查；工具显示`10041`/“编译.wxss文件错误”时先排查全项目样式，不能把其后pageStack为空/rawPath错误直接归为独立自动化阻塞。修复源码、等待watcher、重新检查和普通编译后继续真实操作与截图；禁止手改dist。原生检查通过仍不证明SDK渲染。

- 真实点击、输入、提交、返回与刷新，检查状态恢复和防重复；禁止setData或调用业务方法代替操作。
- 审阅实际文字/控件、长内容、加载/空/错误状态、代表宽度、滚动到底、固定栏、键盘/安全区与遮挡。
- 内部截图后台执行并逐张审阅；不使用系统截屏或系统鼠标键盘做验收。用户明确要求查看工具窗口时可截桌面，另作证据。
- 不自动接受截图基线；敏感数据处理见[安全](security.md)。

## 阻塞与人工交接

- 同一工具或环境阻塞最多尝试两次；明确不支持的操作不重试，不持续轮询或反复更换选择器。
- 无法连接、登录、定位控件或完成交互时，登记[人工验收台账](manual-acceptance.md)：所属计划、已验证内容、阻塞原因、完整步骤、预期结果及发布影响。复用已有编号，不重复登记。
- 登记后继续独立工作；用户方便时集中手动验收，不逐按钮请求，也不等待用户才能收尾。仅要求自动验收时同样登记，不请求当场协助。
- 用户反馈后更新原条目；通过则关闭，发现缺陷则关联修复任务。未受修复影响的通过项不重做。
- 页面错误、数据/权限错误和必要测试失败属于实际缺陷，不能转为工具阻塞绕过处理。

## 完成口径

逻辑测试证明被覆盖行为；构建证明可生成产物；doctor证明工具环境；实际操作和截图审阅只证明所测工具/SDK/宽度/状态。Demo只证明确定性界面合同，API授权、真实AI、专家审核、生产和真机需各自证据。

工具或环境导致缺少交互/视觉证据时登记人工待验，不阻断更新计划推进或最终收尾；结论注明“已收尾，人工待验：MA-xxx”，不得写成全部验收通过。源码编译失败、必要测试失败或已知功能缺陷仍须修复。无视觉变化不强制截图；真机按任务约定执行，未运行不标通过。涉及正式发布的待验项按台账所列发布条件处理，计划收尾不代表允许发布。

记录源码/工作区、模式、命令/退出码、构建时间、开发目录/普通编译、工具/SDK/宽度、角色/入口/流程、截图及补拍原因、失败项和解除条件。
