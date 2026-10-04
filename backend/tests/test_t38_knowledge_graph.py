from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.modules.content.infrastructure.knowledge_catalog_repository import SqlAlchemyKnowledgeCatalogRepository
from app.modules.content.infrastructure.models import (
    KnowledgeCatalog,
    KnowledgeDependency,
    KnowledgeDependencySource,
    KnowledgeModule,
    KnowledgePoint,
    KnowledgePointSource,
    KnowledgeSource,
    KnowledgeStudyMaterial,
)
from app.shared.errors import AppError


def _edges(items: tuple[dict[str, object], ...]) -> set[tuple[str, str]]:
    return {
        (str(dependency["prerequisite_code"]), str(dependency["dependent_code"]))
        for item in items
        for dependency in item["dependencies"]
    }


def test_t38_persisted_catalog_is_complete_evidenced_and_pending_expert_review(db) -> None:
    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    items = repository.tree_view()
    dependencies = [dependency for item in items for dependency in item["dependencies"]]

    assert repository.catalog_version() == "pathology-general-v4"
    assert len(items) == 30
    assert len(repository.module_labels()) == 5
    assert len(dependencies) == 34
    assert all(len(item["learning_objectives"]) >= 2 for item in items)
    assert all(len(set(item["learning_objectives"])) == len(item["learning_objectives"]) for item in items)
    assert all(item["sources"] for item in items)
    assert all(dependency["sources"] for dependency in dependencies)
    assert {item["evidence_status"] for item in items} == {"source_supported"}
    assert {item["medical_review_status"] for item in items} == {"pending_expert_review"}
    assert {dependency["evidence_status"] for dependency in dependencies} == {"source_supported"}
    assert {dependency["medical_review_status"] for dependency in dependencies} == {"pending_expert_review"}
    assert db.scalar(select(func.count(KnowledgeCatalog.id))) == 1
    assert db.scalar(select(func.count(KnowledgeSource.id))) == 14
    infarction = next(item for item in items if item["code"] == "pathology.circulatory.infarction")
    assert {source["source_key"] for source in infarction["sources"]} == {"S09", "S14"}
    assert all("S14" in {source["source_key"] for source in edge["sources"]} for edge in infarction["dependencies"])


def test_t38_corrects_reversed_or_untrustworthy_edges_and_preserves_supported_cross_module_edges(db) -> None:
    items = SqlAlchemyKnowledgeCatalogRepository(db).tree_view()
    edges = _edges(items)
    forbidden = {
        ("pathology.cell-injury.necrosis", "pathology.cell-injury.apoptosis"),
        ("pathology.cell-injury.reversible", "pathology.cell-injury.hypoxia"),
        ("pathology.cell-injury.reversible", "pathology.cell-injury.oxidative"),
        ("pathology.inflammation.vascular", "pathology.inflammation.mediators"),
        ("pathology.inflammation.acute", "pathology.inflammation.chronic"),
        ("pathology.cell-injury.adaptation", "pathology.repair.regeneration"),
        ("pathology.circulatory.congestion", "pathology.circulatory.shock"),
        ("pathology.cell-injury.hypoxia", "pathology.circulatory.shock"),
    }
    required = {
        ("pathology.cell-injury.hypoxia", "pathology.cell-injury.reversible"),
        ("pathology.cell-injury.oxidative", "pathology.cell-injury.reversible"),
        ("pathology.inflammation.mediators", "pathology.inflammation.vascular"),
        ("pathology.inflammation.mediators", "pathology.inflammation.leukocytes"),
        ("pathology.inflammation.chronic", "pathology.repair.fibrosis"),
        ("pathology.circulatory.congestion", "pathology.circulatory.edema"),
        ("pathology.circulatory.thrombosis", "pathology.circulatory.infarction"),
        ("pathology.cell-injury.necrosis", "pathology.circulatory.infarction"),
    }
    assert not forbidden & edges
    assert required <= edges
    edema = next(item for item in items if item["code"] == "pathology.circulatory.edema")
    congestion_edge = next(
        dependency
        for dependency in edema["dependencies"]
        if dependency["prerequisite_code"] == "pathology.circulatory.congestion"
    )
    assert "静脉淤血" in congestion_edge["limitation"]
    assert "主动性充血" in congestion_edge["limitation"]


