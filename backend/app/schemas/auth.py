from datetime import datetime

from pydantic import BaseModel, Field

UserRole = str


class UserRead(BaseModel):
    id: int
    role: UserRole
    nickname: str
    avatar_url: str = ""
    class_ids: list[str] = []
    permissions: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    role: str = Field(pattern="^(student|teacher)$")
    nickname: str = Field(min_length=1, max_length=80)
    external_id: str = Field(min_length=1, max_length=80)
    avatar_url: str = Field(default="", max_length=500)
    class_ids: list[str] = Field(default_factory=list, max_length=50)


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)
    nickname: str = Field(default="微信用户", min_length=1, max_length=80)
    avatar_url: str = Field(default="", max_length=500)
    requested_role: str = Field(default="student", pattern="^(student|teacher)$")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
