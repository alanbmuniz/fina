"""
Rotas de transações financeiras (receitas e despesas).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Transaction, TransactionType
from app.schemas.schemas import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter()


@router.get("/", response_model=List[TransactionOut])
async def list_transactions(
    month: Optional[int]  = Query(None, ge=1, le=12),
    year:  Optional[int]  = Query(None, ge=2000),
    type:  Optional[str]  = Query(None),
    limit: int            = Query(50, le=200),
    offset: int           = Query(0, ge=0),
    db: AsyncSession      = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Lista transações do usuário com filtros opcionais."""
    q = select(Transaction).where(Transaction.user_id == current_user.id)

    if month:
        q = q.where(extract("month", Transaction.date) == month)
    if year:
        q = q.where(extract("year", Transaction.date) == year)
    if type:
        q = q.where(Transaction.type == type)

    q = q.order_by(Transaction.date.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=TransactionOut, status_code=201)
async def create_transaction(
    payload: TransactionCreate,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria nova transação."""
    tx = Transaction(user_id=current_user.id, **payload.model_dump())
    db.add(tx)
    await db.flush()
    return tx


@router.get("/{tx_id}", response_model=TransactionOut)
async def get_transaction(
    tx_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == current_user.id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transação não encontrada")
    return tx


@router.patch("/{tx_id}", response_model=TransactionOut)
async def update_transaction(
    tx_id: int,
    payload: TransactionUpdate,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == current_user.id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transação não encontrada")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tx, field, value)
    return tx


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == current_user.id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transação não encontrada")
    await db.delete(tx)


@router.get("/summary/monthly")
async def monthly_summary(
    year:  int         = Query(..., ge=2000),
    month: int         = Query(..., ge=1, le=12),
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resumo financeiro mensal: receitas, despesas, saldo e breakdown por categoria."""
    q = select(Transaction).where(
        Transaction.user_id == current_user.id,
        extract("year",  Transaction.date) == year,
        extract("month", Transaction.date) == month,
    )
    result = await db.execute(q)
    txs = result.scalars().all()

    total_income  = sum(t.amount for t in txs if t.type == TransactionType.income)
    total_expense = sum(t.amount for t in txs if t.type == TransactionType.expense)
    by_category   = {}
    for t in txs:
        if t.type == TransactionType.expense:
            by_category[t.category.value] = by_category.get(t.category.value, 0) + t.amount

    return {
        "year": year, "month": month,
        "total_income":  round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance":       round(total_income - total_expense, 2),
        "by_category":   {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
        "transaction_count": len(txs),
    }