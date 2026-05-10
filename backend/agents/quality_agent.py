"""
Quality Inspector Agent.
Vision çıktısını alır, fire raporu üretir, kategorize eder.
Pazartesi günü Gemini ile gerçeklenecek.
"""
from typing import Dict


def analyze_quality(vision_result: Dict) -> Dict:
    """TODO Pazartesi: Gemini ile yapılandırılmış kalite raporu üret."""
    severity = "high" if vision_result.get("fire_rate", 0) > 0.2 else "low"
    return {
        "summary": f"{vision_result.get('total_items', 0)} üründe "
                   f"{vision_result.get('damaged', 0)} hasarlı tespit edildi.",
        "severity": severity,
        "categories": {
            "ezik": vision_result.get("damaged", 0),
            "çürük": 0,
            "lekeli": 0,
        },
    }