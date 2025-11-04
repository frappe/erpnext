# 📡 ERIK ERP - API Documentation

**Complete API endpoint reference for ERIK ERP**

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core Modules](#core-modules)
4. [Industry Addons](#industry-addons)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## 🌐 Overview

### Base URL

**Development:**
```
http://localhost:8000
```

**Production:**
```
https://your-domain.com
```

### Interactive Documentation

- **Swagger UI**: `/docs` - Interactive API explorer
- **ReDoc**: `/redoc` - Clean API reference

### Content Type

All requests and responses use JSON:
```
Content-Type: application/json
```

### Authentication

Most endpoints require JWT authentication:
```
Authorization: Bearer <jwt_token>
```

---

## 🔐 Authentication

### POST `/api/auth/register`
Register a new company and user

**Request:**
```json
{
  "company_name": "ABC Ltd",
  "industry": "retail",
  "email": "admin@abc.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@abc.com",
    "full_name": "John Doe",
    "role": "admin",
    "company_id": "uuid"
  }
}
```

---

### POST `/api/auth/login`
Login with email and password

**Request:**
```json
{
  "email": "admin@abc.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@abc.com",
    "full_name": "John Doe",
    "role": "admin",
    "company_id": "uuid"
  }
}
```

---

### GET `/api/auth/me`
Get current user information

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "email": "admin@abc.com",
  "full_name": "John Doe",
  "role": "admin",
  "company_id": "uuid",
  "company": {
    "id": "uuid",
    "name": "ABC Ltd",
    "subscription_plan": "trial",
    "subscription_status": "active"
  }
}
```

---

## 🏢 Core Modules

### Employees

#### GET `/api/employees`
List all employees (company-scoped)

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": "uuid",
    "employee_number": "EMP001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@abc.com",
    "position": "Software Engineer",
    "department_id": "uuid",
    "branch_id": "uuid",
    "salary": 15000.00,
    "employment_status": "active",
    "nrc_number": "123456/78/1",
    "napsa_number": "NA123456",
    "tpin": "1234567890"
  }
]
```

---

#### POST `/api/employees`
Create a new employee

**Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@abc.com",
  "position": "Accountant",
  "department_id": "uuid",
  "branch_id": "uuid",
  "salary": 12000.00,
  "employment_status": "active",
  "nrc_number": "987654/32/1",
  "napsa_number": "NA987654",
  "tpin": "0987654321"
}
```

**Response:**
```json
{
  "id": "uuid",
  "employee_number": "EMP002",
  "first_name": "Jane",
  "last_name": "Smith",
  "company_id": "uuid",
  "created_at": "2025-11-04T10:00:00"
}
```

---

### Finance

#### GET `/api/finance/chart-of-accounts`
Get chart of accounts (hierarchical)

**Response:**
```json
[
  {
    "id": "uuid",
    "account_code": "1000",
    "account_name": "Assets",
    "account_type": "asset",
    "parent_account_id": null,
    "currency": "ZMW",
    "balance": 1000000.00,
    "children": [
      {
        "id": "uuid",
        "account_code": "1100",
        "account_name": "Current Assets",
        "parent_account_id": "uuid",
        "balance": 500000.00
      }
    ]
  }
]
```

---

#### POST `/api/finance/accounts`
Create a new account

**Request:**
```json
{
  "account_code": "1510",
  "account_name": "Office Equipment",
  "account_type": "asset",
  "parent_account_id": "uuid",
  "currency": "ZMW",
  "allow_fx_revaluation": false
}
```

---

#### POST `/api/finance/journal-entries`
Create a journal entry

**Request:**
```json
{
  "journal_number": "JE-2025-001",
  "date": "2025-11-04",
  "description": "Office rent payment",
  "currency": "ZMW",
  "department_id": "uuid",
  "branch_id": "uuid",
  "lines": [
    {
      "account_id": "uuid",
      "debit": 5000.00,
      "credit": 0.00,
      "description": "Rent expense"
    },
    {
      "account_id": "uuid",
      "debit": 0.00,
      "credit": 5000.00,
      "description": "Cash payment"
    }
  ]
}
```

**Response:**
```json
{
  "id": "uuid",
  "journal_number": "JE-2025-001",
  "total_amount": 5000.00,
  "status": "draft",
  "created_at": "2025-11-04T10:00:00"
}
```

---

#### POST `/api/finance/journal-entries/{id}/post`
Post a journal entry (change status from draft to posted)

**Response:**
```json
{
  "id": "uuid",
  "status": "posted",
  "posted_at": "2025-11-04T10:05:00"
}
```

---

#### GET `/api/finance/reports/profit-loss`
Profit & Loss statement

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)
- `department_id` - Optional department filter
- `branch_id` - Optional branch filter

**Response:**
```json
{
  "report_type": "profit_loss",
  "period": {
    "start_date": "2025-01-01",
    "end_date": "2025-11-04"
  },
  "revenue": 500000.00,
  "expenses": 300000.00,
  "net_profit": 200000.00,
  "revenue_accounts": [...],
  "expense_accounts": [...]
}
```

---

#### GET `/api/finance/reports/balance-sheet`
Balance Sheet

**Query Parameters:**
- `as_of_date` - Report date (YYYY-MM-DD)

**Response:**
```json
{
  "report_type": "balance_sheet",
  "as_of_date": "2025-11-04",
  "total_assets": 2000000.00,
  "total_liabilities": 800000.00,
  "total_equity": 1200000.00,
  "assets": [...],
  "liabilities": [...],
  "equity": [...]
}
```

---

### Payroll

#### POST `/api/payroll/generate`
Generate payslips for a month

**Request:**
```json
{
  "month": 11,
  "year": 2025
}
```

**Response:**
```json
{
  "payslips_generated": 50,
  "total_gross": 750000.00,
  "total_paye": 125000.00,
  "total_napsa": 37500.00,
  "total_nhima": 7500.00,
  "total_net": 580000.00
}
```

---

#### GET `/api/payroll/payslips`
List payslips

**Query Parameters:**
- `month` - Month (1-12)
- `year` - Year (e.g., 2025)
- `employee_id` - Optional employee filter

**Response:**
```json
[
  {
    "id": "uuid",
    "employee_id": "uuid",
    "employee_name": "John Doe",
    "month": 11,
    "year": 2025,
    "basic_salary": 15000.00,
    "gross_salary": 15000.00,
    "paye": 2500.00,
    "napsa": 750.00,
    "nhima": 150.00,
    "net_salary": 11600.00,
    "status": "approved"
  }
]
```

---

### Inventory

#### GET `/api/inventory/products`
List all products

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Laptop Dell XPS 13",
    "sku": "LAPTOP-001",
    "category": "Electronics",
    "price": 8000.00,
    "cost": 6000.00,
    "stock_quantity": 25,
    "reorder_level": 5,
    "unit_of_measure": "piece"
  }
]
```

