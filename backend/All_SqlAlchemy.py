"""
Modelos do banco de dados (ORM SQLAlchemy).
Todas as tabelas da aplicação FINA.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────
class TransactionType(str, enum.Enum):
    income  = "income"
    expense = "expense"


class TransactionCategory(str, enum.Enum):
    alimentacao  = "Alimentação"
    moradia      = "Moradia"
    transporte   = "Transporte"
    saude        = "Saúde"
    lazer        = "Lazer"
    educacao     = "Educação"
    vestuario    = "Vestuário"
    investimento = "Investimento"
    salario      = "Salário"
    freelance    = "Freelance"
    outros       = "Outros"


# ─── User ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(120), nullable=False)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    phone            = Column(String(20), nullable=True)
    monthly_income   = Column(Float, default=0.0)
    avatar_url       = Column(String(500), nullable=True)
    is_active        = Column(Boolean, default=True)
    is_verified      = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    transactions     = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    cards            = relationship("CreditCard",  back_populates="user", cascade="all, delete-orphan")
    goals            = relationship("Goal",        back_populates="user", cascade="all, delete-orphan")
    chat_messages    = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens   = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


# ─── Transaction ─────────────────────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type         = Column(SAEnum(TransactionType), nullable=False)
    description  = Column(String(255), nullable=False)
    amount       = Column(Float, nullable=False)
    category     = Column(SAEnum(TransactionCategory), default=TransactionCategory.outros)
    date         = Column(DateTime(timezone=True), nullable=False)
    notes        = Column(Text, nullable=True)
    card_id      = Column(Integer, ForeignKey("credit_cards.id"), nullable=True)
    is_recurring = Column(Boolean, default=False)
    tags         = Column(JSON, default=list)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user         = relationship("User", back_populates="transactions")
    card         = relationship("CreditCard", back_populates="transactions")


# ─── CreditCard ──────────────────────────────────────────────────────────────
class CreditCard(Base):
    __tablename__ = "credit_cards"

    id                    = Column(Integer, primary_key=True, index=True)
    user_id               = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name                  = Column(String(120), nullable=False)
    last_four             = Column(String(4), nullable=True)
    limit_amount          = Column(Float, nullable=False)
    used_amount           = Column(Float, default=0.0)
    closing_day           = Column(Integer, nullable=True)   # dia de fechamento
    due_day               = Column(Integer, nullable=True)   # dia de vencimento
    color                 = Column(String(7), default="#6366f1")
    # Open Finance
    pluggy_item_id        = Column(String(255), nullable=True)  # ID da conexão bancária
    pluggy_account_id     = Column(String(255), nullable=True)
    last_sync             = Column(DateTime(timezone=True), nullable=True)
    is_connected          = Column(Boolean, default=False)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())

    user         = relationship("User", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")


# ─── Goal ────────────────────────────────────────────────────────────────────
class Goal(Base):
    __tablename__ = "goals"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name          = Column(String(255), nullable=False)
    description   = Column(Text, nullable=True)
    target_amount = Column(Float, nullable=False)
    saved_amount  = Column(Float, default=0.0)
    deadline      = Column(DateTime(timezone=True), nullable=True)
    icon          = Column(String(10), default="🎯")
    is_completed  = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    completed_at  = Column(DateTime(timezone=True), nullable=True)

    user          = relationship("User", back_populates="goals")


# ─── ChatMessage ─────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role       = Column(String(20), nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="chat_messages")


# ─── RefreshToken ────────────────────────────────────────────────────────────
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(500), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="refresh_tokens")