"""
Rota do Chat com IA — integração Claude com contexto financeiro completo.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract, func
from datetime import datetime, timezone
import anthropic
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.models import User, Transaction, CreditCard, Goal, ChatMessage, TransactionType
from app.schemas.schemas import ChatRequest, ChatResponse, ChatMessageOut

router = APIRouter()
client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Você é a FINA, assistente financeira pessoal inteligente, empática e confiável.

Fale sempre em português brasileiro, de forma conversacional e direta — como uma consultora financeira de confiança.
Seja objetiva: dê orientações práticas e concretas, não discursos longos.
Use emojis com moderação para humanizar a conversa.

Suas capacidades:
- Analisar saúde financeira com base nos dados reais do usuário
- Orientar sobre viabilidade de compras considerando saldo, cartões e metas
- Identificar padrões de gastos e alertar sobre riscos
- Projetar cenários futuros (ex: "em X meses você consegue juntar Y")
- Sugerir estratégias de economia e investimento
- Fazer cálculos financeiros sob demanda

Regras importantes:
- Use APENAS os dados financeiros fornecidos no contexto
- Nunca invente saldos ou projeções sem base real
- Alerte proativamente sobre riscos de endividamento
- Mantenha respostas em até 4 parágrafos curtos
- Se o usuário perguntar como adicionar dados, oriente-o a usar o app
"""


async def build_financial_context(user: User, db: AsyncSession) -> str:
    """Monta contexto financeiro completo do usuário para a IA."""
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    # Transações do mês
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            extract("year",  Transaction.date) == year,
            extract("month", Transaction.date) == month,
        ).order_by(Transaction.date.desc())
    )
    txs = result.scalars().all()

    total_income  = sum(t.amount for t in txs if t.type == TransactionType.income)
    total_expense = sum(t.amount for t in txs if t.type == TransactionType.expense)
    balance       = total_income - total_expense

    by_cat = {}
    for t in txs:
        if t.type == TransactionType.expense:
            by_cat[t.category.value] = by_cat.get(t.category.value, 0) + t.amount

    top_cats = sorted(by_cat.items(), key=lambda x: -x[1])[:5]

    # Cartões
    cards_result = await db.execute(select(CreditCard).where(CreditCard.user_id == user.id))
    cards = cards_result.scalars().all()
    total_card_limit = sum(c.limit_amount for c in cards)
    total_card_used  = sum(c.used_amount  for c in cards)
    card_usage_pct   = (total_card_used / total_card_limit * 100) if total_card_limit > 0 else 0

    # Metas
    goals_result = await db.execute(
        select(Goal).where(Goal.user_id == user.id, Goal.is_completed == False)
    )
    goals = goals_result.scalars().all()

    # Últimas transações
    last_txs = txs[:5]

    ctx = f"""
=== DADOS FINANCEIROS DE {user.name.upper()} ({month:02d}/{year}) ===

RENDA DECLARADA: R$ {user.monthly_income:,.2f}/mês

MÊS ATUAL:
  Receitas:  R$ {total_income:,.2f}
  Despesas:  R$ {total_expense:,.2f}
  Saldo:     R$ {balance:,.2f} {"✅" if balance >= 0 else "⚠️ NEGATIVO"}
  Taxa de economia: {((balance / total_income * 100) if total_income > 0 else 0):.1f}%

PRINCIPAIS CATEGORIAS DE GASTOS:
{chr(10).join(f"  {cat}: R$ {val:,.2f}" for cat, val in top_cats) or "  Nenhuma despesa registrada"}

CARTÕES DE CRÉDITO:
{chr(10).join(f"  {c.name}: R$ {c.used_amount:,.2f} / R$ {c.limit_amount:,.2f} ({c.used_amount/c.limit_amount*100:.0f}%)" for c in cards) or "  Nenhum cartão cadastrado"}
  Total utilizado: R$ {total_card_used:,.2f} de R$ {total_card_limit:,.2f} ({card_usage_pct:.0f}%)

METAS FINANCEIRAS:
{chr(10).join(f"  {g.icon} {g.name}: R$ {g.saved_amount:,.2f} / R$ {g.target_amount:,.2f} ({g.saved_amount/g.target_amount*100:.0f}%){' | Prazo: '+str(g.deadline.strftime('%d/%m/%Y')) if g.deadline else ''}" for g in goals) or "  Nenhuma meta cadastrada"}

ÚLTIMAS TRANSAÇÕES:
{chr(10).join(f"  {'▲' if t.type.value=='income' else '▼'} {t.description}: R$ {t.amount:,.2f} ({t.category.value})" for t in last_txs) or "  Nenhuma transação recente"}
""".strip()

    return ctx


@router.post("/", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envia mensagem para FINA e recebe resposta contextualizada."""
    # Histórico das últimas 20 mensagens
    hist_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    history = list(reversed(hist_result.scalars().all()))

    # Salva mensagem do usuário
    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    await db.flush()

    # Contexto financeiro atual
    financial_ctx = await build_financial_context(current_user, db)

    # Monta histórico para Claude
    messages = []
    for h in history:
        messages.append({"role": h.role, "content": h.content})
    messages.append({
        "role": "user",
        "content": f"{payload.message}\n\n[CONTEXTO ATUAL DO USUÁRIO]\n{financial_ctx}"
    })

    # Chama Claude
    try:
        response = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=settings.AI_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply_text = response.content[0].text
    except Exception as e:
        raise HTTPException(500, f"Erro na IA: {str(e)}")

    # Salva resposta
    ai_msg = ChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=reply_text,
    )
    db.add(ai_msg)
    await db.flush()

    # Retorna histórico atualizado
    updated_hist = history + [user_msg, ai_msg]
    return ChatResponse(
        reply=reply_text,
        messages=[ChatMessageOut.model_validate(m) for m in updated_hist],
    )


@router.get("/history", response_model=list[ChatMessageOut])
async def chat_history(
    limit: int         = 50,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna histórico de mensagens do usuário."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


@router.delete("/history")
async def clear_history(
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Limpa histórico de chat do usuário."""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == current_user.id)
    )
    for msg in result.scalars().all():
        await db.delete(msg)
    return {"message": "Histórico limpo com sucesso"}