import os

import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from src.app.card.api import router as card_router

app = FastAPI(
    title="pypo API",
    description="pypo API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(card_router, prefix="/card", tags=["card"])


@app.get("/openapi.yaml", include_in_schema=False)
def get_openapi_yaml() -> Response:
    openapi_schema = app.openapi()
    openapi_yaml = yaml.dump(openapi_schema, sort_keys=False, allow_unicode=True)
    return Response(content=openapi_yaml, media_type="text/yaml")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