def test_t38_documented_dependency_matrix_matches_every_persisted_edge_and_source(db) -> None:
    items = SqlAlchemyKnowledgeCatalogRepository(db).tree_view()
    codes_by_title = {str(item["title"]): str(item["code"]) for item in items}
    assert len(codes_by_title) == len(items)
    actual = {
        (str(dependency["prerequisite_code"]), str(dependency["dependent_code"])): (
            str(dependency["relation_kind"]),
            str(dependency["confidence"]),
            {str(source["source_key"]) for source in dependency["sources"]},
            str(dependency["rationale"]),
            str(dependency["limitation"]),
        )
        for item in items
        for dependency in item["dependencies"]
    }
    path = Path(__file__).resolve().parents[2] / "docs/knowledge-base/dependency-audit-v4.md"
    documented = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 7 or not cells[0].isdigit():
            continue
        source, target = (title.strip() for title in cells[1].split("→"))
        documented[(codes_by_title[source], codes_by_title[target])] = (
            cells[2],
            cells[3],
            set(cells[4].split(", ")),
            cells[5],
            cells[6],
        )

    assert len(documented) == len(actual) == 34
    assert documented == actual


def test_t38_tree_and_point_endpoints_expose_the_same_persisted_dependencies(client) -> None:
    token = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "t38-student", "nickname": "学生", "avatar_url": ""},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    tree = client.get("/knowledge/tree", headers=headers)
    point = client.get("/knowledge/points/pathology.circulatory.infarction", headers=headers)

    assert tree.status_code == point.status_code == 200
    tree_item = next(item for item in tree.json()["items"] if item["code"] == point.json()["code"])
    assert point.json()["dependencies"] == tree_item["dependencies"]
    assert point.json()["sources"] == tree_item["sources"]
    assert point.json()["learning_objectives"] == tree_item["learning_objectives"]
    assert tree.json()["medical_review_status"] == "pending_expert_review"


def test_t38_archived_catalog_can_reuse_a_stable_point_code_without_changing_active_view(db) -> None:
    original = SqlAlchemyKnowledgeCatalogRepository(db).point_view("pathology.cell-injury.adaptation")
    archived = KnowledgeCatalog(
        version="pathology-general-archived-test",
        label="历史目录测试",
        status="archived",
        reference_note="仅用于目录版本共存测试",
        evidence_status="source_supported",
        medical_review_status="pending_expert_review",
    )
    db.add(archived)
    db.flush()
    module = KnowledgeModule(
        catalog_id=archived.id,
        code="pathology.cell-injury",
        label="历史细胞损伤",
        description="仅用于测试",
        position=1,
    )
    db.add(module)
    db.flush()
    db.add(
        KnowledgePoint(
            catalog_id=archived.id,
            module_id=module.id,
            code="pathology.cell-injury.adaptation",
            title="历史版本的细胞适应",
            objective="仅用于测试",
            description="仅用于测试",
            case_slug="historical-test",
            position=1,
            evidence_status="source_supported",
            medical_review_status="pending_expert_review",
        )
    )
    db.flush()

    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    assert repository.catalog_version() == "pathology-general-v4"
    assert repository.point_view("pathology.cell-injury.adaptation") == original
    assert len(repository.tree_view()) == 30


def test_t38_active_catalog_accepts_a_new_sourced_module_and_point_without_fixed_counts(db) -> None:
    catalog = db.scalar(select(KnowledgeCatalog).where(KnowledgeCatalog.status == "active"))
    source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.source_key == "S01"))
    module = KnowledgeModule(
        catalog_id=catalog.id,
        code="pathology.additional-test",
        label="新增模块测试",
        description="仅验证目录可由数据库扩展",
        position=0,
    )
    db.add(module)
    db.flush()
    point = KnowledgePoint(
        catalog_id=catalog.id,
        module_id=module.id,
        code="pathology.additional-test.topic",
        title="新增知识点测试",
        objective="验证目录动态读取",
        description="仅用于受管临时数据库测试",
        case_slug="additional-test",
        position=1,
        evidence_status="source_supported",
        medical_review_status="pending_expert_review",
    )
    db.add(point)
    db.flush()
    db.add(KnowledgePointSource(point_id=point.id, source_id=source.id))
    db.add(
        KnowledgeStudyMaterial(
            catalog_id=catalog.id,
            point_id=point.id,
            version="test",
            learning_objectives=["验证目录动态读取", "结合情境说明判断依据"],
            scenario="受管目录扩展测试",
            background=[],
            example={},
            remediation=[],
            reference_note="仅用于受管测试",
            evidence_status="source_supported",
            medical_review_status="pending_expert_review",
        )
    )
    db.flush()

    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    assert len(repository.module_labels()) == 6
    assert len(repository.tree_view()) == 31
    assert repository.tree_view()[0]["system_code"] == module.code
    assert repository.point_view(point.code)["system_code"] == module.code


