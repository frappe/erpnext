# ERIK ERP - Enterprise Resource & Intelligence Kernel

**A modern, multi-tenant SaaS ERP system built for Zambian businesses with global ambitions**

## Overview

ERIK ERP is a comprehensive enterprise resource planning system designed to compete with industry leaders like Odoo and SAP. Built with modern technologies and specifically tailored for Zambian businesses, ERIK ERP provides complete business management capabilities from finance to operations.

## Key Features

### 🏢 Multi-Tenant SaaS Architecture
- Secure company data isolation
- JWT authentication with bcrypt
- Role-Based Access Control (RBAC)
- 7-day free trial for new registrations
- Subscription tiers: Trial, Basic, Premium, Enterprise

### 💰 Finance & Accounting
- Chart of Accounts with hierarchical structure
- Double-entry journal entries
- Multi-currency support (default: ZMW)
- FX gain/loss calculation and revaluation
- Bank reconciliation with auto-matching
- Fixed assets register with automated depreciation
- Accounting period management (close/lock workflows)
- Financial reports (P&L, Balance Sheet) with departmental breakdown

### 👥 HR & Payroll
- Employee management with contracts
- Zambian payroll engine (PAYE, NAPSA, NHIMA)
- Automated payslip generation
- Leave management with approval workflows
- Skills tracking and performance reviews
- Job requisitions and recruitment

### 📦 Inventory & Operations
- Product catalog and multi-location warehouses
- Real-time stock levels and movement tracking
- Universal production engine (manufacturing, agriculture, retail)
- Batch tracking and Work-In-Progress (WIP) valuation
- Transfer pricing for inter-department/branch transfers
- Industry templates (Agriculture, Manufacturing, Retail)

### 📊 Sales & Procurement
- Customer and supplier management
- Multi-line sales orders and purchase orders
- Auto-numbering and status tracking
- Delivery management

### ⚖️ Compliance & Intelligence
- Statutory obligations dashboard (PAYE, NAPSA, NHIMA)
- Smart invoice compliance (QR codes, UBL export, ZRA validation)
- Claude AI Assistant for business insights
- OCR & Document Intelligence for invoice/receipt scanning
- Comprehensive audit trail for SOX/GDPR/ISO 27001/PCI-DSS compliance

### 📱 Mobile Money & POS
- Mobile money provider integration (MTN, Airtel, Zamtel)
- Point of Sale system
- Payment collection and disbursement
- Transaction tracking and reconciliation

### 🏦 Banking Integration
- ZANACO, ABSA, FNB, Stanbic Bank Zambia
- Automatic transaction synchronization
- Auto-reconciliation with bank statements
- Real-time balance checking

### ⚙️ System Management
- Settings module (leave types, tax settings, email templates, salary components)
- Real-time notifications (in-app, email, SMS)
- Audit trail & access logs
- Multi-branch operations with hierarchy
- Super admin platform for tenant management

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
- **Authentication**: JWT with bcrypt password hashing
- **AI/OCR**: Anthropic Claude AI
- **API**: RESTful with OpenAPI/Swagger documentation

### Frontend
- **Framework**: React 18 with Vite
- **Routing**: React Router v6
- **Styling**: Tailwind CSS with custom ERIK theme
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Charts**: Recharts

### Infrastructure
- **Database**: PostgreSQL (Replit-managed)
- **Deployment**: Replit Autoscale
- **Multi-tenancy**: Database-level isolation

## Project Structure

```
├── backend/              # FastAPI backend application
│   ├── main.py          # Main API routes and app configuration
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # Authentication utilities
│   ├── database.py      # Database connection and session management
│   ├── migrations.py    # Database migration utilities
│   ├── utils.py         # Helper utilities
│   ├── ai_assistant.py  # Claude AI integration
│   ├── notification_service.py  # Notification system
│   ├── audit_logger.py  # Audit trail logging
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── App.jsx     # Main app component with routing
│   │   ├── components/ # Reusable React components
│   │   └── pages/      # Page components
│   ├── package.json    # Node.js dependencies
│   └── dist/           # Production build output (generated)
└── README.md           # This file
```

## Quick Start

### Development

The application runs with two workflows:

**Backend API** (port 8000):
```bash
cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (port 5000):
```bash
cd frontend && npm run dev
```

### Production Deployment

The application is configured for Replit Autoscale deployment:

**Build Command**:
```bash
cd frontend && npm install && npm run build
```

**Run Command**:
```bash
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 5000 --workers 2
```

In production, the FastAPI backend serves both the API endpoints and the built React frontend.

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Configuration

### Environment Variables

The application uses the following environment variables (automatically configured on Replit):

- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Claude AI API key (configured via integration)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - Database credentials

## Target Market

### Primary: Zambia
- Zambian tax compliance (PAYE, NAPSA, NHIMA)
- ZMW currency as default
- Local banking integration (ZANACO, ABSA, FNB, Stanbic)
- Mobile money integration (MTN, Airtel, Zamtel)

### Future: Global Expansion
Multi-currency and multi-locale support built-in for international growth.

## Subscription Tiers

- **Trial**: 7-day free trial with full features
- **Basic**: Essential features for small businesses
- **Premium**: Advanced features for growing businesses
- **Enterprise**: Complete feature set with priority support

## Security & Compliance

- Multi-tenant data isolation at database level
- JWT authentication with secure password hashing
- Comprehensive audit trail (SOX, GDPR, ISO 27001, PCI-DSS compliant)
- All login attempts tracked (unknown users, failures, successes)
- IP address and user agent forensics
- Role-Based Access Control (RBAC)

## License

See `license.txt` for details.

## Support

For issues, feature requests, or questions about ERIK ERP, please contact support.

---

**Built with ❤️ for Zambian businesses**
