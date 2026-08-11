"""
Serviço de Open Finance via Pluggy API.
Permite conectar contas bancárias e cartões em modo somente-leitura.
Compatível com Open Finance Brasil (Banco Central).
"""

import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import encrypt_sensitive, decrypt_sensitive
from app.models.models import CreditCard, Transaction, TransactionType, TransactionCategory


class PluggyService:
    """
    Integração com Pluggy (https://pluggy.ai) — agregador financeiro Open Finance Brasil.
    Alternativas: Belvo, Quanto, OpenFinance.com.br
    """

    BASE_URL = settings.PLUGGY_BASE_URL
    _api_key: Optional[str] = None
    _key_expires: Optional[datetime] = None

    @classmethod
    async def _get_api_key(cls) -> str:
        """Obtém e cacheia a API key temporária do Pluggy (válida por 2h)."""
        now = datetime.now(timezone.utc)
        if cls._api_key and cls._key_expires and cls._key_expires > now:
            return cls._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{cls.BASE_URL}/auth",
                json={
                    "clientId":     settings.PLUGGY_CLIENT_ID,
                    "clientSecret": settings.PLUGGY_CLIENT_SECRET,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            cls._api_key = data["apiKey"]
            cls._key_expires = now.replace(hour=now.hour + 2)
            return cls._api_key

    @classmethod
    async def _headers(cls) -> dict:
        key = await cls._get_api_key()
        return {"X-API-KEY": key, "Content-Type": "application/json"}

    # ─── Connect Token (frontend usa para abrir widget) ────────────────────
    @classmethod
    async def create_connect_token(cls, user_id: int) -> str:
        """
        Gera token temporário para o widget de conexão bancária no frontend.
        O widget Pluggy abre o fluxo OAuth com o banco escolhido.
        """
        headers = await cls._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{cls.BASE_URL}/connect_token",
                headers=headers,
                json={"clientUserId": str(user_id)},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["accessToken"]

    # ─── Sincronizar cartão ────────────────────────────────────────────────
    @classmethod
    async def sync_card(cls, card: CreditCard, db: AsyncSession) -> dict:
        """
        Sincroniza faturas e limite de um cartão conectado via Open Finance.
        Atualiza automaticamente used_amount e importa transações.
        """
        if not card.pluggy_account_id:
            return {"error": "Cartão não conectado ao Open Finance"}

        headers = await cls._headers()

        async with httpx.AsyncClient() as client:
            # Dados da conta
            account_resp = await client.get(
                f"{cls.BASE_URL}/accounts/{card.pluggy_account_id}",
                headers=headers, timeout=15,
            )
            account_resp.raise_for_status()
            account = account_resp.json()

            # Transações dos últimos 90 dias
            tx_resp = await client.get(
                f"{cls.BASE_URL}/transactions",
                headers=headers,
                params={"accountId": card.pluggy_account_id, "pageSize": 500},
                timeout=15,
            )
            tx_resp.raise_for_status()
            txs_data = tx_resp.json().get("results", [])

        # Atualiza limite e uso
        if account.get("creditData"):
            card.limit_amount = account["creditData"].get("creditLimit", card.limit_amount)
            card.used_amount  = account["creditData"].get("balance", card.used_amount)
        card.last_sync = datetime.now(timezone.utc)

        # Importa transações novas
        imported = 0
        for tx in txs_data:
            pluggy_id = f"pluggy_{tx['id']}"
            exists = await db.execute(
                select(Transaction).where(
                    Transaction.user_id == card.user_id,
                    Transaction.notes == pluggy_id,
                )
            )
            if exists.scalar_one_or_none():
                continue  # já importada

            new_tx = Transaction(
                user_id=card.user_id,
                card_id=card.id,
                type=TransactionType.expense if tx["amount"] < 0 else TransactionType.income,
                description=tx.get("description", "Transação importada"),
                amount=abs(tx["amount"]),
                category=_map_category(tx.get("category", "")),
                date=datetime.fromisoformat(tx["date"]),
                notes=pluggy_id,  # guarda ID externo para deduplicação
            )
            db.add(new_tx)
            imported += 1

        return {
            "card": card.name,
            "limit": card.limit_amount,
            "used":  card.used_amount,
            "transactions_imported": imported,
            "synced_at": card.last_sync.isoformat(),
        }

    # ─── Revogar conexão ──────────────────────────────────────────────────
    @classmethod
    async def disconnect_card(cls, card: CreditCard) -> bool:
        """Remove conexão bancária (usuário revoga acesso)."""
        if not card.pluggy_item_id:
            return True
        try:
            headers = await cls._headers()
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"{cls.BASE_URL}/items/{card.pluggy_item_id}",
                    headers=headers, timeout=10,
                )
            card.pluggy_item_id   = None
            card.pluggy_account_id = None
            card.is_connected     = False
            return True
        except Exception:
            return False


def _map_category(pluggy_cat: str) -> TransactionCategory:
    """Mapeia categorias da Pluggy para categorias internas."""
    mapping = {
        "Food and Beverage": TransactionCategory.alimentacao,
        "Supermarket":       TransactionCategory.alimentacao,
        "Transport":         TransactionCategory.transporte,
        "Health":            TransactionCategory.saude,
        "Education":         TransactionCategory.educacao,
        "Housing":           TransactionCategory.moradia,
        "Clothing":          TransactionCategory.vestuario,
        "Entertainment":     TransactionCategory.lazer,
        "Income":            TransactionCategory.salario,
    }
    return mapping.get(pluggy_cat, TransactionCategory.outros)