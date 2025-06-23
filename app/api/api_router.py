from typing import Any, Optional, List, Dict
from fastapi import APIRouter
from app.api import bookings

api_router = APIRouter()
api_router.include_router(bookings.router)
