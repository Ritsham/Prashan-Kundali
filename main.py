from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.prashna import router as prashna_router
from app.api.validation import router as validation_router
from app.storage.database import init_db


app = FastAPI(title="Prashna Kundli MVP", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(prashna_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
