"""Compatibility names resolved from the content-owned catalog."""

from app.modules.content.public import knowledge_tree_view

_catalog = knowledge_tree_view()
PATHOLOGY_CATALOG_VERSION = str(_catalog[0]["catalog_version"])
PATHOLOGY_POINTS = {str(p["system_code"]): str(p["system_label"]) for p in _catalog}
