"""
Multi-agent orchestrator.
Vision sonucunu sırasıyla 3 ajandan geçirip toplu rapor üretir.
Bu dosya /analyze endpoint'inde tek satır çağrıyla kullanılır.
"""
from typing import Dict, Optional
from backend.agents import quality_agent, communication_agent, logistics_agent


def run_pipeline(
    vision_result: Dict,
    supplier_name: str = "Tedarikçi A.Ş.",
    company_name: str = "Agrotech Kooperatifi",
    severity_threshold_for_email: tuple = ("medium", "high"),
) -> Dict:
    """
    Vision çıktısını alır, üç ajanı sırayla çalıştırır, toplu sonuç döner.

    Pipeline:
      1. Quality Agent → kalite raporu (her zaman çalışır)
      2. Logistics Agent → sıfır atık yönlendirmesi (hasar varsa)
      3. Communication Agent → tedarikçi mail taslağı (sadece severity yüksekse)

    Args:
        vision_result: Vision Service'in döndürdüğü dict
        supplier_name: Mail alıcısı
        company_name: Mail göndereni
        severity_threshold_for_email: Hangi severity'lerde mail draft edilsin

    Returns:
        {
            "quality_report": {...} | None,
            "logistics_routing": {...} | None,
            "supplier_email": {...} | None,
        }
    """
    output = {
        "quality_report": None,
        "logistics_routing": None,
        "supplier_email": None,
    }

    # 1. Quality Inspector
    try:
        quality_report = quality_agent.analyze_quality(vision_result)
        output["quality_report"] = quality_report
        print(f"[Orchestrator] Quality: severity={quality_report.get('severity')}")
    except Exception as e:
        print(f"[Orchestrator] Quality Agent başarısız: {e}")
        return output  # Quality yoksa diğer ajanlar da çalışmaz

    # 2. Logistics
    has_damage = any(
        quality_report.get("categories", {}).get(c, 0) > 0
        for c in ("ezik", "cürük", "lekeli")
    )
    if has_damage:
        try:
            output["logistics_routing"] = logistics_agent.recommend_routing(quality_report)
            print(f"[Orchestrator] Logistics: {output['logistics_routing'].get('total_recovery_tl', 0)} TL geri kazanım")
        except Exception as e:
            print(f"[Orchestrator] Logistics Agent başarısız: {e}")

    # 3. Communication — sadece severity yüksekse
    severity = quality_report.get("severity")
    if severity in severity_threshold_for_email:
        try:
            output["supplier_email"] = communication_agent.draft_supplier_email(
                quality_report, vision_result, supplier_name, company_name
            )
            print(f"[Orchestrator] Email: {output['supplier_email'].get('subject', '')[:60]}...")
        except Exception as e:
            print(f"[Orchestrator] Communication Agent başarısız: {e}")
    else:
        print(f"[Orchestrator] Severity '{severity}', mail draft edilmedi")

    return output


# Test için
if __name__ == "__main__":
    import json
    test_vision = {
        "total_items": 12,
        "fresh": 8,
        "damaged": 4,
        "fire_rate": 0.33,
        "estimated_loss_tl": 45.5,
        "detections": [],
    }
    result = run_pipeline(test_vision)
    print(json.dumps(result, indent=2, ensure_ascii=False))