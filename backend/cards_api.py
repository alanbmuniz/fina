"""
Rotas de cartões de crédito + sincronização Open Finance.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, CreditCard
from app.schemas.schemas import CardCreate, CardOut
from app.services.openfinance_service import PluggyService

router = APIRouter()


@router.get("/", response_model=List[CardOut])
async def list_cards(
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(CreditCard).where(CreditCard.user_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=CardOut, status_code=201)
async def create_card(
    payload: CardCreate,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = CreditCard(user_id=current_user.id, **payload.model_dump())
    db.add(card)
    await db.flush()
    return card


@router.delete("/{card_id}", status_code=204)
async def delete_card(
    card_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CreditCard).where(CreditCard.id == card_id, CreditCard.user_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Cartão não encontrado")
    await PluggyService.disconnect_card(card)
    await db.delete(card)


# ─── Open Finance ────────────────────────────────────────────────────────────
@router.get("/openfinance/connect-token")
async def get_connect_token(current_user: User = Depends(get_current_user)):
    """Gera token para abrir o widget de conexão bancária no app."""
    try:
        token = await PluggyService.create_connect_token(current_user.id)
        return {"connect_token": token}
    except Exception as e:
        raise HTTPException(503, f"Serviço Open Finance indisponível: {e}")


@router.post("/{card_id}/connect")
async def connect_card_openfinance(
    card_id: int,
    item_id: str,      # retornado pelo widget Pluggy após autenticação
    account_id: str,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vincula um item/conta Open Finance a um cartão cadastrado."""
    result = await db.execute(
        select(CreditCard).where(CreditCard.id == card_id, CreditCard.user_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Cartão não encontrado")

    card.pluggy_item_id    = item_id
    card.pluggy_account_id = account_id
    card.is_connected      = True

    # Sincronização inicial
    sync_result = await PluggyService.sync_card(card, db)
    return {"message": "Cartão conectado com sucesso", "sync": sync_result}


@router.post("/{card_id}/sync")
async def sync_card(
    card_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincroniza manualmente dados do cartão via Open Finance."""
    result = await db.execute(
        select(CreditCard).where(CreditCard.id == card_id, CreditCard.user_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Cartão não encontrado")
    if not card.is_connected:
        raise HTTPException(400, "Cartão não conectado ao Open Finance")

    sync_result = await PluggyService.sync_card(card, db)
    return sync_result