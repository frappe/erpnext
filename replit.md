# ERIK ERP - Enterprise Resource & Intelligence Kernel

## Overview
ERIK ERP is a modern, multi-tenant SaaS enterprise resource planning system designed to manage Finance, HR, Payroll, Inventory, and more. It aims to be a comprehensive ERP system competing with leading solutions, specifically tailored for businesses in Zambia and beyond. The project provides foundational architecture and core modules for future expansion.

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