from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.logging import configure_logging
from routers.webhooks import router as webhook_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield                   # app runs here
    # teardown goes here if needed

app = FastAPI(
    title="Code Review Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(webhook_router, prefix="/webhooks")

@app.get("/health")
async def health():
    return {"status": "ok"}