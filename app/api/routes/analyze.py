from fastapi import APIRouter, HTTPException
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer_service import AnalyzerService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_task_records(request: AnalyzeRequest):
    if not request.uid or not request.taskId:
        logger.warning(f"Failed to analyze: Missing uid or taskId. uid={request.uid}, taskId={request.taskId}")
        raise HTTPException(status_code=400, detail="uid and taskId are required")
        
    return AnalyzerService.analyze_records(request)