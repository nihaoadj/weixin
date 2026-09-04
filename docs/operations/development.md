# 开发规范

## 前端

源码目录：

```text
src/pages                 # uni-app 路由页面
src/components            # 共享 UI
src/features/*/public.ts  # 页面唯一业务入口
src/features/*/{application,domain,infrastructure}
src/platform              # HTTP、storage、runtime、导航、契约
src/bootstrap             # API/Demo 唯一装配
src/shared                # 纯 mapper/status
src/types                 # 兼容领域/展示类型
src/data/contracts/openapi.generated.ts # 唯一 OpenAPI 生成类型输出
```

规则：

- 页面只处理 UI、交互和生命周期状态；业务读写从所属 feature 的 `public.ts` 进入。
- API 请求只放在 `src/platform/http` 的 adapter 路径；页面和 domain/application 不得直接调用 `uni.request`。
- 类型放在 `src/types/`。
- 纯函数放在 `src/utils/`。
- 不要在页面里直接散落 `uni.request` 和 storage key。
- 本地 Demo 数据写在所属 feature 的 infrastructure store；模式由 `src/bootstrap/wiring.ts` 装配。
- 页面新增业务读写时，依赖 feature public API，不要直接依赖本地仓储或已删除的旧 facade；测试应与被测 feature/platform 实现同目录或直接导入其真实模块。
- 页面不得根据网络错误自行切换本地仓储；运行模式只由 `VITE_APP_MODE` 决定。
- 公共颜色、间距、圆角和阴影使用 `uni.scss`/`App.vue` 设计令牌，不在新页面散落品牌色。

边界检查（当前为直接脚本，尚未接入 `package.json` script）：

```bash
node scripts/frontend-boundaries.mjs --self-test
node scripts/frontend-boundaries.mjs
```

统筹接入时可将两条命令合并为 `frontend:boundaries`，不改变 package/lock/CI 的本任务保护范围。

## 后端

源码目录：

```text
backend/app/modules/<module>/{api,application,domain,infrastructure}
backend/app/modules/<module>/public.py
backend/app/modules/<module>/wiring.py
backend/app/bootstrap
backend/app/platform
backend/app/shared
backend/app/api|models|schemas|services  # 仅历史兼容入口
backend/tests
```

规则：

- `api` 只做 HTTP schema、actor 适配、用例调用和 view 映射；`application` 负责用例与事务编排；`domain` 只放纯策略/状态；`infrastructure` 承担 ORM、repository、query 与外部 adapter。
- 模块间只能经 `public.py` 的稳定合同，或在 `api`/`wiring` 的显式 HTTP/组合处协作。不要让 application/domain/infrastructure 直接导入另一模块的 `api`；R05 的边界检查会拒绝该路径。
- `app/bootstrap/model_registry.py` 是 canonical ORM metadata 注册点；`app/models`、`app/schemas` 与 `app/services` 仅为兼容 re-export/facade，禁止在其中新增生产业务实现。
- 所有需要登录的接口都经 Bearer token，并在用例再次校验角色、owner 与数据范围。

后端边界检查（同样尚无 npm 包装 script）：

```bash
python backend/scripts/check_boundaries.py --self-test
python backend/scripts/check_boundaries.py
```

## 测试

前端：

```bash
npm run test
npm run test:coverage
npm run test:e2e
npm run test:e2e:demo
```

病理学公开目录由后端 content 模块生成，修改目录、卡片或样例病例后同步执行：

```bash
python backend/scripts/export_pathology_catalog.py
npm run contract:generate
npm run contract:check
```

`pathology-general-v3` 是当前唯一运行时教学目录；既有卡片编码作为第一轮兼容资源，`.v2` 卡片和病例蓝图的 reinforcement variant 用于第二轮。开发样例均标记为合成内容，不能当作已完成医学审核的生产素材。

T14 历史转换默认只读预览：

```bash
python backend/scripts/transition_pbl_t14.py --database backend/data/dev.db
```

只有确认目标是受管非生产 SQLite 后才可使用 `--apply --confirm-development --backup <新备份路径>`；脚本遇到缺少审核变式或首轮证据时回滚并报告 plan ID。

T15 评价历史回填同样默认只读预览：

```bash
python backend/scripts/backfill_pbl_evaluations.py --database backend/data/dev.db
```

只有受管非生产 SQLite 可追加 `--apply --confirm-development --backup <新备份路径>`。脚本仅回填可由既有 task/attempt/当前判定快照证明的轮次；历史人工结论标记为 legacy，不伪造逐项目标成绩。

后端：

```bash
npm run backend:test:safety
npm run backend:test:migrations
npm run backend:test
npm run backend:check
```

pytest 的根与 `backend/` 入口会在导入应用前绑定 launcher-owned 的随机临时 SQLite。不得自行新建 engine 或绕过 fixture 对未知数据库执行 `drop_all`/`create_all`。

## 提交前检查

```bash
npm run format:check
node scripts/frontend-boundaries.mjs
python backend/scripts/check_boundaries.py
npm run check
```

`npm run check:all` 还会执行契约、后端、依赖审计和两套 E2E；它不替代远程 CI 或分支保护证据。按改动范围选择命令，纯 Markdown 只需格式、链接、路径/命令和 `git diff --check`。

## Git 忽略

以下文件不进入仓库：

```text
node_modules/
dist/
coverage/
backend/.venv/
backend/data/
project.private.config.json
.env
```

## 微信开发者工具：源码与构建目录同步

| 用途          | 命令                      | 开发者工具导入目录                     |
| ------------- | ------------------------- | -------------------------------------- |
| 持续开发      | `npm run dev:mp-weixin`   | `dist/dev/mp-weixin`                   |
| 生产构建检查  | `npm run build:mp-weixin` | `dist/build/mp-weixin`                 |
| H5 浏览器预览 | `npm run dev:h5`          | 使用终端给出的本地 URL，不导入微信工具 |

2026-08-31 本工作区检查时，微信工具打开的是 `dist/dev/mp-weixin`。只运行生产构建不会更新这个目录。开发时保持 dev 命令运行，等待 `Build complete. Watching for changes...`；确认工具项目路径后再编译。

新增/拆分组件或重新生成目录时，工具可能在编译文件尚未齐全时热重载，短暂出现缺少 app.json、WXML 或旧页面残留。先等待完整构建，再在微信工具执行一次普通编译并等待启动结束；不要手改 dist、复制生产文件覆盖 dev、清空用户数据或关闭安全校验来处理同步问题。

若同步后仍报 `Function.prototype.apply` / Zod `Doc.compile` 错误，检查 `src/main.ts` 最先引入 `platform/contracts/validationRuntime`，以及输出 `app.js` 的引入顺序。该模块禁用 Zod 动态代码编译，不禁用 schema 校验。详见 [数据层规范](../data-layer.md)。

本轮设计与复验入口见 [前端设计](../frontend/design.md) 和 [前端验收记录](../records/frontend/validation-2026-08-31.md)。
