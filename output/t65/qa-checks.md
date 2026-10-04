# T65 QA 退役清理验收

验收范围：移除未使用的 `QuestionRepository` / `SqlAlchemyQuestionRepository`，并取消 `QuestionsApplication` 对 repository/UoW 的注入。未修改源码、测试、索引或共享数据库；只在本目录写入验收记录与命令日志。

## 快照与范围核对

- `qa-retirement-before.manifest.json` 声明 30 个源文件；ZIP 含 34 个成员。manifest 中 34/34 个成员的 SHA-256 与字节数均匹配归档内容。
- 归档 SHA-256：`d3c8bf8a67dbfb375891773c7d0d5962a034274405af842d4b2b4c9314fd3732`；manifest SHA-256：`c6c3db21be48265867d060b27b6ab5b1a4520c705aa3f1514464d87df88b648f`；归档内 `snapshot/git-status-before.txt` SHA-256：`39a15cd0d7fec0267bc90831fd8cf323ca1f5d2780e61ce3ab72320367738608`。
- 统一换行符后，当前内容相对归档基线恰有以下 7 个文件差异：
  - `backend/app/modules/content/api/problems.py`
  - `backend/app/modules/qa/api/student_questions.py`
  - `backend/app/modules/qa/application/ports.py`
  - `backend/app/modules/qa/application/use_cases.py`
  - `backend/app/modules/qa/infrastructure/__init__.py`
  - `backend/app/modules/qa/infrastructure/question_repository.py`（已删除）
  - `backend/app/modules/qa/wiring.py`
- `rg -n "questions_application\(|QuestionsApplication\s*\(|SqlAlchemyQuestionRepository|QuestionRepository" backend --glob "*.py"` 退出码 0。没有剩余 `QuestionRepository` 或 `SqlAlchemyQuestionRepository` 引用；唯一直接构造为 `QuestionsApplication()`，API 工厂调用均无 DB 参数。

## 验收结果

| 检查               | 命令（工作目录 `backend/`）                                                                                                              | 退出码 | 结果                                                                                                   |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | -----: | ------------------------------------------------------------------------------------------------------ |
| pytest             | `python -m pytest -q tests/test_api.py tests/test_case_hardening.py tests/test_data_layer.py tests/test_t63_content_learning_pruning.py` |      0 | 28 passed，0 failed，27 warnings，30.24s。警告均为 teardown 时既有 SQLite 外键循环导致的 `SAWarning`。 |
| Ruff               | `python -m ruff check app/modules/qa app/modules/content/api/problems.py`                                                                |      0 | All checks passed。                                                                                    |
| Backend boundaries | `python scripts/check_boundaries.py`                                                                                                     |      0 | `backend-boundaries: PASS`（9 modules）。                                                              |

失败摘要：无。pytest 由 `backend/tests/conftest.py` 创建、校验并清理受管临时数据库；未连接或修改共享真实数据库，自动 fixture 拦截非本地网络连接。

原始输出：`qa-pytest.log`、`qa-ruff.log`、`qa-boundaries.log`；命令及退出码汇总：`qa-checks.log`。

PowerShell 实际执行命令（工作目录 `backend/`；`Tee-Object` 同时保留原始输出）：

```powershell
python -m pytest -q tests/test_api.py tests/test_case_hardening.py tests/test_data_layer.py tests/test_t63_content_learning_pruning.py 2>&1 | Tee-Object -FilePath ..\output\t65\qa-pytest.log; $resultCode=$LASTEXITCODE; Write-Output "EXIT_CODE=$resultCode"; exit $resultCode
python -m ruff check app/modules/qa app/modules/content/api/problems.py 2>&1 | Tee-Object -FilePath ..\output\t65\qa-ruff.log; $resultCode=$LASTEXITCODE; Write-Output "EXIT_CODE=$resultCode"; exit $resultCode
python scripts/check_boundaries.py 2>&1 | Tee-Object -FilePath ..\output\t65\qa-boundaries.log; $resultCode=$LASTEXITCODE; Write-Output "EXIT_CODE=$resultCode"; exit $resultCode
```
