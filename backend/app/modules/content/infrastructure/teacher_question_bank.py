"""Teacher-owned, de-identified question copies with immutable revisions."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.content.infrastructure.question_bank_models import (
    BankArchiveReceipt,
    BankImportReceipt,
    TeacherQuestionBankItem,
    TeacherQuestionBankRevision,
)
from app.modules.content.public import KnowledgeCatalogPort
from app.modules.learning.public import RouteTestQuestionSourcePort
from app.shared.errors import AppError


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_content(content: dict[str, object], catalog: KnowledgeCatalogPort) -> dict[str, object]:
    allowed = {"task_type", "title", "prompt", "options", "answer", "explanation", "point_codes", "dimension_ids"}
    if set(content) != allowed:
        raise AppError("VALIDATION_ERROR", "题库副本字段不完整或含有私人字段", 422)
    task_type = content["task_type"]
    if task_type not in {"retest", "knowledge_review", "discussion", "micro_drill"}:
        raise AppError("VALIDATION_ERROR", "此题型不能保存到个人题库", 422)
    title = content["title"]
    prompt = content["prompt"]
    explanation = content["explanation"]
    if (
        not isinstance(title, str)
        or not 1 <= len(title.strip()) <= 200
        or not isinstance(prompt, str)
        or not 1 <= len(prompt.strip()) <= 2000
        or not isinstance(explanation, str)
        or len(explanation.strip()) > 2000
    ):
        raise AppError("VALIDATION_ERROR", "题库标题、题干或解析长度无效", 422)
    options = content["options"]
    answer = content["answer"]
    points = content["point_codes"]
    dimensions = content["dimension_ids"]
    if (
        not isinstance(options, list)
        or not isinstance(answer, dict)
        or not isinstance(points, list)
        or not points
        or len(points) > 3
        or not all(isinstance(code, str) and code for code in points)
        or len(set(points)) != len(points)
        or not catalog.contains_points(tuple(points))
        or not isinstance(dimensions, list)
        or len(dimensions) > 6
        or not all(isinstance(code, str) and 1 <= len(code) <= 50 for code in dimensions)
        or len(set(dimensions)) != len(dimensions)
    ):
        raise AppError("VALIDATION_ERROR", "题库目标、维度或答案格式无效", 422)
    if task_type in {"retest", "knowledge_review"}:
        selected = answer.get("correct_option")
        if (
            set(answer) != {"correct_option"}
            or type(selected) is not int
            or not 2 <= len(options) <= 6
            or any(not isinstance(option, str) or not 1 <= len(option.strip()) <= 500 for option in options)
            or len(set(options)) != len(options)
            or not 0 <= selected < len(options)
            or not explanation.strip()
        ):
            raise AppError("VALIDATION_ERROR", "客观题选项、答案或解析无效", 422)
    elif options or (task_type == "discussion" and answer):
        raise AppError("VALIDATION_ERROR", "非客观题不能包含选项或自由评分答案", 422)
    if task_type == "micro_drill" and not dimensions:
        raise AppError("VALIDATION_ERROR", "推理题必须保留能力维度", 422)
    for value in (title, prompt, explanation, *options):
        if any(marker in value.lower() for marker in ("student_id", "snapshot_id", "学号：", "学生姓名：")):
            raise AppError("VALIDATION_ERROR", "题目可能包含学生身份或诊断标识，请先去标识化", 422)
    return {
        "task_type": task_type,
        "title": title.strip(),
        "prompt": prompt.strip(),
        "options": [option.strip() for option in options],
        "answer": answer,
        "explanation": explanation.strip(),
        "point_codes": points,
        "dimension_ids": dimensions,
    }


class SqlTeacherQuestionBank:
    def __init__(self, session: Session, sources: RouteTestQuestionSourcePort, catalog: KnowledgeCatalogPort) -> None:
        self._session = session
        self._sources = sources
        self._catalog = catalog

    def import_item(
        self,
        teacher_id: int,
        source_type: str,
        source_id: str,
        source_digest: str,
        client_request_id: str,
        deidentified: bool,
        content: dict[str, object],
    ) -> dict[str, object]:
        if not deidentified or not client_request_id.strip() or len(client_request_id) > 100:
            raise AppError("VALIDATION_ERROR", "请确认去标识化并提供请求标识", 422)
        normalized = _validate_content(content, self._catalog)
        payload_digest = _digest(normalized)
        by_key = self._session.scalar(
            select(BankImportReceipt).where(
                BankImportReceipt.teacher_id == teacher_id,
                BankImportReceipt.client_request_id == client_request_id,
            )
        )
        if by_key is not None:
            if (
                by_key.source_kind != source_type
                or by_key.source_public_id != source_id
                or by_key.source_digest != source_digest
                or by_key.payload_digest != payload_digest
            ):
                raise AppError("STATE_CONFLICT", "入库请求标识已用于其他题目", 409)
            return self.get(teacher_id, by_key.bank_item_id)
        by_source = self._session.scalar(
            select(BankImportReceipt).where(
                BankImportReceipt.teacher_id == teacher_id,
                BankImportReceipt.source_kind == source_type,
                BankImportReceipt.source_public_id == source_id,
                BankImportReceipt.source_digest == source_digest,
            )
        )
        if by_source is not None:
            raise AppError("STATE_CONFLICT", "该来源版本已脱钩，不能再次导入", 409)

        if source_type != "route_test_question":
            raise AppError("VALIDATION_ERROR", "暂不支持此题库来源类型", 422)
        source = self._sources.bank_source(teacher_id, source_id)
        if source_type != source.get("source_type") or source_id != source.get("source_id"):
            raise AppError("STATE_CONFLICT", "题库来源标识无效", 409)
        if source_digest != source["source_digest"]:
            raise AppError("STATE_CONFLICT", "来源题目已更新，请重新预览去标识化副本", 409)
        if normalized["task_type"] != source["task_type"]:
            raise AppError("STATE_CONFLICT", "题库副本题型必须与来源一致", 409)
        if normalized["point_codes"] != source["point_codes"] or normalized["dimension_ids"] != source["dimension_ids"]:
            raise AppError("STATE_CONFLICT", "首次入库须保留来源题目的知识目标与能力维度", 409)
        source_content = {
            key: source[key]
            for key in (
                "task_type",
                "title",
                "prompt",
                "options",
                "answer",
                "explanation",
                "point_codes",
                "dimension_ids",
            )
        }
        if _digest(normalized) != _digest(source_content):
            raise AppError("STATE_CONFLICT", "首次入库须完整保留来源题目的去标识内容", 409)
        source_public_id = source_id
        item = TeacherQuestionBankItem(owner_teacher_id=teacher_id, status="active", version=1)
        self._session.add(item)
        self._session.flush()
        revision = TeacherQuestionBankRevision(
            bank_item_id=item.id,
            version=1,
            source_kind=source_type,
            source_public_id=source_public_id,
            source_package_item_id=None,
            source_digest=source_digest,
            medical_status=source["medical_status"],
            **normalized,
        )
        self._session.add(revision)
        self._session.flush()
        item.current_revision_id = revision.id
        self._session.add(
            BankImportReceipt(
                teacher_id=teacher_id,
                source_kind=source_type,
                source_public_id=source_public_id,
                source_package_item_id=None,
                source_digest=source_digest,
                client_request_id=client_request_id,
                payload_digest=payload_digest,
                bank_item_id=item.id,
            )
        )
        self._session.flush()
        return self._view(item, revision)

    def get(self, teacher_id: int, bank_item_id: int) -> dict[str, object]:
        item = self._session.scalar(
            select(TeacherQuestionBankItem).where(
                TeacherQuestionBankItem.id == bank_item_id,
                TeacherQuestionBankItem.owner_teacher_id == teacher_id,
                TeacherQuestionBankItem.status == "active",
            )
        )
        if item is None:
            raise AppError("RESOURCE_NOT_FOUND", "个人题库题目不存在", 404)
        revision = self._session.get(TeacherQuestionBankRevision, item.current_revision_id)
        if revision is None:
            raise AppError("STATE_CONFLICT", "题库当前版本丢失", 409)
        return self._view(item, revision)

    def list(
        self,
        teacher_id: int,
        status: str,
        point_code: str | None,
        task_type: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        if status not in {"active", "archived"}:
            raise AppError("VALIDATION_ERROR", "题库状态无效", 422)
        if status == "archived":
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        if query is not None and len(query) > 100:
            raise AppError("VALIDATION_ERROR", "搜索词最长100字", 422)
        statement = (
            select(TeacherQuestionBankItem, TeacherQuestionBankRevision)
            .join(
                TeacherQuestionBankRevision,
                TeacherQuestionBankRevision.id == TeacherQuestionBankItem.current_revision_id,
            )
            .where(
                TeacherQuestionBankItem.owner_teacher_id == teacher_id,
                TeacherQuestionBankItem.status == status,
            )
        )
        if task_type:
            statement = statement.where(TeacherQuestionBankRevision.task_type == task_type)
        if query:
            escaped = query.replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(TeacherQuestionBankRevision.title.ilike(f"%{escaped}%", escape="\\"))
        rows = self._session.execute(statement).all()
        if point_code:
            rows = [(item, revision) for item, revision in rows if point_code in revision.point_codes]
        rows.sort(key=lambda pair: (pair[0].updated_at, pair[0].id), reverse=True)
        return {
            "items": [self._view(item, revision) for item, revision in rows[offset : offset + limit]],
            "total": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def update(self, teacher_id: int, bank_item_id: int, version: int, content: dict[str, object]) -> dict[str, object]:
        previous = self.get(teacher_id, bank_item_id)
        item = self._session.get(TeacherQuestionBankItem, bank_item_id)
        if item.status != "active" or item.version != version:
            raise AppError("STATE_CONFLICT", "题库版本已更新或已删除", 409)
        normalized = _validate_content(content, self._catalog)
        if normalized["task_type"] != previous["task_type"]:
            raise AppError("STATE_CONFLICT", "题型不能在题库版本中改变", 409)
        old_revision = self._session.get(TeacherQuestionBankRevision, item.current_revision_id)
        changed = self._session.execute(
            update(TeacherQuestionBankItem)
            .where(
                TeacherQuestionBankItem.id == item.id,
                TeacherQuestionBankItem.owner_teacher_id == teacher_id,
                TeacherQuestionBankItem.version == version,
                TeacherQuestionBankItem.status == "active",
            )
            .values(version=version + 1)
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "题库版本冲突，请刷新重试", 409)
        revision = TeacherQuestionBankRevision(
            bank_item_id=item.id,
            version=version + 1,
            source_kind=old_revision.source_kind,
            source_public_id=old_revision.source_public_id,
            source_package_item_id=old_revision.source_package_item_id,
            source_digest=old_revision.source_digest,
            medical_status="not_required",
            **normalized,
        )
        self._session.add(revision)
        self._session.flush()
        item.current_revision_id = revision.id
        self._session.flush()
        return self._view(item, revision)

    def archive(self, teacher_id: int, bank_item_id: int, version: int, client_request_id: str) -> dict[str, object]:
        if not client_request_id.strip() or len(client_request_id) > 100:
            raise AppError("VALIDATION_ERROR", "删除请求标识无效", 422)
        item = self._session.scalar(
            select(TeacherQuestionBankItem).where(
                TeacherQuestionBankItem.id == bank_item_id,
                TeacherQuestionBankItem.owner_teacher_id == teacher_id,
            )
        )
        if item is None:
            raise AppError("RESOURCE_NOT_FOUND", "个人题库题目不存在", 404)
        receipt = self._session.scalar(
            select(BankArchiveReceipt).where(
                BankArchiveReceipt.teacher_id == teacher_id,
                BankArchiveReceipt.client_request_id == client_request_id,
            )
        )
        if receipt is not None:
            if receipt.bank_item_id != bank_item_id or receipt.expected_version != version:
                raise AppError("STATE_CONFLICT", "删除请求标识已用于其他内容", 409)
            revision = self._session.get(TeacherQuestionBankRevision, item.current_revision_id)
            return self._view(item, revision)
        if item.status != "active" or item.version != version:
            raise AppError("STATE_CONFLICT", "题库已删除或版本已更新", 409)
        changed = self._session.execute(
            update(TeacherQuestionBankItem)
            .where(
                TeacherQuestionBankItem.id == item.id,
                TeacherQuestionBankItem.owner_teacher_id == teacher_id,
                TeacherQuestionBankItem.status == "active",
                TeacherQuestionBankItem.version == version,
            )
            .values(status="archived", version=version + 1)
        )
        if changed.rowcount != 1:
            raise AppError("STATE_CONFLICT", "删除版本冲突，请刷新重试", 409)
        self._session.add(
            BankArchiveReceipt(
                teacher_id=teacher_id,
                bank_item_id=bank_item_id,
                client_request_id=client_request_id,
                expected_version=version,
                result_version=version + 1,
            )
        )
        self._session.flush()
        revision = self._session.get(TeacherQuestionBankRevision, item.current_revision_id)
        return self._view(item, revision)

    @staticmethod
    def _view(item: TeacherQuestionBankItem, revision: TeacherQuestionBankRevision) -> dict[str, object]:
        return {
            "id": item.id,
            "version": item.version,
            "status": item.status,
            "task_type": revision.task_type,
            "title": revision.title,
            "prompt": revision.prompt,
            "options": revision.options,
            "answer": revision.answer,
            "explanation": revision.explanation,
            "point_codes": revision.point_codes,
            "dimension_ids": revision.dimension_ids,
            "medical_review_status": revision.medical_status,
            "updated_at": item.updated_at,
        }


__all__ = ["SqlTeacherQuestionBank"]
