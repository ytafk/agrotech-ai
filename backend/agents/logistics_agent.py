"""
Logistics Agent.
Hasarlı ürün kategorilerine bakarak sıfır atık yönlendirmesi önerir.
Gemini çağrısı için ortak _gemini_helper'ı kullanır.
"""
import json
from typing import Dict
from backend.agents._gemini_helper import generate_json


AVAILABLE_FACILITIES = [
    {"type": "salça", "name": "Salça Fabrikası", "accepts": ["ezik", "lekeli"], "recovery_rate_tl_per_kg": 4.0},
    {"type": "meyve_suyu", "name": "Meyve Suyu Fabrikası", "accepts": ["ezik"], "recovery_rate_tl_per_kg": 5.5},
    {"type": "tursu", "name": "Turşu Fabrikası", "accepts": ["lekeli"], "recovery_rate_tl_per_kg": 3.0},
    {"type": "kompost", "name": "Kompost Tesisi", "accepts": ["cürük"], "recovery_rate_tl_per_kg": 0.5},
]

KG_PER_ITEM = 0.15

LOGISTICS_SYSTEM_PROMPT = """Sen tarım/gıda işletmesi için çalışan sürdürülebilirlik ve lojistik uzmanısın.
Hasarlı ürünleri çöpe atmak yerine farklı tesislere yönlendirerek atık-değer kazandırırsın.

Kurallar:
- Her hasar kategorisi (ezik, çürük, lekeli) için EN UYGUN tesisi seç
- Birden fazla tesis kabul ediyorsa, en yüksek geri kazanım değerine sahip olanı tercih et
- Hiç hasar yoksa boş liste döndür

ÇIKTIYI KESİNLİKLE bu JSON formatında ver:
{
  "routings": [
    {
      "category": "ezik|cürük|lekeli",
      "quantity": int,
      "destination_facility": "tesis_tipi",
      "destination_name": "Tesis Adı",
      "estimated_recovery_tl": float,
      "reasoning": "Kısa Türkçe gerekçe (1 cümle)"
    }
  ],
  "total_recovery_tl": float,
  "sustainability_note": "Yöneticiye 1-2 cümlelik sürdürülebilirlik mesajı"
}"""


def recommend_routing(quality_report: Dict) -> Dict:
    """Quality raporundaki kategori dağılımına göre lojistik tavsiyesi üretir."""
    categories = quality_report.get("categories", {})
    ezik = categories.get("ezik", 0)
    curuk = categories.get("cürük", 0) or categories.get("curuk", 0)
    lekeli = categories.get("lekeli", 0)

    if ezik == 0 and curuk == 0 and lekeli == 0:
        return {
            "routings": [],
            "total_recovery_tl": 0.0,
            "sustainability_note": "Bu kasada hasar tespit edilmedi, yönlendirme gerekmiyor.",
        }

    user_prompt = f"""Hasar kategorileri:
- Ezik: {ezik} adet
- Çürük: {curuk} adet
- Lekeli: {lekeli} adet

Bir ürün ortalama {KG_PER_ITEM} kg.

Mevcut tesisler:
{json.dumps(AVAILABLE_FACILITIES, ensure_ascii=False, indent=2)}

Bu hasarlı ürünleri uygun tesislere yönlendir, geri kazanım değerini hesapla."""

    result = generate_json(
        system_prompt=LOGISTICS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
    )

    if result is None or "routings" not in result:
        return _fallback_routing(ezik, curuk, lekeli)

    return result


def _fallback_routing(ezik: int, curuk: int, lekeli: int) -> Dict:
    """Gemini erişilemediğinde basit kural tabanlı yönlendirme."""
    routings = []
    total = 0.0

    if ezik > 0:
        recovery = ezik * KG_PER_ITEM * 5.5
        routings.append({
            "category": "ezik",
            "quantity": ezik,
            "destination_facility": "meyve_suyu",
            "destination_name": "Meyve Suyu Fabrikası",
            "estimated_recovery_tl": round(recovery, 2),
            "reasoning": "Ezik ürünler sıvılaştırma sürecine uygundur.",
        })
        total += recovery

    if lekeli > 0:
        recovery = lekeli * KG_PER_ITEM * 4.0
        routings.append({
            "category": "lekeli",
            "quantity": lekeli,
            "destination_facility": "salça",
            "destination_name": "Salça Fabrikası",
            "estimated_recovery_tl": round(recovery, 2),
            "reasoning": "Lekeli ürünler salça üretiminde sorun yaratmaz.",
        })
        total += recovery

    if curuk > 0:
        recovery = curuk * KG_PER_ITEM * 0.5
        routings.append({
            "category": "cürük",
            "quantity": curuk,
            "destination_facility": "kompost",
            "destination_name": "Kompost Tesisi",
            "estimated_recovery_tl": round(recovery, 2),
            "reasoning": "Çürük ürünler kompost yapımında değer kazanır.",
        })
        total += recovery

    return {
        "routings": routings,
        "total_recovery_tl": round(total, 2),
        "sustainability_note": f"Hasarlı ürünlerden {total:.2f} TL geri kazanım sağlanabilir.",
    }


# Test için
if __name__ == "__main__":
    test = {
        "summary": "Test",
        "severity": "high",
        "categories": {"ezik": 2, "cürük": 1, "lekeli": 1},
        "recommended_action": "Test",
    }
    print(json.dumps(recommend_routing(test), indent=2, ensure_ascii=False))