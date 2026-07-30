import os

SKILL_WEIGHTS = {
    "python": 20,"django": 20,"drf": 15,"django rest framework": 15,"postgresql": 15,
    "rest api": 10,"fastapi": 10,"celery": 8,"redis": 8,"react": 8,"react.js": 8,
    "redux toolkit": 5,"react router": 3,"docker": 8,"docker compose": 5,
    "nginx": 5,"aws": 8,"typescript": 5,"cicd": 5,"ci/cd": 5,"git": 3,
    "github": 3,"javascript": 3,"sql": 3,"jwt": 5,"rbac": 5,"authentication": 5,
    "django orm": 5,"tailwind": 3,"html": 2,"css": 2,"bootstrap": 2,"mysql": 4,
    "sqlite": 2,"ec2": 5,"rds": 5,"s3": 5,"gunicorn": 3,"pytest": 2,"swagger": 2,
    "openapi": 2,"llm": 5,"ai": 5,"rag": 6,"groq": 4,"gemini": 4,"websockets": 6,"vercel": 2,
}

SKILL_ALIASES = {
    "drf": ["django rest framework"],
    "react": ["react.js"],
    "cicd": ["ci/cd"],
    "django orm": ["django orm"],
    "rest api": ["rest api"],
    "docker compose": ["docker compose"],
    "redux toolkit": ["redux toolkit"],
    "react router": ["react router"],
    "llm integration": ["llm"],
    "tailwind": ["tailwind css"],
    "mvt architecture": ["mvt"],
}

SKILL_CATEGORIES = {
    "must_have": ["python", "django"],
    "nice_to_have": ["drf", "postgresql", "rest api", "fastapi", "celery", "redis", "django orm", "authentication"],
    "bonus": ["react", "docker", "docker compose", "websockets", "rag", "llm", "tailwind", "nginx"],
}

SERVICE_KEY = os.getenv("CV_ENGINE_SERVICE_KEY", "")
PROFILE_JSON_PATH = os.getenv("PROFILE_JSON_PATH", "")
