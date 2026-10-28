import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PartnerApplicationCreate(BaseModel):
    applicant_type: str = Field(default="individual", pattern="^(individual|business)$")
    identity_document_url: str = Field(min_length=8, max_length=2000)
    business_document_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class PartnerApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    applicant_id: uuid.UUID
    applicant_type: str
    status: str
    notes: str | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class PartnerReview(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    review_note: str | None = Field(default=None, max_length=2000)
