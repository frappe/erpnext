# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview

ERIK ERP is a modern, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. Built with cutting-edge technologies and designed with a sleek teal/green color palette inspired by the ERIK brand.

**Project Status**: Phase 3 Complete - Mobile Money, POS & Multi-Branch ✅

## Vision

To build a comprehensive ERP system that competes with Odoo, SAP, and other enterprise solutions, specifically tailored for businesses in Zambia and beyond. This MVP provides the foundational architecture and core modules that can be expanded into a full-featured enterprise system.

## Current Features (Phase 3 - Operations & Super Admin)

### ✅ Multi-Tenant SaaS Architecture
- Each company has its own isolated data
- Secure user authentication with JWT tokens
- Role-based access control (RBAC)
- Company registration with automatic setup
- **ALL endpoints validate company ownership on foreign keys for complete data isolation**

### ✅ Finance & Accounting Module
- **Chart of Accounts**: Hierarchical account structure (Assets, Liabilities, Equity, Revenue, Expenses)
- **Journal Entries**: Double-entry bookkeeping with debit/credit validation
- **Financial Reports**: 
  - Profit & Loss Statement (Income Statement) with date range filtering
  - Balance Sheet (Assets = Liabilities + Equity) as of specific date
  - Cash Flow Statement (Operating, Investing, Financing activities)
- **Real-time Reporting**: View all financial transactions
- **Multi-currency Support**: Default ZMW (Zambian Kwacha) with extensibility

### ✅ HR & Payroll Module
- **Employee Management**: Complete employee database with personal info, position, department, salary
- **Employment Status Tracking**: Active/Inactive status management
- **Zambian Payroll Engine**: 
  - PAYE tax calculation (progressive brackets: 0%, 20%, 30%, 37.5%)
  - **Statutory Compliance**: PAYE calculated on gross salary minus NAPSA only
  - NAPSA: 5% employee + 5% employer contributions
  - NHIMA: 1% employee + 1% employer contributions
  - Automated payslip generation with all statutory deductions
  - Payslip numbering (PAY-00001, PAY-00002, etc.)
- **Leave Management**:
  - Leave Types (Annual, Sick, Maternity, Paternity, etc.) with day allowances
  - Leave Applications with approval workflow
  - Application numbering (LA-00001, LA-00002, etc.)
  - Leave balance tracking per employee

### ✅ Inventory Management
- **Products**: Complete product catalog with SKU, descriptions, unit pricing
- **Warehouses**: Multi-location inventory tracking across facilities
- **Stock Items**: Real-time stock levels by warehouse and product combination
- **Stock Movements**: Track all inventory transactions and adjustments

### ✅ Sales & CRM
- **Customer Management**: Customer database with contact info, addresses, credit limits
- **Sales Orders**: 
  - Multi-line sales orders with auto-numbering (SO-00001, SO-00002, etc.)
  - Product selection with quantity and unit pricing
  - Automatic total amount calculation
  - Order status tracking (draft, confirmed, delivered)
  - Delivery date tracking
  - Order notes and special instructions

### ✅ Procurement
- **Supplier Management**: Supplier database with contact info and payment terms
- **Purchase Orders**:
  - Multi-line purchase orders with auto-numbering (PO-00001, PO-00002, etc.)
  - Product selection with quantity and unit pricing
  - Automatic total amount calculation
  - Expected delivery date tracking
  - Order status tracking (draft, approved, received)
  - Order notes and special instructions

### ✅ Mobile Money Integration
- **Provider Management**: Configure MTN Money, Airtel Money, Zamtel Kwacha
- **Payment Collection**: Receive payments from customers via mobile money
- **Disbursements**: Send payments to suppliers and employees
- **Transaction Tracking**: Real-time transaction history with auto-numbering (MM-000001, MM-000002, etc.)
- **Reconciliation**: Track pending, completed, and failed transactions
- **Multi-Provider Support**: Manage multiple mobile money accounts per company

### ✅ Point of Sale (POS)
- **Fast Checkout**: Quick product selection and cart management
- **Multi-Payment Methods**: Cash, Mobile Money, Card payments
- **Receipt Generation**: Auto-numbered receipts (RCT-000001, RCT-000002, etc.)
- **Terminal Management**: Configure multiple POS terminals per location
- **Sales Tracking**: Real-time sales history and revenue reporting
- **Cashier Sessions**: Opening/closing cash management

