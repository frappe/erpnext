# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview
ERIK ERP is a modern, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. It aims to be a comprehensive ERP system, specifically tailored for businesses in Zambia, with ambitions for global expansion. Key capabilities include multi-currency revaluation, bank reconciliation, smart invoice compliance, and a universal production engine. The project also integrates AI for business insights and OCR for document intelligence.

## User Preferences
- **Primary Color**: Teal/Green (#00D9A3) as shown in ERIK logo
- **Goal**: Build a comprehensive ERP to compete with Odoo and SAP
- **Target Market**: Initially Zambian businesses, expandable globally
- **Business Model**: Multi-tier SaaS (Free, Basic, Premium, Enterprise)

## System Architecture

### Core Features
- **Multi-Tenant SaaS Architecture**: Isolated data for each company, secure JWT authentication, Role-Based Access Control (RBAC), and company registration with automatic setup. Endpoints validate company ownership for data isolation.
- **Finance & Accounting**: Chart of Accounts, Journal Entries (double-entry), Financial Reports (P&L, Balance Sheet), real-time reporting, multi-currency support (default ZMW), FX gain/loss calculation, bank reconciliation, fixed assets register with automated depreciation, and accounting period management with close/lock workflows.
- **HR & Payroll**: Employee Management, Employment Status Tracking, Zambian Payroll Engine (PAYE, NAPSA, NHIMA calculations), automated payslip generation, Leave Management with approval workflows, employment contracts, skills tracking, job requisitions, and performance reviews.
- **Inventory & Operations**: Product catalog, multi-location warehouses, real-time stock levels, stock movement tracking, universal production engine (manufacturing, agriculture, retail), batch tracking, transfer pricing, and Work-In-Progress (WIP) tracking.
- **Sales & Procurement**: Customer and Supplier Management, multi-line Sales Orders and Purchase Orders with auto-numbering and status tracking.
- **Compliance & Intelligence**: Statutory Obligations Dashboard (PAYE, NAPSA, NHIMA with ZRA integration readiness), Smart Invoice Compliance (QR codes, UBL export, ZRA validation), Claude AI Assistant for business insights, and OCR & Document Intelligence using Claude AI Vision for invoice/receipt scanning.
- **System Management**: Settings module (Leave Types, Tax Settings, Email Templates, Salary Components), Notifications System (in-app, email, SMS), Audit Trail & Access Logs.
- **Mobile Money & POS Integration**: Provider management (MTN Money, Airtel Money, Zamtel Kwacha), payment collection/disbursement, transaction tracking, reconciliation, and a Point of Sale system.
- **Multi-Branch Operations**: Branch creation and hierarchy, inter-branch transfers, branch-level reporting.
- **Super Admin Platform**: Tenant management, subscription control, company activation, system analytics, and a 7-day free trial.
- **Dashboard**: Real-time statistics, quick actions, and company activity overview.

### UI/UX
- **Modern Design**: Responsive landing page with a professional look.
- **Theming**: Dark theme with ERIK teal/green branding (#00D9A3), gradient backgrounds, and glassmorphic cards.
- **Navigation**: Organized sidebar navigation for all modules.

### Technical Implementation
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, JWT authentication with bcrypt, RESTful API with OpenAPI/Swagger docs.
- **Frontend**: React 18 with Vite, React Router v6, Tailwind CSS with custom ERIK theme, Lucide React icons, Axios for HTTP.
- **Database**: PostgreSQL.

## External Dependencies
- **Database**: PostgreSQL
- **Frontend Libraries**: React, Vite, React Router, Tailwind CSS, Lucide React, Axios, Recharts
- **Backend Libraries**: FastAPI, SQLAlchemy, bcrypt, cryptography (Fernet encryption)
- **AI/OCR**: Anthropic Claude AI (for assistant and vision)
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha
- **Banking APIs**: ZANACO, ABSA Bank Zambia, FNB Zambia, Stanbic Bank Zambia

## Development Progress

### Phase 1: Banking Integration ✅ COMPLETE (6/6 tasks)
- Enhanced banking schema with external transactions, reconciliation rules
- Bank API integration framework for 5 Zambian banks (ABSA, Stanbic, FNB, Zanaco, Atlas Mara)
- Mobile money integrations (MTN, Airtel, Zamtel) with transaction sync
- Automated posting engine (bank feeds → GL entries, receipts → AR, payments → AP)
- AI-driven reconciliation engine with auto-match logic
- Frontend banking UI (connections, transaction feeds, reconciliation dashboard)
- **Security**: Fernet (AES-128) encryption for bank credentials

### Phase 2: Operational Intelligence ✅ COMPLETE (12/12 tasks)

**Manufacturing Engine (3 tasks):**
- Database schema: BillOfMaterials, BOMLine, Routing, RoutingOperation, ProductionOrder, ProductionOrderLine, WorkInProgress, CostLayer (all tables created in PostgreSQL)
- Production Workflow Service: Complete lifecycle management (Draft → Confirmed → In Progress → Completed/Cancelled), material issue to WIP, labor/overhead posting, WIP to finished goods conversion, cost calculation
- Activity-Based Costing (ABC) Engine: BOM cost calculation with materials/labor/overhead, ABC overhead allocation using cost drivers (machine hours, setups, QC), cost variance analysis (standard vs actual)

**Advanced Inventory (3 tasks):**
- Database schema: BatchLot, SerialNumber, QualityControl, ConsignmentStock, LandedCost, LandedCostAllocation, TransferPricingRule
- FEFO (First-Expired-First-Out) picking logic with expiry date management, quality hold/release workflow, batch/lot tracking
- Serial number assignment and tracking with warranty management
- Landed cost allocation service: freight, insurance, customs duty, handling charges with multiple allocation methods (value, quantity, weight, volume)
- Transfer pricing rules for inter-location transfers
- Consignment in/out inventory tracking with third-party stock management

**Consolidation & Reporting (6 tasks):**
- Database schema: Sector, Enterprise (organizational hierarchy for Department → Sector → Enterprise consolidation)
- Consolidated Profit & Loss Statement generation across departments/sectors
- Consolidated Balance Sheet with asset/liability aggregation
- Cash Flow Statement generator with Operating/Investing/Financing classification and drill-down capability
- Multi-dimensional reporting engine (units, weight, volume, value dimensions)
- Yield reports: expected vs actual production, normal vs abnormal loss classification, scrap analysis
- Surplus/shortage inventory analysis with reorder level comparisons

**Phase 2 Services Created:**
- `backend/services/manufacturing/production_workflow.py` - Full production order lifecycle
- `backend/services/manufacturing/costing_engine.py` - Activity-based costing
- `backend/services/inventory/advanced_inventory.py` - FEFO, serial tracking, quality controls
- `backend/services/inventory/landed_cost_service.py` - Landed costs and consignment tracking
- `backend/services/reporting/consolidation_engine.py` - Financial consolidation and reporting

**Progress**: 18/41 total tasks complete (43.9% overall)

### Phase 3: Finance, HR & Payroll Enhancement ⚙️ IN PROGRESS (24/24 tasks)

**Statutory Compliance Tracking System:**
- StatutoryObligation model with due dates, alerts, and percentage completion tracking
- ComplianceChecklist model for tracking compliance tasks (preparation, calculation, filing, payment, documentation)
- Automated obligation generation for PAYE, NAPSA, NHIMA, VAT, WHT, Turnover Tax, Provisional Tax, Corporate Tax
- Due date management with user confirmation workflow
- Time-based alerts (5-10 days before due dates) with priority levels (normal, high, urgent, critical)
- Compliance dashboard with percentage tracking and breakdown by category
- Automated notification system for statutory deadlines

**Enhanced Employee Model (Zambian Compliance):**
- Comprehensive personal details (name, maiden name, contact, emergency contact)
- National ID, passport, driver's license, place of birth
- Full address (residential, postal, city, province)
- Employment details (position, department, supervisor, branch)
- Employment dates (joined, probation, confirmation, contract end, retirement, termination)
- Employment status tracking (active, probation, suspended, terminated, retired)
- Banking details (bank account, branch, SWIFT code)
- Mobile money (MTN, Airtel, Zamtel)
- **Critical Statutory IDs:**
  - TPIN (Tax Payer Identification Number)
  - NAPSA Number (National Pension Scheme Authority)
  - NHIMA Number (National Health Insurance)
  - Workers Compensation Number
  - Statutory exemption flags (NAPSA, NHIMA, PAYE exempted)
- Labour law compliance (employment contract, contract signed date, labour card, work permit)
- Leave entitlements (annual 24 days, accrued, taken, balance, sick, maternity, paternity)
- Skills & qualifications (education level, certifications, professional skills)
- Dependents tracking (number, details for benefits & tax relief)
- Onboarding/offboarding checklists with completion tracking
- Document management (photo, CV, ID, tax clearance, certificates)
- Retirement age monitoring and automatic retirement date calculation

**Zambian Payroll Engine (2025 Rates):**
- Accurate PAYE calculation using 2025 progressive tax brackets:
  - 0 - ZMW 5,100/month: 0%
  - ZMW 5,101 - 8,200: 20%
  - ZMW 8,201 - 11,200: 30%
  - Above ZMW 11,200: 37%
- NAPSA contributions (5% employee + 5% employer, ceiling ZMW 34,164, max ZMW 1,708.20 each)
- NHIMA contributions (0.5% employee + 0.5% employer = 1% total)
- Workers Compensation Fund (1% employer contribution)
- Correct calculation order: Gross → NAPSA → Taxable Income → PAYE → NHIMA → Net Pay
- Loan deduction integration
- Employer cost calculation (gross + statutory employer contributions)
- Multi-currency payroll support

**Payroll Models:**
- Payrun: Batch payroll processing (draft → validated → posted → exported)
- Payslip: Individual employee payslips with PDF generation
- SalaryComponentDefinition: Configurable earnings/deductions with formula engine
- Payrun validation with error tracking
- GL integration (payroll posting to journal entries)
- Bank file export for payments
- Statutory totals aggregation (PAYE, NAPSA, NHIMA)

**HR Management Models:**
- EmployeeContract: Contract management (permanent, fixed-term, probation) with document storage
- EmployeeLoan: Loans & salary advances with amortization schedules and payroll integration
- JobRequisition: Job requisitions with approval workflow and budget tracking
- TaxSetting: Configurable tax rates and brackets by jurisdiction

**Notification System:**
- In-app, email, SMS delivery channels
- Priority levels (low, normal, high, urgent)
- Reference linking to obligations, payruns, leaves, loans
- Read/unread tracking
- Action URLs for navigation
- Auto-expiry for old notifications
- Statutory obligation alerts with compliance percentage in notification

**Phase 3 Services Created:**
- `backend/services/payroll/zambian_payroll_engine.py` - Complete 2025 Zambian payroll calculations
- `backend/services/compliance/statutory_compliance.py` - Statutory tracking, alerts, compliance percentage
- Notification service integration for time-based alerts

**Database Enhancements:**
- 11 new Phase 3 tables created (StatutoryObligation, ComplianceChecklist, Notification, Payrun, Payslip, EmployeeContract, EmployeeLoan, JobRequisition, SalaryComponentDefinition, TaxSetting, enhanced Employee)
- Enhanced Employee model with 60+ compliance-ready fields
- Full audit trail support
- JSON fields for flexible data storage (benefits, skills, dependents, checklists)

**Next Steps for Phase 3 Completion:**
- Create CRUD API routes for all new models
- Build frontend UI components (Compliance Dashboard, Payroll Wizard, Employee Onboarding)
- Implement scheduled jobs for automatic obligation generation and alert sending
- Add finance module APIs (Chart of Accounts, Journal Entries, Invoices, Payments)
- Create Smart Invoice compliance (QR codes, UBL export, ZRA validation)

### Phase 4: Communication & AI (Pending)
- Communication platform (chat, WhatsApp, email, SMS)
- OCR & AI assistant integration with Claude Vision
- Pricing & licensing management

### Phase 5: Final Features (Pending)
- Industry templates, multi-company consolidation, project management
- Green initiative & CSR tracking
- Marketplace & job hub, national ID integration
- Comprehensive UAT and deployment