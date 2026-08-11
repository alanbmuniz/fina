"""
Schemas Pydantic — validação de entrada/saída da API.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.models import TransactionType, TransactionCategory


# ─── Auth ─────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    name:           str       = Field(..., min_length=2, max_length=120)
    email:          EmailStr
    password:       str       = Field(..., min_length=8)
    phone:          Optional[str] = None
    monthly_income: float     = Field(default=0.0, ge=0)

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          "UserOut"

class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id:             int
    name:           str
    email:          str
    phone:          Optional[str]
    monthly_income: float
    avatar_url:     Optional[str]
    is_verified:    bool
    created_at:     datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name:           Optional[str]  = Field(None, min_length=2, max_length=120)
    phone:          Optional[str]  = None
    monthly_income: Optional[float] = Field(None, ge=0)
    avatar_url:     Optional[str]  = None


# ─── Transaction ──────────────────────────────────────────────────────────────
class TransactionCreate(BaseModel):
    type:        TransactionType
    description: str             = Field(..., min_length=1, max_length=255)
    amount:      float           = Field(..., gt=0)
    category:    TransactionCategory = TransactionCategory.outros
    date:        datetime
    notes:       Optional[str]   = None
    card_id:     Optional[int]   = None
    is_recurring: bool           = False
    tags:        List[str]       = []

class TransactionOut(BaseModel):
    id:          int
    type:        str
    description: str
    amount:      float
    category:    str
    date:        datetime
    notes:       Optional[str]
    card_id:     Optional[int]
    is_recurring: bool
    tags:        List[str]
    created_at:  datetime

    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    description: Optional[str]   = None
    amount:      Optional[float] = Field(None, gt=0)
    category:    Optional[TransactionCategory] = None
    notes:       Optional[str]   = None
    tags:        Optional[List[str]] = None


# ─── CreditCard ───────────────────────────────────────────────────────────────
class CardCreate(BaseModel):
    name:         str   = Field(..., min_length=2, max_length=120)
    last_four:    Optional[str] = Field(None, min_length=4, max_length=4)
    limit_amount: float = Field(..., gt=0)
    used_amount:  float = Field(default=0.0, ge=0)
    closing_day:  Optional[int] = Field(None, ge=1, le=31)
    due_day:      Optional[int] = Field(None, ge=1, le=31)
    color:        str   = "#6366f1"

class CardOut(BaseModel):
    id:            int
    name:          str
    last_four:     Optional[str]
    limit_amount:  float
    used_amount:   float
    closing_day:   Optional[int]
    due_day:       Optional[int]
    color:         str
    is_connected:  bool
    last_sync:     Optional[datetime]
    created_at:    datetime

    class Config:
        from_attributes = True


# ─── Goal ─────────────────────────────────────────────────────────────────────
class GoalCreate(BaseModel):
    name:          str   = Field(..., min_length=2, max_length=255)
    description:   Optional[str] = None
    target_amount: float = Field(..., gt=0)
    saved_amount:  float = Field(default=0.0, ge=0)
    deadline:      Optional[datetime] = None
    icon:          str   = "🎯"

class GoalOut(BaseModel):
    id:            int
    name:          str
    description:   Optional[str]
    target_amount: float
    saved_amount:  float
    deadline:      Optional[datetime]
    icon:          str
    is_completed:  bool
    created_at:    datetime
    completed_at:  Optional[datetime]

    class Config:
        from_attributes = True

class GoalUpdate(BaseModel):
    saved_amount:  Optional[float] = Field(None, ge=0)
    target_amount: Optional[float] = Field(None, gt=0)
    deadline:      Optional[datetime] = None
    description:   Optional[str] = None


# ─── Chat ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class ChatMessageOut(BaseModel):
    id:         int
    role:       str
    content:    str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    reply:    str
    messages: List[ChatMessageOut]


# ─── Reports ──────────────────────────────────────────────────────────────────
class MonthlyReport(BaseModel):
    month:         str
    total_income:  float
    total_expense: float
    balance:       float
    by_category:   dict
    top_expenses:  List[TransactionOut]

class FinancialHealth(BaseModel):
    score:            int          # 0–100
    label:            str          # "Excelente", "Boa", "Regular", "Crítica"
    card_usage_pct:   float
    savings_rate_pct: float
    alerts:           List[str]
    suggestions:      List[str]


# Atualizar referência forward
TokenResponse.model_rebuild()