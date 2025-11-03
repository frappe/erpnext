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
- **Finance & Accounting**: Chart of Accounts, double-entry Journal Entries, Financial Reports (P&L, Balance Sheet, Cash Flow), real-time reporting, multi-currency support (ZMW default), FX gain/loss, bank reconciliation, fixed assets with depreciation, and accounting period management.
- **HR & Payroll**: Employee Management (with extensive Zambian compliance fields like TPIN, NAPSA, NHIMA), Zambian Payroll Engine (2025 rates for PAYE, NAPSA, NHIMA, Workers Comp), automated payslips, Leave Management, employment contracts, and statutory compliance tracking with alerts.
- **Inventory & Operations**: Product catalog, multi-location warehouses, real-time stock, stock movement, universal production engine (manufacturing, agriculture, retail), batch/serial tracking, FEFO logic, landed cost allocation, and transfer pricing.
- **Sales & Procurement**: Customer/Supplier Management, multi-line Sales Orders and Purchase Orders.
- **Compliance & Intelligence**: Statutory Obligations Dashboard (ZRA integration readiness), Smart Invoice Compliance (QR, UBL, ZRA validation), Claude AI Assistant for insights, and OCR for document processing.
- **System Management**: Configurable settings, in-app/email/SMS Notifications, and Audit Trail.
- **Mobile Money & POS Integration**: Management of MTN Money, Airtel Money, Zamtel Kwacha for payments, transaction tracking, reconciliation, and a Point of Sale system.
- **Multi-Branch Operations**: Branch creation, inter-branch transfers, and branch-level reporting.
- **Super Admin Platform**: Tenant management, subscription control, system analytics, and 7-day free trial.
- **Dashboard**: Real-time statistics and company activity overview.

### UI/UX
- **Modern Design**: Responsive landing page with a professional aesthetic.
- **Theming**: Dark theme with ERIK teal/green branding (#00D9A3), gradient backgrounds, and glassmorphic cards.
- **Navigation**: Organized sidebar navigation for all modules.

### Technical Implementation
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, JWT authentication (bcrypt), RESTful API with OpenAPI/Swagger.
- **Frontend**: React 18 (Vite), React Router v6, Tailwind CSS (custom ERIK theme), Lucide React icons, Axios.
- **Database**: PostgreSQL.

## External Dependencies
- **Database**: PostgreSQL
- **Frontend Libraries**: React, Vite, React Router, Tailwind CSS, Lucide React, Axios, Recharts
- **Backend Libraries**: FastAPI, SQLAlchemy, bcrypt, cryptography (Fernet encryption), python-dateutil
- **AI/OCR**: Anthropic Claude AI (for assistant and vision)
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha
- **Banking APIs**: ZANACO, ABSA Bank Zambia, FNB Zambia, Stanbic Bank Zambia

## Development Progress

### Phase 3 Completed (November 2025)

#### Backend APIs (40+ Production Endpoints)
- **Compliance Module** (backend/routers/compliance.py)
  - Statutory obligations CRUD with automatic monthly generation
  - Obligation status tracking (pending, paid, overdue, waived)
  - Compliance percentage calculation
  - Deadline-based filtering and alerts
  - Payment recording with journal entry integration

- **Payroll Module** (backend/routers/payroll.py)
  - Payrun creation and management
  - Automatic 2025 Zambian tax calculation (PAYE, NAPSA, NHIMA, Workers Comp)
  - Individual payslip generation with detailed breakdowns
  - Gross salary computation with allowances/deductions
  - Payrun finalization and approval workflow
  - Multi-month payroll history tracking

- **Employee Module** (backend/routers/employees.py)
  - Full employee CRUD with Zambian compliance fields
  - Employee search, filtering, and pagination
  - Leave management (applications, types, balances)
  - Employee document uploads
  - Comprehensive Zambian data fields (TPIN, NAPSA, NHIMA, NRC, etc.)

- **Finance Module** (backend/routers/finance.py)
  - Chart of Accounts with account types
  - Journal entry creation (double-entry bookkeeping)
  - Financial reporting (P&L, Balance Sheet, Trial Balance)
  - Account balance tracking
  - Multi-currency transaction support

#### Smart Invoice Service (backend/smart_invoice.py)
- QR code generation with ZRA compliance data (TPIN, invoice number, amount, date)
- UBL 2.1 XML export for electronic invoicing
- ZRA e-invoice validation (required fields, tax calculations)
- Digital signature support for invoice authenticity
- Industry-standard invoice format compliance

#### Scheduled Jobs Service (backend/scheduled_jobs.py)
- Service framework created for automatic monthly statutory obligation generation (15th of each month)
- Service framework created for daily compliance deadline checking with email alerts (7-day, 3-day, same-day warnings)
- Requires APScheduler package installation and activation in main.py
- Notification service integration ready for automated alerts
- Status: **NOT ACTIVE** - Code written but scheduler not started pending APScheduler dependency installation

#### Frontend Components
- **Compliance Dashboard** (frontend/src/pages/Compliance.jsx)
  - Real-time compliance percentage display
  - Color-coded obligation status cards (pending, paid, overdue)
  - Interactive obligation checklist with payment recording
  - Deadline-based alerts and filtering
  - Responsive grid layout with glassmorphic design

- **Payroll Wizard** (frontend/src/pages/Payroll.jsx)
  - Step-by-step payrun creation wizard
  - Employee selection with search and filtering
  - Automatic payslip calculation preview
  - Individual payslip viewing with detailed breakdowns
  - Payrun history and status tracking
  - Export capabilities for payslips

#### Utilities & Services
- **Sample Data Generator** (backend/sample_data_generator.py)
  - Demo company creation with Zambian defaults
  - Sample employee generation with compliance data
  - Chart of accounts initialization (Assets, Liabilities, Income, Expenses)
  - Statutory obligations setup for current period
  - Journal entry examples
  - Status: Field mapping issues - data can be created via UI

- **Audit Logger** (backend/audit_logger.py)
  - Comprehensive audit trail for all data changes
  - User action tracking with timestamps
  - IP address and entity tracking
  - Detailed change logging (before/after states)

- **Notification Service** (backend/notification_service.py)
  - Multi-channel notifications (in-app, email, SMS)
  - Priority-based notification queue
  - User preference management
  - Notification templates for common events

### Technical Highlights
- **Database Schema**: PostgreSQL with 40+ tables covering all modules
- **API Design**: RESTful with OpenAPI/Swagger documentation at /docs
- **Authentication**: JWT bearer token with company-scoped data isolation
- **Code Organization**: Modular router structure for easy maintenance
- **Error Handling**: Comprehensive exception handling with meaningful messages
- **Data Validation**: Pydantic models for request/response validation
- **Compliance Focus**: Deep integration of Zambian tax and labor regulations

### Known Limitations & Future Work
- Scheduled jobs require APScheduler package installation
- Notification endpoints need implementation (/api/notifications/unread-count)
- Sample data generator needs field mapping updates
- Leave management endpoints need frontend integration
- Smart invoice QR/UBL features require qrcode package installation

### Current System Status
- Backend: Running on port 8000 with 40+ working endpoints
- Frontend: Running on port 5000 with all core modules accessible
- Database: PostgreSQL with synchronized schema
- Authentication: Fully functional with company-based multi-tenancy