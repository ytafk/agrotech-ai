"""
Quality Inspector Agent.
Vision çıktısını alır, Gemini ile yapılandırılmış kalite raporu üretir.
Gemini çağrısı için ortak _gemini_helper'ı kullanır (retry logic).
"""
from typing import Dict
from backend.agents._gemini_helper import generate_json


QUALITY_SYSTEM_PROMPT = """Sen tarım ve gıda işletmeleri için çalışan deneyimli bir kalite kontrol uzmanısın.
Kasalardan gelen ürün analiz sonuçlarını yorumlayıp yöneticiye somut, eyleme yönelik raporlar sunarsın.

Görevin:
1. summary: Yöneticiye 2-3 cümlelik anlamlı bir özet yaz. Sayıları somut kullan, "yüksek", "düşük" gibi muğlak kelimeler değil.
2. severity: Aciliyet seviyesini belirle:
   - "low": fire oranı %10'un altında
   - "medium": %10-25 arası
   - "high": %25 ve üstü
3. categories: Hasarlı sayısını üç kategoriye dağıt (toplamı hasarlı sayısına eşit olmalı):
   - "ezik": fiziksel hasar gören ama yenilebilir
   - "cürük": tamamen bozulmuş
   - "lekeli": yüzeysel hasar, ezik değil
4. recommended_action: Yöneticiye tek cümlelik somut tavsiye.

ÇIKTIYI KESİNLİKLE bu JSON formatında ver:
{
  "summary": "string",
  "severity": "low" | "medium" | "high",
  "categories": {"ezik": int, "cürük": int, "lekeli": int},
  "recommended_action": "string"
}"""


def analyze_quality(vision_result: Dict) -> Dict:
    """Vision sonucunu alır, Gemini ile yapılandırılmış kalite raporu üretir."""
    total = vision_result.get("total_items", 0)
    damaged = vision_result.get("damaged", 0)
    fresh = vision_result.get("fresh", 0)
    fire_rate = vision_result.get("fire_rate", 0)
    loss_tl = vision_result.get("estimated_loss_tl", 0)

    user_prompt = f"""Kasanın analiz sonucu:
- Toplam ürün: {total}
- Taze: {fresh}
- Hasarlı: {damaged}
- Fire oranı: %{fire_rate * 100:.1f}
- Tahmini maddi zarar: {loss_tl} TL

Bu kasa için kalite raporunu üret."""

    report = generate_json(
        system_prompt=QUALITY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
    )

    # Helper başarısızsa veya eksik alan varsa fallback
    required = ["summary", "severity", "categories", "recommended_action"]
    if report is None or not all(k in report for k in required):
        return _fallback_report(vision_result)

    return report


def _fallback_report(vision_result: Dict) -> Dict:
    """Gemini erişilemediğinde temel mantıkla rapor üret."""
    damaged = vision_result.get("damaged", 0)
    fire_rate = vision_result.get("fire_rate", 0)

    if fire_rate < 0.10:
        severity = "low"
    elif fire_rate < 0.25:
        severity = "medium"
    else:
        severity = "high"

    return {
        "summary": (
            f"Toplam {vision_result.get('total_items', 0)} ürün incelendi, "
            f"{damaged} tanesi hasarlı tespit edildi. Fire oranı %{fire_rate * 100:.1f}."
        ),
        "severity": severity,
        "categories": {"ezik": damaged, "cürük": 0, "lekeli": 0},
        "recommended_action": "Manuel kontrol yapılması önerilir.",
    }


# Test için
if __name__ == "__main__":
    import json
    test = {"total_items": 12, "fresh": 8, "damaged": 4, "fire_rate": 0.33, "estimated_loss_tl": 45.50}
    result = analyze_quality(test)
    print(json.dumps(result, indent=2, ensure_ascii=False))