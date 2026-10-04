# T64 S6 内容点击定位

2026-10-03。状态：S6点击故障修复已收尾。用户最终确认PBL/学情及内容的个人题库与创建病例恢复；全部资源操作仍沿用MA-T64-001补验。下文保留定位与失败记录，不把早期失败覆盖为通过。

## API与运行模式

病例列表、详情、编辑内容、创建、更新与删除对应`/problems`；个人题库列表、详情、更新、删除与导入对应`/teacher/question-bank`。后端已注册路由，前端ApiContentRepository已有对应调用。这是源码核对，并非真实API联调通过。当前开发产物明确为Demo，内容按钮不依赖后端连接。

## 早期调整（触摸拦截现已撤回）

资源按钮使用显式原生`tap.stop`，按钮及输入框用`touchstart.stop`隔离工作台横向手势识别。保留原业务方法、所有权校验、删除确认、API/Demo装配及布局；横向切换仍可从非控件区域开始。组件与实际控件增加稳定id供原生定位。新增原生tap入口的创建/查看/编辑/搜索检查，以及真实手势识别器不接收控件触摸起点的检查。

该修改解决控件事件进入祖先手势的风险，但尚未证明是用户报告问题的完整根因；不能以DOM行为测试称微信点击已恢复。

## 检查与证据

- 六份定向行为测试43项通过，exit 0；相关Lint/格式通过，exit 0，见[静态记录](content-click-static.log)。最新控件id后Resources的Lint/格式再次通过。
- 最新完整`npm run type-check`通过，exit 0，见[类型记录](content-click-types-final.log)；先前模块边界216项通过，事件属性未改变业务依赖。
- 显式Demo生产构建通过，exit 0，见[构建记录](content-click-build-final.log)。开发/生产各80份生成WXML用安装工具的原生wcc检查通过，exit 0，见[模板记录](content-click-wxml-final.log)；未改样式，复用S5原生WXSS证据。
- 早期控制台曾报`platform/mappers/messages.js is not defined`；磁盘产物存在且514条相对require无缺失。停止旧watcher、完整Demo重编译后恢复登录，但用户确认点击仍失效，因此模块加载错误不作为完整根因。
- 调用simulator_open_page时曾把query写入page路径，模拟器显示WXML错误；改为不带query的合法页面路径并重新打开同一项目后恢复。原生模板检查无错误，此过程不作为源码缺陷或点击通过证据。
- 当前SDK 3.17.2、548×1182，普通登录教师真实tap后进入PBL，再运行时reLaunch到内容。画面已审阅：[当前内容首屏](content-click-chain.jpg)。运行时导航不计作底栏/资源标签点击。
- 深层组件selector对标签/创建返回ok，但画面仍是病例列表且route仍content；扁平控件id返回no such element。仅返回ok没有预期结果，均不记为通过。已停止同类探测，见[标签](content-click-native-chain.log)、[创建](content-click-native-create.log)、[扁平id](content-click-native-flat-id.log)。没有调用业务方法或setData制造点击效果，没有清存储。
- 进一步只读定位确认：querySelector分别使用根组件id及`根id >>> 控件id`，都返回同一elementId=5、nodeId=5、TeacherWorkspaceDeck组件。工具未穿透到按钮，先前深层tap实际命中了组件根，属于选择器工具限制，不能归因业务事件失败。证据见[根组件查询](content-click-root-query.log)、[深层查询](content-click-deep-query.log)。根组件原生WXML确认资源按钮存在、id正确且编辑/删除未禁用；不保存包含完整列表文本的临时诊断产物。

## 接续：教师共享工作台

用户进一步确认教师Demo仅底栏可点击，其余PBL/学情/内容全部失效，故仅改资源按钮的处理不足。共享Deck内容层生成catchtouchstart/move/end/cancel，导航位于它的外部；所有预加载页仍挂载，旧版仅用pointer-events隔离非当前页，存在原生滚动/输入层命中风险。

