"""
Logistics Agent.
Hasarlı ürünleri kategorisine göre lojistik yönlendirir (salça, kompost vb.).
Pazartesi günü Gemini ile gerçeklenecek.
"""
from typing import Dict, List


def recommend_routing(quality_report: Dict) -> List[Dict]:
    """TODO Pazartesi: Gemini ile sıfır atık tavsiyesi üret."""
    return [
        {
            "category": "ezik",
            "destination": "Salça tesisi",
            "estimated_recovery_tl": 0.0,
        },
    ]