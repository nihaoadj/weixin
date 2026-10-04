# 项目代码与目录组织规范

编制日期：2026-10-04。状态：后续结构重构的参考基线，尚未实施目录迁移。

## 1. 适用范围与依据

本文规范 Git 仓库中的源码、模块、测试、配置、资源、生成文件和运行产物的组织方式，适用于 Vue 3 / TypeScript / uni-app 前端与 Python / FastAPI 后端。本文不讨论操作系统文件系统布局。

依据优先级为：语言和工具的官方约束、多个来源相互印证的工程原则、广泛关注的开源实践。项目已有规范只用于了解现状，不用于证明推荐方案正确。目录示例和迁移步骤是本文综合建议，不是任何组织发布的统一标准。

### 1.1 规则等级

| 标记     | 含义                                       | 后续重构时如何使用                       |
| -------- | ------------------------------------------ | ---------------------------------------- |
| **约束** | 所选语言、框架或工具的实际要求             | 保持兼容；改动相关配置后重新验证         |
| **原则** | 多个来源支持的工程方向，不统一规定目录名称 | 作为评估结构的主要标准                   |
| **建议** | 本文为此类项目选出的默认方案               | 可采用等效布局；替代方案应说明职责与依赖 |
| **可选** | 只在特定规模、复杂度或部署方式下有价值     | 满足条件后再引入                         |

“原则”表示所引用来源相互支持，不表示经过行业投票或成为正式标准。本文采用后，团队可以将部分建议纳入自动检查；不能因此把它们解释成行业强制要求。

### 1.2 GitHub 实践来源及关注度

下表星数于 2026-10-04 查询 GitHub REST API 的 `stargazers_count` 得到，是当日辅助记录。五个仓库当时均未归档。API 链接会返回实时数据，当日响应字段另保存在[来源记录](references/code-organization-sources-20261004.json)。星数只辅助筛选，不证明某条建议形成行业共识。

