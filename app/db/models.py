from typing import Any, Optional, List, Dict
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from .database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    pet_name = Column(String, nullable=False)
    service = Column(String, nullable=False)
    appointment_time = Column(DateTime, nullable=False)
    is_cancelled = Column(Boolean, default=False, nullable=False)  # Explicitly set nullable=False

