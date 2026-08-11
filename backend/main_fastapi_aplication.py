"""
FINA - Financial Assistant API
Backend principal FastAPI com autenticação JWT, banco de dados PostgreSQL e integração IA.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, users, transactions, cards, goals, ai_chat, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: criar tabelas se não existirem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Banco de dados inicializado")
    yield
    # Shutdown
    await engine.dispose()
    print("🔒 Conexões encerradas")


app = FastAPI(
    title="FINA - Assistente Financeiro",
    description="API completa para gerenciamento financeiro pessoal com IA",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ─── Middlewares ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Autenticação"])
app.include_router(users.router,        prefix="/api/v1/users",        tags=["Usuários"])
app.include_router(transactions.router, prefix="/api/v1/transactions",  tags=["Transações"])
app.include_router(cards.router,        prefix="/api/v1/cards",        tags=["Cartões"])
app.include_router(goals.router,        prefix="/api/v1/goals",        tags=["Metas"])
app.include_router(ai_chat.router,      prefix="/api/v1/chat",         tags=["Chat IA"])
app.include_router(reports.router,      prefix="/api/v1/reports",      tags=["Relatórios"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "FINA API", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)