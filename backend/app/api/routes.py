
from datetime import datetime, timezone
import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_profile, require_roles
from app.models.profile import Profile
from app.models.partner_application import PartnerApplication
from app.models.equipment import Equipment
from app.models.booking import Booking
from app.schemas.profile import ProfileRead
from app.schemas.partner import (
    PartnerApplicationCreate,
    PartnerApplicationRead,
    PartnerReview,
)
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate, EquipmentRead
from app.schemas.booking import BookingCreate, BookingRead


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "healthy", "service": "Rentozz API"}


@router.get("/me", response_model=ProfileRead)
def read_me(profile: Profile = Depends(get_current_profile)):
    return profile


# -------------------- PARTNER APPLICATIONS --------------------

@router.post(
    "/partner-applications",
    response_model=PartnerApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_as_partner(
    payload: PartnerApplicationCreate,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    if profile.role == "admin":
        raise HTTPException(400, "Admin accounts cannot apply as rental partners.")

    existing = db.scalar(
        select(PartnerApplication).where(
            PartnerApplication.applicant_id == profile.id,
            PartnerApplication.status == "pending",
        )
    )
    if existing:
        raise HTTPException(409, "You already have a pending partner application.")

    if (
        payload.applicant_type == "business"
        and not payload.business_document_url
    ):
        raise HTTPException(422, "Business document is required for business applications.")

    application = PartnerApplication(
        applicant_id=profile.id,
        **payload.model_dump(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/partner-applications/me", response_model=list[PartnerApplicationRead])
def my_partner_applications(
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(PartnerApplication)
            .where(PartnerApplication.applicant_id == profile.id)
            .order_by(PartnerApplication.created_at.desc())
        ).all()
    )


@router.get(
    "/admin/partner-applications",
    response_model=list[PartnerApplicationRead],
)
def list_partner_applications(
    application_status: str = Query(
        default="pending",
        alias="status",
        pattern="^(pending|approved|rejected|all)$",
    ),
    admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    query = select(PartnerApplication).order_by(PartnerApplication.created_at.asc())

    if application_status != "all":
        query = query.where(PartnerApplication.status == application_status)

    return list(db.scalars(query).all())


@router.post(
    "/admin/partner-applications/{application_id}/review",
    response_model=PartnerApplicationRead,
)
def review_partner_application(
    application_id: uuid.UUID,
    payload: PartnerReview,
    admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    application = db.get(PartnerApplication, application_id)

    if application is None:
        raise HTTPException(404, "Application not found.")
    if application.status != "pending":
        raise HTTPException(409, "This application has already been reviewed.")

    applicant = db.get(Profile, application.applicant_id)
    if applicant is None:
        raise HTTPException(404, "Applicant profile not found.")

    application.status = payload.decision
    application.reviewed_by = admin.id
    application.review_note = payload.review_note
    application.reviewed_at = datetime.now(timezone.utc)

    if payload.decision == "approved":
        applicant.role = "rental_partner"

    db.commit()
    db.refresh(application)
    return application


# -------------------- EQUIPMENT --------------------



@router.get("/equipment", response_model=list[EquipmentRead])
def browse_equipment(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    city: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(
        default="newest",
        pattern="^(newest|price_asc|price_desc)$",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Equipment).where(
        Equipment.is_available.is_(True)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Equipment.name.ilike(term),
                Equipment.description.ilike(term),
            )
        )

    if category and category.strip():
        query = query.where(
            Equipment.category.ilike(category.strip())
        )

    if city and city.strip():
        query = query.where(
            Equipment.city.ilike(city.strip())
        )

    if sort_by == "price_asc":
        query = query.order_by(
            Equipment.daily_rate.asc(),
            Equipment.created_at.desc(),
        )
    elif sort_by == "price_desc":
        query = query.order_by(
            Equipment.daily_rate.desc(),
            Equipment.created_at.desc(),
        )
    else:
        query = query.order_by(
            Equipment.created_at.desc()
        )

    query = query.limit(limit).offset(offset)

    return list(db.scalars(query).all())



@router.get("/equipment/mine", response_model=list[EquipmentRead])
def my_equipment(
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(Equipment)
            .where(Equipment.owner_id == partner.id)
            .order_by(Equipment.created_at.desc())
        ).all()
    )


@router.get("/equipment/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)

    if item is None or not item.is_available:
        raise HTTPException(404, "Equipment listing not found.")

    return item


@router.post(
    "/equipment",
    response_model=EquipmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment(
    payload: EquipmentCreate,
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()

    if data.get("image_url") is not None:
        data["image_url"] = str(data["image_url"])

    item = Equipment(owner_id=partner.id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/equipment/{equipment_id}", response_model=EquipmentRead)
def update_equipment(
    equipment_id: uuid.UUID,
    payload: EquipmentUpdate,
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    item = db.get(Equipment, equipment_id)

    if item is None:
        raise HTTPException(404, "Equipment listing not found.")
    if item.owner_id != partner.id:
        raise HTTPException(403, "You can only edit your own listings.")

    changes = payload.model_dump(exclude_unset=True)

    # Do not allow null for fields required by the database.
    required_fields = {
        "name", "description", "category", "condition", "city", "daily_rate",
        "security_deposit", "rent_to_buy_enabled", "is_available",
    }
    for field in required_fields:
        if field in changes and changes[field] is None:
            raise HTTPException(422, f"{field} cannot be null.")

    if changes.get("image_url") is not None:
        changes["image_url"] = str(changes["image_url"])

    final_rent_to_buy = changes.get("rent_to_buy_enabled", item.rent_to_buy_enabled)
    final_purchase_price = changes.get("purchase_price", item.purchase_price)

    if final_rent_to_buy and final_purchase_price is None:
        raise HTTPException(
            422,
            "Purchase price is required to enable Rent & Buy.",
        )

    for field, value in changes.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_200_OK)
def delete_equipment(
    equipment_id: uuid.UUID,
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    item = db.get(Equipment, equipment_id)

    if item is None:
        raise HTTPException(404, "Equipment listing not found.")
    if item.owner_id != partner.id:
        raise HTTPException(403, "You can only remove your own listings.")

    # Soft delete: preserve booking history and foreign-key references.
    item.is_available = False
    db.commit()

    return {"message": "Listing removed from public search."}


# -------------------- BOOKINGS --------------------

@router.post(
    "/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    payload: BookingCreate,
    renter: Profile = Depends(require_roles("renter", "rental_partner")),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    if payload.start_at <= now:
        raise HTTPException(422, "Booking start time must be in the future.")

    # Lock the equipment row so concurrent requests for the same item
    # serialize while availability is checked.
    equipment = db.scalar(
        select(Equipment)
        .where(Equipment.id == payload.equipment_id)
        .with_for_update()
    )

    if equipment is None or not equipment.is_available:
        raise HTTPException(404, "Equipment is not available.")
    if equipment.owner_id == renter.id:
        raise HTTPException(400, "You cannot book your own equipment.")

    overlap = db.scalar(
        select(Booking.id).where(
            Booking.equipment_id == equipment.id,
            Booking.status == "confirmed",
            Booking.start_at < payload.end_at,
            Booking.end_at > payload.start_at,
        ).limit(1)
    )

    if overlap:
        raise HTTPException(
            409,
            "This equipment is already booked for part of that period.",
        )

    seconds = Decimal(str((payload.end_at - payload.start_at).total_seconds()))
    days = (seconds / Decimal("86400")).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )
    total = (equipment.daily_rate * days).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    booking = Booking(
        renter_id=renter.id,
        equipment_id=equipment.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        total_price=total,
        security_deposit=equipment.security_deposit,
        status="confirmed",
        renter_notes=payload.renter_notes,
    )

    db.add(booking)

    try:
        db.commit()
        db.refresh(booking)
    except Exception:
        db.rollback()
        raise HTTPException(
            409,
            "Booking could not be confirmed. Check availability and try again.",
        )

    return booking




@router.get("/bookings/mine", response_model=list[BookingRead])
def my_bookings(
    booking_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(confirmed|cancelled|completed|disputed)$",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    query = select(Booking).where(
        Booking.renter_id == profile.id
    )

    if booking_status is not None:
        query = query.where(Booking.status == booking_status)

    query = (
        query.order_by(Booking.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(query).all())



@router.get("/bookings/received", response_model=list[BookingRead])
def received_bookings(
    booking_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(confirmed|cancelled|completed|disputed)$",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    equipment_ids = select(Equipment.id).where(
        Equipment.owner_id == partner.id
    )

    query = select(Booking).where(
        Booking.equipment_id.in_(equipment_ids)
    )

    if booking_status is not None:
        query = query.where(Booking.status == booking_status)

    query = query.order_by(Booking.created_at.desc()).limit(limit).offset(offset)

    return list(db.scalars(query).all())



@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(
    booking_id: uuid.UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)

    if booking is None:
        raise HTTPException(404, "Booking not found.")

    equipment = db.get(Equipment, booking.equipment_id)
    is_renter = booking.renter_id == profile.id
    is_owner = equipment is not None and equipment.owner_id == profile.id

    if not (is_renter or is_owner or profile.role == "admin"):
        raise HTTPException(403, "You cannot cancel this booking.")

    if booking.status != "confirmed":
        raise HTTPException(409, "Only confirmed bookings can be cancelled.")

    if booking.start_at <= datetime.now(timezone.utc):
        raise HTTPException(409, "A booking cannot be cancelled after its start time.")

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking



@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
def complete_booking(
    booking_id: uuid.UUID,
    partner: Profile = Depends(require_roles("rental_partner")),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)

    if booking is None:
        raise HTTPException(404, "Booking not found.")

    equipment = db.get(Equipment, booking.equipment_id)

    if equipment is None or equipment.owner_id != partner.id:
        raise HTTPException(
            403, "You can only complete bookings for your own equipment."
        )

    if booking.status != "confirmed":
        raise HTTPException(
            409, "Only confirmed bookings can be completed."
        )

    if booking.end_at > datetime.now(timezone.utc):
        raise HTTPException(
            409, "A booking can only be completed after its end time."
        )

    booking.status = "completed"
    db.commit()
    db.refresh(booking)

    return booking



@router.get("/equipment/{equipment_id}/availability")
def check_equipment_availability(
    equipment_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    db: Session = Depends(get_db),
):
    # Validate requested time period
    if start_at >= end_at:
        raise HTTPException(
            status_code=422,
            detail="end_at must be later than start_at.",
        )

    if start_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=422,
            detail="start_at must be in the future.",
        )

    # Find equipment
    equipment = db.get(Equipment, equipment_id)

    if equipment is None or not equipment.is_available:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found or unavailable.",
        )

    # Check overlapping confirmed bookings
    overlapping_booking = db.scalar(
        select(Booking.id).where(
            Booking.equipment_id == equipment_id,
            Booking.status == "confirmed",
            Booking.start_at < end_at,
            Booking.end_at > start_at,
        ).limit(1)
    )

    available = overlapping_booking is None

    return {
        "equipment_id": str(equipment_id),
        "start_at": start_at,
        "end_at": end_at,
        "available": available,
        "message": (
            "Equipment is available for these dates."
            if available
            else "Equipment is already booked during this period."
        ),
    }
