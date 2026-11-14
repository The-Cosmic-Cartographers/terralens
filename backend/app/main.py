from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import get_store
from app.api.v1 import router as v1_router
from app.config import CORS_ORIGINS
from app.errors import install_error_handlers
from app.models import Health

app = FastAPI(title="TerraLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(v1_router)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", data_version=get_store().data_version())
