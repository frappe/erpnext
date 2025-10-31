from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
import schemas
import auth
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ERIK ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "ERIK ERP API is running", "version": "1.0.0"}

@app.post("/api/auth/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    company = models.Company(
        name=user.company_name,
        currency="ZMW"
    )
    db.add(company)
    db.flush()
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role="admin",
        company_id=company.id
    )
    db.add(new_user)
    
    default_accounts = [
        {"code": "1000", "name": "Assets", "type": "asset"},
        {"code": "1100", "name": "Current Assets", "type": "asset", "parent": "1000"},
        {"code": "1110", "name": "Cash and Bank", "type": "asset", "parent": "1100"},
        {"code": "1120", "name": "Accounts Receivable", "type": "asset", "parent": "1100"},
        {"code": "2000", "name": "Liabilities", "type": "liability"},
        {"code": "2100", "name": "Current Liabilities", "type": "liability", "parent": "2000"},
        {"code": "2110", "name": "Accounts Payable", "type": "liability", "parent": "2100"},
        {"code": "3000", "name": "Equity", "type": "equity"},
        {"code": "4000", "name": "Revenue", "type": "revenue"},
        {"code": "5000", "name": "Expenses", "type": "expense"},
        {"code": "5100", "name": "Operating Expenses", "type": "expense", "parent": "5000"},
        {"code": "5200", "name": "Payroll Expenses", "type": "expense", "parent": "5000"},
    ]
    
    accounts_map = {}
    for acc_data in default_accounts:
        parent_id = accounts_map.get(acc_data.get("parent"))
        account = models.Account(
            company_id=company.id,
            code=acc_data["code"],
            name=acc_data["name"],
            account_type=acc_data["type"],
            parent_id=parent_id
        )
        db.add(account)
        accounts_map[acc_data["code"]] = account
    
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/api/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    total_employees = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id
    ).count()
    
    total_accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id
    ).count()
    
    total_journals = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).count()
    
    return {
        "total_employees": total_employees,
        "total_accounts": total_accounts,
        "total_journals": total_journals,
        "company_name": company.name if company else "Unknown"
    }

@app.get("/api/employees", response_model=list[schemas.EmployeeResponse])
def get_employees(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    employees = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id
    ).all()
    return employees

@app.post("/api/employees", response_model=schemas.EmployeeResponse)
def create_employee(
    employee: schemas.EmployeeCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_employee = models.Employee(
        company_id=current_user.company_id,
        **employee.dict()
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@app.get("/api/accounts", response_model=list[schemas.AccountResponse])
def get_accounts(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id
    ).all()
    return accounts

@app.post("/api/accounts", response_model=schemas.AccountResponse)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_account = models.Account(
        company_id=current_user.company_id,
        **account.dict()
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@app.get("/api/journals", response_model=list[schemas.JournalEntryResponse])
def get_journals(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    journals = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).order_by(models.JournalEntry.date.desc()).all()
    return journals

@app.post("/api/journals", response_model=schemas.JournalEntryResponse)
def create_journal(
    journal: schemas.JournalEntryCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    journal_count = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).count()
    
    journal_number = f"JE-{journal_count + 1:05d}"
    
    new_journal = models.JournalEntry(
        company_id=current_user.company_id,
        journal_number=journal_number,
        date=journal.date,
        description=journal.description,
        currency=journal.currency,
        total_amount=journal.total_amount,
        created_by=current_user.id,
        status="posted"
    )
    db.add(new_journal)
    db.flush()
    
    for line in journal.lines:
        journal_line = models.JournalLine(
            journal_id=new_journal.id,
            **line.dict()
        )
        db.add(journal_line)
    
    db.commit()
    db.refresh(new_journal)
    return new_journal

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
