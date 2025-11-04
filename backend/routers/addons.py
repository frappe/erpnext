from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Addon, CompanyAddon
import schemas
from auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/addons", tags=["addons"])

# Seed official addons
OFFICIAL_ADDONS = [
    {
        "addon_code": "construction",
        "addon_name": "Construction & Real Estate",
        "category": "Industry",
        "description": "Project management, job costing, BOQ, contractor management",
        "icon": "🏗️",
        "pricing_model": "per_user",
        "monthly_price": 50.0,
        "features": "Project & Job Costing, Bill of Quantities, Procurement Tracking, Contractor Management"
    },
    {
        "addon_code": "agriculture",
        "addon_name": "Agriculture & Agribusiness",
        "category": "Industry",
        "description": "Farm management, crop planning, livestock tracking",
        "icon": "🌾",
        "pricing_model": "per_user",
        "monthly_price": 40.0,
        "features": "Crop Planning, Livestock Management, Harvest Tracking, Farm Equipment"
    },
    {
        "addon_code": "healthcare",
        "addon_name": "Healthcare & Pharmaceuticals",
        "category": "Industry",
        "description": "Patient records, appointments, pharmacy, billing",
        "icon": "🏥",
        "pricing_model": "per_user",
        "monthly_price": 70.0,
        "features": "Patient EMR, Appointments, Pharmacy Inventory, Insurance Claims"
    },
    {
        "addon_code": "retail",
        "addon_name": "Retail, Wholesale & POS",
        "category": "Industry",
        "description": "Point of sale, inventory, multi-store management",
        "icon": "🏪",
        "pricing_model": "per_store",
        "monthly_price": 30.0,
        "features": "POS System, Multi-branch, Loyalty Programs, E-Commerce Sync"
    },
    {
        "addon_code": "education",
        "addon_name": "Education & Training",
        "category": "Industry",
        "description": "Student records, timetables, fee management, academic tracking",
        "icon": "🏫",
        "pricing_model": "per_student",
        "monthly_price": 5.0,
        "features": "Student Enrollment, Attendance, Fee Invoicing, Academic Performance"
    },
    {
        "addon_code": "transport",
        "addon_name": "Transport & Logistics",
        "category": "Industry",
        "description": "Fleet management, route planning, maintenance tracking",
        "icon": "🚚",
        "pricing_model": "per_vehicle",
        "monthly_price": 25.0,
        "features": "Fleet Management, Route Planning, Fuel Tracking, GPS Integration"
    },
    {
        "addon_code": "hospitality",
        "addon_name": "Hospitality & Restaurants",
        "category": "Industry",
        "description": "Room bookings, restaurant POS, kitchen inventory",
        "icon": "🍽️",
        "pricing_model": "per_room",
        "monthly_price": 20.0,
        "features": "Reservation Management, Housekeeping, Restaurant POS, Event Management"
    },
    {
        "addon_code": "realestate",
        "addon_name": "Real Estate Development",
        "category": "Industry",
        "description": "Property management, lease tracking, tenant management",
        "icon": "🏘️",
        "pricing_model": "per_property",
        "monthly_price": 35.0,
        "features": "Property Portfolio, Lease Agreements, Tenant Management, Maintenance Scheduling"
    },
    {
        "addon_code": "legal",
        "addon_name": "Legal Practice Management",
        "category": "Industry",
        "description": "Case management, legal documents, client billing, court tracking",
        "icon": "⚖️",
        "pricing_model": "per_user",
        "monthly_price": 60.0,
        "features": "Case Management, Document Library, Time & Billing, Court Calendar"
    },
    {
        "addon_code": "ngo",
        "addon_name": "NGO & Non-Profit",
        "category": "Industry",
        "description": "Grant management, donor tracking, project monitoring",
        "icon": "🕊️",
        "pricing_model": "per_project",
        "monthly_price": 35.0,
        "features": "Donor Management, Grant Budgeting, Project Tracking, Compliance Reporting"
    },
    {
        "addon_code": "advmanufacturing",
        "addon_name": "Advanced Manufacturing",
        "category": "Industry",
        "description": "Production orders, quality control, shop floor management",
        "icon": "🏭",
        "pricing_model": "per_user",
        "monthly_price": 60.0,
        "features": "Work Orders, Shop Floor Control, Machine Maintenance, Quality Assurance"
    },
    {
        "addon_code": "logistics",
        "addon_name": "Logistics & Warehousing",
        "category": "Industry",
        "description": "Warehouse management, shipment tracking, inventory optimization",
        "icon": "📦",
        "pricing_model": "per_warehouse",
        "monthly_price": 45.0,
        "features": "Warehouse Management, Shipment Tracking, Inventory Optimization, 3PL Integration"
    },
    {
        "addon_code": "telecom",
        "addon_name": "Telecommunications",
        "category": "Industry",
        "description": "Subscriber management, billing, network resources",
        "icon": "🌐",
        "pricing_model": "enterprise",
        "monthly_price": 250.0,
        "features": "Customer Onboarding, Plan Management, Usage Billing, Tower Maintenance"
    },
    {
        "addon_code": "energy",
        "addon_name": "Energy & Utilities",
        "category": "Industry",
        "description": "Meter management, consumption billing, outage scheduling",
        "icon": "💡",
        "pricing_model": "per_customer",
        "monthly_price": 2.0,
        "features": "Meter Reading, Billing & Collections, Outage Management, Asset Lifecycle"
    },
    {
        "addon_code": "media",
        "addon_name": "Media & Publishing",
        "category": "Industry",
        "description": "Content management, publication scheduling, subscription tracking",
        "icon": "📰",
        "pricing_model": "per_user",
        "monthly_price": 40.0,
        "features": "Content Management, Editorial Calendar, Subscriptions, Ad Management"
    },
    {
        "addon_code": "insurance",
        "addon_name": "Insurance & Underwriting",
        "category": "Industry",
        "description": "Policy management, claims processing, agent commissions",
        "icon": "💰",
        "pricing_model": "per_user",
        "monthly_price": 80.0,
        "features": "Policy Administration, Claims Processing, Agent Management, Premium Billing"
    },
    {
        "addon_code": "government",
        "addon_name": "Government & Public Sector",
        "category": "Industry",
        "description": "Permit management, public services, budget tracking",
        "icon": "🏛️",
        "pricing_model": "enterprise",
        "monthly_price": 150.0,
        "features": "Permit Management, Public Services, Departmental Budgeting, Procurement Compliance"
    }
]

