# 内容页固定区域滚动

2026-10-03。按用户截图进行展示布局维护，不改API、Demo数据、权限、导航结果或业务操作。

- TeacherContentScreen使用TeacherPageFrame fixed-content，整页主体高度100%、min-height:0、overflow:hidden；顶部插画固定。
- 资源组件占满剩余区域；资源页签、搜索、标题/创建按钮固定且不压缩，列表及其加载/空态/失败态放入单一原生scroll-view。列表flex:1、height:0、min-height:0，在底部导航上方独立滚动；记录尾部保留内边距，最后一条可完整滚入视野。
- 显式width:100%避免原生自定义组件收窄；原生宿主栏、安全区与底栏由现有容器保留，不新增fixed叠层或catchtouch，保持刚验收恢复的普通tap。
- 切换资源/搜索后列表视图重建回到起点，不重建资料数据，搜索/返回上下文保持。

验证：三个相关spec共24项、完整type-check通过。初次Lint两个属性顺序警告已修正，最终定向Lint/格式exit 0，见[行为/类型](content-fixed-scroll-checks.log)、[最终Lint](content-fixed-scroll-lint-final.log)。Demo构建exit 0，见[构建](content-fixed-scroll-build.log)。开发/生产原生WXSS各70份、WXML各80份通过，见[原生检查](content-fixed-scroll-native.log)。

微信SDK3.17.2、548×1182，教师登录真实tap、运行时导航到内容；已审阅[个人题库首屏](content-fixed-scroll-bank.jpg)。原生资源组件内createSelectorQuery只读矩形测量确认页签/创建区位于列表上方，列表独立获得剩余高度（窗口宽428px、列表宽392px/高450.4px，列表起于固定创建区下方，结束于底栏上方），见[区域测量](content-fixed-scroll-rects.log)。运行时导航和矩形不算实际滚动/按钮点击证据；已知SDK深selector仅命中Deck根，未重复探测或用setData/业务方法制造交互。

剩余实际滚动至末条/切换与返回的操作沿用MA-T64-001；既有教师点击恢复回执不因纯布局变更重复要求。原图压缩仍保留，不提交/推送。
