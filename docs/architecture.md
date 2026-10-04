# 架构与数据合同

本页定义模块与数据边界；业务见[产品](product.md)，权限见[安全](security.md)。函数、路由及字段以源码/生成契约为准。

## 前端模块与公开接口

`src/pages`拥有路由与页面生命周期；业务专属视图及邻近测试归入`src/features/*/presentation`，`src/components`保留通用UI与跨功能教师工作区。页面和应用壳可以组合功能视图；所有展示代码的业务读写只经`src/features/*/public.ts`进入用例、领域port与adapter，不直接导入domain/application/infrastructure。domain/application保持纯业务，不直接使用`uni.request`、storage key或后端URL。`src/platform`拥有HTTP、storage、runtime、导航、缓存和契约；`src/bootstrap/wiring.ts`是唯一API/Demo装配点。

Demo知识目录的生成快照与字段映射归内容模块；装配根向学习repository注入读取函数，学习模块不直接读取内容模块内部文件。`src/types`与`src/shared/mappers`承载现有共享展示合同和映射，跨模块装配测试归`src/test/integration`；共享实现不反向依赖功能内部实现。

公开接口返回领域/展示模型，不暴露DTO、Zod实现或StorageGateway。边界映射显式处理snake_case、可空字段、状态与版本；不以默认值掩盖缺少字段或非法枚举。`src/services`和业务`src/data`运行目录已移除，不恢复旧facade；`src/data/contracts`只保留生成契约。

页面导航使用platform入口：主入口`goPrimary`对应reLaunch，详情`goDetail`对应navigateTo，替换详情`replaceDetail`对应redirectTo。详情保留原生返回、来源section/筛选与适用的无栈回退；旧路径只规范化到现行路由，不渲染重复页面。导航键和兼容映射以源码为准，不从历史计划恢复旧标签。

## 后端模块与事务

后端模块组织为`api/application/domain/infrastructure`、`public.py`和`wiring.py`。api适配HTTP schema/Actor、调用用例、映射view；application编排业务与事务；domain保持纯策略；infrastructure实现ORM、repository、query及外部adapter。

跨模块通过稳定`public.py`合同或注入port；只允许api/wiring在显式组合处依赖其他api，application/domain/infrastructure不得这样导入。核心业务不依赖FastAPI、SQLAlchemy、HTTP客户端或旧services。bootstrap显式装配，不引入service locator。`backend/app/bootstrap/model_registry.py`注册canonical ORM；旧api/models/schemas/services仅兼容入口，不新增业务。

repository只flush，用例拥有commit/rollback与请求级UoW；不可变Actor经HTTP认证后仍在用例校验角色、owner、成员和数据范围。AppError映射稳定code及401/403/404/409/422/5xx状态，不把无权限或服务失败映成空列表。

AI审核记录与对应训练、非紧急问答、计划和通知写入同一事务；审核或commit失败应回滚并明确失败，不提交半份业务结果。紧急医学安全分流不调用AI。训练完成后的跨模块学习副作用由bootstrap连接，按来源幂等；学习生成失败不倒回已经完成的训练，也不递归触发。

学习路线完成shell与固定PBL分析同事务写入。HTTP响应后后台调度仅传不可变locator，使用独立Session；先提交有时限claim，再进行外部调用，响应以token/版本/期限CAS写回。已发布内容不可重新生成，迟到响应不能覆盖。最终答卷、结果和证据事件同事务提交；证据失败整笔回滚。

## API/Demo与会话

`VITE_APP_MODE=demo|api`在启动时选定。API失败显式报错，禁止自动fallback、混写两套数据或迁移Demo数据进API。

API业务数据不持久化到客户端离线仓库。Demo与本地会话按用户和schema版本隔离；合法旧数据先成功写入新版本再删除旧项，损坏数据保留原值并明确失败，不静默覆写。现行版本与迁移能力查store实现。

仅GET缓存：普通列表/详情30秒、线程15秒、分析最长60秒，最多128项；相同用户、method、path和query并发去重，各消费者仍执行schema校验。写入按相关前缀失效；token变化、401和登出清空缓存并增加会话revision。旧请求不得回写新会话、重新填充缓存或覆盖新版列表。

分页默认20、最大100，以updated_at降序/id降序稳定排序；摘要预览160字符。追加按ID去重，错误重试保留已有列表并校验请求版本。offset不是数据库快照，写入期间可能移动记录，不承诺稳定快照游标。

## 运行时与生成契约

服务端错误使用`{detail:{code,message,reason?}}`；受控reason用于状态冲突，旧流程写入为RETIRED_FLOW；前端兼容历史字符串detail，新接口维持统一合同。缺失字段用undefined，确实可空的历史写入用null；非法值不能被mapper默默兜底。

OpenAPI、生成类型、DTO mapper及运行时schema一起更新。`docs/openapi.json`与`src/data/contracts/openapi.generated.ts`经`npm run contract:generate`生成，禁止手改；`contract:check`在临时目录重生成比较，不改源码。

`src/main.ts`首先导入`src/platform/contracts/validationRuntime.ts`，让微信jitless运行时关闭Zod动态代码编译，仍完整执行schema校验。同步异常先检查引入和编译产物顺序，不跳过校验。

