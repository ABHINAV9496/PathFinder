from fastapi import FastAPI
from app.routers import tailor, generate_cv, enrich, health

app = FastAPI(title="CV Engine", version="1.0.0")

app.include_router(health.router)
app.include_router(tailor.router)
app.include_router(generate_cv.router)
app.include_router(enrich.router)


@app.get("/")
def root():
    return {"status": "cv-engine", "version": "1.0.0"}
