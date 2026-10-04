from app.modules.content.infrastructure.knowledge_catalog_repository import SqlAlchemyKnowledgeCatalogRepository


def test_every_catalog_point_has_complete_versioned_study_material(db):
    catalog = SqlAlchemyKnowledgeCatalogRepository(db)
    points = catalog.tree_view()
    assert points
    materials = [catalog.study_material_view(str(point["code"])) for point in points]
    assert all(
        material
        and material["version"]
        and material["objective"]
        and len(material["learning_objectives"]) >= 2
        and material["scenario"]
        and material["background"]
        and material["example"]
        and material["remediation"]
        and material["reference"]
        and material["evidence_status"] == "source_supported"
        and material["medical_review_status"] == "pending_expert_review"
        for material in materials
    )
