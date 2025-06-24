from typing import Any, Optional, List, Dict
from sqlalchemy.orm import Session
from app.db.models import Booking
from app.models.booking import BookingCreate

def create_booking(db: Session, booking_data: BookingCreate) -> Booking:
    booking = Booking(**booking_data.dict())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

def get_user_bookings(db: Session, user_id: int) -> List[Booking]:
    return db.query(Booking).filter(Booking.user_id == user_id).all()

def cancel_booking(db: Session, booking_id: int) -> Optional[Booking]:
    booking = db.get(Booking, booking_id)
    if booking:
        booking.is_cancelled = True
        db.commit()
    return booking
