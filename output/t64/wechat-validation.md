# T64 微信检查摘要

2026-10-03，工作区D:/CODE/weixin/wxprogrom7.15；显式`VITE_APP_MODE=demo`。开发目录`dist/dev/mp-weixin`，CLI为`D:/codeapp/微信web开发者工具/wechatide.cmd`，client为`Codex`。

| 检查                                                                        | 结果与证据                                                                                                                                                 |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run dev:mp-weixin`                                                     | 初次Build complete约10.5秒，相关热更新完成，watcher保持运行；未改生成物                                                                                    |
| `npm run build:mp-weixin`                                                   | exit 0，[构建日志](build-demo.log)；现有Zod PURE注释警告，无编译失败                                                                                       |
| `node scripts/wechat/check-wxss.mjs --project dist/dev/mp-weixin`           | exit 0，69份，[开发WXSS](wxss-development.log)                                                                                                             |
| `node scripts/wechat/check-wxss.mjs --project dist/build/mp-weixin`         | exit 0，69份，[生产WXSS](wxss-production.log)                                                                                                              |
| `open_project_window`、`simulator_refresh`                                  | 复用指定开发项目，均ok；普通编译                                                                                                                           |
| `npm run test:mp:doctor`                                                    | exit 0，SDK3.17.2、URL校验开启，[环境日志](wechat-doctor.log)                                                                                              |
| 第一次真实登录交互                                                          | `simulator_open_page`打开`pages/login/login`成功；`automation_element_action`对`.role-button.teacher`执行tap，ok=false，rawPath/getPageMetaByWebviewId错误 |
| 第二次真实登录交互                                                          | 仅关闭并重新打开同一项目窗口，正式打开登录页成功；同一教师按钮tap超时。停止后续交互及截图重试                                                              |
| `compile_wxml`，file-path=`components/teacher/TeacherContentResources.wxml` | 工具ok=true，生成函数`$gwx`，codeLength=782836，[内容模板日志](wechat-content-wxml.log)                                                                    |

工具进程正常返回不等于tap成功；两次tap均未通过。未清业务存储、未手改dist、未禁用URL校验、未用setData或业务方法模拟操作。未获得T64当前渲染截图，不用T63图片代替。WXML/WXSS仅证明语法可编译。

真实登录、内容两标签、创建/绑定/保存、课堂选用、编辑/删除及题库导入/持久化的人工步骤统一见[MA-T64-001](../../docs/manual-acceptance.md#ma-t64-001)。不扩展为API真实服务、生产、真实AI或真机验收。
