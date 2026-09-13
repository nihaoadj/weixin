# 依赖升级基线

## 目标

本次升级覆盖 uni-app/Vue 工具链、前端运行时与测试依赖、FastAPI 后端依赖以及 CI 供应链检查。发布门槛为 npm 生产树和完整树均无 high/critical 漏洞，Python 锁定依赖通过 `pip-audit`。

## 基线与结果

以下表格是历史升级证据，不代表实时审计。T01–T25 的阶段背景见 [概述](../update_plan/01-25-summary.md)。微信是唯一产品目标；后续工具链验收必须包含 [开发者工具实际渲染](wechat-validation.md)，不能以历史构建替代。

| 范围         |                                    升级前 |                                    升级后 |
| ------------ | ----------------------------------------: | ----------------------------------------: |
| npm 全树     |                       15 high、2 critical |                        0 high、0 critical |
| npm 生产树   |                       12 high、0 critical |                        0 high、0 critical |
| 前端关键版本 | Vite 5.2.8、Vitest 2、TypeScript 4、Zod 3 | Vite 7.3.6、Vitest 3、TypeScript 5、Zod 4 |

## 兼容性决定

- 所有直接 `@dcloudio/*` 包统一采用 `3.0.0-alpha-5020520260824002`，避免跨批次混用。
- DCloud 插件的发布元数据把 Vite peer 固定为 5.2.8；Vite 5 含未修复的 high 漏洞，因此项目采用 Vite 7.3.6，并以 `npm ci --legacy-peer-deps` 安装。
- 历史上曾完成 TypeScript、H5 构建和微信小程序构建。H5 已由 T25 退役；后续任一 DCloud 或 Vite 升级必须重跑适用的 API/Demo 测试和微信小程序构建。
- Python 依赖源文件为 `requirements.in` 与 `requirements-dev.in`；生成的 txt 文件为带哈希的可复现锁文件，禁止手工编辑。
- JWT 实现从 `python-jose` 迁移到 `PyJWT[crypto]`，移除了 `ecdsa` 的无修复漏洞依赖链；令牌算法、过期时间与接口响应保持不变。

## 维护流程

1. 修改 `.in` 或 `package.json` 中的直接依赖。
2. 使用 `pip-compile --generate-hashes --allow-unsafe` 重新生成后端锁文件，并执行干净环境安装。
3. 执行 `npm run audit:prod`、`npm run audit:all` 和 `npm run backend:audit`。
4. 执行 `npm run check:all`；仅在所有质量门槛通过后更新本报告的审计数字。
