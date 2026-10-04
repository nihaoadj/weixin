# 微信页面进入方法核对

2026-10-02。最新结论：开发目录与进入参数正确；仅关闭并重开指定项目窗口后，模拟器恢复登录、教师待办、PBL与独立测试队列渲染。原WXSS编译错误已不再持续，内部根因未定位。当前剩余阻塞是CLI无法定位组件内导航与审阅按钮，不能把页面直达当真实导航点击通过。

## 核对事实

- 本地 wechatide 工具说明版本 0.3.9；check_wechatide_status --skill-version 0.3.9 返回 loginExpired=false、versionRelation=equal、tokenRequired=false。
- project_list 显示开发产物目录与仓库根目录分别是已导入项目。本轮操作始终指定开发产物目录 D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin，未误指生产目录；生成 project.config.json 未设置 miniprogramRoot，使用目录本身，根仓库配置的 dist/dev/mp-weixin 不会在此目录重复拼接。
- open_project_window --project D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin --window-mode liteMode 返回 ok=true、type=reuse、winId=s0，未新建项目窗口。
- simulator_open_page --project 开发目录 --page pages/login/login 返回 ok=true，但这是编译触发成功，不证明编译完成。
- 改用标准反斜杠绝对路径，显式确认窗口后 currentPage 仍业务 ok=false/rawPath；pageStack 返回 ok=true、pageStack=[]，页面尚未创建。
- simulator_screenshot 显示 WXSS 编译错误。受影响课堂组件及未修改登录页 compile_wxss 返回 code=10041，CLI进程exit 0不等于业务成功。
- 同一安装目录下原生 wcsc.exe -lc app.wxss pages/login/login.wxss 退出码0；对全部71个生成WXSS编译退出码0。[控制文件](native-wxss-control.log)、[全部样式](native-wxss-all.log)。这只证明独立编译器语法检查，不证明当前模拟器编译链路。
- 最新 WeappLog 2026-10-02-09-00-29-534.log 中多次 webview on error 为 WXSS 编译错误，没有具体源码位置或 unexpected token。未保存完整工具日志以避免不必要的账号/运行信息留存。

## 判断与限制

此前未显式检查项目窗口复用状态，步骤不完整；补齐后现象相同，不能把它认定为根因。现有证据更指向工具当前编译/运行上下文异常，但尚不能细分为编译桥、配置、缓存或基础库问题。没有重置工具数据、升级/降级依赖、关闭URL校验、改dist或改业务方法来替代真实点击。

## 本次复查的恢复与交互证据

- 内部wcc-electron编译桥在安装目录Electron 36.6.0/Node 22.16.0运行，全部71个WXSS、44页编译exit 0，47个结果条目：[日志](wxss-addon-probe.log)。仅诊断，不修改安装文件或dist。
- close_project_window仅关闭指定开发目录项目；open_project_window随后返回newopen/s0。未清理缓存/数据，未更换基础库或关闭URL校验。立即pageStack仍空；编译完成后currentPage为pages/login/login。
- 真实tap .role-button.teacher成功，后续currentPage为pages/teacher/index/index。simulator_open_page直达PBL后currentPage为pages/teacher/pbl/index，截图已审阅：[课堂看板](pbl-list-reopened.jpg)。当前恢复了保存的课堂，学生尚在形成综合，因此没有诊断和测试按钮。
- 独立队列截图已审阅：[测试待办](test-queue-reopened.jpg)。tap .queue-back真实返回待办；tap .todo-row真实进入pages/teacher/pbl/test-queue?reviewKind=pending_review。
- 主导航使用组件穿透与普通页面selector两次均no such element；队列.queue-action也no such element。页面截图有控件，但接口无法定位，停止重试。未使用setData、业务方法或系统鼠标键盘替代。

人工待验MA-T54-001保留，范围缩为组件内课堂/诊断/最终测试入口、详情返回与剩余操作。此次恢复证明重开项目会话有效，不能据此认定缓存、SDK或业务样式为根因。