本轮最小调整：Deck四个触摸事件改为普通bindtouch（取消stop），保留原手势识别；非当前pane在idle时visibility:hidden，在拖动/回弹期间显露，完成后重新隐藏，当前页始终可见。不卸载页面、不重建数据，不改API/Demo装配或权限。该修正针对共享容器的风险，实际根因与恢复仍需真实按钮反馈，不能以风险分析宣布修复成功。

- 九份定向共71项通过，完整类型、Deck定向Lint/格式、边界216 implementation files均exit 0。由Luna xhigh执行主代理选定检查，日志见[共享容器检查](teacher-deck-click-checks.log)。
- Demo生产构建exit 0，见[构建](teacher-deck-click-build.log)。开发/生产各70份WXSS及80份WXML原生检查exit 0，见[原生检查](teacher-deck-click-native.log)。
- 普通刷新曾出现编译错误页及rawPath/登录tap timeout；没有以Vite成功掩盖该结果。关闭并重新打开同一开发项目窗口、普通打开登录页后，教师真实tap成功，随后currentPage确认PBL。没有清业务存储或工具缓存，见[登录](teacher-deck-click-login.log)、[路由](teacher-deck-click-route.log)。
- 原生根组件WXML只读核对当前PBL有两个pane，一个当前页可见，一个inactive+hidden；确认新源码实际已加载，见[原生容器摘要](teacher-deck-native-inspection.json)。临时完整WXML诊断产物已删除，只保留无业务内容的类名与计数。
- 向用户请求当前版本的PBL班级选择、学情日期范围与内容创建按钮实际复测；不重试已知不支持穿透的SDK selector，不以组件根tap代替按钮tap。

用户回执：共享容器修正后PBL和学情恢复响应，只有内容仍失效。该回执是实际交互恢复的证据，不能扩大为内容已恢复。

## 接续：内容普通原生事件

撤回先前内容控件独有的touchstart.stop和tap.stop，统一普通原生tap；输入框继续原生input/confirm。保持共享Deck修正、布局、业务方法和身份保护。相关检查改为普通2px点击触摸传播但不启动横向滑动，不再要求以catchtouch阻止祖先。拖动仍由Deck识别。

- 资源与Deck三份相关spec共31项通过，完整type-check、资源组件及spec的Lint/格式均exit 0，见[普通tap检查](content-plain-tap-checks.log)。其余共享容器检查未受改动影响，不重复。
- 最新Demo生产构建exit 0，见[构建](content-plain-tap-build.log)；开发/生产各80份原生WXML exit 0，见[模板](content-plain-tap-native.log)。未改样式，复用刚通过的各70份WXSS。
- 重开同一开发项目并普通编译后，当前content原生作用域只读核对成功：由Deck→Pane4→ContentScreen直接找到Resources（Resources为ContentScreen的插槽所有者子组件，不是Frame的所有者子组件）。它有Vue实例、26个事件属性且未销毁，Vue $scope与原生Resources对象一致。创建e5_8a、搜索及两页签均为function，见[所有者](content-native-scope-owner.log)、[绑定](content-native-event-bindings.log)。未调用这些事件函数或导航业务方法制造结果；诊断参数临时文件已删除。
- 以上证明绑定存在，尚不证明实际tap命中，向用户请求当前普通tap版本实际复测。

最终用户回执：“两处均恢复响应”，指当前普通tap版本的个人题库页签与创建病例。与前一次PBL/学情恢复回执一起，确认教师三部分代表性实际交互恢复。恢复不依赖API或清缓存；保留修正：共享Deck普通bindtouch、静止隐藏非当前页及内容按钮普通tap。先前内容catchtouch隔离未解决问题，已全部撤销，不遗留两套触摸方案。

S6故障修复收尾；查看/编辑/删除取消及完整滚动/返回尚无SDK实际按钮证据，逻辑测试通过，剩余人工补验沿用[MA-T64-001](../../docs/manual-acceptance.md)。本轮不新增第三份完整计划，不声明全部按钮/真机/API联调通过。
