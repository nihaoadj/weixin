# T63 微信验证摘要

2026-10-03，工作区增量修改；Demo模式。复用PID6960 watcher，dist/dev/mp-weixin为当前开发项目，14:40后生成本次资源与学生入口改动。CLI为D:/codeapp/微信web开发者工具/wechatide.cmd，client=Codex，SDK3.17.2，URL校验开启，548×1182模拟器。未清理数据、关闭安全校验或手改dist。

| 操作                                                                            | 结果                                                         |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| simulator_refresh --project dist/dev/mp-weixin                                  | exit0，ok=true                                               |
| npm run test:mp:doctor                                                          | 初次exit1，普通编译完成后exit0                               |
| node scripts/wechat/check-wxss.mjs --project dist/dev/mp-weixin                 | exit0，73文件                                                |
| VITE_APP_MODE=demo npm run build:mp-weixin                                      | exit0，Build complete，日志build-demo.log                    |
| 原生WXSS检查dist/build/mp-weixin                                                | exit0，71文件，wxss-production.log                           |
| 登录页.role-button.teacher / .role-button.student真实tap                        | exit0，ok=true                                               |
| simulator_open_page pages/teacher/content/index，resource=cases / question-bank | exit0，ok=true；不是标签真实点击                             |
| 正确内容页.resource-switch读取、.resource-tab真实tap                            | CLI exit0但ok=false / no such element，2次后停止             |
| 学习首页.practice-card--knowledge真实tap                                        | exit0，ok=true；currentPage确认knowledge-node与有效topicCode |
| 学习首页.learning-page scrollTo x=0 y=1600                                      | exit0、ok=true，但画面未移动，不算底部验证通过               |
| 4张最终代表截图                                                                 | exit0、ok=true，逐张审阅，见交付记录                         |

操作修正：误用未注册的pages/teacher/problems/problems、pages/common/login/login；改为src/pages.json中的正式路径后页面正常。错误图片已清理，不当作环境或源码缺陷。scrollTo初次缺x参数返回ok=false，补全参数后仍无视觉移动，未继续试探。

组件标签/筛选/详情返回及学生底部可见状态登记MA-T63-001；接口、逻辑和渲染证据各按实际范围计，不以直接打开页面、测试或构建替代真实交互。
