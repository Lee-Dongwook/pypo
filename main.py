import uvicorn
import yaml

from fastapi import FastAPI
from fastapi.responses import Response

app = FastAPI(
    title="pypo API",
    description="pypo API",
    version="0.1.0"
)

@app.get("/openapi.yaml", include_in_schema=False)
def get_openapi_yaml() -> Response:
    openapi_schema = app.openapi()
    openapi_yaml = yaml.dump(openapi_schema, sort_keys=False, allow_unicode=True)
    return Response(content=openapi_yaml, media_type="text/yaml")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
