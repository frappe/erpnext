# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview

ERIK ERP is a modern, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. Built with cutting-edge technologies and designed with a sleek teal/green color palette inspired by the ERIK brand.

**Project Status**: MVP Phase 1 - Core Foundation Complete ✅

## Vision

To build a comprehensive ERP system that competes with Odoo, SAP, and other enterprise solutions, specifically tailored for businesses in Zambia and beyond. This MVP provides the foundational architecture and core modules that can be expanded into a full-featured enterprise system.

## Current Features (MVP Phase 1)

### ✅ Multi-Tenant SaaS Architecture
- Each company has its own isolated data
- Secure user authentication with JWT tokens
- Role-based access control (RBAC)
- Company registration with automatic setup

### ✅ Finance Module
- **Chart of Accounts**: Hierarchical account structure (Assets, Liabilities, Equity, Revenue, Expenses)
- **Journal Entries**: Double-entry bookkeeping with debit/credit lines
- **Real-time Reporting**: View all financial transactions
- **Multi-currency Support**: Default ZMW (Zambian Kwacha) with extensibility

### ✅ HR Module
- **Employee Management**: Complete employee database
- **Employee Records**: Personal info, position, department, salary
- **Employment Status Tracking**: Active/Inactive status management
- **Basic Payroll Structure**: Foundation for payroll calculations

### ✅ Dashboard
- Real-time statistics (employees, accounts, journal entries)
- Quick actions for common tasks
- Company overview and activity tracking

### ✅ Modern UI/UX
- Responsive design works on desktop, tablet, and mobile
- Dark theme with ERIK teal/green branding (#00D9A3)
- Gradient backgrounds and glassmorphic cards
- Smooth animations and transitions

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

**October 31, 2025**: 
- ✅ Initial MVP development complete
- ✅ Multi-tenant architecture implemented
- ✅ Finance module (Accounts, Journals) working
- ✅ HR module (Employees) working  
- ✅ Dashboard with real-time stats
- ✅ Beautiful UI with ERIK branding
- ✅ Both backend and frontend workflows running successfully

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
