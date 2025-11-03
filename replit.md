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
- **Backend Libraries**: FastAPI, SQLAlchemy, bcrypt
- **AI/OCR**: Anthropic Claude AI (for assistant and vision)
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha
- **Banking APIs**: ZANACO, ABSA Bank Zambia, FNB Zambia, Stanbic Bank Zambia