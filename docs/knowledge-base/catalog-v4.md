# pathology-general-v4 目录与节点

知识点编码跨版本保持稳定，数据库仅在同一目录版本内限制重复编码，因此归档旧版与 active 新版可并存；显示标题、说明、来源、审核状态和边可以通过新迁移演进。每个模块恰有 6 个节点。

| 模块           | 稳定编码                            | 知识点           |
| -------------- | ----------------------------------- | ---------------- |
| 细胞损伤与适应 | `pathology.cell-injury.adaptation`  | 细胞适应         |
| 细胞损伤与适应 | `pathology.cell-injury.reversible`  | 可逆性损伤       |
| 细胞损伤与适应 | `pathology.cell-injury.necrosis`    | 坏死             |
| 细胞损伤与适应 | `pathology.cell-injury.apoptosis`   | 凋亡             |
| 细胞损伤与适应 | `pathology.cell-injury.hypoxia`     | 缺氧性损伤       |
| 细胞损伤与适应 | `pathology.cell-injury.oxidative`   | 氧化应激损伤     |
| 炎症           | `pathology.inflammation.vascular`   | 炎症血管反应     |
| 炎症           | `pathology.inflammation.leukocytes` | 白细胞募集       |
| 炎症           | `pathology.inflammation.mediators`  | 炎症介质         |
| 炎症           | `pathology.inflammation.acute`      | 急性炎症形态     |
| 炎症           | `pathology.inflammation.chronic`    | 慢性炎症         |
| 炎症           | `pathology.inflammation.granuloma`  | 肉芽肿性炎症     |
| 修复           | `pathology.repair.regeneration`     | 组织再生         |
| 修复           | `pathology.repair.granulation`      | 肉芽组织         |
| 修复           | `pathology.repair.matrix`           | 细胞外基质重塑   |
| 修复           | `pathology.repair.wound`            | 创伤愈合         |
| 修复           | `pathology.repair.fibrosis`         | 纤维化           |
| 修复           | `pathology.repair.factors`          | 影响修复的因素   |
| 循环障碍       | `pathology.circulatory.congestion`  | 充血与淤血       |
| 循环障碍       | `pathology.circulatory.edema`       | 水肿             |
| 循环障碍       | `pathology.circulatory.thrombosis`  | 血栓形成         |
| 循环障碍       | `pathology.circulatory.embolism`    | 栓塞             |
| 循环障碍       | `pathology.circulatory.infarction`  | 梗死             |
| 循环障碍       | `pathology.circulatory.shock`       | 休克             |
| 肿瘤           | `pathology.neoplasm.atypia`         | 肿瘤异型性       |
| 肿瘤           | `pathology.neoplasm.behavior`       | 良恶性肿瘤区别   |
| 肿瘤           | `pathology.neoplasm.spread`         | 浸润与转移       |
| 肿瘤           | `pathology.neoplasm.carcinogenesis` | 肿瘤发生机制     |
| 肿瘤           | `pathology.neoplasm.grading`        | 肿瘤分级与分期   |
| 肿瘤           | `pathology.neoplasm.effects`        | 肿瘤对机体的影响 |

## 节点合同

每个 active 节点必须有模块、顺序、标题、学习目标、机制描述、病例 slug、至少一个来源、证据状态和医学审核状态。每个节点必须恰有一份同目录学习材料。学习材料独立保存版本、情境、背景、示例、补学段落和审核状态。

浏览节点不改变学习状态；学习状态只由复习、作答、正式任务或允许的证据事件更新。目录版本变化不得重写历史学习证据中的稳定编码。
