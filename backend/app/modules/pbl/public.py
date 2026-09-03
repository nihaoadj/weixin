"""PBL stable contracts are exposed through API and wiring only."""

from app.modules.pbl.application.ports import PblInferenceGateway

__all__ = ["PblInferenceGateway"]
