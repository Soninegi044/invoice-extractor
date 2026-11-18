import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <-- YEH IMPORT ADD KAREIN

from app.api.routes import router
from app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Invoice Extractor MVP", lifespan=lifespan)

# <-- YEH CORS WALA BLOCK ADD KAREIN (app = FastAPI(...) ke theek niche) -->
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # MVP ke liye sabko allow kar rahe hain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"ok": True}