"""
Quality Inspector Agent.
Vision çıktısını alır, Gemini ile yapılandırılmış kalite raporu üretir.
"""
import os
import json
from typing import Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=QUALITY_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        report = json.loads(response.text)

        # Doğrulama: gerekli alanlar var mı?
        required = ["summary", "severity", "categories", "recommended_action"]
        if not all(k in report for k in required):
            raise ValueError(f"Eksik alanlar: {set(required) - set(report.keys())}")

        return report

    except (json.JSONDecodeError, ValueError, Exception) as e:
        print(f"[QualityAgent] Hata: {e}, fallback rapor döndürülüyor")
        return _fallback_report(vision_result)


def _fallback_report(vision_result: Dict) -> Dict:
    """Gemini hata verdiğinde temel mantıkla rapor üret."""
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


# Test için: python -m backend.agents.quality_agent
if __name__ == "__main__":
    test_cases = [
        {"total_items": 12, "fresh": 8, "damaged": 4, "fire_rate": 0.33, "estimated_loss_tl": 45.50},
        {"total_items": 20, "fresh": 19, "damaged": 1, "fire_rate": 0.05, "estimated_loss_tl": 12.0},
        {"total_items": 8, "fresh": 2, "damaged": 6, "fire_rate": 0.75, "estimated_loss_tl": 90.0},
    ]
    for i, case in enumerate(test_cases, 1):
        print(f"\n=== Test {i} ===")
        print(f"Girdi: {case}")
        result = analyze_quality(case)
        print(f"Çıktı: {json.dumps(result, indent=2, ensure_ascii=False)}")