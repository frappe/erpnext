# 📂 ERIK ERP - Complete Project Structure

**Detailed breakdown of every file and folder in the ERIK ERP codebase**

---

## 📖 Table of Contents

1. [Root Directory](#root-directory)
2. [Backend Structure](#backend-structure)
3. [Frontend Structure](#frontend-structure)
4. [Configuration Files](#configuration-files)
5. [Documentation Files](#documentation-files)

---

## 🌲 Complete Directory Tree

```
erik-erp/
├── attached_assets/              # Stock images and media assets
├── backend/                      # FastAPI backend application
│   ├── routers/                  # API endpoint modules
│   │   ├── __init__.py
│   │   ├── addons.py            # Addon marketplace API
│   │   ├── advmanufacturing.py  # Advanced manufacturing addon
│   │   ├── agriculture.py        # Agriculture addon
│   │   ├── bank_connections.py   # Bank connection management
│   │   ├── banking.py            # Banking operations
│   │   ├── chat.py               # AI assistant chat
│   │   ├── compliance.py         # Statutory compliance
│   │   ├── construction.py       # Construction addon
│   │   ├── education.py          # Education addon
│   │   ├── employees.py          # Employee management
│   │   ├── energy.py             # Energy addon
│   │   ├── finance.py            # Finance & accounting
│   │   ├── government.py         # Government addon
│   │   ├── healthcare.py         # Healthcare addon
│   │   ├── hospitality.py        # Hospitality addon
│   │   ├── insurance.py          # Insurance addon
│   │   ├── inventory.py          # Inventory management
│   │   ├── legal.py              # Legal addon
│   │   ├── logistics.py          # Logistics addon
│   │   ├── manufacturing.py      # Manufacturing
│   │   ├── media.py              # Media addon
│   │   ├── ngo.py                # NGO addon
│   │   ├── ocr.py                # OCR processing
│   │   ├── payroll.py            # Payroll processing
│   │   ├── procurement.py        # Purchase orders & suppliers
│   │   ├── realestate.py         # Real estate addon
│   │   ├── retail.py             # Retail addon
│   │   ├── sales.py              # Sales orders & customers
│   │   ├── super_admin.py        # Tenant management
│   │   ├── tax.py                # Tax management
│   │   ├── telecom.py            # Telecom addon
│   │   └── transport.py          # Transport addon
│   ├── services/                 # Business logic layer
│   │   ├── banking/              # Bank integrations
│   │   │   ├── __init__.py
│   │   │   ├── absa_integration.py          # ABSA Bank API
│   │   │   ├── atlas_mara_integration.py    # Atlas Mara Bank API
│   │   │   ├── auto_posting_service.py      # Auto bank posting
│   │   │   ├── bank_factory.py              # Bank provider factory
│   │   │   ├── bank_sync_service.py         # Bank sync service
│   │   │   ├── base_bank_integration.py     # Base bank class
│   │   │   ├── fnb_integration.py           # FNB Bank API
│   │   │   ├── reconciliation_engine.py     # Auto reconciliation
│   │   │   ├── stanbic_integration.py       # Stanbic Bank API
│   │   │   └── zanaco_integration.py        # ZANACO Bank API
│   │   ├── compliance/           # Compliance services
│   │   │   ├── __init__.py
│   │   │   └── statutory_compliance.py      # ZRA, NAPSA, NHIMA
│   │   ├── finance/              # Finance services
│   │   │   └── __init__.py
│   │   ├── inventory/            # Inventory services
│   │   │   ├── __init__.py
│   │   │   ├── advanced_inventory.py        # Advanced features
│   │   │   └── landed_cost_service.py       # Landed cost allocation
│   │   ├── manufacturing/        # Manufacturing services
│   │   │   ├── __init__.py
│   │   │   ├── costing_engine.py            # Product costing
│   │   │   └── production_workflow.py       # Production flow
│   │   ├── mobile_money/         # Mobile money integrations
│   │   │   ├── __init__.py
│   │   │   ├── airtel_integration.py        # Airtel Money API
│   │   │   ├── base_mobile_money.py         # Base MM class
│   │   │   ├── mtn_integration.py           # MTN Money API
│   │   │   └── zamtel_integration.py        # Zamtel Kwacha API
│   │   ├── payroll/              # Payroll services
│   │   │   ├── __init__.py
│   │   │   └── zambian_payroll_engine.py    # PAYE, NAPSA, NHIMA
│   │   ├── reporting/            # Reporting services
│   │   │   ├── __init__.py
│   │   │   └── consolidation_engine.py      # Multi-branch consolidation
│   │   ├── __init__.py
│   │   └── ocr_service.py        # OCR document processing
│   ├── ai_assistant.py           # Claude AI integration
│   ├── audit_logger.py           # Audit trail service
│   ├── auth.py                   # JWT authentication
│   ├── banking_service.py        # Banking facade service
│   ├── database.py               # Database connection & session
│   ├── main.py                   # Main FastAPI app
│   ├── migrations.py             # Database migration utilities
│   ├── models.py                 # SQLAlchemy ORM models (ALL models)
│   ├── notification_service.py   # Notification system
│   ├── ocr_service.py            # OCR service wrapper
│   ├── requirements.txt          # Python dependencies
│   ├── sample_data_generator.py  # Demo data generator
│   ├── scheduled_jobs.py         # Background jobs (APScheduler)
│   ├── schemas.py                # Pydantic schemas (ALL schemas)
│   ├── smart_invoice.py          # Smart invoice compliance
│   └── utils.py                  # Helper utilities
├── frontend/                     # React frontend application
│   ├── public/                   # Static assets
│   │   └── assets/
│   │       └── erik-logo.png    # ERIK branding
│   ├── src/                      # React source code
│   │   ├── assets/               # Frontend assets
│   │   ├── components/           # Reusable React components
│   │   │   ├── Banking/          # Banking components
│   │   │   ├── DisclaimerModal.jsx
│   │   │   ├── Layout.jsx        # Main layout with sidebar
│   │   │   └── NotificationCenter.jsx
│   │   ├── pages/                # Page components (routes)
│   │   │   ├── Banking/          # Banking pages
│   │   │   │   ├── BankConnections.jsx
│   │   │   │   ├── ReconciliationDashboard.jsx
│   │   │   │   └── TransactionFeed.jsx
│   │   │   ├── Accounts.jsx      # Chart of accounts
│   │   │   ├── AddonStore.jsx    # Addon marketplace
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── AIAssistant.jsx   # Claude AI chat
│   │   │   ├── AuditTrail.jsx    # Audit logs
│   │   │   ├── BankReconciliation.jsx
│   │   │   ├── Branches.jsx      # Branch management
│   │   │   ├── Compliance.jsx    # Statutory compliance
│   │   │   ├── ConsolidatedReports.jsx
│   │   │   ├── CustomerManagement.jsx
│   │   │   ├── Customers.jsx
│   │   │   ├── Dashboard.jsx     # Main dashboard (14+ metrics)
│   │   │   ├── Departments.jsx   # Department management
│   │   │   ├── Employees.jsx     # Employee list/CRUD
│   │   │   ├── InventoryDashboard.jsx
│   │   │   ├── Journals.jsx      # Journal entries
│   │   │   ├── Landing.jsx       # Landing page
│   │   │   ├── Leave.jsx         # Leave management
│   │   │   ├── Login.jsx         # Login page
│   │   │   ├── ManufacturingDashboard.jsx
│   │   │   ├── MobileMoney.jsx   # Mobile money management
│   │   │   ├── OCRUpload.jsx     # OCR document upload
│   │   │   ├── Payroll.jsx       # Payroll processing
│   │   │   ├── POS.jsx           # Point of sale
│   │   │   ├── ProductCatalog.jsx
│   │   │   ├── Products.jsx      # Product list/CRUD
│   │   │   ├── PurchaseOrders.jsx
│   │   │   ├── Register.jsx      # Company registration
│   │   │   ├── Reports.jsx       # Financial reports
│   │   │   ├── SalesOrders.jsx
│   │   │   ├── SecuritySettings.jsx
│   │   │   ├── Settings.jsx      # System settings
│   │   │   ├── StatutoryObligations.jsx
│   │   │   ├── SuperAdmin.jsx    # Tenant management
│   │   │   ├── SupplierManagement.jsx
│   │   │   ├── Suppliers.jsx
│   │   │   └── TaxDashboard.jsx
│   │   ├── services/             # Frontend services
│   │   │   └── api.js            # Axios HTTP client
│   │   ├── styles/               # CSS styles
│   │   │   └── index.css         # Tailwind + custom CSS
│   │   ├── App.jsx               # Main app component with routing
│   │   └── main.jsx              # React entry point
│   ├── index.html                # HTML template
│   ├── package-lock.json         # Locked dependencies
│   ├── package.json              # Node.js dependencies
│   ├── postcss.config.js         # PostCSS configuration
│   ├── tailwind.config.js        # Tailwind CSS theme (ERIK colors)
│   └── vite.config.js            # Vite build configuration
├── .replit                       # Replit configuration
├── API_DOCUMENTATION.md          # API endpoint reference
├── ARCHITECTURE_GAP_ANALYSIS.md  # Architecture analysis
├── attributions.md               # Third-party attributions
├── build.sh                      # Build script
├── DEPLOYMENT.md                 # Deployment guide
├── DEVELOPER_GUIDE.md            # Developer documentation
├── GAP_ANALYSIS.md               # Gap analysis
├── license.txt                   # License
├── main.py                       # Root main file (symlink)
├── PROJECT_STRUCTURE.md          # This file
├── pyproject.toml                # Python project config (uv)
├── README.md                     # Main README
├── replit.md                     # Replit project documentation
└── uv.lock                       # UV package manager lock file
```

---

## 📁 Root Directory

### Configuration Files

| File | Purpose |
|------|---------|
| `.replit` | Replit environment configuration (workflows, ports, deployment) |
| `pyproject.toml` | Python project metadata (for uv package manager) |
| `uv.lock` | Locked Python dependencies (uv) |
| `build.sh` | Build script for deployment |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project README with overview and quick start |
| `DEVELOPER_GUIDE.md` | Comprehensive developer documentation |
| `PROJECT_STRUCTURE.md` | This file - complete project structure breakdown |
| `API_DOCUMENTATION.md` | API endpoint reference |
| `DEPLOYMENT.md` | Production deployment guide |
| `replit.md` | Replit-specific project documentation |
| `ARCHITECTURE_GAP_ANALYSIS.md` | Architecture analysis document |
| `GAP_ANALYSIS.md` | Feature gap analysis |
| `attributions.md` | Third-party library attributions |
| `license.txt` | Software license |

---

## 🐍 Backend Structure

### Core Files

#### `main.py`
**Purpose**: Main FastAPI application initialization

**Responsibilities**:
- Create FastAPI app instance
- Configure CORS middleware
- Register all routers
- Initialize database on startup
- Serve React frontend in production
- Health check endpoints

**Key Code**:
```python
app = FastAPI(title="ERIK ERP API")

# CORS configuration
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Register routers
app.include_router(finance.router)
app.include_router(employees.router)
# ... all other routers

# Startup event
@app.on_event("startup")
def startup_event():
    init_db()  # Create tables
```

---

#### `models.py`
**Purpose**: All SQLAlchemy database models in one file

**Contains** (100+ models):
- `Company` - Multi-tenant companies
- `User` - Authentication users
- `Employee` - HR employee records
- `Department` - Organizational departments
- `Branch` - Multi-branch locations
- `Account` - Chart of accounts
- `JournalEntry` - Journal entries
- `JournalLine` - Journal entry lines
- `Product` - Product catalog
- `Warehouse` - Warehouse locations
- `StockMovement` - Inventory movements
- `SalesOrder` - Sales orders
- `PurchaseOrder` - Purchase orders
- `Customer` - Customer master
- `Supplier` - Supplier master
- `Payslip` - Payroll payslips
- `LeaveRequest` - Leave management
- `BankConnection` - Bank integrations
- `MobileMoneyProvider` - Mobile money providers
- `ProductionOrder` - Manufacturing orders
- `BillOfMaterials` - BOM
- `Addon` - Addon marketplace
- `CompanyAddon` - Activated addons per company
- 17 addon-specific models (ConstructionProject, Farm, Patient, etc.)

---

#### `schemas.py`
**Purpose**: All Pydantic request/response schemas

**Contains** (200+ schemas):
- `UserCreate`, `UserResponse`
- `EmployeeCreate`, `EmployeeResponse`
- `AccountCreate`, `AccountResponse`
- `JournalEntryCreate`, `JournalEntryResponse`
- `ProductCreate`, `ProductResponse`
- And many more for all models

---

#### `auth.py`
**Purpose**: JWT authentication utilities

**Key Functions**:
- `create_access_token()` - Generate JWT
- `verify_token()` - Validate JWT
- `get_current_user()` - Extract user from JWT
- Password hashing with bcrypt

---

#### `database.py`
**Purpose**: Database connection and session management

**Key Code**:
```python
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Routers (API Endpoints)

Each router file handles a specific module:

| Router File | API Prefix | Purpose |
|------------|------------|---------|
| `addons.py` | `/api/addons` | Addon marketplace CRUD |
| `finance.py` | `/api/finance` | Accounts, journals, reports |
| `employees.py` | `/api/employees` | Employee management |
| `payroll.py` | `/api/payroll` | Payroll processing |
| `inventory.py` | `/api/inventory` | Products, warehouses, stock |
| `sales.py` | `/api/sales` | Sales orders, customers |
| `procurement.py` | `/api/procurement` | Purchase orders, suppliers |
| `manufacturing.py` | `/api/manufacturing` | Production, BOM |
| `banking.py` | `/api/banking` | Banking operations |
| `compliance.py` | `/api/compliance` | Statutory obligations |
| `super_admin.py` | `/api/super-admin` | Tenant management |
| `chat.py` | `/api/chat` | AI assistant |
| `ocr.py` | `/api/ocr` | OCR processing |

**17 Addon Routers**:
- `construction.py` - `/api/construction`
- `agriculture.py` - `/api/agriculture`
- `healthcare.py` - `/api/healthcare`
- `retail.py` - `/api/retail`
- `education.py` - `/api/education`
- `transport.py` - `/api/transport`
- `hospitality.py` - `/api/hospitality`
- `realestate.py` - `/api/realestate`
- `legal.py` - `/api/legal`
- `ngo.py` - `/api/ngo`
- `advmanufacturing.py` - `/api/advmanufacturing`
- `logistics.py` - `/api/logistics`
- `telecom.py` - `/api/telecom`
- `energy.py` - `/api/energy`
- `media.py` - `/api/media`
- `insurance.py` - `/api/insurance`
- `government.py` - `/api/government`

---

### Services (Business Logic)

#### Banking Services (`services/banking/`)

| File | Purpose |
|------|---------|
| `base_bank_integration.py` | Abstract base class for all banks |
| `zanaco_integration.py` | ZANACO Bank API integration |
| `absa_integration.py` | ABSA Bank API integration |
| `fnb_integration.py` | FNB Bank API integration |
| `stanbic_integration.py` | Stanbic Bank API integration |
| `bank_factory.py` | Factory pattern for bank selection |
| `bank_sync_service.py` | Automated bank sync |
| `reconciliation_engine.py` | ML-powered auto-matching |
| `auto_posting_service.py` | Auto-post bank transactions to GL |

#### Mobile Money Services (`services/mobile_money/`)

| File | Purpose |
|------|---------|
| `base_mobile_money.py` | Abstract base class |
| `mtn_integration.py` | MTN Money API |
| `airtel_integration.py` | Airtel Money API |
| `zamtel_integration.py` | Zamtel Kwacha API |

#### Payroll Services (`services/payroll/`)

| File | Purpose |
|------|---------|
| `zambian_payroll_engine.py` | PAYE, NAPSA, NHIMA calculations (2025 rates) |

#### Inventory Services (`services/inventory/`)

| File | Purpose |
|------|---------|
| `advanced_inventory.py` | FEFO, batch tracking, serial numbers |
| `landed_cost_service.py` | Freight, customs, insurance allocation |

#### Manufacturing Services (`services/manufacturing/`)

| File | Purpose |
|------|---------|
| `production_workflow.py` | Raw → WIP → Finished goods flow |
| `costing_engine.py` | Standard, average, FIFO costing |

#### Compliance Services (`services/compliance/`)

| File | Purpose |
|------|---------|
| `statutory_compliance.py` | ZRA, NAPSA, NHIMA tracking |

#### Reporting Services (`services/reporting/`)

| File | Purpose |
|------|---------|
| `consolidation_engine.py` | Multi-branch P&L and Balance Sheet consolidation |

---

### Utilities

| File | Purpose |
|------|---------|
| `ai_assistant.py` | Claude AI integration for business insights |
| `ocr_service.py` | OCR document processing with Claude Vision |
| `notification_service.py` | Email, SMS, in-app notifications |
| `audit_logger.py` | Comprehensive audit trail logging |
| `smart_invoice.py` | QR code, UBL export, ZRA compliance |
| `banking_service.py` | Facade for banking integrations |
| `scheduled_jobs.py` | Background jobs (APScheduler) |
| `sample_data_generator.py` | Generate demo data for testing |
| `migrations.py` | Database migration utilities |
| `utils.py` | Helper functions (UUID generation, etc.) |

---

## ⚛️ Frontend Structure

### Core Files

#### `main.jsx`
**Purpose**: React application entry point

**Responsibilities**:
- Render React app into DOM
- Wrap app with React Router

---

#### `App.jsx`
**Purpose**: Main app component with routing

**Responsibilities**:
- Define all routes
- Wrap authenticated routes with Layout
- Handle public routes (Landing, Login, Register)

**Key Routes**:
```jsx
<Routes>
  <Route path="/" element={<Landing />} />
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  
  {/* Authenticated routes */}
  <Route element={<Layout />}>
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/employees" element={<Employees />} />
    <Route path="/addon-store" element={<AddonStore />} />
    {/* ... 40+ more routes */}
  </Route>
</Routes>
```

---

### Components

#### `Layout.jsx`
**Purpose**: Main application layout with sidebar navigation

**Features**:
- Sidebar with all navigation links
- Top bar with notifications and user menu
- Content area (Outlet for child routes)
- Responsive design (mobile drawer)

---

#### `NotificationCenter.jsx`
**Purpose**: Real-time notification center

**Features**:
- Unread notification count badge
- Dropdown with notification list
- Mark as read functionality

---

#### `DisclaimerModal.jsx`
**Purpose**: Legal disclaimer modal

---

### Pages

All page components in `pages/` directory:

| Page File | Route | Purpose |
|-----------|-------|---------|
| `Landing.jsx` | `/` | Landing page with sign-up |
| `Login.jsx` | `/login` | User login |
| `Register.jsx` | `/register` | Company registration |
| `Dashboard.jsx` | `/dashboard` | Main dashboard (14+ metrics) |
| `AddonStore.jsx` | `/addon-store` | Addon marketplace |
| `Employees.jsx` | `/employees` | Employee list/CRUD |
| `Payroll.jsx` | `/payroll` | Payroll processing |
| `Departments.jsx` | `/departments` | Department management |
| `Branches.jsx` | `/branches` | Branch management |
| `Leave.jsx` | `/leave` | Leave requests |
| `Accounts.jsx` | `/finance/chart-of-accounts` | Chart of accounts |
| `Journals.jsx` | `/finance/journal-entries` | Journal entries |
| `Reports.jsx` | `/finance/reports` | Financial reports |
| `Products.jsx` | `/inventory/products` | Product catalog |
| `ProductCatalog.jsx` | `/inventory/catalog` | Product catalog view |
| `InventoryDashboard.jsx` | `/inventory/dashboard` | Inventory overview |
| `SalesOrders.jsx` | `/sales/orders` | Sales order management |
| `Customers.jsx` | `/sales/customers` | Customer management |
| `PurchaseOrders.jsx` | `/procurement/orders` | Purchase orders |
| `Suppliers.jsx` | `/procurement/suppliers` | Supplier management |
| `ManufacturingDashboard.jsx` | `/manufacturing` | Manufacturing overview |
| `BankReconciliation.jsx` | `/banking/reconciliation` | Bank reconciliation |
| `MobileMoney.jsx` | `/mobile-money` | Mobile money management |
| `POS.jsx` | `/pos` | Point of sale |
| `Compliance.jsx` | `/compliance` | Statutory obligations |
| `StatutoryObligations.jsx` | `/compliance/obligations` | PAYE, NAPSA, NHIMA |
| `TaxDashboard.jsx` | `/tax` | Tax dashboard |
| `AIAssistant.jsx` | `/ai-assistant` | Claude AI chat |
| `OCRUpload.jsx` | `/ocr` | OCR document upload |
| `AuditTrail.jsx` | `/audit-trail` | Audit logs |
| `Settings.jsx` | `/settings` | System settings |
| `SecuritySettings.jsx` | `/security` | Security settings |
| `SuperAdmin.jsx` | `/super-admin` | Tenant management (super admin) |

---

### Services

#### `api.js`
**Purpose**: Centralized Axios HTTP client

**Features**:
- Base URL configuration
- JWT token injection
- 401 error handling (redirect to login)
- Interceptors for auth

---

### Styles

#### `index.css`
**Purpose**: Tailwind CSS + custom styles

**Includes**:
- Tailwind directives
- Custom ERIK theme colors (#00D9A3)
- Global styles
- Gradient backgrounds
- Glassmorphic effects

---

### Configuration Files

#### `vite.config.js`
**Purpose**: Vite build configuration

**Features**:
- React plugin
- Proxy configuration (`/api` → `http://localhost:8000`)
- Build output directory
- Development server settings

---

#### `tailwind.config.js`
**Purpose**: Tailwind CSS theme configuration

**Custom Theme**:
```javascript
colors: {
  primary: {
    DEFAULT: '#00D9A3',  // ERIK teal/green
    dark: '#00B388',
    light: '#33E3B8',
  }
}
```

---

#### `postcss.config.js`
**Purpose**: PostCSS configuration for Tailwind

---

## 📋 File Responsibilities Summary

### Backend Files by Responsibility

**API Layer** (26 router files)
- Handle HTTP requests/responses
- Validate input (Pydantic)
- Call business logic (services)
- Return JSON responses

**Business Logic** (services/)
- Complex calculations (payroll, costing)
- External API integrations (banks, mobile money)
- Multi-step workflows (production, reconciliation)

**Data Layer** (models.py, database.py)
- Database models (SQLAlchemy)
- Database connections
- Query composition

**Cross-Cutting Concerns**
- Authentication (auth.py)
- Audit logging (audit_logger.py)
- Notifications (notification_service.py)
- AI/OCR (ai_assistant.py, ocr_service.py)

### Frontend Files by Responsibility

**Routing** (App.jsx)
- Define all application routes
- Protected route wrappers

**Layout** (components/Layout.jsx)
- Sidebar navigation
- Top bar
- Content area

**Pages** (pages/*.jsx)
- UI for specific features
- State management
- API calls via api.js

**Services** (services/api.js)
- HTTP client
- Auth token management
- Error handling

---

## 🔍 Finding Files Quickly

### Need to add a new API endpoint?
→ `backend/routers/` (create new file or add to existing)

### Need to add a new database table?
→ `backend/models.py` (add new model)

### Need to add a new page?
→ `frontend/src/pages/` (create new component)

### Need to modify navigation?
→ `frontend/src/components/Layout.jsx`

### Need to add business logic?
→ `backend/services/` (create service file)

### Need to modify Zambian payroll?
→ `backend/services/payroll/zambian_payroll_engine.py`

### Need to add a bank integration?
→ `backend/services/banking/` (create new integration file)

---

## 📊 File Count Summary

| Category | Count | Location |
|----------|-------|----------|
| **Backend Routers** | 26 | `backend/routers/*.py` |
| **Backend Services** | 20+ | `backend/services/*/*.py` |
| **Frontend Pages** | 40+ | `frontend/src/pages/*.jsx` |
| **Frontend Components** | 5+ | `frontend/src/components/*.jsx` |
| **Database Models** | 100+ | `backend/models.py` |
| **Pydantic Schemas** | 200+ | `backend/schemas.py` |
| **Documentation** | 8 | `*.md` files |

**Total Files**: 300+ files across backend and frontend

---

## 🎯 Key Takeaways

1. **Backend is modular** - Each router handles one module
2. **Services separate business logic** - Thin controllers, fat services
3. **All models in one file** - `models.py` for easy searching
4. **All schemas in one file** - `schemas.py` for consistency
5. **Frontend pages map to routes** - One page per route
6. **Shared API client** - `api.js` handles all HTTP
7. **Multi-tenant everywhere** - `company_id` on every table

---

**For more details, see:**
- [README.md](README.md) - Project overview
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API reference
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

---

*Last updated: November 4, 2025*
