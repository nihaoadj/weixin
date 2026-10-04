from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.content.infrastructure.models import (
    KnowledgeCardContribution,
    KnowledgeCatalog,
    KnowledgeDependency,
    KnowledgeDependencySource,
    KnowledgeModule,
    KnowledgePoint,
    KnowledgePointSource,
    KnowledgeSource,
    KnowledgeStudyMaterial,
)
from app.modules.content.public import CatalogCardRecord, KnowledgeCatalogPort
from app.shared.errors import AppError


class SqlAlchemyKnowledgeCatalogRepository(KnowledgeCatalogPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _active(self) -> KnowledgeCatalog:
        catalogs = self._session.scalars(
            select(KnowledgeCatalog).where(KnowledgeCatalog.status == "active").order_by(KnowledgeCatalog.id)
        ).all()
        if len(catalogs) != 1:
            raise AppError("SERVICE_ERROR", "知识目录不可用", 503)
        return catalogs[0]

    def catalog_version(self) -> str:
        self.tree_view()
        return self._active().version

    def module_labels(self) -> dict[str, str]:
        self.tree_view()
        catalog = self._active()
        return {
            item.code: item.label
            for item in self._session.scalars(
                select(KnowledgeModule)
                .where(KnowledgeModule.catalog_id == catalog.id)
                .order_by(KnowledgeModule.position)
            ).all()
        }

    def _source_views(self, links: list[tuple[int, KnowledgeSource]]) -> dict[int, list[dict[str, str]]]:
        values: dict[int, list[dict[str, str]]] = defaultdict(list)
        for owner_id, source in links:
            try:
                date.fromisoformat(source.accessed_on)
            except (TypeError, ValueError):
                raise AppError("SERVICE_ERROR", "知识来源信息无效", 503) from None
            if (
                not source.source_key.strip()
                or not source.title.strip()
                or not source.publisher.strip()
                or not source.url.startswith("https://")
            ):
                raise AppError("SERVICE_ERROR", "知识来源信息无效", 503)
            values[owner_id].append(
                {
                    "source_key": source.source_key,
                    "title": source.title,
                    "publisher": source.publisher,
                    "url": source.url,
                    "source_type": source.source_type,
                    "accessed_on": source.accessed_on,
                }
            )
        return values

    @staticmethod
    def _assert_acyclic(codes: set[str], edges: list[tuple[str, str]]) -> None:
        incoming = {code: 0 for code in codes}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for source, target in edges:
            if source not in codes or target not in codes or source == target:
                raise AppError("SERVICE_ERROR", "知识目录关系无效", 503)
            incoming[target] += 1
            outgoing[source].append(target)
        queue = [code for code, count in incoming.items() if count == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for target in outgoing[current]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    queue.append(target)
        if visited != len(codes):
            raise AppError("SERVICE_ERROR", "知识目录关系存在循环", 503)

    def tree_view(self) -> tuple[dict[str, object], ...]:
        catalog = self._active()
        modules = self._session.scalars(
            select(KnowledgeModule).where(KnowledgeModule.catalog_id == catalog.id).order_by(KnowledgeModule.position)
        ).all()
        module_by_id = {item.id: item for item in modules}
        points = self._session.scalars(
            select(KnowledgePoint)
            .outerjoin(KnowledgeModule, KnowledgeModule.id == KnowledgePoint.module_id)
            .where(KnowledgePoint.catalog_id == catalog.id)
            .order_by(KnowledgeModule.position, KnowledgePoint.position)
        ).all()
        point_by_id = {item.id: item for item in points}
        point_sources = self._source_views(
            list(
                self._session.execute(
                    select(KnowledgePointSource.point_id, KnowledgeSource)
                    .join(KnowledgeSource, KnowledgeSource.id == KnowledgePointSource.source_id)
                    .join(KnowledgePoint, KnowledgePoint.id == KnowledgePointSource.point_id)
                    .where(KnowledgePoint.catalog_id == catalog.id)
                    .order_by(KnowledgePointSource.point_id, KnowledgeSource.source_key)
                ).all()
            )
        )
        dependencies = self._session.scalars(
            select(KnowledgeDependency)
            .where(KnowledgeDependency.catalog_id == catalog.id)
            .order_by(KnowledgeDependency.position)
        ).all()
        dependency_sources = self._source_views(
            list(
                self._session.execute(
                    select(KnowledgeDependencySource.dependency_id, KnowledgeSource)
                    .join(KnowledgeSource, KnowledgeSource.id == KnowledgeDependencySource.source_id)
                    .join(KnowledgeDependency, KnowledgeDependency.id == KnowledgeDependencySource.dependency_id)
                    .where(KnowledgeDependency.catalog_id == catalog.id)
                    .order_by(KnowledgeDependencySource.dependency_id, KnowledgeSource.source_key)
                ).all()
            )
        )
        materials = {
            item.point_id: item
            for item in self._session.scalars(
                select(KnowledgeStudyMaterial).where(KnowledgeStudyMaterial.catalog_id == catalog.id)
            ).all()
        }
        if (
            not modules
            or not points
            or set(materials) != set(point_by_id)
            or any(material.catalog_id != catalog.id for material in materials.values())
        ):
            raise AppError("SERVICE_ERROR", "知识目录不完整", 503)
        if any(not item.code.strip() or not item.label.strip() or not item.description.strip() for item in modules):
            raise AppError("SERVICE_ERROR", "知识模块信息不完整", 503)
        if any(
            not item.code.strip()
            or not item.title.strip()
            or not item.objective.strip()
            or not item.description.strip()
            or not item.case_slug.strip()
            for item in points
        ):
            raise AppError("SERVICE_ERROR", "知识点信息不完整", 503)
        if any(
            not item.version.strip()
            or not isinstance(item.learning_objectives, list)
            or len(item.learning_objectives or []) < 2
            or any(not str(objective).strip() for objective in item.learning_objectives)
            or len({str(objective).strip() for objective in item.learning_objectives}) != len(item.learning_objectives)
            or not item.scenario.strip()
            or not item.reference_note.strip()
            for item in materials.values()
        ):
            raise AppError("SERVICE_ERROR", "知识材料信息不完整", 503)
        if any(not point_sources.get(point.id) for point in points):
            raise AppError("SERVICE_ERROR", "知识点来源不完整", 503)
        if any(not dependency_sources.get(edge.id) for edge in dependencies):
            raise AppError("SERVICE_ERROR", "知识关系来源不完整", 503)
        if any(not edge.rationale.strip() or not edge.limitation.strip() for edge in dependencies):
            raise AppError("SERVICE_ERROR", "知识关系说明不完整", 503)
        edge_codes = [
            (point_by_id[edge.prerequisite_point_id].code, point_by_id[edge.dependent_point_id].code)
            for edge in dependencies
            if edge.prerequisite_point_id in point_by_id and edge.dependent_point_id in point_by_id
        ]
        if len(edge_codes) != len(dependencies):
            raise AppError("SERVICE_ERROR", "知识目录存在悬空关系", 503)
        self._assert_acyclic({point.code for point in points}, edge_codes)
        incoming: dict[int, list[dict[str, object]]] = defaultdict(list)
        outgoing: dict[int, list[str]] = defaultdict(list)
        for edge in dependencies:
            source = point_by_id[edge.prerequisite_point_id]
            target = point_by_id[edge.dependent_point_id]
            incoming[target.id].append(
                {
                    "id": edge.id,
                    "prerequisite_code": source.code,
                    "dependent_code": target.code,
                    "relation_kind": edge.relation_kind,
                    "rationale": edge.rationale,
                    "limitation": edge.limitation,
                    "confidence": edge.confidence,
                    "evidence_status": edge.evidence_status,
                    "medical_review_status": edge.medical_review_status,
                    "sources": dependency_sources[edge.id],
                }
            )
            outgoing[source.id].append(target.code)
        card_counts = dict(
            self._session.execute(
                select(KnowledgeCardContribution.point_code, func.count(KnowledgeCardContribution.id))
                .where(KnowledgeCardContribution.status == "approved")
                .group_by(KnowledgeCardContribution.point_code)
            ).all()
        )
        result: list[dict[str, object]] = []
        for point in points:
            module = module_by_id.get(point.module_id)
            if module is None or module.catalog_id != catalog.id:
                raise AppError("SERVICE_ERROR", "知识点模块无效", 503)
            edge_views = incoming.get(point.id, [])
            result.append(
                {
                    "code": point.code,
                    "system_code": module.code,
                    "system_label": module.label,
                    "topic": module.code,
                    "title": point.title,
                    "objective": point.objective,
                    "learning_objectives": list(materials[point.id].learning_objectives or []),
                    "reference": catalog.reference_note,
                    "card_count": int(card_counts.get(point.code, 0)),
                    "catalog_version": catalog.version,
                    "catalog_evidence_status": catalog.evidence_status,
                    "catalog_medical_review_status": catalog.medical_review_status,
                    "parent_code": module.code,
                    "description": point.description,
                    "position": point.position,
                    "prerequisite_codes": [str(edge["prerequisite_code"]) for edge in edge_views],
                    "related_codes": outgoing.get(point.id, []),
                    "dependencies": edge_views,
                    "sources": point_sources[point.id],
                    "evidence_status": point.evidence_status,
                    "medical_review_status": point.medical_review_status,
                    "relationship_note": (
                        "箭头表示建议学习前置；具体医学语义、限制和来源见依赖详情，不代表唯一病因或必然进展。"
                    ),
                    "case_slug": point.case_slug,
                }
            )
        return tuple(result)

    def point_view(self, code: str) -> dict[str, object] | None:
        return next((item for item in self.tree_view() if item["code"] == code), None)

    def contains_points(self, point_codes: tuple[str, ...]) -> bool:
        self.tree_view()
        if not point_codes:
            return True
        catalog = self._active()
        count = self._session.scalar(
            select(func.count(KnowledgePoint.id)).where(
                KnowledgePoint.catalog_id == catalog.id, KnowledgePoint.code.in_(set(point_codes))
            )
        )
        return int(count or 0) == len(set(point_codes))

    def study_material_view(self, point_code: str) -> dict[str, object] | None:
        self.tree_view()
        catalog = self._active()
        row = self._session.execute(
            select(KnowledgePoint, KnowledgeStudyMaterial)
            .join(KnowledgeStudyMaterial, KnowledgeStudyMaterial.point_id == KnowledgePoint.id)
            .where(KnowledgePoint.catalog_id == catalog.id, KnowledgePoint.code == point_code)
        ).one_or_none()
        if row is None:
            return None
        point, material = row
        return {
            "version": material.version,
            "point_code": point.code,
            "title": point.title,
            "objective": point.objective,
            "learning_objectives": list(material.learning_objectives or []),
            "scenario": material.scenario,
            "background": list(material.background or []),
            "example": dict(material.example or {}),
            "remediation": list(material.remediation or []),
            "reference": material.reference_note,
            "evidence_status": material.evidence_status,
            "medical_review_status": material.medical_review_status,
        }

    @staticmethod
    def _card(card: KnowledgeCardContribution) -> CatalogCardRecord:
        return CatalogCardRecord(
            code=str(card.catalog_card_code),
            point_code=card.point_code,
            prompt=card.prompt,
            options=tuple(card.options or []),
            correct_option=-1 if card.correct_option is None else card.correct_option,
            explanation=card.explanation,
            reference=card.reference,
            card_type=card.card_type,
        )

    def card_for_code(self, code: str) -> CatalogCardRecord | None:
        self.tree_view()
        card = self._session.scalar(
            select(KnowledgeCardContribution).where(
                KnowledgeCardContribution.catalog_card_code == code,
                KnowledgeCardContribution.status == "approved",
            )
        )
        return self._card(card) if card is not None else None

    def cards_for_points(self, point_codes: tuple[str, ...]) -> tuple[CatalogCardRecord, ...]:
        self.tree_view()
        if not point_codes:
            return ()
        cards = self._session.scalars(
            select(KnowledgeCardContribution)
            .where(
                KnowledgeCardContribution.point_code.in_(set(point_codes)),
                KnowledgeCardContribution.status == "approved",
                KnowledgeCardContribution.catalog_card_code.is_not(None),
                KnowledgeCardContribution.card_type == "single_choice",
                ~KnowledgeCardContribution.catalog_card_code.endswith(".v2"),
            )
            .order_by(KnowledgeCardContribution.catalog_card_code)
        ).all()
        return tuple(self._card(card) for card in cards)
