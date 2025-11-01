# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview
ERIK ERP is a modern, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. It aims to be a comprehensive ERP system competing with leading solutions, specifically tailored for businesses in Zambia and beyond. The project provides foundational architecture and core modules for future expansion.

## Recent Changes

### Phase 1 Completed (November 1, 2025)
**Tasks 1-5: Foundation & AI Integration**
1. ✅ **ERIK Logo Branding**: Replaced "Replit Agent" with custom ERIK logo throughout the application
2. ✅ **Security Disclaimer**: Added comprehensive legal disclaimers about data security and multi-tenant architecture  
3. ✅ **Claude AI Assistant**: Integrated Anthropic Claude AI for intelligent business insights and recommendations
4. ✅ **Statutory Obligations Dashboard**: Real-time compliance monitoring for PAYE, NAPSA, NHIMA with ZRA integration readiness
5. ✅ **Department-to-Company Reporting**: Hierarchical department structure with consolidated P&L and Balance Sheet reports

**Key Implementation Details:**
- **Department Model**: Hierarchical structure with parent-child relationships, manager assignment, and full multi-tenant security
- **Dimensional Tracking**: All transactions (Journal Entry, Sales Order, Purchase Order) and Employees now track department_id and branch_id
- **Consolidated Reports**: P&L and Balance Sheet aggregation by department/branch/company with revenue, expense, asset, liability, and equity categorization
- **Multi-Tenant Security**: Comprehensive validation prevents cross-tenant references for departments, branches, managers, parents, and all foreign keys
- **Employee Schema**: Updated to use department_id foreign key instead of string for proper relational integrity
- **Beautiful UI**: Modern department management interface with CRUD operations and consolidated reports with drill-down capabilities

**Security Enhancements:**
- All transaction create endpoints validate department_id and branch_id ownership
- Department CRUD validates parent_dept_id and manager_id ownership  
- Employee creation validates department_id ownership
- Lowercase account type taxonomy alignment across all queries
- Production-ready with architect approval

## User Preferences
- **Primary Color**: Teal/Green (#00D9A3) as shown in ERIK logo
- **Goal**: Build a comprehensive ERP to compete with Odoo and SAP
- **Target Market**: Initially Zambian businesses, expandable globally
- **Business Model**: Multi-tier SaaS (Free, Basic, Premium, Enterprise)

## System Architecture

### Core Features
- **Multi-Tenant SaaS Architecture**: Isolated data for each company, secure JWT authentication, Role-Based Access Control (RBAC), and company registration with automatic setup. Endpoints validate company ownership for data isolation.
- **Finance & Accounting**: Chart of Accounts, Journal Entries (double-entry), Financial Reports (P&L, Balance Sheet), real-time reporting, multi-currency support (default ZMW).
- **HR & Payroll**: Employee Management, Employment Status Tracking, Zambian Payroll Engine (PAYE, NAPSA, NHIMA calculations), automated payslip generation, Leave Management with approval workflows and balance tracking.
- **Inventory Management**: Product catalog, multi-location warehouses, real-time stock levels, and stock movement tracking.
- **Sales & CRM**: Customer Management, multi-line Sales Orders with auto-numbering, status tracking, and delivery management.
- **Procurement**: Supplier Management, multi-line Purchase Orders with auto-numbering, status tracking, and expected delivery dates.
- **Mobile Money Integration**: Provider management (MTN Money, Airtel Money, Zamtel Kwacha), payment collection/disbursement, transaction tracking, and reconciliation.
- **Point of Sale (POS)**: Fast checkout, multi-payment methods, receipt generation, terminal management, sales tracking, and cashier sessions.
- **Multi-Branch Operations**: Branch creation and hierarchy, inter-branch transfers, branch-level reporting, and manager assignment.
- **Super Admin Platform**: Tenant management, subscription control (Trial/Basic/Premium/Enterprise), company activation, system analytics, and a 7-day free trial for new registrations.
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
- **Mobile Money Providers**: MTN Money, Airtel Money, Zamtel Kwacha (integrated)