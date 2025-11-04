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

### Phase 4A: Super Admin Platform (November 2025)

#### Super Admin Database Models (backend/models.py)
- **SubscriptionPlan**: Multi-tier plan management (Free, Basic, Premium, Enterprise) with quotas for users, employees, storage, API calls, and branches. Includes module/feature permissions and trial period configuration.
- **SubscriptionPayment**: Payment transaction tracking for subscription billing with support for multiple payment methods (MTN Money, Airtel Money, bank transfer, Stripe). Includes provider integration and status tracking.
- **PlatformSettings**: Global platform configuration (maintenance mode, default trial days, email settings, feature flags). Centralized control for platform-wide settings.
- **SupportTicket**: Customer support ticket system with priority levels, categorization, assignment, and resolution tracking. Enables platform-wide support management.
- **SystemLog**: Comprehensive logging of API requests, errors, and system events. Includes request metadata, performance metrics, and log level filtering.
- **APIUsageLog**: API usage tracking per tenant with monthly aggregation. Supports quota enforcement and usage analytics.

#### Super Admin Backend APIs (backend/routers/super_admin.py)
- **Tenant Management**:
  - List all tenants with filtering (status, plan, search)
  - Get detailed tenant information with usage stats
  - Update tenant subscription and status
  - Suspend/activate tenant accounts
  - Real-time user count, employee count, API usage tracking

- **Subscription Plan Management**:
  - Create, read, update subscription plans
  - Define plan quotas and feature permissions
  - Track tenant count per plan
  - Support for monthly/annual pricing in multiple currencies

- **Platform Analytics**:
  - Dashboard analytics (total/active/trial tenants, new signups)
  - Subscription breakdown by plan
  - Revenue tracking (ready for payment integration)
  - Support ticket statistics
  - System health monitoring (error tracking)
  - Tenant growth analytics with configurable periods

- **Support Ticket Management**:
  - Create, list, update support tickets
  - Priority-based filtering (critical, high, medium, low)
  - Status tracking (open, in_progress, resolved, closed)
  - Auto-generated ticket numbers
  - Assignment and resolution workflow

#### Super Admin Frontend (frontend/src/pages/SuperAdmin.jsx)
- **Overview Dashboard**:
  - Real-time tenant statistics with trend indicators
  - Active/trial/total tenant counts
  - Open support ticket alerts
  - Subscription breakdown visualization
  - Purple/pink gradient theme (distinct from tenant UI)

- **Tenant Management Tab**:
  - Search tenants by name/email/tax ID
  - Filter by subscription status
  - One-click suspend/activate actions
  - Tenant details with usage stats
  - Responsive table with glassmorphic design

- **Subscription Plans Tab**:
  - Visual plan cards with pricing display
  - Tenant count per plan
  - Feature and quota breakdown
  - Monthly/annual pricing comparison

- **Support Ticket Tab**:
  - Recent ticket list with priority/status indicators
  - Color-coded priority levels
  - Auto-generated ticket numbering
  - Quick status overview

#### Technical Highlights
- **is_super_admin User Flag**: Added to User model for role-based access control
- **Super Admin Middleware**: Endpoint protection requiring super admin status
- **Cross-Tenant Queries**: Platform-wide data access without company scoping
- **Dedicated Route**: `/super-admin` path with distinct UI/UX
- **REST API Design**: 15+ endpoints following RESTful conventions
- **Pydantic Validation**: Strong typing for request/response models

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