@router.get("/marketplace")
async def get_addon_marketplace(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all available addons in the marketplace"""
    addons = db.query(Addon).filter(Addon.is_official == True).all()
    
    # Seed if empty
    if not addons:
        for addon_data in OFFICIAL_ADDONS:
            addon = Addon(**addon_data)
            db.add(addon)
        db.commit()
        addons = db.query(Addon).all()
    
    return addons

@router.get("/my-addons", response_model=List[dict])
async def get_my_addons(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get addons activated for current company"""
    company_addons = db.query(CompanyAddon).filter(
        CompanyAddon.company_id == current_user.company_id,
        CompanyAddon.is_active == True
    ).all()
    
    result = []
    for ca in company_addons:
        addon = db.query(Addon).filter(Addon.id == ca.addon_id).first()
        if addon:
            result.append({
                "id": ca.id,
                "addon": addon,
                "activated_at": ca.activated_at,
                "settings": ca.settings
            })
    
    return result

@router.post("/activate/{addon_code}")
async def activate_addon(
    addon_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Activate an addon for the company"""
    addon = db.query(Addon).filter(Addon.addon_code == addon_code).first()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    # Check if already activated
    existing = db.query(CompanyAddon).filter(
        CompanyAddon.company_id == current_user.company_id,
        CompanyAddon.addon_id == addon.id,
        CompanyAddon.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Addon already activated")
    
    company_addon = CompanyAddon(
        company_id=current_user.company_id,
        addon_id=addon.id,
        is_active=True
    )
    db.add(company_addon)
    db.commit()
    
    return {"message": f"{addon.addon_name} activated successfully", "addon": addon}

@router.post("/deactivate/{addon_code}")
async def deactivate_addon(
    addon_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Deactivate an addon for the company"""
    addon = db.query(Addon).filter(Addon.addon_code == addon_code).first()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    company_addon = db.query(CompanyAddon).filter(
        CompanyAddon.company_id == current_user.company_id,
        CompanyAddon.addon_id == addon.id,
        CompanyAddon.is_active == True
    ).first()
    
    if not company_addon:
        raise HTTPException(status_code=404, detail="Addon not activated")
    
    company_addon.is_active = False
    company_addon.deactivated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"{addon.addon_name} deactivated successfully"}
