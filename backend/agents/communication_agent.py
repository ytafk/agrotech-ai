"""
Communication Agent.
Quality raporundan tedarikçiye gönderilecek mail taslağı üretir.
Pazartesi günü Gemini ile gerçeklenecek.
"""
from typing import Dict


def draft_supplier_email(quality_report: Dict, supplier_name: str = "Tedarikçi A") -> str:
    """TODO Pazartesi: Gemini ile profesyonel iade maili taslağı oluştur."""
    return (
        f"Sayın {supplier_name},\n\n"
        f"[Mail içeriği Pazartesi Gemini tarafından üretilecek]\n\n"
        f"Saygılarımızla."
    )