### ✅ Multi-Branch Operations
- **Branch Management**: Create and manage multiple business locations
- **Branch Hierarchy**: Designate main branch and sub-branches
- **Inter-Branch Transfers**: Move inventory between locations with auto-numbered transfers (BT-00001, BT-00002, etc.)
- **Branch-Level Reporting**: Track sales, inventory, and performance by branch
- **Manager Assignment**: Assign branch managers from employee database

### ✅ Super Admin Platform
- **Tenant Management**: View and manage all companies on the platform
- **Subscription Control**: Manage plans (Trial/Basic/Premium/Enterprise)
- **Company Activation**: Activate or deactivate company accounts
- **System Analytics**: Platform-wide usage statistics and reporting
- **7-Day Free Trial**: Automatic trial for all new registrations

### ✅ Dashboard
- Real-time statistics (employees, accounts, journal entries, orders)
- Quick actions for common tasks
- Company overview and activity tracking

### ✅ Modern UI/UX
- Responsive design works on desktop, tablet, and mobile
- Dark theme with ERIK teal/green branding (#00D9A3)
- Gradient backgrounds and glassmorphic cards
- Smooth animations and transitions
- Organized navigation with sections:
  - **Main**: Dashboard, Reports
  - **HR & Payroll**: Employees, Leave Types, Leave Applications, Payslips
  - **Finance**: Accounts, Journals
  - **Inventory & Sales**: Products, Warehouses, Stock, Customers, Sales Orders
  - **Procurement**: Suppliers, Purchase Orders
  - **Operations**: Point of Sale, Branches, Mobile Money
  - **Admin**: Super Admin Dashboard (role-restricted)

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (Replit managed)
- **ORM**: SQLAlchemy 2.0
- **Authentication**: JWT tokens with bcrypt password hashing
- **API**: RESTful with automatic OpenAPI/Swagger docs

### Frontend
- **Framework**: React 18 with Vite
- **Routing**: React Router v6
- **Styling**: Tailwind CSS with custom ERIK theme
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Charts**: Recharts (for future analytics)

### Infrastructure
- **Hosting**: Replit (development)
- **Database**: PostgreSQL with automatic backups
- **Deployment**: Ready for SaaS deployment

## Project Structure

```
.
├── backend/               # FastAPI backend
│   ├── main.py           # API routes and endpoints
│   ├── models.py         # SQLAlchemy database models
│   ├── schemas.py        # Pydantic validation schemas
│   ├── auth.py           # Authentication & authorization
│   ├── database.py       # Database connection
│   └── requirements.txt  # Python dependencies
│
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/  # Reusable React components
│   │   │   └── Layout.jsx
│   │   ├── pages/       # Page components
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Employees.jsx
│   │   │   ├── Accounts.jsx
│   │   │   └── Journals.jsx
│   │   ├── services/    # API integration
│   │   │   └── api.js
│   │   ├── styles/      # Global styles
│   │   │   └── index.css
│   │   ├── App.jsx      # Main app component
│   │   └── main.jsx     # Entry point
│   ├── index.html
│   ├── vite.config.js   # Vite configuration
│   ├── tailwind.config.js
│   └── package.json
│
└── erpnext/             # Legacy ERPNext code (for reference)
```

## Database Schema

### Multi-Tenant Design

All tables include `company_id` for data isolation:

- **companies**: Multi-tenant company registry
- **users**: User accounts linked to companies
- **employees**: HR employee records
- **accounts**: Chart of accounts (hierarchical)
- **journal_entries**: Financial journal headers
- **journal_lines**: Journal entry lines (debits/credits)

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new company and admin user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/users/me` - Get current user profile

### Dashboard
- `GET /api/dashboard/stats` - Get company statistics

### Finance
- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Create new account
- `GET /api/journals` - List journal entries
- `POST /api/journals` - Create journal entry

### HR
- `GET /api/employees` - List all employees
- `POST /api/employees` - Create new employee

## Color Palette (ERIK Branding)

```css
Primary:   #00D9A3  (Bright teal/green - from logo)
Accent:    #00FFB8  (Light teal)
Dark:      #0A1628  (Deep navy background)
Light:     #1E2A3A  (Card/panel background)
```

## How to Use

### 1. Register a Company
- Click "Register here" on the login page
- Enter your company name, full name, email, and password
- System automatically creates default chart of accounts

### 2. Add Employees
- Navigate to "Employees" in the sidebar
- Click "Add Employee"
- Fill in employee details (number, name, position, department, salary, etc.)

### 3. Manage Chart of Accounts
- Navigate to "Accounts"
- View the pre-loaded account structure
- Add custom accounts as needed

### 4. Record Transactions
- Navigate to "Journals"
- Click "New Entry"
- Create double-entry journal with debits and credits

## Development

### Running Locally

The project has two workflows:
1. **Backend API** - Runs on `http://127.0.0.1:8000`
2. **Frontend** - Runs on `http://0.0.0.0:5000` (automatically proxies API calls)

Both workflows start automatically in Replit.

### API Documentation

Interactive API docs available at: `http://127.0.0.1:8000/docs`

## Roadmap - Future Phases

### Phase 2: Enhanced Finance
- [ ] Bank reconciliation
- [ ] Financial reports (P&L, Balance Sheet, Cash Flow)
- [ ] Multi-currency with exchange rates
- [ ] Tax calculations and reports
- [ ] ZRA Smart Invoice integration

### Phase 3: Advanced HR & Payroll
- [ ] Complete payroll engine with PAYE, NAPSA, NHIMA
- [ ] Leave management system
- [ ] Attendance tracking
- [ ] Performance appraisals
- [ ] Payslip generation and distribution

### Phase 4: Inventory & Procurement
- [ ] Inventory management
- [ ] Purchase orders and requisitions
- [ ] Stock tracking and valuation
- [ ] Supplier management

### Phase 5: Manufacturing
- [ ] Bill of Materials (BOM)
- [ ] Production orders
- [ ] Work-in-progress tracking
- [ ] Industry-specific templates

### Phase 6: AI & Automation
- [ ] AI-powered financial insights
- [ ] Automated journal entry suggestions
- [ ] Predictive analytics
- [ ] Document OCR and smart scanning

### Phase 7: Compliance & Integrations
- [ ] ZRA integration for tax filing
- [ ] Bank API integrations
- [ ] Mobile money integrations (MTN, Airtel, Zamtel)
- [ ] WhatsApp business integration

## Recent Changes

**October 31, 2025 - Phase 3 Complete: Mobile Money, POS & Multi-Branch**:
- ✅ **Mobile Money Integration**: Full MTN, Airtel, Zamtel Kwacha payment processing
  - Provider management with API credential configuration
  - Payment collection and disbursement flows
  - Transaction tracking with auto-numbering (MM-XXXXXX)
  - Real-time transaction status (pending, completed, failed)
- ✅ **Point of Sale (POS) System**: Complete retail checkout solution
  - Fast checkout with product cart management
  - Multi-payment methods (Cash, Mobile Money, Card)
  - Auto-numbered receipts (RCT-XXXXXX)
  - Terminal management and cashier sessions
  - Real-time sales tracking and revenue reporting
- ✅ **Multi-Branch Operations**: Enterprise branch management
  - Branch creation and hierarchy (main/sub branches)
  - Inter-branch stock transfers with auto-numbering (BT-XXXXX)
  - Branch manager assignments
  - Branch-level inventory and reporting
- ✅ **Full CRUD Operations**: All modules support create, read, update, delete with company scoping
- ✅ **New Navigation Section**: "Operations" section added to sidebar with POS, Branches, Mobile Money
- ✅ All workflows tested and running successfully

## User Preferences

- **Primary Color**: Teal/Green (#00D9A3) as shown in ERIK logo
- **Goal**: Build a comprehensive ERP to compete with Odoo and SAP
- **Target Market**: Initially Zambian businesses, expandable globally
- **Business Model**: Multi-tier SaaS (Free, Basic, Premium, Enterprise)

## Notes

This MVP provides a solid foundation with:
- ✅ Production-ready architecture
- ✅ Scalable multi-tenant design
- ✅ Modern tech stack
- ✅ Professional UI/UX
- ✅ Core finance and HR functionality

The system is ready for:
- Investor demonstrations
- Initial client pilots
- Feature expansion
- Team collaboration

## Next Steps

1. **Test the MVP**: Register a company, add employees, create accounts and journals
2. **Choose next module**: Based on business priority (Payroll? Inventory? Reports?)
3. **Expand incrementally**: Build feature by feature
4. **Get user feedback**: Deploy to pilot clients
5. **Scale infrastructure**: Move to production hosting when ready

---

**Built with 💚 for ERIK ERP - Making enterprise management intelligent and accessible.**
