from datetime import datetime
from typing import List, Tuple
from app.schemas.analyze import AnalyzeResponse, TaskRecordItem

class AnalyzerService:
    @staticmethod
    def analyze_records(records: List[TaskRecordItem]) -> AnalyzeResponse:
        # 1. 時間順（古い順）にソート
        sorted_records = sorted(records, key=lambda x: x.recordedAt)
        
        # 2. 全ての間隔（分）を計算し、異常値を除外する（ガードロジック）
        intervals = []
        for i in range(1, len(sorted_records)):
            diff = sorted_records[i].recordedAt - sorted_records[i-1].recordedAt
            interval_minutes = diff.total_seconds() / 60.0
            
            # 1分未満の誤タップや、24時間(1440分)以上の記録忘れなどを除外
            if interval_minutes < 1.0 or interval_minutes >= 1440.0:
                continue
                
            intervals.append(interval_minutes)

        # 3. 信頼度判定に使用する「フィルタ後の有効データ数（間隔の数）」
        data_points = len(intervals)

        if data_points < 4:
            confidence = "low"
        elif data_points < 8:
            confidence = "medium"
        else:
            confidence = "high"

        # 4. データ不足時（フィルタ後の間隔が1件未満＝比較不能）のフォールバック
        if data_points < 1:
            return AnalyzeResponse(
                averageIntervalMinutes=0.0,
                latestIntervalMinutes=0.0,
                differencePercent=0.0,
                status="normal",
                trend="stable",
                dataPoints=data_points,
                confidence="low",     # 強制的にlow
                urgency="low",        # 強制的にlow
                estimatedNextMinutes=0.0,
                primaryMessage="記録を続けてみましょう。",
                secondaryMessage="記録が少ないため、もう少しデータが集まると傾向が分かります"
            )

        # 5. 平均と最新を取得
        avg_interval = sum(intervals) / len(intervals)
        latest_interval = intervals[-1]

        # 6. 判定 (differencePercent と status と urgency)
        diff_pct = ((latest_interval - avg_interval) / avg_interval) * 100 if avg_interval > 0 else 0
        
        if diff_pct >= 20.0:
            status = "long"
        elif diff_pct <= -20.0:
            status = "short"
        else:
            status = "normal"

        abs_diff = abs(diff_pct)
        if abs_diff < 20.0:
            urgency = "low"
        elif abs_diff < 40.0:
            urgency = "medium"
        else:
            urgency = "high"

        # 7. 傾向 (trend) - 直近3つの間隔を使用
        trend = "stable"
        if len(intervals) >= 3:
            recent_3 = intervals[-3:] # 古いものから順 [t-2, t-1, latest]
            if recent_3[0] < recent_3[1] < recent_3[2]:
                trend = "getting_longer"
            elif recent_3[0] > recent_3[1] > recent_3[2]:
                trend = "getting_shorter"

        # 8. 次回予測 (estimatedNextMinutes)
        estimated_next = avg_interval - (avg_interval - latest_interval) * 0.5
        if estimated_next < 0:
            estimated_next = avg_interval # 負の値になった場合のセーフガード

        # 9. メッセージ生成
        primary, secondary = AnalyzerService._generate_messages(status, trend, urgency, confidence)

        return AnalyzeResponse(
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
