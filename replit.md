# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview
ERIK ERP is a comprehensive, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. It aims to be a leading ERP solution, initially targeting Zambian businesses with ambitions for global expansion. Key capabilities include multi-currency support, bank reconciliation, smart invoice compliance, a universal production engine, and AI-driven business insights and OCR document intelligence. The project envisions a multi-tier SaaS business model (Free, Basic, Premium, Enterprise) to compete with established ERP providers like Odoo and SAP.

## User Preferences
- **Primary Color**: Teal/Green (#00D9A3) as shown in ERIK logo
- **Goal**: Build a comprehensive ERP to compete with Odoo and SAP
- **Target Market**: Initially Zambian businesses, expandable globally
- **Business Model**: Multi-tier SaaS (Free, Basic, Premium, Enterprise)

## System Architecture

### Core Features
- **Multi-Tenant SaaS Architecture**: Isolated data, secure JWT authentication, Role-Based Access Control (RBAC), company registration with automatic setup, and company-scoped data validation.
- **Financial Management**: Chart of Accounts, double-entry Journal Entries, Financial Reports (P&L, Balance Sheet, Cash Flow), multi-currency support, FX gain/loss, bank reconciliation, fixed assets, and accounting period management.
- **HR & Payroll**: Employee Management (with Zambian compliance fields), Zambian Payroll Engine (2025 rates for PAYE, NAPSA, NHIMA, Workers Comp), automated payslips, Leave Management, employment contracts, and statutory compliance tracking.
- **Inventory & Operations**: Product catalog, multi-location warehouses, real-time stock, stock movement, universal production engine, batch/serial tracking, FEFO logic, landed cost allocation, and transfer pricing.
- **Sales & Procurement**: Customer/Supplier Management, multi-line Sales Orders and Purchase Orders.
- **Compliance & Intelligence**: Statutory Obligations Dashboard (ZRA integration readiness), Smart Invoice Compliance (QR, UBL, ZRA validation), Claude AI Assistant for insights, and OCR for document processing.
- **System Management**: Configurable settings, notifications, and Audit Trail.
- **Mobile Money & POS Integration**: Management of MTN Money, Airtel Money, Zamtel Kwacha for payments, transaction tracking, reconciliation, and a Point of Sale system.
- **Multi-Branch Operations**: Branch creation, inter-branch transfers, and branch-level reporting.
- **Super Admin Platform**: Tenant management, subscription control, system analytics, and 7-day free trial.
- **Dashboard**: Real-time statistics and company activity overview.
- **Addon Marketplace**: Industry-specific modules that can be activated/deactivated per tenant, including Construction, Healthcare, Agriculture, Retail, Education, Transport, Hospitality, Real Estate, Legal, NGO, Manufacturing, Logistics, Telecom, Energy, Media, Insurance, and Government sectors.

### UI/UX
- **Modern Design**: Responsive landing page with a professional aesthetic.
- **Theming**: Dark theme with ERIK teal/green branding (#00D9A3), gradient backgrounds, and glassmorphic cards.
- **Navigation**: Organized sidebar navigation for all modules.

### Technical Implementation
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, JWT authentication (bcrypt), RESTful API with OpenAPI/Swagger.
- **Frontend**: React 18 (Vite), React Router v6, Tailwind CSS (custom ERIK theme), Lucide React icons, Axios.
- **Database**: PostgreSQL.

## Recent Updates (November 4, 2025)

### Latest Enhancements (Evening Session)
**Addon Marketplace Full Integration:**
- Updated OFFICIAL_ADDONS list to include all 17 industry modules with proper addon codes
- Fixed addon seeding mechanism to display all modules in marketplace
- Enhanced addon card designs with beautiful gradients and icons
- Cleared addons table to force reseed with complete module set

**Comprehensive Dashboard Upgrade:**
- Expanded dashboard with 14+ real-time statistics including:
  - Core: Employees, Departments, Chart of Accounts, Journal Entries
  - Inventory: Products, Warehouses
  - Sales & Procurement: Sales Orders, Purchase Orders, Customers, Suppliers
  - HR: Payslips Generated
  - Banking: Bank Accounts
  - Addons: Active Addons count
  - Subscription: Plan and Status display
- Fixed database query errors by using .id selection instead of full model queries
- Beautiful gradient card designs with color-coded categories
- Added System Status, Quick Actions, and Recent Activity cards
- Responsive grid layout (1-5 columns depending on screen size)
- Hover animations and glassmorphic effects

**ALL 17 INDUSTRY MODULES COMPLETED:**
1. **Construction & Real Estate** (🏗️) - Project management, Bill of Quantities
2. **Agriculture & Agribusiness** (🌾) - Farm management, Crop planning, Livestock tracking
3. **Healthcare & Pharmaceuticals** (🏥) - Patient management, Appointment scheduling
4. **Retail, Wholesale & POS** (🏪) - Store management, POS sales tracking
5. **Education & Training** (🏫) - Student information system, Enrollment management
6. **Transport & Logistics** (🚚) - Vehicle fleet, Trip management
7. **Hospitality & Restaurants** (🍽️) - Room management, Hotel reservations
8. **Real Estate Development** (🏘️) - Property management, Lease tracking
9. **Legal Practice Management** (⚖️) - Case management, Legal documents
10. **NGO & Non-Profit** (🕊️) - Donor management, Grant tracking
11. **Advanced Manufacturing** (🏭) - Production orders, Quality control
12. **Logistics & Warehousing** (📦) - Warehouse management, Shipment tracking
13. **Telecommunications** (🌐) - Subscriber management, Telecom plans
14. **Energy & Utilities** (💡) - Meter management, Consumption tracking
15. **Media & Publishing** (📰) - Content management, Publications
16. **Insurance & Underwriting** (💰) - Policy management, Claims processing
17. **Government & Public Sector** (🏛️) - Permit management, Public services

**Technical Features:**
- Backend API with activation/deactivation endpoints
- Beautiful frontend Addon Store UI with card-based layout
- Per-tenant addon management with activation tracking
- Full CRUD operations for all 17 industry modules
- Integrated into main navigation sidebar
- Database models and schemas for all modules
- Dedicated routers for each industry sector
- Multi-tenant isolation with company_id scoping
- Comprehensive dashboard backend API with 13+ metrics
- Fixed database query performance issues

**Login Credentials:**
- Super Admin: admin@erikerp.com / SuperAdmin2025!
- Tenant Account: nabaloans@gmail.com / Tenant2025! (Company: NABA CENTRAL)

## External Dependencies
- **Database**: PostgreSQL
- **Frontend Libraries**: React, Vite, React Router, Tailwind CSS, Lucide React, Axios, Recharts
- **Backend Libraries**: FastAPI, SQLAlchemy, bcrypt, cryptography (Fernet encryption), python-dateutil
- **AI/OCR**: Anthropic Claude AI (for assistant and vision)
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha
- **Banking APIs**: ZANACO, ABSA Bank Zambia, FNB Zambia, Stanbic Bank Zambia