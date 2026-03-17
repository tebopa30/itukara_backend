from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime

class TaskRecordItem(BaseModel):
    recordedAt: datetime

class AnalyzeRequest(BaseModel):
    records: List[TaskRecordItem]

class AnalyzeResponse(BaseModel):
    # 既存の統計情報
    averageIntervalMinutes: float
    latestIntervalMinutes: float
    differencePercent: float
    status: Literal["short", "normal", "long"]
    trend: Literal["stable", "getting_longer", "getting_shorter"]
    
    # 新規：信頼性・緊急度・予測・メッセージ分離
    dataPoints: int
    confidence: Literal["low", "medium", "high"]
    urgency: Literal["low", "medium", "high"]
    estimatedNextMinutes: float
    primaryMessage: str
    secondaryMessage: str
