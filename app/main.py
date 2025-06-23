from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from typing import Any, Optional, List, Dict


# --- CONFIG ---

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = "sqlite:///./pet_barbershop.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

app = FastAPI()

# --- MODELS ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_salon_owner = Column(Boolean, default=False)

class Salon(Base):
    __tablename__ = "salons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    price = Column(Integer)  # price in cents
    duration_minutes = Column(Integer)
    salon_id = Column(Integer, ForeignKey("salons.id"))
    salon = relationship("Salon")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    appointment_time = Column(DateTime)
    user = relationship("User")
    service = relationship("Service")

Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---

class UserCreate(BaseModel):
    username: str
    password: str
    is_salon_owner: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class SalonCreate(BaseModel):
    name: str

class ServiceCreate(BaseModel):
    name: str
    price: int
    duration_minutes: int
    salon_id: int

class BookingCreate(BaseModel):
    service_id: int
    appointment_time: datetime

class BookingOut(BaseModel):
    id: int
    appointment_time: datetime
    service_name: str
    salon_name: str

    class Config:
        orm_mode = True

# --- Utility Functions ---

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "sub": data.get("sub")})  # Add this line
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(db: Session = Depends(SessionLocal), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(db, username)
    if user is None:
        raise credentials_exception
    return user

# --- ROUTES ---

@app.post("/register/", status_code=201)
def register(user: UserCreate, db: Session = Depends(SessionLocal)):
    if get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password, is_salon_owner=user.is_salon_owner)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"username": db_user.username, "is_salon_owner": db_user.is_salon_owner}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(SessionLocal)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/salons/", status_code=201)
def create_salon(salon: SalonCreate, current_user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    if not current_user.is_salon_owner:
        raise HTTPException(status_code=403, detail="Not authorized to create salons")
    db_salon = Salon(name=salon.name, owner_id=current_user.id)
    db.add(db_salon)
    db.commit()
    db.refresh(db_salon)
    return db_salon

@app.post("/services/", status_code=201)
def create_service(service: ServiceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    salon = db.query(Salon).filter(Salon.id == service.salon_id).first()
    if not salon or salon.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add services to this salon")
    db_service = Service(
        name=service.name,
        price=service.price,
        duration_minutes=service.duration_minutes,
        salon_id=service.salon_id
    )
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@app.post("/bookings/", status_code=201)
def create_booking(booking: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Check if appointment_time conflicts with existing bookings for the same salon within service duration
    existing_bookings = (
        db.query(Booking)
        .join(Service)
        .filter(
            Service.salon_id == service.salon_id,
            Booking.appointment_time >= booking.appointment_time,
            Booking.appointment_time < booking.appointment_time + timedelta(minutes=service.duration_minutes),
        )
        .all()
    )
    if existing_bookings:
        raise HTTPException(status_code=400, detail="Time slot already booked")

    db_booking = Booking(
        user_id=current_user.id,
        service_id=service.id,
        appointment_time=booking.appointment_time
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return {"message": "Booking confirmed", "booking_id": db_booking.id}

@app.get("/bookings/", response_model=list[BookingOut])
def get_my_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(SessionLocal)):
    bookings = (
        db.query(Booking)
        .join(Service)
        .join(Salon)
        .filter(Booking.user_id == current_user.id)
        .all()
    )
    return [
        BookingOut(
            id=b.id,
            appointment_time=b.appointment_time,
            service_name=b.service.name,
            salon_name=b.service.salon.name,
        )
        for b in bookings
    ]





