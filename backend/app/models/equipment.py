import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint("daily_rate > 0", name="ck_equipment_daily_rate_positive"),
        CheckConstraint("hourly_rate IS NULL OR hourly_rate > 0", name="ck_equipment_hourly_rate_positive"),
        CheckConstraint("security_deposit >= 0", name="ck_equipment_deposit_nonnegative"),
        CheckConstraint("purchase_price IS NULL OR purchase_price > 0", name="ck_equipment_purchase_price_positive"),
        CheckConstraint("NOT rent_to_buy_enabled OR purchase_price IS NOT NULL", name="ck_equipment_rent_buy_price_required"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    security_deposit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    rent_to_buy_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
