# 当前审计

## 已核实事实

- 学生角色默认进入 `src/pages/student/pbl/pbl.vue`，教师默认进入 `src/pages/teacher/index/index.vue` 的 PBL 工作区。
- `StudentNav` 提供课堂、任务、知识、答疑、记录五个主入口，但 PBL 页面直接把导航放在内容末尾；长对话中用户须滚动到底部才能切换主路径。
- 知识、学习和历史页面已有固定底部导航壳与底部留白，样式与 PBL 页面不一致。
- 教师工作区将 tab 切换编码为 `goReplace(ROUTES.teacherWorkspace, { tab })`，每次切换都会替换页面、重新触发生命周期和失去已加载的视图状态。
- PBL 任务组件具备加载、失败、提交和幂等提交标识，但缺少任务总进度和“下一步”视觉重点。
- 前端仅通过 feature public API 读写数据；`src/platform/navigation/index.ts` 统一实现路由去重和失败反馈。

## 影响边界

本轮只编辑 Vue 页面、UI 组件、导航编排和前端测试。API/Demo 仍经既有 wiring 与 public API 获取同一领域对象；无 schema、OpenAPI、数据库或生成物影响。

## 既有改动保护

工作区在本轮开始前已包含 T10/T11 未提交改动和 untracked 文件。仅修改本计划列出的文件，不执行 reset、clean、restore、提交或推送。
