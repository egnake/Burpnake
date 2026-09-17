"""
Response Differ Analysis Module

Kör zafiyetlerin (Blind SQLi, Blind XSS) tespiti için HTTP yanıtlarının farklılıklarını inceler.
Kelimeler, uzunluk, süre ve durum kodlarını karşılaştırır.
"""
import re
from typing import Dict, Any, Tuple

class ResponseDiffer:
    def __init__(self):
        pass

    def extract_features(self, response_text: str, status_code: int, duration_ms: float = 0) -> Dict[str, Any]:
        """
        Bir HTTP yanıtından kıyaslama yapılabilecek özellikleri çıkarır.
        """
        headers_end = response_text.find("\r\n\r\n")
        body = response_text[headers_end + 4:] if headers_end != -1 else response_text
        
        words = re.findall(r'\b\w+\b', body.lower())
        word_count = len(words)
        
        return {
            "status_code": status_code,
            "length": len(body),
            "word_count": word_count,
            "duration_ms": duration_ms
        }
        
    def compare(self, base_features: Dict[str, Any], new_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        İki yanıt özelliğini karşılaştırır ve anormallikleri tespit eder.
        """
        diff = {
            "is_anomaly": False,
            "status_diff": new_features["status_code"] != base_features["status_code"],
            "length_diff": abs(new_features["length"] - base_features["length"]),
            "word_count_diff": abs(new_features["word_count"] - base_features["word_count"]),
            "time_diff": new_features["duration_ms"] - base_features["duration_ms"],
            "reason": ""
        }
        
        if diff["status_diff"]:
            diff["is_anomaly"] = True
            diff["reason"] = "Status code changed"
        elif diff["word_count_diff"] > max(10, base_features["word_count"] * 0.1):
            diff["is_anomaly"] = True
            diff["reason"] = f"Significant word count difference ({diff['word_count_diff']})"
        elif diff["time_diff"] > 4000:  
            diff["is_anomaly"] = True
            diff["reason"] = f"Time delay detected ({diff['time_diff']}ms)"
            
        return diff

response_differ = ResponseDiffer()