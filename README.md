# 🌟 ERIK ERP - Enterprise Resource & Intelligence Kernel

[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](license.txt)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)

**A modern, comprehensive multi-tenant SaaS ERP system built for Zambian businesses with global ambitions**

> *Compete with Odoo and SAP - Built with modern tech, designed for Africa*

---

## 📖 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Industry Addons](#industry-addons)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Subscription Tiers](#subscription-tiers)
- [Security & Compliance](#security--compliance)
- [Target Market](#target-market)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

ERIK ERP is a **comprehensive enterprise resource planning system** designed to compete with industry leaders like Odoo and SAP. Built with modern technologies and specifically tailored for Zambian businesses, ERIK ERP provides complete business management capabilities from finance to operations.

### Why ERIK ERP?

✅ **Multi-Tenant SaaS** - Secure, isolated company data with subscription management  
✅ **Zambian Compliance** - PAYE, NAPSA, NHIMA, ZRA-ready  
✅ **Modern Stack** - FastAPI + React + PostgreSQL + AI  
✅ **Industry Addons** - 17 pre-built industry modules ready to activate  
✅ **AI-Powered** - Claude AI for insights + OCR for document processing  
✅ **Local Integrations** - Zambian banks + mobile money providers  
✅ **Global Ready** - Multi-currency, multi-locale support built-in  

---

## 🚀 Key Features

### 🏢 Multi-Tenant SaaS Architecture
- **Secure Company Data Isolation** - Complete data separation per tenant
- **JWT Authentication** - Secure token-based auth with bcrypt password hashing
- **Role-Based Access Control (RBAC)** - Granular permissions system
- **7-Day Free Trial** - Automatic trial for new registrations
- **Subscription Management** - Trial, Basic, Premium, Enterprise tiers
- **Super Admin Platform** - Tenant management, analytics, and control

### 💰 Finance & Accounting
- **Chart of Accounts** - Hierarchical account structure with parent-child relationships
- **Double-Entry Journal Entries** - Full accounting with debits/credits
- **Multi-Currency Support** - ZMW default, supports USD, EUR, GBP, ZAR, etc.
- **FX Gain/Loss Calculation** - Automatic foreign exchange revaluation
- **Bank Reconciliation** - Auto-matching with ML-powered suggestions
- **Fixed Assets Register** - Automated depreciation (straight-line, declining balance)
- **Accounting Period Management** - Period close/lock workflows
- **Financial Reports** - P&L, Balance Sheet, Cash Flow with drill-down
- **Departmental Accounting** - Cost center tracking and reporting

### 👥 HR & Payroll
- **Employee Management** - Complete employee lifecycle with contracts
- **Zambian Payroll Engine** - 2025 PAYE, NAPSA, NHIMA, Workers' Comp rates
- **Automated Payslip Generation** - PDF payslips with statutory deductions
- **Leave Management** - Leave requests, approvals, and balances
- **Skills Tracking** - Employee competencies and certifications
- **Performance Reviews** - KPI tracking and appraisals
- **Job Requisitions** - Recruitment workflow management

### 📦 Inventory & Operations
- **Product Catalog** - Comprehensive product master data
- **Multi-Location Warehouses** - Unlimited warehouse support
- **Real-Time Stock Levels** - Live inventory tracking
- **Stock Movement Tracking** - All in/out movements logged
- **Universal Production Engine** - Manufacturing, agriculture, retail templates
- **Batch/Serial Tracking** - FEFO (First Expired, First Out) logic
- **Work-In-Progress (WIP) Valuation** - Real-time production costing
- **Landed Cost Allocation** - Freight, customs, insurance allocation
- **Transfer Pricing** - Inter-department and inter-branch pricing

### 📊 Sales & Procurement
- **Customer Management** - CRM with credit limits and payment terms
- **Supplier Management** - Vendor master with performance tracking
- **Multi-Line Sales Orders** - Complex order management with line items
- **Purchase Orders** - PO creation, approval, and tracking
- **Auto-Numbering** - Intelligent document numbering
- **Delivery Management** - Shipping and delivery tracking

### ⚖️ Compliance & Intelligence
- **Statutory Obligations Dashboard** - PAYE, NAPSA, NHIMA tracking
- **Smart Invoice Compliance** - QR codes, UBL export, ZRA validation
- **Claude AI Assistant** - Business insights and natural language queries
- **OCR & Document Intelligence** - Invoice and receipt scanning
- **Comprehensive Audit Trail** - SOX, GDPR, ISO 27001, PCI-DSS compliant
- **Login Forensics** - Failed attempts, IP tracking, user agent logging

### 📱 Mobile Money & POS
- **Mobile Money Integration** - MTN Money, Airtel Money, Zamtel Kwacha
- **Point of Sale (POS)** - Retail POS system with receipt printing
- **Payment Collection** - Multi-channel payment processing
- **Payment Disbursement** - Bulk payouts and vendor payments
- **Transaction Tracking** - Real-time transaction monitoring
- **Auto-Reconciliation** - Mobile money statement reconciliation

### 🏦 Banking Integration
- **Bank Connections** - ZANACO, ABSA, FNB, Stanbic Bank Zambia
- **Automatic Transaction Sync** - Daily bank feed imports
- **Auto-Reconciliation** - ML-powered transaction matching
- **Real-Time Balance Checking** - Live bank balance queries
- **Multi-Bank Support** - Unlimited bank accounts per company

### 🏭 Manufacturing
- **Bill of Materials (BOM)** - Multi-level BOM support
- **Production Orders** - Work order management
- **Production Workflow** - Raw materials → WIP → Finished goods
- **Costing Engine** - Standard, average, FIFO costing
- **Capacity Planning** - Resource allocation and scheduling
- **Quality Control** - Inspection checkpoints and quality gates

### 🌐 Multi-Branch Operations
- **Branch Hierarchy** - Unlimited branches with parent-child structure
- **Inter-Branch Transfers** - Stock and cash transfers between branches
- **Branch-Level Reporting** - P&L and Balance Sheet per branch
- **Consolidated Reports** - Company-wide financial consolidation
- **Transfer Pricing** - Branch-to-branch pricing rules

### ⚙️ System Management
- **Settings Module** - Leave types, tax settings, email templates, salary components
- **Real-Time Notifications** - In-app, email, and SMS notifications
- **Audit Trail** - Complete activity logs with user tracking
- **Access Logs** - Security monitoring and forensics
- **Notification Center** - Centralized notification management

---

## 🎨 Industry Addons (17 Modules)

ERIK ERP features a comprehensive **Addon Marketplace** with 17 industry-specific modules that can be activated per tenant:

| Icon | Addon Name | Description | Pricing |
|------|-----------|-------------|---------|
| 🏗️ | **Construction & Real Estate** | Project management, job costing, BOQ, contractor management | $50/user/mo |
| 🌾 | **Agriculture & Agribusiness** | Farm management, crop planning, livestock tracking | $40/user/mo |
| 🏥 | **Healthcare & Pharmaceuticals** | Patient records, appointments, pharmacy, billing | $70/user/mo |
| 🏪 | **Retail, Wholesale & POS** | Point of sale, inventory, multi-store management | $30/user/mo |
| 🏫 | **Education & Training** | Student information system, enrollment, courses | $45/user/mo |
| 🚚 | **Transport & Logistics** | Fleet management, trip planning, fuel tracking | $50/user/mo |
| 🍽️ | **Hospitality & Restaurants** | Room management, reservations, table booking | $40/user/mo |
| 🏘️ | **Real Estate Development** | Property management, lease tracking, tenant portal | $55/user/mo |
| ⚖️ | **Legal Practice Management** | Case management, legal documents, time tracking | $60/user/mo |
| 🕊️ | **NGO & Non-Profit** | Donor management, grant tracking, project funding | $35/user/mo |
| 🏭 | **Advanced Manufacturing** | Production orders, quality control, shop floor | $65/user/mo |
| 📦 | **Logistics & Warehousing** | Warehouse management, shipment tracking, 3PL | $50/user/mo |
| 🌐 | **Telecommunications** | Subscriber management, billing, service plans | $60/user/mo |
| 💡 | **Energy & Utilities** | Meter management, consumption tracking, billing | $55/user/mo |
| 📰 | **Media & Publishing** | Content management, publications, subscriptions | $45/user/mo |
| 💰 | **Insurance & Underwriting** | Policy management, claims processing, underwriting | $70/user/mo |
| 🏛️ | **Government & Public Sector** | Permit management, public services, licensing | $50/user/mo |

**All addons include:**
- ✅ Full CRUD operations
- ✅ Multi-tenant isolation
- ✅ Company-scoped data
- ✅ Beautiful UI components
- ✅ API endpoints with Swagger docs
- ✅ Activate/deactivate per tenant

---

## 🛠 Technology Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11 | Programming language |
| **FastAPI** | 0.109.0 | Web framework |
| **SQLAlchemy** | 2.0.25 | ORM for database |
| **PostgreSQL** | 16 | Relational database |
| **Pydantic** | 2.5.3 | Data validation |
| **JWT** | 3.3.0 | Authentication |
| **bcrypt** | 4.1.2 | Password hashing |
| **Anthropic Claude** | 0.18.1 | AI assistant & OCR |
| **APScheduler** | 3.10.4 | Scheduled jobs |
| **QRCode** | 7.4.2 | QR code generation |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **React** | 18.2 | UI framework |
| **Vite** | 5.0.11 | Build tool |
| **React Router** | 6.21.0 | Client-side routing |
| **Tailwind CSS** | 3.4.1 | Styling |
| **Lucide React** | 0.307.0 | Icons |
| **Axios** | 1.6.5 | HTTP client |
| **Recharts** | 2.10.3 | Charts & graphs |

### Infrastructure
- **Database**: PostgreSQL 16 (Replit-managed)
- **Deployment**: Replit Autoscale (serverless)
- **AI/OCR**: Anthropic Claude AI (Replit integration)
- **Multi-Tenancy**: Database-level isolation with company_id scoping

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Anthropic API Key (for AI features)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd erik-erp
```

2. **Set up environment variables**
```bash
# Database
export DATABASE_URL="postgresql://user:password@localhost:5432/erikerp"
export PGHOST="localhost"
export PGPORT="5432"
export PGUSER="postgres"
export PGPASSWORD="yourpassword"
export PGDATABASE="erikerp"

# AI (via Replit integration)
export ANTHROPIC_API_KEY="your-api-key"
```

3. **Start Backend** (Terminal 1)
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

4. **Start Frontend** (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

5. **Access the application**
- **Frontend**: http://localhost:5000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Default Credentials

**Super Admin:**
- Email: `admin@erikerp.com`
- Password: `SuperAdmin2025!`

**Tenant Account:**
- Email: `nabaloans@gmail.com`
- Password: `Tenant2025!`
- Company: `NABA CENTRAL`

---

## 📁 Project Structure

```
erik-erp/
├── backend/                      # FastAPI backend application
│   ├── routers/                  # API route modules
│   │   ├── addons.py            # Addon marketplace endpoints
│   │   ├── finance.py           # Finance & accounting
│   │   ├── employees.py         # HR & employee management
│   │   ├── payroll.py           # Zambian payroll engine
│   │   ├── inventory.py         # Inventory & warehousing
│   │   ├── sales.py             # Sales orders & customers
│   │   ├── procurement.py       # Purchase orders & suppliers
│   │   ├── manufacturing.py     # Production & BOM
│   │   ├── banking.py           # Banking & reconciliation
│   │   ├── compliance.py        # Statutory compliance
│   │   ├── tax.py               # Tax management
│   │   ├── super_admin.py       # Tenant management
│   │   ├── construction.py      # Construction addon
│   │   ├── agriculture.py       # Agriculture addon
│   │   ├── healthcare.py        # Healthcare addon
│   │   ├── retail.py            # Retail addon
│   │   ├── education.py         # Education addon
│   │   ├── transport.py         # Transport addon
│   │   ├── hospitality.py       # Hospitality addon
│   │   ├── realestate.py        # Real estate addon
│   │   ├── legal.py             # Legal addon
│   │   ├── ngo.py               # NGO addon
│   │   ├── advmanufacturing.py  # Advanced manufacturing addon
│   │   ├── logistics.py         # Logistics addon
│   │   ├── telecom.py           # Telecom addon
│   │   ├── energy.py            # Energy addon
│   │   ├── media.py             # Media addon
│   │   ├── insurance.py         # Insurance addon
│   │   ├── government.py        # Government addon
│   │   ├── chat.py              # AI assistant
│   │   └── ocr.py               # OCR processing
│   ├── services/                 # Business logic services
│   │   ├── banking/             # Bank integrations (ZANACO, ABSA, FNB, Stanbic)
│   │   ├── mobile_money/        # Mobile money (MTN, Airtel, Zamtel)
│   │   ├── payroll/             # Zambian payroll engine
│   │   ├── inventory/           # Advanced inventory logic
│   │   ├── manufacturing/       # Production workflows
│   │   ├── finance/             # Finance utilities
│   │   ├── compliance/          # Compliance tracking
│   │   └── reporting/           # Consolidation engine
│   ├── main.py                   # Main FastAPI app & routes
│   ├── models.py                 # SQLAlchemy database models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── auth.py                   # JWT authentication
│   ├── database.py               # Database connection & session
│   ├── migrations.py             # Database migration utilities
│   ├── utils.py                  # Helper functions
│   ├── ai_assistant.py           # Claude AI integration
│   ├── ocr_service.py            # OCR document processing
│   ├── notification_service.py   # Notification system
│   ├── audit_logger.py           # Audit trail logging
│   ├── smart_invoice.py          # Smart invoice compliance
│   ├── banking_service.py        # Banking facade
│   ├── scheduled_jobs.py         # Background jobs
│   ├── sample_data_generator.py  # Demo data generator
│   └── requirements.txt          # Python dependencies
│
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── components/           # Reusable components
│   │   │   ├── Layout.jsx       # Main layout with sidebar
│   │   │   ├── NotificationCenter.jsx
│   │   │   ├── DisclaimerModal.jsx
│   │   │   └── Banking/         # Banking components
│   │   ├── pages/                # Page components
│   │   │   ├── Landing.jsx      # Landing page
│   │   │   ├── Login.jsx        # Login page
│   │   │   ├── Register.jsx     # Company registration
│   │   │   ├── Dashboard.jsx    # Main dashboard (14+ metrics)
│   │   │   ├── AddonStore.jsx   # Addon marketplace
│   │   │   ├── Employees.jsx    # Employee management
│   │   │   ├── Payroll.jsx      # Payroll processing
│   │   │   ├── Journals.jsx     # Journal entries
│   │   │   ├── Accounts.jsx     # Chart of accounts
│   │   │   ├── Products.jsx     # Product catalog
│   │   │   ├── SalesOrders.jsx  # Sales orders
│   │   │   ├── PurchaseOrders.jsx
│   │   │   ├── Customers.jsx
│   │   │   ├── Suppliers.jsx
│   │   │   ├── MobileMoney.jsx
│   │   │   ├── POS.jsx
│   │   │   ├── Reports.jsx
│   │   │   ├── AIAssistant.jsx
│   │   │   ├── OCRUpload.jsx
│   │   │   ├── SuperAdmin.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── Banking/         # Banking pages
│   │   ├── services/
│   │   │   └── api.js           # Axios API client
│   │   ├── styles/
│   │   │   └── index.css        # Tailwind + custom styles
│   │   ├── App.jsx               # Main app with routing
│   │   └── main.jsx              # React entry point
│   ├── public/
│   │   └── assets/
│   │       └── erik-logo.png    # ERIK logo
│   ├── index.html                # HTML template
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite configuration
│   ├── tailwind.config.js        # Tailwind theme (ERIK colors)
│   └── postcss.config.js         # PostCSS config
│
├── .replit                       # Replit configuration
├── replit.md                     # Project documentation
├── README.md                     # This file
├── DEVELOPER_GUIDE.md            # Detailed developer documentation
├── PROJECT_STRUCTURE.md          # Complete file structure breakdown
├── API_DOCUMENTATION.md          # API endpoint reference
├── DEPLOYMENT.md                 # Deployment guide
└── license.txt                   # License information
```

---

## 📚 API Documentation

### Interactive Documentation

Once the backend is running, access comprehensive API documentation:

- **Swagger UI**: http://localhost:8000/docs (interactive API explorer)
- **ReDoc**: http://localhost:8000/redoc (clean API reference)

### API Endpoint Categories

- `/api/auth/*` - Authentication & authorization
- `/api/companies/*` - Company/tenant management
- `/api/users/*` - User management
- `/api/employees/*` - HR & employee data
- `/api/payroll/*` - Payroll processing
- `/api/finance/*` - Accounts, journals, reports
- `/api/inventory/*` - Products, warehouses, stock
- `/api/sales/*` - Sales orders, customers
- `/api/procurement/*` - Purchase orders, suppliers
- `/api/manufacturing/*` - Production, BOM
- `/api/banking/*` - Bank connections, reconciliation
- `/api/mobile-money/*` - Mobile money transactions
- `/api/compliance/*` - Statutory obligations
- `/api/addons/*` - Addon marketplace
- `/api/chat/*` - AI assistant
- `/api/ocr/*` - Document OCR
- `/api/super-admin/*` - Tenant administration

For detailed endpoint documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

---

## 🔐 Environment Variables

### Required Variables

```bash
# Database (auto-configured on Replit)
DATABASE_URL=postgresql://user:password@host:port/database
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=yourpassword
PGDATABASE=erikerp

# AI & OCR (configured via Replit integration)
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Optional Variables

```bash
# JWT Secret (auto-generated if not provided)
SECRET_KEY=your-secret-key-here

# Environment
ENVIRONMENT=development  # or production

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## 🚀 Deployment

### Replit Autoscale (Recommended)

ERIK ERP is configured for Replit Autoscale deployment (serverless, auto-scaling).

**Important**: Before deploying, manually edit `.replit` file:

1. **Find lines 50-85** (all `[[ports]]` sections)
2. **Delete ALL port configurations**
3. **Save the file**

This allows Replit to auto-detect port 80 for production.

**Deployment Configuration:**
```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 80"]
build = ["sh", "-c", "cd frontend && npm install && npm run build"]
```

### Manual Deployment

For other platforms (AWS, GCP, Azure, DigitalOcean):

1. **Build frontend:**
```bash
cd frontend && npm install && npm run build
```

2. **Install backend dependencies:**
```bash
cd backend && pip install -r requirements.txt
```

3. **Run with Gunicorn (production):**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:80
```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 💼 Subscription Tiers

| Tier | Price | Features | Target |
|------|-------|----------|--------|
| **Trial** | Free (7 days) | Full features, limited time | Evaluation |
| **Basic** | $50/month | Essential features, 5 users | Small business |
| **Premium** | $150/month | Advanced features, 25 users | Growing business |
| **Enterprise** | Custom | All features, unlimited users | Large enterprise |

**All tiers include:**
- ✅ Unlimited companies (multi-tenant)
- ✅ Core ERP modules (Finance, HR, Inventory)
- ✅ Mobile money & banking integration
- ✅ Statutory compliance (PAYE, NAPSA, NHIMA)
- ✅ Email & SMS notifications
- ✅ Audit trail & security

**Premium & Enterprise add:**
- ✅ AI Assistant (Claude)
- ✅ OCR Document Processing
- ✅ Advanced manufacturing
- ✅ Multi-branch operations
- ✅ Addon marketplace access
- ✅ Priority support

---

## 🔒 Security & Compliance

### Security Features
- **Multi-Tenant Data Isolation** - Complete separation at database level
- **JWT Authentication** - Secure token-based authentication
- **bcrypt Password Hashing** - Industry-standard password encryption
- **Role-Based Access Control (RBAC)** - Granular permission system
- **Comprehensive Audit Trail** - All actions logged with user & timestamp
- **Login Forensics** - Failed attempts, IP tracking, user agent logging
- **SQL Injection Protection** - SQLAlchemy ORM parameterized queries
- **XSS Protection** - React auto-escaping + Content Security Policy
- **CSRF Protection** - Token-based CSRF prevention

### Compliance Standards
- ✅ **SOX** - Sarbanes-Oxley (audit trail, access controls)
- ✅ **GDPR** - Data privacy and user consent
- ✅ **ISO 27001** - Information security management
- ✅ **PCI-DSS** - Payment card industry security (if handling cards)

### Zambian Compliance
- ✅ **ZRA (Zambia Revenue Authority)** - Smart invoice, QR codes, UBL export
- ✅ **PAYE (Pay As You Earn)** - 2025 tax rates and brackets
- ✅ **NAPSA (National Pension Scheme)** - 5% employee, 5% employer
- ✅ **NHIMA (Health Insurance)** - 1% contribution tracking
- ✅ **Workers' Compensation** - 1% employer contribution

---

## 🌍 Target Market

### Primary Market: Zambia 🇿🇲
- **Zambian Tax Compliance** - PAYE, NAPSA, NHIMA, ZRA-ready
- **Local Currency** - ZMW (Zambian Kwacha) as default
- **Local Banking** - ZANACO, ABSA, FNB, Stanbic Bank Zambia
- **Mobile Money** - MTN Money, Airtel Money, Zamtel Kwacha
- **Industry Focus** - Mining, agriculture, retail, manufacturing, hospitality

### Future Markets: Global Expansion 🌐
- **Multi-Currency** - USD, EUR, GBP, ZAR, and more
- **Multi-Locale** - Date formats, number formats, translations
- **Scalable Infrastructure** - Cloud-native, serverless architecture
- **Regional Customization** - Country-specific compliance modules

---

## 📸 Screenshots

### Dashboard
![Dashboard with 14+ real-time metrics](#)

### Addon Marketplace
![17 industry-specific addons](#)

### Finance Module
![Chart of Accounts, Journal Entries, Financial Reports](#)

### Payroll
![Zambian payroll with PAYE, NAPSA, NHIMA](#)

---

## 🤝 Contributing

We welcome contributions to ERIK ERP! Please see our [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for:

- Code style guidelines
- Development workflow
- Testing requirements
- Pull request process

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

See [license.txt](license.txt) for details.

---

## 📞 Support

For issues, feature requests, or questions about ERIK ERP:

- 📧 **Email**: support@erikerp.com
- 🐛 **Bug Reports**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📚 **Documentation**: [Developer Guide](DEVELOPER_GUIDE.md)

---

## 🙏 Acknowledgments

- **FastAPI** - Modern, fast web framework
- **React** - Powerful UI library
- **Anthropic Claude** - AI assistant & OCR
- **Tailwind CSS** - Utility-first CSS framework
- **PostgreSQL** - Robust relational database

---

## 🌟 Star Us!

If you find ERIK ERP helpful, please consider giving us a star ⭐ on GitHub!

---

**Built with ❤️ for Zambian businesses and beyond**

*Competing with Odoo and SAP - One module at a time* 🚀
