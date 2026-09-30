from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401 — регистрация моделей перед create_all
from app.cache import close_redis, init_redis
from app.database import Base, engine
from app.routers import auth_router, projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:               # создание таблиц при старте
        await conn.run_sync(Base.metadata.create_all)
    init_redis()
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(title="HW Final — Projects API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(projects_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}