| 仓库                                                                                            |                                                                 Stars 快照 | 本文参考内容                          | 适用限制                                 |
| ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------: | ------------------------------------- | ---------------------------------------- |
| [google/styleguide](https://github.com/google/styleguide)                                       |                   [39,646](https://api.github.com/repos/google/styleguide) | 风格一致、名称明确、语言规则          | Google 自身约定，不是通用目录标准        |
| [alan2207/bulletproof-react](https://github.com/alan2207/bulletproof-react)                     |          [35,939](https://api.github.com/repos/alan2207/bulletproof-react) | 按功能聚合、局部归属、依赖方向        | React 实践；本文只借鉴组织原则           |
| [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)     |  [18,138](https://api.github.com/repos/zhanymkanov/fastapi-best-practices) | 多业务 FastAPI 应用按领域组织         | 作者团队的经验，不是 FastAPI 官方标准    |
| [github/gitignore](https://github.com/github/gitignore)                                         |                   [176,016](https://api.github.com/repos/github/gitignore) | Python、Node 等环境的忽略模板         | 模板须按实际产物调整                     |
| [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) | [4,603](https://api.github.com/repos/audreyfeldroy/cookiecutter-pypackage) | Python 包的源码、测试、文档与配置分离 | 面向可分发的 Python 包，不直接套用到服务 |

## 2. 结构设计原则

**原则：先表达业务归属，再按需要区分技术职责。** 中大型业务应用优先让同一功能的代码靠近；避免一个业务变化必须同时穿过全局 `components/`、`services/`、`models/`、`utils/`。功能内部仍可按 UI、API、规则等职责分组。小型应用可以采用较平的目录。这个方向得到 [Angular 官方组织建议](https://angular.dev/style-guide#organize-your-project-by-feature-areas)、[Bulletproof React 的功能组织实践](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)和 [FastAPI Best Practices 的多领域经验](https://github.com/zhanymkanov/fastapi-best-practices#project-structure)支持；Angular 和 React 的框架细节不移植到 uni-app。

**建议：一个文件围绕一个明确概念，一个目录围绕一类连贯职责。** 密切关联的小函数、类型可以同文件；出现两个独立变化原因时再拆分。文件行数、目录深度和文件数量可以作为观察指标，不采用“超过固定行数必拆”之类缺少适用依据的硬限制。[Angular 官方的一概念一文件建议](https://angular.dev/style-guide#one-concept-per-file)允许相关的小概念共存。

**建议：每份业务实现有明确的维护归属。** 模块负责自己的规则、内部模型和数据访问；共享目录承载可以脱离具体业务使用的能力。两处代码相似不立即证明应该抽象成共享模块，先确认含义和变化方向相同。

**建议：目录层级应服务于真实职责。** 没有代码或独立职责时不创建占位层；简单业务不必复制复杂业务的分层。热门实践也明确要求按需创建子目录。[Bulletproof React](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)

## 3. 仓库根目录

### 3.1 推荐基线

**建议：前端源码与后端源码有清楚的根边界，其余文件按用途归类。** 对一个前端、一个后端的仓库，以下布局足以表达职责。目录名属于建议，工具识别的入口文件除外。

```text
project/
├─ src/                  # uni-app 前端源码根
├─ backend/
│  ├─ app/               # Python 应用包，或选择 src/<package>/
│  ├─ tests/
│  ├─ alembic/
│  ├─ scripts/           # 后端专用维护脚本
│  └─ pyproject.toml
├─ contracts/            # 可选：独立维护的接口契约或契约快照
├─ docs/                 # 人可读的说明与决策
├─ scripts/              # 仓库级构建、生成、检查脚本
├─ config/               # 工具允许迁移且确需分组的配置
├─ e2e/                  # 跨页面或跨系统端到端测试
├─ artifacts/            # 本地产物；默认不纳入 Git
├─ .github/workflows/    # 使用 GitHub Actions 时的 CI 配置
├─ package.json
├─ package-lock.json
└─ README.md
```

`artifacts/` 是本文选定的产物目录示例，现有 `output/` 也可承担同等职责。不要仅为替换名称移动整个目录。`contracts/` 只在需要独立契约职责时创建；契约和类型生成工具支持的路径决定实际位置。

**可选：多个独立应用或共享包出现后，采用 `apps/` 与 `packages/`。** 引入的理由应是独立构建、部署或复用需求，而不是目录看起来更标准。一个小程序加一个后端不自动需要 workspace 工具或独立包发布。

### 3.2 根目录与脚本职责

**建议：根目录保留项目入口、工具要求的位置和少量总说明。** 产品截图、下载资料、实验文件、数据库和日志进入明确分类的目录。工具原生配置可以留在它要求或默认搜索的位置，不强制全部迁入 `config/`。

根 `scripts/` 承担前后端协调、构建和检查；`backend/scripts/` 承担后端专用运维。业务运行时不能反向依赖维护脚本。脚本输出位置、调用工作目录和入口命令应明确，不把个人机器绝对路径写进仓库。

## 4. 前端组织

### 4.1 框架入口与业务目录

**约束：保持 uni-app 源码根、页面注册和资源复制机制一致。** `App.vue`、页面配置 `pages.json`、应用配置 `manifest.json`、入口文件和 `static/` 按所用 CLI / TypeScript 模板配置放置。官方展示的是工程源码结构；CLI 项目的源码根可位于仓库 `src/`，不能把官方示例里的“根”机械理解为 Git 仓库根。[uni-app 工程目录说明](https://uniapp.dcloud.net.cn/tutorial/project)

**建议：路由页面保持在框架约定位置，业务实现以功能聚合。** 推荐示意如下，子目录按需创建：

```text
src/
├─ App.vue
├─ main.ts
├─ pages.json
├─ manifest.json
├─ pages/
│  └─ classroom/detail/detail.vue  # 路由参数、生命周期、页面组合
├─ features/
│  └─ classroom/
│     ├─ components/ClassroomDetail.vue
│     ├─ composables/useClassroomDetail.ts
│     ├─ api/classroom-api.ts
│     ├─ model/classroom.ts
│     └─ model/classroom.spec.ts
├─ shared/
│  ├─ ui/                          # 无业务归属的通用 UI
│  └─ lib/                         # 无业务归属的纯函数
├─ platform/                       # HTTP、存储、微信运行环境适配
├─ app/                            # 初始化、全局配置与功能组合
├─ generated/                      # 工具生成代码；可按用途细分
├─ styles/                         # 可编译的全局样式
└─ static/                         # 按 uni-app 规则复制的资源
```

`app/` 可采用 `bootstrap/` 等名称；`shared/ui/` 可采用职责明确的全局 `components/`。规范关注的是归属与依赖，不要求为同等职责换名。上述目录树是本文的 Vue/uni-app 适配建议，并非直接复制 React 模板。

**建议：跨功能的页面工作区、导航壳和组合组件属于应用展示区域，不能为消除全局目录而塞进一个业务模块。** `components/` 可以明确区分通用 UI 与应用组合；只有单一功能拥有的实现才迁入该功能。跨模块公共类型可以集中维护，但须说明所属合同，保持纯类型并避免循环依赖。

### 4.2 文件归属规则

| 内容                                     | 建议位置                   | 判断方法                         |
| ---------------------------------------- | -------------------------- | -------------------------------- |
| 路由地址、页面参数、页面生命周期         | `pages/`                   | 与小程序页面注册直接关联         |
| 只服务一个功能的组件、状态、类型与工具   | 对应 `features/<feature>/` | 离开该功能后没有独立用途         |
| 通用按钮、布局、日期格式化等             | 一个统一的共享区域         | 不认识具体业务，也不依赖业务模块 |
| HTTP 基础客户端、存储驱动、微信 API 包装 | `platform/` 或等效技术区域 | 提供基础能力；不承担特定业务决策 |
| 某功能的 API 调用和响应映射              | 对应功能内部               | 字段和语义归该功能所有           |
| 全局初始化、模式选择、模块组合           | `app/` 或等效装配区域      | 负责连接不同功能与基础设施       |

**建议：页面或组件可以直接调用所属功能的接口，不强制每次操作经过多层转发。** 当业务编排、规则或适配变复杂时，再抽出用例或领域模块。服务端权限判断不能因前端拆出“领域层”而转移到客户端。

**建议：功能内部的 Vue 状态逻辑采用 composable，纯计算保留普通函数。** Vue 官方将 composable 用于封装和复用有状态逻辑；无需把所有工具函数改成 `useXxx`。[Vue Composables](https://vuejs.org/guide/reusability/composables.html)

### 4.3 依赖与导出

**建议：共享基础能力不依赖业务；功能不依赖页面与应用装配；页面和装配组合功能。** 跨功能协作需要明确允许的合同及方向，禁止循环引用和无约定地穿透内部实现。是否完全禁止跨功能导入是架构选择，本文不将某一种隔离策略设为行业通则。

**可选：为需要稳定边界的模块设置明确的公开接口。** 可以是小型 `public.ts`、专门的 API 文件或被约定为公开的直接导入路径。公开接口与“把整个目录全部重新导出”是不同问题。

不要为了统一入口在每一级目录建立 `index.ts` 并 `export *` 所有文件。Bulletproof React 当前建议直接导入，提出大型集中导出文件可能影响 Vite 的构建优化；本文据此建议按需导出、避免初始化副作用，并以实际构建结果判断影响。它并不能证明所有 `public.ts` 都有问题。[原文的导出与依赖建议](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md)

## 5. 后端组织

### 5.1 Python 包布局

**约束：目录与 Python 的导入、安装和启动方式必须配套。** 常见两种布局都可以成立：

| 布局                 | 典型路径                            | 适用情况及代价                                                   |
| -------------------- | ----------------------------------- | ---------------------------------------------------------------- |
| 应用包直接位于服务根 | `backend/app/main.py`               | 部署服务较直观；必须确认启动与测试采用一致导入路径               |
| `src` 布局           | `backend/src/pathology_app/main.py` | 需要按包安装、测试发布包或隔离仓库根文件的项目；要配置安装及启动 |

PyPA 说明 `src` 布局可避免意外导入工作目录中的源码，但通常增加安装步骤；FastAPI 官方大型应用示例使用 `app/main.py`。因此，“所有 Python 项目必须迁入 src”不成立。[PyPA 布局取舍](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)、[FastAPI 官方多文件应用](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

本文建议先保留能够可靠启动与测试的应用包布局；只有安装、导入或分发问题提供明确收益时才迁移。普通 Python 包可使用 `__init__.py`；namespace package 是另一种有效机制，不把每个目录都强制变成包。

### 5.2 业务模块与层数

**建议：多个业务领域的后端按业务模块聚合。** 简单模块可以在模块内直接放置 `router.py`、`schemas.py`、`service.py` 和 `models.py` 等文件。模块名表示业务能力，具体文件名和是否需要每一种职责由代码决定。[FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices#project-structure)

**建议：使用 `APIRouter` 按业务组织 HTTP 路由，在应用入口组合。** 官方提供 `APIRouter` 与多文件组合方式，没有要求固定的四层架构、`modules/` 或 `public.py` 文件名。[FastAPI 官方说明](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

**可选：复杂模块再采用显式分层。** 当业务规则需要脱离 HTTP / ORM 独立验证，或外部实现需要替换时，可以采用以下职责。目录树仅说明边界，不是所有模块的迁移目标：

```text
backend/app/
├─ main.py
├─ modules/
│  └─ classroom/
│     ├─ api/               # HTTP 路由、请求与响应转换
│     ├─ application/       # 用例编排、事务协作
│     ├─ domain/            # 业务规则与模型
│     └─ infrastructure/    # 数据库与外部服务实现
├─ platform/                # 技术基础能力
└─ bootstrap/               # 创建应用与装配依赖
```

采用这一方案时，领域规则应不依赖 FastAPI、SQLAlchemy 或具体 HTTP 客户端；应用层通过抽象协作，基础设施实现这些抽象。Microsoft 的 DDD 分层材料支持这一依赖隔离原则，但原文面向 .NET 微服务；这里只借鉴职责，不能据此要求拆成微服务。[Microsoft DDD 分层说明](https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice)

**建议：允许简单与复杂模块具有不同层数，但统一边界含义。** 不为了目录整齐给简单 CRUD 增加多层只转发调用的文件；也不在同一业务内长期维护两套完整实现。兼容入口若确需保留，应明确调用者、迁移目标与删除条件。

## 6. 命名、路径与文本格式

### 6.1 命名建议

**建议：名称描述实际内容，路径大小写精确一致。** TypeScript 提供 `forceConsistentCasingInFileNames` 检查大小写不一致，尤其适合同时在 Windows 与 Linux 工作的仓库。[TypeScript 官方配置](https://www.typescriptlang.org/tsconfig/forceConsistentCasingInFileNames.html)

| 对象                 | 本文默认建议                   | 例子                                | 性质                    |
| -------------------- | ------------------------------ | ----------------------------------- | ----------------------- |
| 前端普通目录         | 小写，多个词用 `-`             | `question-bank/`                    | 团队风格选择            |
| 普通 TypeScript 文件 | `kebab-case.ts`                | `classroom-api.ts`                  | 团队风格选择            |
| Vue SFC 组件         | `PascalCase.vue`，与组件名匹配 | `ClassroomCard.vue`                 | 本文建议                |
| uni-app 路由文件     | 与注册路径及项目页面约定一致   | `pages/classroom/detail/detail.vue` | 框架配置优先            |
| Vue composable       | 与导出的 `useXxx` 对应         | `useClassroomDetail.ts`             | Vue 使用惯例的适配建议  |
| Python 模块          | 小写，按需用下划线             | `classroom_service.py`              | PEP 8 建议              |
| Python 包            | 简短、小写，尽量避免下划线     | `classroom/`                        | PEP 8 建议              |
| 前端单元测试         | 与被测文件同名，加 `.spec.ts`  | `classroom.spec.ts`                 | 本文默认；测试配置配套  |
| 后端测试             | `test_*.py`                    | `test_classroom.py`                 | pytest 默认发现规则之一 |
| 文档与普通资源       | 名称描述主题或用途             | `code-organization-standard.md`     | 团队风格选择            |

Python 命名依据 [PEP 8](https://peps.python.org/pep-0008/#package-and-module-names)；测试发现依据 [pytest](https://docs.pytest.org/en/stable/explanation/goodpractices.html#conventions-for-python-test-discovery)。Vue 官方推荐 SFC 中使用 PascalCase 组件名，本文进一步让组件文件名与其一致；文件名方案不是 Vue 运行硬约束。[Vue 组件命名](https://vuejs.org/guide/components/registration.html#component-name-casing)

**建议：采用一种明确风格，但不要将大小写方案当作重构的首要目标。** Google TypeScript Guide 使用 `snake_case` 文件名，Angular 使用连字符，足以说明不存在跨 TypeScript 项目的唯一命名共识。本文选用 kebab-case 是默认决策；已有统一 camelCase 或 snake_case 可保留，混用应有具体原因。[Google TypeScript Guide](https://google.github.io/styleguide/tsguide.html)、[Angular 文件命名](https://angular.dev/style-guide#separate-words-in-file-names-with-hyphens)

**建议：避免含义不明的 `common.ts`、`helpers.ts`、`manager.py`、`misc/`。** `utils/`、`types/` 并非绝对禁止，但范围应清楚；业务专属类型与工具留在业务模块。`new`、`old`、`final2` 和阶段编号不用于永久运行代码的身份，版本历史交给 Git。

### 6.2 文本与跨平台

**建议：普通源码采用 UTF-8、LF 和文件末尾换行，并由工具维护。** Python 缩进遵循 Python 工具规则，前端缩进遵循 formatter；无需手工复制两套格式要求。[EditorConfig](https://editorconfig.org/)可以声明这些属性。

`.editorconfig` 负责编辑器一致性，formatter 负责排版，`.gitattributes` 负责 Git 的文本与二进制、换行处理。特定 Windows 脚本确需 CRLF 时单独声明；二进制不要做文本换行转换。[Git gitattributes](https://git-scm.com/docs/gitattributes)

**建议：代码与构建路径使用便于跨平台的字符，并精确匹配引用。** 新增路径优先 ASCII，避免空格、Windows 保留名称和仅大小写不同的同级文件。中文文档或设计材料不是自动违规；先验证工具支持，再决定是否迁移。

## 7. 测试、接口契约与生成物

### 7.1 测试归属

**建议：前端单元测试靠近被测源码，后端集中测试目录按业务或职责分组，端到端测试独立。** 这是适合本技术组合的默认方案，不是所有语言必须同一种测试布局；pytest 同时支持包外与包内测试。[Angular 的邻近测试建议](https://angular.dev/style-guide#group-closely-related-files-together-in-the-same-directory)、[pytest 的布局说明](https://docs.pytest.org/en/stable/explanation/goodpractices.html#choosing-a-test-layout)

```text
src/features/classroom/model/classroom.spec.ts
backend/tests/classroom/test_membership.py
backend/tests/integration/test_classroom_api.py
e2e/classroom-flow.spec.ts
```

目录同时按业务和测试类型划分时，需要选定一个主要维度，并在测试配置中声明发现范围。`fixtures/` 保存确定、必要且可维护的测试输入；截图、覆盖率、执行日志与临时数据库属于测试输出。

**建议：可运行 Demo 的实现与测试替身区分。** Demo 若属于应用运行模式，其实现归对应功能适配器或运行配置，不能为了整理目录搬入仅供测试导入的区域；测试 fixture 不被生产代码反向引用。

### 7.2 生成文件管理

**建议：每一类生成文件都声明输入来源、生成命令、输出路径、是否跟踪，以及如何检查漂移。** 文件名后缀如 `.generated.ts` 或目录如 `generated/` 都可使用，关键是能识别和重现。工具支持时加入“由工具生成”的文件头。

| 文件类别                                   | Git 默认策略                                   | 维护方式                             |
| ------------------------------------------ | ---------------------------------------------- | ------------------------------------ |
| OpenAPI 快照、生成的 SDK / TypeScript 类型 | 按消费方式决定；需要评审或构建直接消费时可跟踪 | 修改来源与生成器，重新生成，检查差异 |
| npm 的 `package-lock.json`                 | 跟踪                                           | 使用包管理器更新并评审依赖变化       |
| 已使用的数据库迁移                         | 跟踪                                           | 保持版本关系；按迁移流程增量演进     |
| 构建输出、缓存、覆盖率、临时导出           | 忽略                                           | 由工具重建                           |

npm 明确建议提交 `package-lock.json`，因此“所有自动生成文件都不入库”不成立。[npm 官方说明](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/)

Alembic 的迁移文件是数据库演进代码；执行顺序依据 revision 关系，不能凭文件名排序重写版本链。生成迁移脚本仍需要开发者维护与审核，不把它们当作可随意删除的编译产物。[Alembic 官方教程](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

**建议：机器契约与人读文档在职责上分开。** 可以把 OpenAPI 快照放到 `contracts/`，也可以保留工具已经支持的路径；迁移目录时同步生成器、消费者、CI 和文档链接。集中存放不是优先于可靠生成的目标。

## 8. 配置、资源与运行产物

### 8.1 配置与秘密

**原则：可变部署配置与代码分离，秘密不进入源码和普通配置。** 提交必要的非秘密配置、变量说明与 `.env.example`，实际值通过部署环境或秘密管理机制提供。前端包可被用户读取，不能承载服务端秘密。[Twelve-Factor 配置原则](https://12factor.net/config)、[OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

**建议：同一配置值有明确来源与覆盖顺序。** 区分仓库工具配置、后端运行配置、前端可公开运行配置；模块配置靠近模块，跨模块配置在统一入口读取。不要在多个目录维持同名、同用途且各自生效的副本。

### 8.2 静态资源与设计材料

**约束：uni-app 的 `static/` 资源遵循其复制机制。** 未使用的普通静态文件也可能进入最终包；可编译的 JS / Vue / CSS / SCSS 放在源码区域。平台专用资源按框架支持的子目录组织，引用迁移后需要验证实际小程序包。[uni-app static 说明](https://uniapp.dcloud.net.cn/tutorial/project#static目录)

**建议：运行资源按业务或通用用途分组，设计参考图单独存放。** 例如 `static/classroom/`、`static/icons/` 与 `docs/design/`。不把设计稿、取证截图、原始大图放进运行静态目录；资源来源和授权信息在需要时记录。动态字符串引用的资源不能只靠静态 import 搜索判断是否无用。

### 8.3 忽略与保留

**约束：`.gitignore` 不会取消已经跟踪的文件。** 新增忽略规则不能自动清理 Git 历史或 index；后续处理已跟踪产物时，要单独评估保留价值与使用者。[Git gitignore](https://git-scm.com/docs/gitignore)

**建议：依赖、虚拟环境、缓存、构建和临时执行输出默认不入库。** 基于 [github/gitignore](https://github.com/github/gitignore) 的 Node/Python 模板调整规则，但不要照搬后误忽略源码或必要 fixture。

| 内容                                                | 默认处理                               |
| --------------------------------------------------- | -------------------------------------- |
| `node_modules/`、`.venv/`、`__pycache__/`、工具缓存 | 忽略，可重建                           |
| `dist/`、`build/`、`coverage/`、测试报告            | 忽略，CI 可作为 artifact 保存          |
| 本地数据库、上传内容、运行日志、实际 `.env`         | 与源码隔离，不进入普通源码提交         |
| 可脱敏、可复现的小型测试输入                        | 按用途纳入测试 fixture                 |
| 必要验收结论、决策与证据索引                        | 可跟踪的 Markdown 或小型结构化文件     |
| 大量截图、录像、历史报告、归档包                    | 明确保留策略，按需要使用制品或文档存储 |

`artifacts/`、`output/`、`tmp/` 等名称不决定内容是否可以删除。整理前应分类：可重建产物、必要证据、原始输入、敏感运行数据。必要证据可保留索引、摘要和外部存储定位，不以 Git 历史代替所有运行数据的保管。

## 9. 文档与规则维护

**建议：入口短、主题清楚、决策可追溯。** 根 README 说明项目用途、基本启动与文档入口；模块说明只记录难以从目录与接口直接推断的边界。会影响长期结构的选择可以记录在 ADR 或架构文档中。

规则与事实分开：规范描述期望；源码和可执行配置证明实现；计划描述实施顺序；验收记录说明验证结果。历史计划与历史说明不能被当成当前已经生效的结构。

**建议：同一条规则维护一个权威版本。** 文档之间通过链接引用；不在根 README、模块 README、Agent 指令和技能文件中复制完整目录规则。文档应明确哪些布局已实施、哪些还只是目标。

## 10. 不应当作通用标准的做法

| 做法                                               | 评估结论                                             |
| -------------------------------------------------- | ---------------------------------------------------- |
| 每个功能都必须有 domain/application/infrastructure | 可选架构；须有复杂度或依赖隔离收益                   |
| 所有访问只能经过 `public.ts` / `public.py`         | 公开边界有价值；这些文件名和唯一入口策略属于项目选择 |
| 所有前后端都必须迁入 `apps/`                       | 多应用工作区的一种布局，不是全栈仓库必需条件         |
| 所有 Python 服务必须改成可发布的 `src` 包          | 要看导入、安装、测试和分发需要                       |
| 所有生成文件都加入 `.gitignore`                    | 锁文件、契约快照和迁移等需要单独判断                 |
| 行数、深度或文件数超过统一数字就必须拆             | 缺少跨项目适用依据；主要看职责与依赖                 |
| 禁止一切 `utils/`、`services/`、`types/`           | 名称不决定质量；明确范围并避免混杂即可               |
| 星数最高的模板就是最佳目标目录树                   | 关注度不能替代技术栈、维护成本和需求适配             |

这些结论由前述官方材料与实践之间的差异综合得出。真正需要固定的是归属、兼容性、依赖规则与可重复验证；具体目录词汇和抽象层数可以不同。

## 11. 后续重构的实施与验收

以下是本文建议的迁移方法，不表示本次已经执行项目重构。

### 11.1 实施顺序

1. **建立现状清单。** 记录受跟踪源码、未跟踪工作、生成物、运行目录与工具入口；识别动态资源、字符串路由、Python 导入与脚本引用。仅看目录是否存在不足以判断它是否仍有运行用途。
2. **确定归属和依赖。** 为业务能力列出维护模块、对外接口、允许依赖；先决定结构的意义，再画目标目录。
3. **建立旧路径到新路径映射。** 每一批写明迁移理由、调用者、配置更新、生成器更新、验证与回退方式。无明确收益的换名可以不做。
4. **按独立模块渐进迁移。** 将纯移动与行为变化区分，尽量保持接口和行为稳定。需要兼容壳时写清删除条件，不留下无限期的重复实现。
5. **同步工具与消费路径。** 包括 Vite / TypeScript 别名、ESLint 范围、测试发现、uni-app 页面与资源、Python 启动、Alembic、CI、代码生成及文档链接。
6. **运行与影响相称的检查。** 无效路径、循环依赖和必要测试失败必须解决；需要外部环境的验证单独说明。迁移集成节点再运行必要的构建和跨模块回归。
7. **收尾。** 对照映射查残留引用与重复实现，更新当前结构说明，删除本次可确认无用的临时文件；不按目录名称批量删除既有工作和证据。

### 11.2 出口检查

- 每类文件有清晰位置；业务专属文件没有无理由地散落在共享目录。
- 入口、路由、导入、资源、生成器与 CI 的路径与目标结构一致。
- 约定的模块依赖可检查，迁移未引入循环或越界访问。
- 必要测试和构建通过；仅静态检查不能代替实际构建或运行验证。
- 生成快照与来源一致，锁文件和迁移历史保持可用。
- 检查 Git 路径的大小写冲突及引用的精确大小写；仅大小写重命名使用临时中间名。能使用 Linux CI 时，再验证真实导入与构建；不能执行时说明这项未验证。
- 从约定工作目录和干净安装流程验证启动/测试，避免借用未声明依赖或个人目录。工作区已有未提交修改时，不用清理或覆盖用户工作来制造干净检出；使用隔离副本或远程 CI，并说明验证范围。
- 可重建产物与源码分开；必要原始输入和证据仍能定位。
- 当前文档反映已实现状态，兼容入口有退出条件，未验证项有明确说明。

### 11.3 本项目可复用的检查入口

下列命令已在本项目源码或配置中确认存在，是后续执行候选。本次仅编写文档，没有执行这些运行检查。项目原有边界脚本需先审查其规则是否与新目标一致，不能用旧规则的通过结果证明新规范正确。

| 重构影响             | 现有入口                                                         |
| -------------------- | ---------------------------------------------------------------- |
| 前端路径、类型和引用 | `npm run type-check`、`npm run lint`                             |
| 前端行为与小程序编译 | `npm run test`、`npm run build:mp-weixin`                        |
| 前端模块边界         | `node scripts/frontend-boundaries.mjs`                           |
| 后端模块边界         | `python backend/scripts/check_boundaries.py`                     |
| 后端静态与回归       | `npm run backend:check`                                          |
| 生成契约一致性       | `npm run contract:check`                                         |
| 迁移与数据库测试资源 | `npm run backend:test:migrations`、`npm run backend:test:safety` |

命令来源为根 [package.json](../package.json)、[前端边界脚本](../scripts/frontend-boundaries.mjs)、[后端边界脚本](../backend/scripts/check_boundaries.py)。修改命令入口时同步更新引用；选择必要检查，不默认每批执行全部命令。

## 12. 本项目迁移前需要核对的事项

以下仅是 2026-10-04 的只读观察和核对方向，不是代码审计结论，也不用于反向支持本文原则：

| 已观察到的对象                                                               | 后续核对方向                                                 |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 前端已有 `features/`，同时存在全局 `components/`、`types/`、`shared/` 等区域 | 按实际业务归属判断是否局部化，保留确有通用职责的共享代码     |
| 后端 `modules/` 与旧式顶层目录并存                                           | 查明哪些文件是活动实现、兼容入口或空目录；不凭名称判断冗余   |
| 生成快照分布于 `docs/` 与不同源码区域                                        | 先核对生成器与消费者，再决定是否集中或仅增加标识             |
| `output/` 中存在阶段证据与大量工作区变化                                     | 先建立内容分类和保留策略，不能直接当作可删除缓存             |
| 现有前后端边界配置                                                           | 按独立确定的新架构逐条核对与更新，不把已有规则直接搬进新规范 |

目前的契约生成入口为 [scripts/contract.mjs](../scripts/contract.mjs)，管理四个快照：`docs/openapi.json`、`src/data/contracts/openapi.generated.ts`、`src/test/fixtures/case-draft.json` 与 `src/features/content/infrastructure/pathologyCatalog.generated.json`。四类快照均受 `contract:check` 检查。如调整路径，需成套迁移生成与检查逻辑。

后续可据本文先形成文件归属清单、依赖关系和迁移映射，再选择具体目录树。本文本身不确认当前项目已经符合这些规则，也不构成目录迁移已经完成的证据。

2026-10-04本仓库应用本文的分类、修复与验证见[文件组织审计](code-organization-audit.md)；规范的证据等级独立于本仓库既有结构。
