# 🔧 ERIK ERP - Developer Guide

**Complete technical documentation for developers building and extending ERIK ERP**

---

## 📖 Table of Contents

1. [Getting Started](#getting-started)
2. [Architecture Overview](#architecture-overview)
3. [Database Schema](#database-schema)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [API Development](#api-development)
7. [Authentication & Authorization](#authentication--authorization)
8. [Multi-Tenancy](#multi-tenancy)
9. [Zambian Compliance](#zambian-compliance)
10. [Testing](#testing)
11. [Debugging](#debugging)
12. [Performance Optimization](#performance-optimization)
13. [Security Best Practices](#security-best-practices)
14. [Contributing](#contributing)

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** - Backend programming language
- **Node.js 20+** - Frontend build tools
- **PostgreSQL 16+** - Database
- **Git** - Version control
- **Anthropic API Key** - AI features (optional for development)

### Initial Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd erik-erp
```

2. **Create PostgreSQL database:**
```bash
createdb erikerp
```

3. **Set up environment variables:**
```bash
# Create .env file in backend/
DATABASE_URL=postgresql://user:password@localhost:5432/erikerp
ANTHROPIC_API_KEY=sk-ant-xxxxx
SECRET_KEY=your-secret-key-here
```

4. **Install backend dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

5. **Install frontend dependencies:**
```bash
cd frontend
npm install
```

6. **Initialize database (automatic on first run):**
The application automatically creates all tables on startup using SQLAlchemy models.

7. **Run development servers:**

Terminal 1 (Backend):
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

8. **Access the application:**
- Frontend: http://localhost:5000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🏗 Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  React 18 + Vite + Tailwind CSS + React Router              │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Pages    │  │Components│  │ Services │  │  Styles  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST (Axios)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                     Backend API                              │
│  FastAPI + SQLAlchemy + Pydantic + JWT                      │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Routers  │  │ Services │  │  Models  │  │  Auth    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ SQL (SQLAlchemy ORM)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    PostgreSQL 16                             │
│  Multi-tenant database with company_id scoping              │
└─────────────────────────────────────────────────────────────┘

External Integrations:
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Anthropic API   │  │  Bank APIs       │  │  Mobile Money    │
│  (Claude AI)     │  │  (ZANACO, etc)   │  │  (MTN, Airtel)   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Key Design Patterns

#### 1. **Multi-Tenant Architecture**
- All tables have `company_id` foreign key
- Every API endpoint filters by `current_user.company_id`
- Database-level isolation ensures data security

#### 2. **MVC Pattern (Modified for API)**
- **Models** (`models.py`): SQLAlchemy ORM models
- **Schemas** (`schemas.py`): Pydantic request/response schemas
- **Routers** (`routers/*`): FastAPI route handlers
- **Services** (`services/*`): Business logic layer

#### 3. **Repository Pattern**
- Services encapsulate complex business logic
- Routers remain thin (validation + service calls)
- Example: `ZambianPayrollEngine` in `services/payroll/`

#### 4. **Dependency Injection**
- FastAPI's `Depends()` for database sessions
- `get_current_user()` dependency for authentication
- `get_db()` dependency for database access

---

## 💾 Database Schema

### Core Tables

#### Companies (Multi-Tenancy)
```python
companies
├── id (PK)
├── name
├── industry
├── subscription_plan (trial, basic, premium, enterprise)
├── subscription_status (active, suspended, cancelled)
├── trial_ends_at
└── created_at
```

#### Users (Authentication)
```python
users
├── id (PK)
├── company_id (FK → companies)
├── email (unique)
├── password_hash
├── full_name
├── role (super_admin, admin, manager, user)
└── is_active
```

#### Employees (HR)
```python
employees
├── id (PK)
├── company_id (FK → companies)
├── employee_number
├── first_name, last_name
├── nrc_number (Zambian National Registration Card)
├── napsa_number
├── tpin (Tax Payer Identification Number)
├── department_id (FK → departments)
├── branch_id (FK → branches)
├── salary, position
└── employment_status
```

#### Accounts (Finance)
```python
accounts
├── id (PK)
├── company_id (FK → companies)
├── account_code (unique per company)
├── account_name
├── account_type (asset, liability, equity, revenue, expense)
├── parent_account_id (FK → accounts, self-referencing)
├── currency (default: ZMW)
└── allow_fx_revaluation
```

#### Journal Entries (Finance)
```python
journal_entries
├── id (PK)
├── company_id (FK → companies)
├── journal_number
├── date
├── description
├── currency
├── total_amount
├── status (draft, posted)
├── department_id (FK → departments)
├── branch_id (FK → branches)
└── created_by

journal_lines (one-to-many)
├── id (PK)
├── journal_id (FK → journal_entries)
├── account_id (FK → accounts)
├── debit
├── credit
└── description
```

### Multi-Tenant Pattern

**Every tenant-scoped table follows this pattern:**

```python
class SomeModel(Base):
    __tablename__ = "some_table"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    # ... other fields
    
    # Relationship to company
    company = relationship("Company", back_populates="some_tables")
```

**Querying with multi-tenancy:**

```python
# ALWAYS filter by company_id
items = db.query(models.Product)\
    .filter(models.Product.company_id == current_user.company_id)\
    .all()
```

---

## 🐍 Backend Development

### Project Structure

```
backend/
├── routers/              # API endpoints (one file per module)
│   ├── finance.py       # /api/finance/*
│   ├── employees.py     # /api/employees/*
│   └── ...
├── services/             # Business logic
│   ├── payroll/
│   │   └── zambian_payroll_engine.py
│   └── ...
├── models.py             # SQLAlchemy models (ALL models)
├── schemas.py            # Pydantic schemas (ALL schemas)
├── main.py               # FastAPI app initialization
├── auth.py               # JWT authentication
├── database.py           # Database connection
└── utils.py              # Helper functions
```

### Adding a New API Endpoint

1. **Define Pydantic schema** in `schemas.py`:
```python
class ProductCreate(BaseModel):
    name: str
    sku: str
    price: float
    category: str

class ProductResponse(BaseModel):
    id: str
    company_id: str
    name: str
    sku: str
    price: float
    created_at: datetime
    
    class Config:
        from_attributes = True
```

2. **Define SQLAlchemy model** in `models.py`:
```python
class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="products")
```

3. **Create router** in `routers/products.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.post("/", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Create product
    db_product = models.Product(
        **product.dict(),
        company_id=current_user.company_id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[schemas.ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # ALWAYS filter by company_id
    products = db.query(models.Product)\
        .filter(models.Product.company_id == current_user.company_id)\
        .all()
    return products
```

4. **Register router** in `main.py`:
```python
from routers import products

app.include_router(products.router)
```

### Zambian Payroll Engine

The Zambian payroll engine implements 2025 tax rates:

```python
# services/payroll/zambian_payroll_engine.py

class ZambianPayrollEngine:
    # 2025 PAYE Brackets
    PAYE_BRACKETS = [
        (0, 4800, 0.00),        # First K4,800: 0%
        (4800, 9600, 0.20),     # Next K4,800: 20%
        (9600, 14400, 0.30),    # Next K4,800: 30%
        (14400, float('inf'), 0.375)  # Above K14,400: 37.5%
    ]
    
    # Statutory rates
    NAPSA_EMPLOYEE_RATE = 0.05  # 5%
    NAPSA_EMPLOYER_RATE = 0.05  # 5%
    NHIMA_RATE = 0.01           # 1%
    WORKERS_COMP_RATE = 0.01    # 1%
    
    def calculate_payroll(self, employee, basic_salary):
        # Calculate gross salary
        gross = basic_salary + allowances
        
        # Calculate NAPSA (capped at K23,707.80)
        napsa_deduction = min(gross * self.NAPSA_EMPLOYEE_RATE, 23707.80)
        
        # Calculate taxable income
        taxable = gross - napsa_deduction
        
        # Calculate PAYE
        paye = self._calculate_paye(taxable)
        
        # Calculate NHIMA
        nhima = gross * self.NHIMA_RATE
        
        # Calculate net salary
        net = gross - (paye + napsa_deduction + nhima)
        
        return {
            'gross': gross,
            'paye': paye,
            'napsa': napsa_deduction,
            'nhima': nhima,
            'net': net
        }
```

---

## ⚛️ Frontend Development

### Project Structure

```
frontend/src/
├── components/           # Reusable components
│   ├── Layout.jsx       # Main layout with sidebar
│   └── ...
├── pages/                # Page components (routes)
│   ├── Dashboard.jsx
│   ├── Employees.jsx
│   └── ...
├── services/
│   └── api.js           # Axios API client
├── styles/
│   └── index.css        # Tailwind + custom styles
├── App.jsx               # Main app with routing
└── main.jsx              # React entry point
```

### API Service (Axios)

```javascript
// services/api.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (redirect to login)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Creating a New Page

1. **Create page component** in `pages/MyNewPage.jsx`:
```jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

function MyNewPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  
  useEffect(() => {
    fetchData();
  }, []);
  
  const fetchData = async () => {
    try {
      const response = await api.get('/my-endpoint');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <div className="p-6">Loading...</div>;
  }
  
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">My New Page</h1>
      {/* Your content here */}
    </div>
  );
}

export default MyNewPage;
```

2. **Add route** in `App.jsx`:
```jsx
import MyNewPage from './pages/MyNewPage';

// Inside Routes
<Route path="/my-new-page" element={<MyNewPage />} />
```

3. **Add navigation** in `components/Layout.jsx`:
```jsx
<Link
  to="/my-new-page"
  className="flex items-center space-x-3 px-4 py-3 hover:bg-gray-700 rounded-lg"
>
  <MyIcon className="w-5 h-5" />
  <span>My New Page</span>
</Link>
```

### Tailwind Theme (ERIK Colors)

```javascript
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00D9A3',  // ERIK teal/green
          dark: '#00B388',
          light: '#33E3B8',
        },
        secondary: {
          DEFAULT: '#1E293B',  // Dark blue-gray
          light: '#334155',
        },
      },
    },
  },
};
```

---

## 🔐 Authentication & Authorization

### JWT Authentication Flow

```
1. User Login
   ↓
2. Backend validates credentials
   ↓
3. Backend generates JWT token
   ↓
4. Frontend stores token in localStorage
   ↓
5. Frontend includes token in all API requests
   (Authorization: Bearer <token>)
   ↓
6. Backend validates token on each request
   ↓
7. Backend extracts user_id from token
   ↓
8. Backend loads user from database
   ↓
9. Backend filters data by user.company_id
```

### Creating Protected Endpoints

```python
from fastapi import Depends
from auth import get_current_user
import models

@router.get("/protected")
def protected_endpoint(
    current_user: models.User = Depends(get_current_user)
):
    # current_user is automatically loaded from JWT token
    # Data is automatically filtered by company_id
    return {"message": f"Hello, {current_user.full_name}"}
```

### Role-Based Access Control

```python
def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.delete("/critical-action")
def critical_action(
    current_user: models.User = Depends(require_admin)
):
    # Only admins can access this endpoint
    pass
```

---

## 🏢 Multi-Tenancy

### Key Principles

1. **Every table has `company_id`**
2. **Every query filters by `company_id`**
3. **JWT token contains `user_id`, user contains `company_id`**
4. **Data isolation is enforced at database level**

### Multi-Tenant Query Pattern

```python
# CORRECT ✅
items = db.query(models.Item)\
    .filter(models.Item.company_id == current_user.company_id)\
    .all()

# INCORRECT ❌ (exposes all companies' data)
items = db.query(models.Item).all()
```

### Testing Multi-Tenancy

```python
# Create two companies
company1 = create_company("Company A")
company2 = create_company("Company B")

# Create users for each company
user1 = create_user(company1.id, "user1@companya.com")
user2 = create_user(company2.id, "user2@companyb.com")

# Create products for each company
product1 = create_product(company1.id, "Product A")
product2 = create_product(company2.id, "Product B")

# Test isolation
# User 1 should only see Product A
# User 2 should only see Product B
```

---

## 🇿🇲 Zambian Compliance

### PAYE (Pay As You Earn) - 2025 Rates

```python
# Monthly brackets (ZMW)
K0 - K4,800: 0%
K4,801 - K9,600: 20%
K9,601 - K14,400: 30%
K14,401+: 37.5%
```

### NAPSA (National Pension Scheme Authority)

```python
Employee contribution: 5% of gross salary
Employer contribution: 5% of gross salary
Maximum monthly contribution: K23,707.80 (based on max insurable earnings)
```

### NHIMA (National Health Insurance Management Authority)

```python
Employee contribution: 1% of gross salary
```

### Workers' Compensation

```python
Employer contribution: 1% of gross salary
```

### ZRA (Zambia Revenue Authority) Smart Invoice

```python
# Smart invoice requirements:
1. QR code with invoice details
2. UBL (Universal Business Language) XML export
3. TPIN validation
4. Electronic submission readiness
```

---

## 🧪 Testing

### Backend Testing

```bash
# Install pytest
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Example Test

```python
# tests/test_payroll.py
from services.payroll.zambian_payroll_engine import ZambianPayrollEngine

def test_paye_calculation():
    engine = ZambianPayrollEngine()
    
    # Test zero PAYE (below K4,800)
    paye = engine._calculate_paye(4000)
    assert paye == 0
    
    # Test 20% bracket
    paye = engine._calculate_paye(8000)
    assert paye == 640  # (8000 - 4800) * 0.20
    
    # Test multiple brackets
    paye = engine._calculate_paye(15000)
    expected = (4800 * 0) + (4800 * 0.20) + (4800 * 0.30) + (600 * 0.375)
    assert abs(paye - expected) < 0.01
```

---

## 🐛 Debugging

### Backend Debugging

```bash
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for debugging
import pdb; pdb.set_trace()
```

### Frontend Debugging

```javascript
// React DevTools (browser extension)
// Console logging
console.log('Debug:', data);

// Network tab (inspect API calls)
// React Error Boundaries
```

### Common Issues

**Issue: 401 Unauthorized**
```
Solution: Check JWT token in localStorage, verify token not expired
```

**Issue: Database connection failed**
```
Solution: Verify DATABASE_URL, check PostgreSQL is running
```

**Issue: CORS errors**
```
Solution: Ensure CORS is configured in FastAPI main.py
```

---

## ⚡ Performance Optimization

### Database Query Optimization

```python
# Use eager loading to avoid N+1 queries
from sqlalchemy.orm import joinedload

# SLOW ❌ (N+1 query problem)
orders = db.query(models.Order).all()
for order in orders:
    print(order.customer.name)  # Triggers separate query

# FAST ✅ (single query with join)
orders = db.query(models.Order)\
    .options(joinedload(models.Order.customer))\
    .all()
for order in orders:
    print(order.customer.name)  # No additional query
```

### Frontend Optimization

```javascript
// Use React.memo for expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  // Component code
});

// Use useMemo for expensive calculations
const sortedData = useMemo(
  () => data.sort((a, b) => a.value - b.value),
  [data]
);

// Use useCallback for event handlers
const handleClick = useCallback(() => {
  // Handler code
}, [dependencies]);
```

---

## 🔒 Security Best Practices

1. **Never commit secrets to Git**
2. **Always validate user input** (Pydantic handles this)
3. **Use parameterized queries** (SQLAlchemy ORM handles this)
4. **Implement rate limiting** (prevent brute-force attacks)
5. **Enable HTTPS in production**
6. **Keep dependencies updated** (`pip list --outdated`)
7. **Use environment variables** for sensitive config
8. **Implement audit logging** for critical actions
9. **Validate JWT tokens** on every request
10. **Sanitize user-generated content** (prevent XSS)

---

## 🤝 Contributing

### Code Style

**Backend (Python):**
- Follow PEP 8
- Use type hints
- Document functions with docstrings

**Frontend (JavaScript):**
- Use ES6+ features
- Functional components with hooks
- PropTypes or TypeScript

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "Add: My feature description"

# Push to remote
git push origin feature/my-feature

# Create pull request on GitHub
```

### Commit Message Convention

```
Add: New feature
Fix: Bug fix
Update: Update existing feature
Refactor: Code refactoring
Docs: Documentation changes
Test: Add tests
```

---

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **React Docs**: https://react.dev
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Tailwind CSS**: https://tailwindcss.com
- **PostgreSQL Docs**: https://www.postgresql.org/docs

---

**Happy coding! 🚀**

*For questions or issues, see [README.md](README.md) for support contacts.*
