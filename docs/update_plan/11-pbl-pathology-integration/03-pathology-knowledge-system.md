# 病理学知识体系

## 待实现目标

唯一权威目录由 content 持有，版本 pathology-general-v2。五个既有主题编码作为父节点，子节点采用父编码加稳定后缀。PBL、QA、报告、训练、学习和分析统一引用；前端快照由脚本生成并检查漂移。

| 父主题                 | 六个子节点后缀与含义                                                                                                 |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| pathology.cell-injury  | adaptation 细胞适应；reversible 可逆损伤；necrosis 坏死；apoptosis 凋亡；hypoxia 缺氧损伤；oxidative 氧化应激        |
| pathology.inflammation | vascular 血管反应；leukocytes 白细胞募集；mediators 炎症介质；acute 急性炎症形态；chronic 慢性炎症；granuloma 肉芽肿 |
| pathology.repair       | regeneration 再生；granulation 肉芽组织；matrix 基质重塑；wound 创伤愈合；fibrosis 纤维化；factors 修复影响因素      |
| pathology.circulatory  | congestion 充血淤血；edema 水肿；thrombosis 血栓；embolism 栓塞；infarction 梗死；shock 休克                         |
| pathology.neoplasm     | atypia 异型性；behavior 良恶性；spread 浸润转移；carcinogenesis 发生机制；grading 分级分期；effects 机体影响         |

每点有目标、概念说明、版本、参考、前置和相关编码及关系说明；前置关系无环。每点两张不同客观题（practice/retest）及一张 recall，共九十卡；五个病例按主题提供公开情境、阶段任务、蓝图、rubric、知识绑定。内容是合成教学材料，不宣称专家已审核。

目录公共数据不含卡片答案或病例隐藏字段。API 学生仅在提交后取得客观答案解释；recall 先揭晓再自评，自评不计客观正确率。Demo 为明确标注的合成演示数据，不充当 API 权限和真实模型证据。

保留训练 history/problem_representation/differential/tests/management 标识，显示病理教学文案。知识关系只用于导航/推荐；发布任务、浏览目录或 AI 候选不会改变掌握状态。旧内科学编码只允许出现在迁移识别清单、历史说明与负向测试中，不可新增学习写入。