列表提供必要摘要，详情按需读取；避免用逐条详情请求补列表字段形成N+1。跨模块查询经最小只读port，不共享ORM内部对象。

教师PBL、学情、内容保留原根地址，三个薄入口挂载TeacherWorkspaceDeck；容器按PBL/总览/知识/学生/内容组织真实正文，当前与邻项提前初始化并保留已访问实例。横向切换提交当前索引，不调用reLaunch；底栏是Deck自身原生节点，tap从currentTarget.dataset读取工作区并立即激活目标；正文索引与底栏选中/图标在同一渲染层更新，不经外层Frame插槽/props；页签点击复用激活逻辑，取消原动画提交；详情路径/返回参数不变。正文经teacherScreenContext接收初始合法查询、当前项状态及页面show刷新，等待实例原生$nextTick后读取组件ref；只有当前项在详情返回后刷新。身份变化按generation重建正文并拒绝旧ready回调。各工作区独立拥有筛选与请求状态，三学情正文共享范围且仅当前项保存面板偏好，经各自 feature public 访问业务；待办只消费 Learning 待审队列和 Content 最小资源动作摘要。旧教师统计与课堂进度地址仅解析合法上下文并重定向学情，不保留第二套聚合适配。轻量班级、面板、课堂、日期及资源筛选按用户/工作区分别保存，不存业务正文。新的队列、资源摘要与学情投影不启用 GET 缓存，旧请求不得覆盖新筛选或身份。

教师学情经 PBL public read port 读取授权原课堂的最小研讨事实，按参与开始时间统计阶段，不读取消息正文、自主研讨或私人续问；研讨参与与路线发布批次分别聚合。Demo 在 bootstrap 接入同等读取，新增参与持久化不可变开始时间，旧记录缺少时间则保持只读且不补造。内容资源按钮消费服务端实时 `allowed_actions` 投影，缺失投影按无动作处理，写入接口仍独立校验授权与状态。

教师 Insights 由 Analytics 组合课堂范围、Learning 最小路线/完成结果及 PBL 有效完成诊断 port。发布批次进度、完成测试结果、完成诊断分别使用北京时间日期窗口；自主路线、私人续问和修订不匹配的完成诊断不进入教师投影。最终测试详情的 `current_scope_active` 由 Learning 每次读取计算，不持久化，历史可读与当前写入授权分开；写接口仍校验班级/成员活动范围。

## 证据与统计

`learning_evidence_events` / `learning_evidence_metrics`为append-only：同dedupe_key同payload幂等，异payload冲突；仅记录必要指标与来源，不记录完整回答或prompt。证据可见范围见[产品](product.md#研讨回应与证据)与[安全](security.md#服务端授权)。缺失成绩为null，不能补0。课堂最终测试仅写knowledge指标，两种新来源classroom_final_test/private_final_test按冻结结果验证，不写六维过程分数；教师统计不读取自主来源。活动时长只按明确、受限的时间区间估计，不用AI猜测。

知识库经`KnowledgeCatalogPort`读取数据库唯一active catalog；缺失、多active、悬空、无来源或循环关系显式失败，不回退静态数据。节点/边及来源见[知识库](knowledge-base/README.md)。

学生学情是 Learning 所属的本人只读投影，通过 PBL public read port 读取参与与校验后的完成诊断，通过 Learning 自有仓储读取路线、阅读与完成结果，不恢复退役报告接口、不共享跨模块 ORM。接口不接收客户端 student_id，不返回回答、消息正文、隐藏病例或评分参考答案。无需新增存储；Demo 从当前持久化流程实时聚合，API/Demo 在 bootstrap 装配，页面经 Learning public 读取。学情不启用 GET 缓存，以便返回时体现最新步骤和判分结果。

## T63 内容与复习退役边界

Content 活动资源仅为 guided_case 和个人题库，旧问题/教师卡读写为受角色校验的退役兼容接口；QA 的旧学生问题/问题线程关闭，通用会话助手保留。Learning 的 knowledge-map 和 Study/Routes 保持现行目录与路线合同，独立复习 HTTP 写入拒绝、队列为空。保留内部知识状态计算与历史模型，不做表或历史证据删除；Demo 仓储同步活动读取、写入拒绝和身份顺序，页面继续经 feature public，装配仍在 bootstrap/wiring。旧地址壳只导航，不再调用退役业务。

## T64 资源删除与历史快照

Content教师病例保存校验完整definition/rubric后即教学可用，allowed_actions仅本人edit/delete；活动列表/详情和新课堂选用排除逻辑删除。已有PBL课堂opening与版本/digest快照保持，独立病例训练新增内部problem_snapshot JSON，创建attempt时冻结，旧attempt在资源首次编辑/删除前经Training公有port补快照，后续训练用自身快照，不泄露隐藏定义。Content跨模块冻结由bootstrap装配，Demo通过对应公有helper/回调在wiring装配，不能从内容仓储直接读取训练内部存储。个人题库沿用archived内部存储标记删除，API/Demo活动读取均隐藏；不提供恢复、不回写原测试，版本及请求幂等校验保留。旧专家审核记录保留但不再阻挡教师个人资源保存。
