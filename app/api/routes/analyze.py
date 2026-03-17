from fastapi import APIRouter
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer_service import AnalyzerService

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_task_records(request: AnalyzeRequest):
    return AnalyzerService.analyze_records(request.records)