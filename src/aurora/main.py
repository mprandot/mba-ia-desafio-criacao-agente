from contextlib import asynccontextmanager

from fastapi import FastAPI

from aurora.adk.runtime import AuroraRuntime
from aurora.api.routes import router
from aurora.infra import repository as repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo.init_db()
    if not repo.get_area("quadra"):
        repo.restore()
    runtime = AuroraRuntime()
    await runtime.prepare()
    app.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.close()


app = FastAPI(title="Residencial Aurora", lifespan=lifespan)
app.include_router(router)
