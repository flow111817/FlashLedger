from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

# --- 数据库设置 ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/ledger.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 数据模型 ---

class Ledger(Base):
    __tablename__ = "ledgers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    budget = Column(Float, default=0.0) # 新增预算字段
    created = Column(DateTime, default=datetime.now)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    # 这里关联 Ledger 表，但为了兼容旧数据，暂时不做强外键约束，只存 ID
    ledger_id = Column(Integer, index=True) 
    amount = Column(Float)
    category = Column(String)
    type = Column(String)
    date = Column(String)
    note = Column(String, nullable=True)
    created = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class LedgerCreate(BaseModel):
    name: str
    budget: float = 0.0

class LedgerUpdate(BaseModel):
    name: str = None
    budget: float = None

class TransactionCreate(BaseModel):
    ledger_id: int
    amount: float
    category: str
    type: str
    date: str
    note: str = ""

# --- FastAPI App ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API: Ledgers (账本 + 预算) ---
@app.get("/ledgers")
def get_ledgers(db: Session = Depends(get_db)):
    return db.query(Ledger).order_by(Ledger.created.desc()).all()

@app.post("/ledgers")
def create_ledger(item: LedgerCreate, db: Session = Depends(get_db)):
    db_ledger = Ledger(name=item.name, budget=item.budget)
    db.add(db_ledger)
    db.commit()
    db.refresh(db_ledger)
    return db_ledger

@app.put("/ledgers/{l_id}")
def update_ledger(l_id: int, item: LedgerUpdate, db: Session = Depends(get_db)):
    db_ledger = db.query(Ledger).filter(Ledger.id == l_id).first()
    if not db_ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    if item.name is not None:
        db_ledger.name = item.name
    if item.budget is not None:
        db_ledger.budget = item.budget
    db.commit()
    db.refresh(db_ledger)
    return db_ledger

@app.delete("/ledgers/{l_id}")
def delete_ledger(l_id: int, db: Session = Depends(get_db)):
    db_ledger = db.query(Ledger).filter(Ledger.id == l_id).first()
    if not db_ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    # 删除账本同时删除关联的交易
    db.query(Transaction).filter(Transaction.ledger_id == l_id).delete()
    db.delete(db_ledger)
    db.commit()
    return {"ok": True}

# --- API: Transactions ---
@app.get("/transactions")
def read_transactions(ledger_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if ledger_id:
        query = query.filter(Transaction.ledger_id == ledger_id)
    return query.order_by(Transaction.date.desc(), Transaction.created.desc()).all()

@app.post("/transactions")
def create_transaction(item: TransactionCreate, db: Session = Depends(get_db)):
    db_item = Transaction(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/transactions/{t_id}")
def update_transaction(t_id: int, item: TransactionCreate, db: Session = Depends(get_db)):
    db_item = db.query(Transaction).filter(Transaction.id == t_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/transactions/{t_id}")
def delete_transaction(t_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Transaction).filter(Transaction.id == t_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(db_item)
    db.commit()
    return {"ok": True}