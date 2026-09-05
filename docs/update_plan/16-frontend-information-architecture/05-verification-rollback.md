# 验证与回退

## 计划门禁

- T16 范围 Prettier 检查；
- Markdown 相对链接和文件存在性检查；
- 尾随空白检查；
- `git diff --check`；
- `python .agents/skills/wx-engineering-standards/scripts/self_check.py`。

## 自动化验证

- 组件/页面：四项导航、active/aria-current、资源分组、标题去重和键盘操作。
- 导航：一级 `reLaunch`、二级 `navigateTo`、连续流程 `redirectTo`、返回兜底和重复点击去重。
- 教师：四 workspace、深链接兼容、切换状态保留和权限入口。
- 前端门禁：边界 self-test/full、Prettier、Lint、类型、单测、H5 与微信构建。
- E2E：学生完整跳转链、教师 workspace、320/768/1024/1440 无溢出与首屏可用性、API/Demo 路径。
- 安全：工作树秘密扫描和 `git diff --check`。

不执行契约生成、数据库迁移和后端完整测试，因为本任务不修改 Pydantic 路由、OpenAPI、模型、数据库、权限或服务端业务；该决定及风险写入交付记录。

## 视觉验收

- 对学生学习页、训练资源页、PBL、学情、答疑和教师工作台进行 H5 截图检查。
- 只在确认新布局正确后更新受影响的基准图；不得用提高阈值或隐藏元素使视觉测试通过。
- 微信构建通过不等于真机验收，真机安全区、字体和返回行为保留为外部验收。

## 回退

- 回退 T16 的导航组件、页面模板/样式、路由类型和文档即可；不涉及数据恢复、迁移或服务端回退。
- 页面路径与教师查询 key 未删除，回退不会要求转换历史链接或本地数据。
- 不清理或改动任务开始前已有的 `output/`。
