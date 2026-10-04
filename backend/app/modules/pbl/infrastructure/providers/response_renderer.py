from app.modules.pbl.application.records import LearningResponseRecord
from app.modules.pbl.infrastructure.provider_schema import LearningResponse


def render_learning_response(value: LearningResponse | LearningResponseRecord) -> str:
    points = "\n".join(f"• {point}" for point in value.key_points)
    text = f"回应\n{value.opening}\n\n关键要点\n{points}\n\n下一步\n{value.next_step}"
    if len(text) > 4000:
        raise ValueError("learning response exceeds maximum length")
    return text
