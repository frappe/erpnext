# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview
ERIK ERP is a comprehensive, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. It aims to be a leading ERP solution, initially targeting Zambian businesses with ambitions for global expansion. Key capabilities include multi-currency support, bank reconciliation, smart invoice compliance, a universal production engine, and AI-driven business insights and OCR document intelligence. The project envisions a multi-tier SaaS business model (Free, Basic, Premium, Enterprise) to compete with established ERP providers like Odoo and SAP.

## Current Implementation Status
**Finance Module: ✅ 100% COMPLETE** - November 7, 2025

### ✅ Completed Finance Module (PRODUCTION READY)
All 10 tasks completed and tested:

1. ✅ Compact journal entries with reversals and batch import
2. ✅ 3-tier approval workflow (draft → approve → post → lock)
3. ✅ Period close & lock functionality with validation
4. ✅ Multi-currency FX revaluation with scheduled jobs
5. ✅ Smart Invoice (UBL 2.1 XML, JSON export, QR codes, ZRA validation)
6. ✅ Payment matching engine (auto-match with confidence scoring)
7. ✅ Fixed asset depreciation (straight-line, declining balance, schedules, disposal)
8. ✅ Intercompany transactions & eliminations (consolidation ready)
9. ✅ Financial reports with drill-down capability
   - Balance Sheet (Statement of Financial Position)
   - Income Statement (Profit & Loss)
   - Trial Balance
   - General Ledger Report
   - Account Activity (drill-down from reports to transactions)
10. ✅ End-to-end testing & sign-off (10/10 tests passed)

**📊 Finance Module Stats:**
- 45+ API Endpoints
- 9 Service Modules
- 10/10 E2E Tests Passed
- Production-Ready ✅

### 🚀 HR & Payroll Module (IN PROGRESS) - 33% Complete (5/15 tasks)
**Phase 2 Started:** November 7, 2025

**Completed Tasks:**
1. ✅ H1: Employee Document Management - Secure upload/download for contracts, IDs, certificates
2. ✅ H2.1: Attendance Management - Shift definitions, rostering, attendance capture with CSV import
3. ✅ H2.2: Leave Workflow Enhancement - Leave request submission, approval workflow, balance tracking with payroll integration
4. ✅ H3.1: Payroll Run System - Batch payroll processing with preview and approval workflow
5. ✅ H3.2: Payroll Journal Posting - Auto-create GL journals from payroll and generate bank payment files

**Pending Tasks (10 remaining):**
- H3.3: Payslip Generation
- H4.1-H4.2: Employee Loans & Advances, Automatic Deductions
- H5.1-H5.2: TPIN Validation, Statutory Compliance Exports
- H6.1-H6.2: Employee Self-Service Portal, Leave Requests
- H7.1-H7.2: HR Analytics Dashboard, Onboarding Automation
- H-TEST: End-to-End Testing & UAT

### 🎯 Next Modules
- Inventory & Operations Module (0%)
- Banking Integration Module (0%)

## User Preferences
- **Primary Color**: Teal/Green (#00D9A3) as shown in ERIK logo
- **Goal**: Build a comprehensive ERP to compete with Odoo and SAP
- **Target Market**: Initially Zambian businesses, expandable globally
- **Business Model**: Multi-tier SaaS (Free, Basic, Premium, Enterprise)

## System Architecture

### Core Features
- **Multi-Tenant SaaS Architecture**: Isolated data, secure JWT authentication, Role-Based Access Control (RBAC), company registration, and company-scoped data validation.
- **Financial Management**: Chart of Accounts, double-entry Journal Entries, Financial Reports, multi-currency support, FX gain/loss, bank reconciliation, fixed assets, accounting period management, **intercompany transactions with elimination entries for consolidation**, payment matching engine, smart invoice compliance (UBL/QR/ZRA), and automated fixed asset depreciation.
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

## External Dependencies
- **Database**: PostgreSQL
- **Frontend Libraries**: React, Vite, React Router, Tailwind CSS, Lucide React, Axios, Recharts
- **Backend Libraries**: FastAPI, SQLAlchemy, bcrypt, cryptography (Fernet encryption), python-dateutil, qrcode[pil], Pillow
- **AI/OCR**: Anthropic Claude AI (for assistant and vision)
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha
- **Banking APIs**: ZANACO, ABSA Bank Zambia, FNB Zambia, Stanbic Bank Zambia