---

#### POST `/api/inventory/products`
Create a new product

**Request:**
```json
{
  "name": "iPhone 15 Pro",
  "sku": "PHONE-001",
  "category": "Electronics",
  "price": 12000.00,
  "cost": 9000.00,
  "reorder_level": 10,
  "unit_of_measure": "piece"
}
```

---

#### GET `/api/inventory/warehouses`
List all warehouses

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Main Warehouse",
    "location": "Lusaka",
    "type": "warehouse",
    "is_active": true
  }
]
```

---

#### POST `/api/inventory/stock-movement`
Record stock movement

**Request:**
```json
{
  "product_id": "uuid",
  "warehouse_id": "uuid",
  "movement_type": "in",
  "quantity": 100,
  "reason": "Purchase receipt",
  "reference_number": "PO-001"
}
```

---

### Sales

#### GET `/api/sales/orders`
List sales orders

**Response:**
```json
[
  {
    "id": "uuid",
    "order_number": "SO-2025-001",
    "customer_id": "uuid",
    "customer_name": "ABC Corp",
    "order_date": "2025-11-04",
    "total_amount": 50000.00,
    "status": "confirmed",
    "lines": [
      {
        "product_id": "uuid",
        "product_name": "Laptop Dell XPS 13",
        "quantity": 5,
        "unit_price": 8000.00,
        "total": 40000.00
      }
    ]
  }
]
```

---

#### POST `/api/sales/orders`
Create a sales order

**Request:**
```json
{
  "customer_id": "uuid",
  "order_date": "2025-11-04",
  "delivery_date": "2025-11-10",
  "lines": [
    {
      "product_id": "uuid",
      "quantity": 3,
      "unit_price": 8000.00
    }
  ]
}
```

---

### Procurement

#### GET `/api/procurement/purchase-orders`
List purchase orders

**Response:**
```json
[
  {
    "id": "uuid",
    "po_number": "PO-2025-001",
    "supplier_id": "uuid",
    "supplier_name": "Tech Supplies Ltd",
    "order_date": "2025-11-04",
    "total_amount": 60000.00,
    "status": "approved"
  }
]
```

---

### Banking

#### GET `/api/banking/connections`
List bank connections

**Response:**
```json
[
  {
    "id": "uuid",
    "bank_name": "ZANACO",
    "account_number": "1234567890",
    "account_name": "ABC Ltd Operating Account",
    "currency": "ZMW",
    "current_balance": 500000.00,
    "last_sync": "2025-11-04T08:00:00",
    "is_active": true
  }
]
```

---

#### POST `/api/banking/sync/{connection_id}`
Sync bank transactions

**Response:**
```json
{
  "transactions_imported": 25,
  "last_sync": "2025-11-04T10:00:00"
}
```

---

#### POST `/api/banking/reconcile`
Auto-reconcile bank transactions

**Request:**
```json
{
  "bank_connection_id": "uuid",
  "start_date": "2025-11-01",
  "end_date": "2025-11-04"
}
```

**Response:**
```json
{
  "matched": 20,
  "unmatched": 5,
  "suggested_matches": [
    {
      "bank_transaction_id": "uuid",
      "journal_entry_id": "uuid",
      "confidence": 0.95
    }
  ]
}
```

---

### Mobile Money

#### GET `/api/mobile-money/providers`
List mobile money providers

**Response:**
```json
[
  {
    "id": "uuid",
    "provider_name": "MTN Money",
    "phone_number": "+260971234567",
    "account_name": "ABC Ltd",
    "balance": 50000.00,
    "is_active": true
  }
]
```

---

### Compliance

#### GET `/api/compliance/statutory-obligations`
Get statutory obligations summary

**Response:**
```json
{
  "paye": {
    "current_month": 125000.00,
    "ytd": 1500000.00,
    "status": "pending",
    "due_date": "2025-11-10"
  },
  "napsa": {
    "employee_contribution": 37500.00,
    "employer_contribution": 37500.00,
    "total": 75000.00,
    "status": "pending",
    "due_date": "2025-11-10"
  },
  "nhima": {
    "current_month": 7500.00,
    "ytd": 90000.00,
    "status": "pending",
    "due_date": "2025-11-10"
  }
}
```

---

### Dashboard

#### GET `/api/dashboard/stats`
Get dashboard statistics

**Response:**
```json
{
  "employees": 50,
  "departments": 8,
  "branches": 3,
  "chart_of_accounts": 150,
  "journal_entries": 500,
  "products": 200,
  "warehouses": 5,
  "sales_orders": 75,
  "purchase_orders": 60,
  "customers": 100,
  "suppliers": 45,
  "bank_accounts": 4,
  "payslips_generated": 50,
  "active_addons": 3,
  "subscription_plan": "premium",
  "subscription_status": "active"
}
```

---

## 🎨 Industry Addons

### Addon Marketplace

#### GET `/api/addons/marketplace`
List all available addons

**Response:**
```json
[
  {
    "id": "uuid",
    "addon_code": "construction",
    "addon_name": "Construction & Real Estate",
    "description": "Project management, job costing, BOQ, contractor management",
    "category": "Industry",
    "monthly_price": 50.00,
    "pricing_model": "per_user",
    "features": "Project & Job Costing, Bill of Quantities, Procurement Tracking, Contractor Management",
    "icon": "🏗️",
    "is_official": true
  }
]
```

---

#### GET `/api/addons/my-addons`
List activated addons for current company

**Response:**
```json
[
  {
    "addon_id": "uuid",
    "addon_code": "construction",
    "addon_name": "Construction & Real Estate",
    "activated_at": "2025-10-01T10:00:00",
    "is_active": true
  }
]
```

---

#### POST `/api/addons/activate`
Activate an addon

**Request:**
```json
{
  "addon_id": "uuid"
}
```

**Response:**
```json
{
  "message": "Addon activated successfully",
  "addon_code": "construction",
  "activated_at": "2025-11-04T10:00:00"
}
```

---

#### POST `/api/addons/deactivate/{addon_id}`
Deactivate an addon

**Response:**
```json
{
  "message": "Addon deactivated successfully",
  "addon_code": "construction"
}
```

---

### Construction Addon

#### GET `/api/construction/projects`
List construction projects

**Response:**
```json
[
  {
    "id": "uuid",
    "project_name": "Office Building - Lusaka CBD",
    "project_code": "PROJ-001",
    "client_name": "XYZ Developers",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "budget": 5000000.00,
    "actual_cost": 2500000.00,
    "status": "in_progress"
  }
]
```

---

### Agriculture Addon

#### GET `/api/agriculture/farms`
List farms

**Response:**
```json
[
  {
    "id": "uuid",
    "farm_name": "Green Valley Farm",
    "location": "Chongwe",
    "size_hectares": 100.5,
    "farm_type": "crop",
    "primary_crop": "Maize"
  }
]
```

---

### Healthcare Addon

#### GET `/api/healthcare/patients`
List patients

**Response:**
```json
[
  {
    "id": "uuid",
    "patient_number": "PAT-001",
    "first_name": "Alice",
    "last_name": "Banda",
    "date_of_birth": "1990-05-15",
    "gender": "female",
    "phone_number": "+260971234567",
    "nrc_number": "123456/78/1"
  }
]
```

---

## 🎯 AI & OCR

### AI Assistant

#### POST `/api/chat/message`
Send a message to Claude AI assistant

**Request:**
```json
{
  "message": "What was our total revenue last month?"
}
```

**Response:**
```json
{
  "response": "Based on your financial data, your total revenue for October 2025 was K450,000. This represents a 15% increase compared to September.",
  "timestamp": "2025-11-04T10:00:00"
}
```

---

### OCR

#### POST `/api/ocr/upload`
Upload and process a document

**Request:**
```
Content-Type: multipart/form-data