def test_t38_repository_refuses_a_persisted_cycle(db) -> None:
    catalog = db.scalar(select(KnowledgeCatalog).where(KnowledgeCatalog.status == "active"))
    points = {
        point.code: point
        for point in db.scalars(select(KnowledgePoint).where(KnowledgePoint.catalog_id == catalog.id)).all()
    }
    source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.source_key == "S01"))
    dependency = KnowledgeDependency(
        catalog_id=catalog.id,
        prerequisite_point_id=points["pathology.cell-injury.necrosis"].id,
        dependent_point_id=points["pathology.cell-injury.adaptation"].id,
        relation_kind="mechanistic_basis",
        rationale="测试循环关系。",
        limitation="仅用于验证目录拒绝循环。",
        confidence="moderate",
        evidence_status="source_supported",
        medical_review_status="pending_expert_review",
        position=999,
    )
    db.add(dependency)
    db.flush()
    db.add(KnowledgeDependencySource(dependency_id=dependency.id, source_id=source.id))
    db.flush()

    with pytest.raises(AppError) as error:
        SqlAlchemyKnowledgeCatalogRepository(db).tree_view()
    assert error.value.code == "SERVICE_ERROR" and error.value.status_code == 503

    with pytest.raises(AppError, match="知识目录关系存在循环"):
        SqlAlchemyKnowledgeCatalogRepository(db).contains_points(())


def test_t38_invalid_catalog_fails_all_read_paths_instead_of_serving_partial_data(db) -> None:
    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    point = db.scalar(select(KnowledgePoint).where(KnowledgePoint.code == "pathology.cell-injury.adaptation"))
    db.query(KnowledgePointSource).filter(KnowledgePointSource.point_id == point.id).delete()
    db.flush()

    for read in (
        repository.catalog_version,
        repository.module_labels,
        lambda: repository.contains_points(()),
        lambda: repository.study_material_view(point.code),
        lambda: repository.cards_for_points(()),
    ):
        with pytest.raises(AppError, match="知识点来源不完整"):
            read()


def test_t38_invalid_linked_source_metadata_fails_all_read_paths(db) -> None:
    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.source_key == "S01"))
    source.url = ""
    source.accessed_on = "not-a-date"
    db.flush()

    for read in (
        repository.tree_view,
        repository.catalog_version,
        lambda: repository.contains_points(()),
        lambda: repository.cards_for_points(()),
    ):
        with pytest.raises(AppError, match="知识来源信息无效"):
            read()


def test_t38_missing_material_fails_study_and_tree_reads(db) -> None:
    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    point = db.scalar(select(KnowledgePoint).where(KnowledgePoint.code == "pathology.cell-injury.adaptation"))
    db.query(KnowledgeStudyMaterial).filter(KnowledgeStudyMaterial.point_id == point.id).delete()
    db.flush()

    for read in (repository.tree_view, lambda: repository.study_material_view(point.code)):
        with pytest.raises(AppError, match="知识目录不完整"):
            read()


def test_t39_material_with_fewer_than_two_learning_objectives_fails_all_catalog_reads(db) -> None:
    repository = SqlAlchemyKnowledgeCatalogRepository(db)
    material = db.scalar(select(KnowledgeStudyMaterial).order_by(KnowledgeStudyMaterial.id))
    material.learning_objectives = ["只有一个目标"]
    db.flush()

    for read in (repository.tree_view, lambda: repository.study_material_view("pathology.cell-injury.adaptation")):
        with pytest.raises(AppError, match="知识材料信息不完整"):
            read()
