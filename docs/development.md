# 开发规范

## 前端

源码目录：

```text
src/pages
src/components
src/services
src/types
src/utils
```

规则：

- 页面只处理 UI 和交互。
- API 请求放在 `src/services/`。
- 类型放在 `src/types/`。
- 纯函数放在 `src/utils/`。
- 不要在页面里直接散落 `uni.request` 和 storage key。
- 本地 Demo 数据写在 `repository.ts`。
- 远程迁移入口写在 `repositoryAsync.ts`。
- 页面新增业务读写时，优先依赖 `repositoryAsync.ts`，不要直接依赖本地仓储。
- 页面不得根据网络错误自行切换本地仓储；运行模式只由 `VITE_APP_MODE` 决定。
- 公共颜色、间距、圆角和阴影使用 `uni.scss`/`App.vue` 设计令牌，不在新页面散落品牌色。

## 后端

源码目录：

```text
backend/app/api
backend/app/core
backend/app/models
backend/app/schemas
backend/app/services
backend/tests
```

规则：

- 路由只做参数校验和响应组织。
- 业务逻辑放在 service。
- 数据结构放在 schema。
- 数据表放在 model。
- 所有需要登录的接口都走 Bearer token。
- 数据库模型放在 `backend/app/models/`，请求/响应模型放在 `backend/app/schemas/`，不要再新增根级 `models.py` 或 `schemas.py`。

## 测试

前端：

```bash
npm run test
npm run test:coverage
npm run test:e2e
```

后端：

```bash
cd backend
python -m ruff check .
python -m pytest --cov=app --cov-report=term-missing -q
```

## 提交前检查

```bash
npm run check
npm run check:all
```

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
