import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookingCreate(BaseModel):
    equipment_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    renter_notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at and end_at must include a timezone, for example +05:30")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    renter_id: uuid.UUID
    equipment_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    total_price: Decimal
    security_deposit: Decimal
    status: str
    renter_notes: str | None
    created_at: datetime
