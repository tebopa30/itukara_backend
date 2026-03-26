from datetime import datetime
from typing import List, Tuple
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse, TaskRecordItem
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import logging

logger = logging.getLogger(__name__)

def get_firestore_client() -> firestore.Client:
    if not firebase_admin._apps:
        firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
        if not firebase_creds_json:
            raise ValueError("FIREBASE_CREDENTIALS が設定されていません")
        
        # 🔹 ここで改行文字を修正
        cred_dict = json.loads(firebase_creds_json)
        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    return firestore.client()

class AnalyzerService:

    @staticmethod
    def analyze_records(request: AnalyzeRequest) -> AnalyzeResponse:
        try:
            records = request.records
            sorted_records = sorted(records, key=lambda x: x.recordedAt)

            intervals = []
            for i in range(1, len(sorted_records)):
                diff = sorted_records[i].recordedAt - sorted_records[i-1].recordedAt
                interval_minutes = diff.total_seconds() / 60.0

                if interval_minutes < 1.0 or interval_minutes >= 1440.0:
                    continue

                intervals.append(interval_minutes)

            data_points = len(intervals)

            if data_points < 1:
                response = AnalyzeResponse(
                    averageIntervalMinutes=0.0,
                    latestIntervalMinutes=0.0,
                    differencePercent=0.0,
                    status="normal",
                    trend="stable",
                    dataPoints=data_points,
                    confidence="low",
                    urgency="low",
                    estimatedNextMinutes=0.0,
                    primaryMessage="記録を続けてみましょう。",
                    secondaryMessage="記録が少ないため、もう少しデータが集まると傾向が分かります"
                )

                # 🔥 Firestore保存 (失敗してもレスポンスは返す)
                AnalyzerService._save_to_firestore(request, response)
                return response

            avg_interval = sum(intervals) / len(intervals)
            latest_interval = intervals[-1]
            diff_pct = ((latest_interval - avg_interval) / avg_interval) * 100 if avg_interval > 0 else 0

            if diff_pct >= 20.0:
                status = "long"
            elif diff_pct <= -20.0:
                status = "short"
            else:
                status = "normal"

            abs_diff = abs(diff_pct)
            urgency = "low" if abs_diff < 20 else "medium" if abs_diff < 40 else "high"

            trend = "stable"
            if len(intervals) >= 3:
                recent_3 = intervals[-3:]
                if recent_3[0] < recent_3[1] < recent_3[2]:
                    trend = "getting_longer"
                elif recent_3[0] > recent_3[1] > recent_3[2]:
                    trend = "getting_shorter"

            estimated_next = avg_interval - (avg_interval - latest_interval) * 0.5
            if estimated_next < 0:
                estimated_next = avg_interval

            confidence = "low" if data_points < 4 else "medium" if data_points < 8 else "high"

            primary, secondary = AnalyzerService._generate_messages(status, trend, urgency, confidence)

            response = AnalyzeResponse(
                averageIntervalMinutes=round(avg_interval, 1),
                latestIntervalMinutes=round(latest_interval, 1),
                differencePercent=round(diff_pct, 1),
                status=status,
                trend=trend,
                dataPoints=data_points,
                confidence=confidence,
                urgency=urgency,
                estimatedNextMinutes=round(estimated_next, 1),
                primaryMessage=primary,
                secondaryMessage=secondary
            )

            # 🔥 Firestore保存 (失敗してもレスポンスは返す)
            AnalyzerService._save_to_firestore(request, response)

            return response
            
        except Exception as e:
            logger.error(f"[AnalyzerService] Error analyzing records: {e}", exc_info=True)
            # クラッシュを避け、安全なデフォルト値を返す
            return AnalyzeResponse(
                averageIntervalMinutes=0.0,
                latestIntervalMinutes=0.0,
                differencePercent=0.0,
                status="normal",
                trend="stable",
                dataPoints=0,
                confidence="low",
                urgency="low",
                estimatedNextMinutes=0.0,
                primaryMessage="分析中にエラーが発生しました",
                secondaryMessage="次回以降の記録で改善される可能性があります"
            )


    @staticmethod
    def _save_to_firestore(request: AnalyzeRequest, response: AnalyzeResponse):
        try:
            db = get_firestore_client()
            # UID単位でタスクごとに保存: users/{uid}/analysis/{taskId}
            db.collection("users").document(request.uid) \
              .collection("analysis").document(request.taskId).set({
                "taskId": request.taskId,
                "taskTitle": request.taskTitle,
                "records": [r.recordedAt.isoformat() for r in request.records],
                "result": response.dict(),
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            # Firestore保存失敗はアプリクラッシュさせない (200 OKとして処理継続)
            logger.error(f"[AnalyzerService] Firestore save failed: {e}", exc_info=True)


    @staticmethod
    def _generate_messages(status: str, trend: str, urgency: str, confidence: str) -> Tuple[str, str]:
        primary = ""
        secondary = ""

        # Primary Message: 行動や結論を優しく促す
        if status == "long":
            if urgency == "high":
                primary = "そろそろ対応してあげると良さそうです。"
            else:
                primary = "いつもより少し間隔が空いています。"
        elif status == "short":
            if urgency == "high":
                primary = "いつもより早いペースで求めているかもしれません。"
            else:
                primary = "いつもより少し早いペースです。"
        else:
            primary = "いつも通りの良いペースです。"

        # Secondary Message: 傾向の補足や安心感を与える言葉
        if confidence == "low":
            secondary = "記録が少ないため、もう少しデータが集まると傾向が分かります"
        else:
            if trend == "getting_longer":
                secondary = "ここ数回、少しずつ間隔が長くなる傾向があります"
            elif trend == "getting_shorter":
                secondary = "ここ数回、少しずつ間隔が短くなる傾向があります"
            else:
                if status == "normal":
                    secondary = "今のリズムを大切にしましょう"
                else:
                    secondary = "一時的な変化かもしれないので、無理せず様子を見てくださいね"

        return primary, secondary
