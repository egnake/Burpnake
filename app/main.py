"""BurpNake Main FastAPI Application - v2.0.0"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import AuthMiddleware
import logging

from app.config import settings
from app.core.llm_gateway import llm_gateway
from app.api import (
    routes_scope,
    routes_import,
    routes_analysis,
    routes_chat,
    routes_report,
)
from app.api import routes_live, routes_programs, routes_findings, routes_export, routes_notes, routes_stream
from app.api import routes_agent
from app.api import routes_replay, routes_chain, routes_cvss
from app.modules.request_replayer import request_replayer
from app.modules.database import init_db
from app.modules.passive_analyzer import passive_analysis_loop
from app.modules.agent_loop import init_agent
from app.modules.collaborator_client import collaborator_client

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("burpnake")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """BurpNake baslangic ve kapanis olaylari."""
    logger.info("=" * 50)
    logger.info("  BurpNake v2.0.0 — AI Bug Bounty Platform")
    logger.info("=" * 50)

    # Veritabanini baslat
    init_db()

    # Otonom ajan motorunu baslat
    agent = init_agent(llm_gateway, request_replayer)
    logger.info("[Agent] Autonomous hunting engine initialized")

    # LLM saglayicilarini kontrol et
    providers_status = await llm_gateway.check_providers()
    logger.info(f"[LLM] Providers: {providers_status}")

    # Pasif analiz dongusu arka planda
    analyzer_task = asyncio.create_task(
        passive_analysis_loop(llm_gateway, interval_seconds=10)
    )
    logger.info("[Analyzer] Passive analysis loop started")

    collaborator_task = asyncio.create_task(
        collaborator_client.start_polling(interval=15)
    )
    logger.info("[Collaborator] OOB polling started")

    yield

    # Temizlik
    analyzer_task.cancel()
    collaborator_task.cancel()
    logger.info("[BurpNake] Shutting down...")
    await llm_gateway.close()
    await request_replayer.close()
    await collaborator_client.close()


app = FastAPI(
    title="BurpNake API",
    description="AI-Powered Bug Bounty Hunting Platform — Autonomous Vulnerability Discovery",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — frontend'e izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

# Tum router'lari kaydet
app.include_router(routes_scope.router)
app.include_router(routes_import.router)
app.include_router(routes_analysis.router)
app.include_router(routes_chat.router)
app.include_router(routes_report.router)
app.include_router(routes_live.router)
app.include_router(routes_programs.router, prefix="/api/programs", tags=["programs"])
app.include_router(routes_findings.router, prefix="/api/findings", tags=["findings"])
app.include_router(routes_export.router, prefix="/api/export", tags=["export"])
app.include_router(routes_notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(routes_stream.router, prefix="/api/stream", tags=["stream"])
app.include_router(routes_agent.router)
app.include_router(routes_replay.router)
app.include_router(routes_chain.router)
app.include_router(routes_cvss.router)


@app.get("/")
async def root():
    """API durumu."""
    return {
        "app": "BurpNake",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "llm_providers": await llm_gateway.check_providers(),
    }


@app.get("/health")
async def health():
    """Docker / load balancer saglik kontrolu."""
    return {"status": "healthy", "app": "BurpNake"}
