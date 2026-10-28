
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class EquipmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    category: str = Field(min_length=2, max_length=100)
    condition: str = Field(min_length=2, max_length=50)
    city: str = Field(min_length=2, max_length=100)
    hourly_rate: Decimal | None = Field(default=None, gt=0)
    daily_rate: Decimal = Field(gt=0)
    security_deposit: Decimal = Field(default=Decimal("0.00"), ge=0)
    purchase_price: Decimal | None = Field(default=None, gt=0)
    rent_to_buy_enabled: bool = False
    image_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_rent_to_buy(self):
        if self.rent_to_buy_enabled and self.purchase_price is None:
            raise ValueError("Purchase price is required for Rent & Buy.")
        return self


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    condition: str | None = Field(default=None, min_length=2, max_length=50)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    hourly_rate: Decimal | None = Field(default=None, gt=0)
    daily_rate: Decimal | None = Field(default=None, gt=0)
    security_deposit: Decimal | None = Field(default=None, ge=0)
    purchase_price: Decimal | None = Field(default=None, gt=0)
    rent_to_buy_enabled: bool | None = None
    image_url: HttpUrl | None = None
    is_available: bool | None = None

    @model_validator(mode="after")
    def validate_rent_to_buy(self):
        if self.rent_to_buy_enabled is True and self.purchase_price is None:
            # The route checks the existing listing's price as well.
            return self
        return self


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str
    category: str
    condition: str
    city: str
    hourly_rate: Decimal | None
    daily_rate: Decimal
    security_deposit: Decimal
    purchase_price: Decimal | None
    rent_to_buy_enabled: bool
    image_url: str | None
    is_available: bool
    created_at: datetime
