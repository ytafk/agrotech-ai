"""
Communication Agent.
Quality raporundan tedarikçiye gönderilecek iade maili taslağı üretir.
"""
import os
from typing import Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

COMMUNICATION_SYSTEM_PROMPT = """Sen tarım/gıda işletmesi adına tedarikçilerle iletişim kuran profesyonel bir asistansın.
Kalite kontrol raporundan yola çıkarak tedarikçiye gönderilecek bir iade/şikayet maili taslağı hazırlarsın.

Yazım kuralları:
- Türkçe, resmi ama nazik bir dilde
- Net rakamlar kullan (kaç ürün, fire oranı, maddi zarar)
- Suçlayıcı değil, çözüm odaklı bir ton
- Konu satırı + selamlama + gövde + kapanış formatında
- 150-200 kelime arası, uzatma
- Sonunda kanıt fotoğrafının ekte olduğunu belirt
"NOT: Mail sonundaki imzaya KESİNLİKLE 'Asistan' kelimesi koyma; sadece şirket adı olsun."
ÇIKTIYI KESİNLİKLE bu JSON formatında ver:
{
  "subject": "Mail konu satırı",
  "body": "Mail gövdesi (selamlama dahil, tek string, paragraflar arası \\n\\n)"
}"""


def draft_supplier_email(
    quality_report: Dict,
    vision_result: Dict,
    supplier_name: str = "Tedarikçi",
    company_name: str = "Agrotech Kooperatifi",
) -> Dict:
    """Quality raporu ve vision sonucundan tedarikçi maili taslağı üretir."""

    user_prompt = f"""Tedarikçi: {supplier_name}
Bizim işletme: {company_name}

Kalite Raporu:
- Özet: {quality_report.get('summary', '')}
- Aciliyet: {quality_report.get('severity', 'medium')}
- Tavsiye: {quality_report.get('recommended_action', '')}

Sayısal veriler:
- Toplam ürün: {vision_result.get('total_items', 0)}
- Hasarlı: {vision_result.get('damaged', 0)}
- Fire oranı: %{vision_result.get('fire_rate', 0) * 100:.1f}
- Tahmini zarar: {vision_result.get('estimated_loss_tl', 0)} TL

Hasar dağılımı: {quality_report.get('categories', {})}

Bu tedarikçiye gönderilecek iade maili taslağını hazırla."""

    import json

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=COMMUNICATION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        email = json.loads(response.text)
        if "subject" not in email or "body" not in email:
            raise ValueError("Eksik alanlar")
        return email
    except Exception as e:
        print(f"[CommunicationAgent] Hata: {e}, fallback mail döndürülüyor")
        return _fallback_email(quality_report, vision_result, supplier_name, company_name)


def _fallback_email(quality_report, vision_result, supplier_name, company_name) -> Dict:
    return {
        "subject": f"İade Talebi — Kalite Sorunu (Fire %{vision_result.get('fire_rate', 0) * 100:.1f})",
        "body": (
            f"Sayın {supplier_name} yetkilisi,\n\n"
            f"Tarafınızdan teslim alınan üründe yapılan kalite kontrol sonucunda "
            f"{vision_result.get('damaged', 0)} adet hasarlı ürün tespit edilmiştir. "
            f"Toplam {vision_result.get('total_items', 0)} üründeki fire oranı "
            f"%{vision_result.get('fire_rate', 0) * 100:.1f} olup, tahmini maddi zarar "
            f"{vision_result.get('estimated_loss_tl', 0)} TL'dir.\n\n"
            f"İade ve telafi süreci için en kısa sürede tarafımıza dönüş yapmanızı rica ederiz. "
            f"Kanıt fotoğrafları ekte sunulmuştur.\n\n"
            f"Saygılarımızla,\n{company_name}"
        ),
    }


if __name__ == "__main__":
    import json

    test_quality = {
        "summary": "Bu kasadaki 12 ürünün 4'ü (%33.0) hasarlı, 45.5 TL maddi zarar.",
        "severity": "high",
        "categories": {"ezik": 2, "cürük": 1, "lekeli": 1},
        "recommended_action": "Yüksek fire oranı, taşıma şartları gözden geçirilmeli.",
    }
    test_vision = {
        "total_items": 12,
        "fresh": 8,
        "damaged": 4,
        "fire_rate": 0.33,
        "estimated_loss_tl": 45.5,
    }
    result = draft_supplier_email(test_quality, test_vision, "Yıldız Üretim A.Ş.", "Yeşil Kooperatif")
    print(f"KONU: {result['subject']}\n")
    print(f"GÖVDE:\n{result['body']}")