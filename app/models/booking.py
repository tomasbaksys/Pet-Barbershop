from pydantic import BaseModel, Field
from datetime import datetime

class BookingCreate(BaseModel):
    user_id: int
    pet_name: str = Field(..., example="Bella")
    service: str = Field(..., example="Haircut")
    appointment_time: datetime = Field(..., example="2025-07-01T14:00:00")

class BookingResponse(BaseModel):
    id: int
    user_id: int
    pet_name: str
    service: str
    appointment_time: datetime
    is_cancelled: bool

    class Config:
        orm_mode = True