file: <invoice.pdf>
document_type: invoice
```

**Response:**
```json
{
  "id": "uuid",
  "document_type": "invoice",
  "extracted_data": {
    "invoice_number": "INV-2025-001",
    "invoice_date": "2025-11-01",
    "supplier_name": "Tech Supplies Ltd",
    "total_amount": 25000.00,
    "line_items": [
      {
        "description": "Laptop HP ProBook",
        "quantity": 2,
        "unit_price": 10000.00,
        "total": 20000.00
      }
    ]
  },
  "confidence": 0.95,
  "status": "processed"
}
```

---

## ⚠️ Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Common Error Examples

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found:**
```json
{
  "detail": "Employee not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 🚦 Rate Limiting

**Current Status**: Not implemented

**Planned**:
- 100 requests/minute per user
- 1000 requests/hour per company
- Rate limit headers in responses

---

## 📝 Notes

1. **Multi-Tenancy**: All endpoints automatically filter by `company_id` from JWT token
2. **Pagination**: Not yet implemented (planned for large datasets)
3. **Filtering**: Most list endpoints accept query parameters for filtering
4. **Sorting**: Not yet implemented (planned)
5. **Webhooks**: Not yet implemented (planned for integrations)

---

## 🔗 Additional Resources

- **Interactive Docs**: `/docs` - Swagger UI
- **OpenAPI Schema**: `/openapi.json`
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Project Structure**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

*Last updated: November 4, 2025*
