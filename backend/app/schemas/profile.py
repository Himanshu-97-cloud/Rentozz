import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    role: str
    created_at: datetime
