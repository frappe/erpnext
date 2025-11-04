from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

class Addon(Base):
    __tablename__ = "addons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    addon_code = Column(String, unique=True, nullable=False)
    addon_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String)
    is_official = Column(Boolean, default=True)
    pricing_model = Column(String)
    monthly_price = Column(Float, default=0.0)
    features = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompanyAddon(Base):
    __tablename__ = "company_addons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    addon_id = Column(String, ForeignKey('addons.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)
    settings = Column(Text)

# Construction & Real Estate
class ConstructionProject(Base):
    __tablename__ = "construction_projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    project_code = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    client_name = Column(String)
    location = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(Float)
    actual_cost = Column(Float, default=0.0)
    status = Column(String, default='planning')
    progress_percent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class BillOfQuantities(Base):
    __tablename__ = "bill_of_quantities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    project_id = Column(String, ForeignKey('construction_projects.id'))
    item_code = Column(String)
    description = Column(Text)
    unit = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Agriculture & Agribusiness
class Farm(Base):
    __tablename__ = "farms"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_code = Column(String, nullable=False)
    farm_name = Column(String, nullable=False)
    location = Column(String)
    total_area = Column(Float)
    area_unit = Column(String, default='hectares')
    farm_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CropPlanting(Base):
    __tablename__ = "crop_plantings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_id = Column(String, ForeignKey('farms.id'))
    crop_name = Column(String, nullable=False)
    variety = Column(String)
    planting_date = Column(Date)
    expected_harvest = Column(Date)
    area_planted = Column(Float)
    expected_yield = Column(Float)
    actual_yield = Column(Float)
    status = Column(String, default='planted')
    created_at = Column(DateTime, default=datetime.utcnow)

class Livestock(Base):
    __tablename__ = "livestock"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_id = Column(String, ForeignKey('farms.id'))
    animal_type = Column(String, nullable=False)
    tag_number = Column(String, unique=True)
    breed = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    weight = Column(Float)
    health_status = Column(String, default='healthy')
    created_at = Column(DateTime, default=datetime.utcnow)

# Healthcare & Pharmaceuticals
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    patient_number = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    blood_group = Column(String)
    allergies = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    patient_id = Column(String, ForeignKey('patients.id'))
    doctor_name = Column(String)
    appointment_date = Column(DateTime)
    reason = Column(Text)
    status = Column(String, default='scheduled')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Retail & POS
class Store(Base):
    __tablename__ = "stores"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    store_code = Column(String, nullable=False)
    store_name = Column(String, nullable=False)
    location = Column(String)
    phone = Column(String)
    manager_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class POSSale(Base):
    __tablename__ = "pos_sales"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    store_id = Column(String, ForeignKey('stores.id'))
    receipt_number = Column(String, unique=True, nullable=False)
    sale_date = Column(DateTime, default=datetime.utcnow)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    payment_method = Column(String)
    cashier_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Education
class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    student_number = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String)
    grade_level = Column(String)
    enrollment_date = Column(Date)
    guardian_name = Column(String)
    guardian_phone = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

# Transport & Logistics
class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    registration_number = Column(String, unique=True, nullable=False)
    vehicle_type = Column(String)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    capacity = Column(Float)
    fuel_type = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    vehicle_id = Column(String, ForeignKey('vehicles.id'))
    trip_number = Column(String, nullable=False)
    driver_name = Column(String)
    origin = Column(String)
    destination = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    distance_km = Column(Float)
    freight_charges = Column(Float)
    status = Column(String, default='scheduled')
    created_at = Column(DateTime, default=datetime.utcnow)

# Hospitality
class Room(Base):
    __tablename__ = "hotel_rooms"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    room_number = Column(String, nullable=False)
    room_type = Column(String)
    capacity = Column(Integer)
    rate_per_night = Column(Float)
    floor = Column(Integer)
    status = Column(String, default='available')
    created_at = Column(DateTime, default=datetime.utcnow)

class Reservation(Base):
    __tablename__ = "reservations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    room_id = Column(String, ForeignKey('hotel_rooms.id'))
    guest_name = Column(String, nullable=False)
    guest_phone = Column(String)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    total_amount = Column(Float)
    status = Column(String, default='confirmed')
    created_at = Column(DateTime, default=datetime.utcnow)
