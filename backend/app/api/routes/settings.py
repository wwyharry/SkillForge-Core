from fastapi import APIRouter, HTTPException

from app.schemas.model_config import ModelApiConfig
from app.schemas.settings import ModelApiTestRequest, ModelApiTestResult
from app.services.model_client import ModelApiClient
from app.services.model_config import ModelConfigService

router = APIRouter(prefix="/settings", tags=["settings"])
service = ModelConfigService()


@router.get("/model-api")
def get_model_api_config():
    return service.masked()


@router.post("/model-api")
def save_model_api_config(payload: ModelApiConfig):
    try:
        return service.save(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/model-api/test", response_model=ModelApiTestResult)
def test_model_api_connection(payload: ModelApiTestRequest):
    try:
        result = ModelApiClient(payload.config).test_connection()
        return ModelApiTestResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
