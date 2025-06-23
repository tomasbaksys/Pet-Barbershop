from typing import Any, Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.booking import BookingCreate, BookingResponse
from app.services.booking_service import create_booking, get_user_bookings, cancel_booking

router = APIRouter(prefix="/bookings", tags=["Bookings"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=BookingResponse)
def book_appointment(booking: BookingCreate, db: Session = Depends(get_db)):
    return create_booking(db, booking)

@router.get("/user/{user_id}", response_model=list[BookingResponse])
def list_user_bookings(user_id: int, db: Session = Depends(get_db)):
    return get_user_bookings(db, user_id)

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_existing_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = cancel_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
