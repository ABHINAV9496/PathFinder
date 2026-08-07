from fastapi import FastAPI

from coverletter.routers import generate, health

app = FastAPI(title="Cover Letter Engine", version="1.0.0")

app.include_router(health.router)
app.include_router(generate.router)


@app.get("/")
def root():
    return {"status": "cover-letter-engine", "version": "1.0.0"}
