from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from graph_rag_poc.api_models import AnswerRequest, HealthView, InvestigationResponse, SeedView, SummaryView, UseCaseView
from graph_rag_poc.config import Settings, get_settings
from graph_rag_poc.graph_store import Neo4jGraphStore
from graph_rag_poc.logging_utils import configure_logging, get_logger
from graph_rag_poc.service import GraphRagService


def create_app(
    service: GraphRagService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("API")

    owns_service = service is None
    if service is None:
        store = Neo4jGraphStore(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        service = GraphRagService(settings=settings, store=store)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("application_starting", app=settings.app_name, openai_enabled=settings.openai_enabled)
        service.initialize()
        yield
        if owns_service:
            service.close()
        logger.info("application_stopped")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.service = service

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", response_model=HealthView)
    def health(request: Request) -> HealthView:
        return _service(request).health()

    @app.get("/summary", response_model=SummaryView)
    def summary(request: Request) -> SummaryView:
        logger.info("summary_requested")
        return _service(request).summary()

    @app.get("/use-case", response_model=UseCaseView)
    def use_case(request: Request) -> UseCaseView:
        logger.info("use_case_requested")
        return _service(request).use_case_view()

    @app.post("/admin/seed", response_model=SeedView)
    def seed(request: Request) -> SeedView:
        logger.info("seed_requested")
        return _service(request).seed_demo_graph(reset=True)

    @app.post("/ask", response_model=InvestigationResponse)
    def ask(payload: AnswerRequest, request: Request) -> InvestigationResponse:
        logger.info("question_received", mode=payload.mode, top_k=payload.top_k, question=payload.question)
        return _service(request).investigate(
            question=payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
        )

    return app


def _service(request: Request) -> GraphRagService:
    return request.app.state.service


app = create_app()
