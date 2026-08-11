"""
Rotas de Metas (goals.py), Relatórios (reports.py) e Serviço de Usuário.
Arquivo combinado para organização.
"""

# ════════════════════════════════════════════════════════════════
# goals.py
# ════════════════════════════════════════════════════════════════
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Goal, Transaction, TransactionType
from app.schemas.schemas import GoalCreate, GoalOut, GoalUpdate, FinancialHealth

goals_router = APIRouter()


@goals_router.get("/", response_model=List[GoalOut])
async def list_goals(
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at.desc()))
    return result.scalars().all()


@goals_router.post("/", response_model=GoalOut, status_code=201)
async def create_goal(
    payload: GoalCreate,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = Goal(user_id=current_user.id, **payload.model_dump())
    db.add(goal)
    await db.flush()
    return goal


@goals_router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(goal, field, value)

    # Marca como concluída automaticamente
    if goal.saved_amount >= goal.target_amount and not goal.is_completed:
        goal.is_completed = True
        goal.completed_at = datetime.now(timezone.utc)
    return goal


@goals_router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")
    await db.delete(goal)


@goals_router.get("/{goal_id}/projection")
async def goal_projection(
    goal_id: int,
    monthly_contribution: float,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Projeta quantos meses faltam para atingir a meta com uma contribuição mensal."""
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")

    remaining = goal.target_amount - goal.saved_amount
    if monthly_contribution <= 0:
        return {"error": "Contribuição deve ser positiva"}
    if remaining <= 0:
        return {"months": 0, "message": "Meta já atingida! 🎉"}

    months = int(remaining / monthly_contribution) + (1 if remaining % monthly_contribution else 0)
    from datetime import date
    today = date.today()
    target_date = date(today.year + (today.month + months - 1) // 12, (today.month + months - 1) % 12 + 1, 1)

    return {
        "goal": goal.name,
        "remaining": round(remaining, 2),
        "monthly_contribution": monthly_contribution,
        "months_needed": months,
        "estimated_date": target_date.strftime("%B/%Y"),
    }


# ════════════════════════════════════════════════════════════════
# reports.py
# ════════════════════════════════════════════════════════════════
reports_router = APIRouter()

from app.models.models import CreditCard
from app.schemas.schemas import FinancialHealth


@reports_router.get("/health", response_model=FinancialHealth)
async def financial_health(
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calcula score de saúde financeira de 0 a 100."""
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == current_user.id,
            extract("year",  Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
    )
    txs = result.scalars().all()

    income  = sum(t.amount for t in txs if t.type == TransactionType.income) or current_user.monthly_income
    expense = sum(t.amount for t in txs if t.type == TransactionType.expense)
    balance = income - expense

    cards_result = await db.execute(select(CreditCard).where(CreditCard.user_id == current_user.id))
    cards = cards_result.scalars().all()
    total_limit = sum(c.limit_amount for c in cards) or 1
    total_used  = sum(c.used_amount  for c in cards)
    card_pct    = (total_used / total_limit) * 100

    savings_rate = (balance / income * 100) if income > 0 else 0

    # Score: 40% taxa de poupança + 40% uso de cartão + 20% equilíbrio
    score = 0
    if savings_rate >= 20: score += 40
    elif savings_rate >= 10: score += 25
    elif savings_rate >= 0: score += 10

    if card_pct <= 30: score += 40
    elif card_pct <= 60: score += 25
    elif card_pct <= 80: score += 10

    if balance >= 0: score += 20
    score = min(score, 100)

    label = "Excelente 🟢" if score >= 80 else "Boa 🟡" if score >= 60 else "Regular 🟠" if score >= 40 else "Crítica 🔴"

    alerts, suggestions = [], []
    if card_pct > 80:
        alerts.append(f"⚠️ Uso dos cartões em {card_pct:.0f}% — risco alto de endividamento")
    if savings_rate < 0:
        alerts.append("🚨 Despesas maiores que receitas este mês!")
    if savings_rate < 10 and savings_rate >= 0:
        suggestions.append("💡 Tente economizar pelo menos 10% da renda mensal")
    if card_pct > 50:
        suggestions.append("💡 Reduza o uso do cartão abaixo de 30% do limite")
    if not cards:
        suggestions.append("💡 Adicione seus cartões para monitoramento completo")

    return FinancialHealth(
        score=score, label=label,
        card_usage_pct=round(card_pct, 1),
        savings_rate_pct=round(savings_rate, 1),
        alerts=alerts, suggestions=suggestions,
    )


# ════════════════════════════════════════════════════════════════
# user_service.py  (importado por outros módulos)
# ════════════════════════════════════════════════════════════════
class UserService:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str):
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()