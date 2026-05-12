from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(
    title="Agrotech-AI Backend",
    description="Otonom Kalite Kontrol ve Fire Ajanı API",
    version="0.1.0"
)

# Streamlit'ten istek gelecek, CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic modelleri ---
class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: List[float]  # [x, y, w, h]

class Supplier(BaseModel):
    id: str
    name: str


class Facility(BaseModel):
    id: str
    type: str
    name: str
    accepts: List[str]


class EmailSendRequest(BaseModel):
    supplier_id: str
    subject: str
    body: str
    email_type: str = "iade"  # "iade" veya "degisim"


class EmailSendResponse(BaseModel):
    status: str
    timestamp: str
    supplier_name: str

class AnalysisResult(BaseModel):
    total_items: int
    fresh: int
    damaged: int
    fire_rate: float
    estimated_loss_tl: float
    detections: List[Detection]
    agent_report: Optional[str] = None
    quality_report: Optional[dict] = None
    supplier_email: Optional[dict] = None
    logistics_routing: Optional[dict] = None 

# --- Endpoint'ler ---
@app.get("/")
def root():
    return {
        "service": "Agrotech-AI",
        "status": "alive",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)):
    """
    Fotoğraf alır, vision + multi-agent pipeline çalıştırır.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Sadece görüntü dosyaları kabul edilir")

    image_bytes = await file.read()
    print(f"[/analyze] Fotoğraf alındı: {file.filename}, {len(image_bytes) / 1024:.1f} KB")

    # 1. Vision analizi
    vision_result = None
    try:
        from backend.services import vision_service
        vision_result = vision_service.detect_quality(image_bytes)
        print(f"[/analyze] Vision: total={vision_result['total_items']}, damaged={vision_result['damaged']}")
    except Exception as e:
        print(f"[/analyze] Vision hatası, dummy kullanılıyor: {e}")

    if vision_result is None:
        vision_result = {
            "total_items": 12,
            "fresh": 8,
            "damaged": 4,
            "fire_rate": 0.33,
            "estimated_loss_tl": 45.50,
            "detections": [
                {"class_name": "fresh", "confidence": 0.94, "bbox": [10, 20, 100, 110]},
                {"class_name": "fresh", "confidence": 0.89, "bbox": [110, 25, 90, 100]},
                {"class_name": "damaged", "confidence": 0.87, "bbox": [210, 30, 100, 110]},
                {"class_name": "damaged", "confidence": 0.82, "bbox": [10, 150, 100, 105]},
            ],
        }

    # 2. Multi-agent pipeline
    from backend.orchestrator import run_pipeline
    pipeline_result = run_pipeline(vision_result)

    quality_report = pipeline_result["quality_report"]
    agent_summary = quality_report.get("summary") if quality_report else None

    return AnalysisResult(
        total_items=vision_result["total_items"],
        fresh=vision_result["fresh"],
        damaged=vision_result["damaged"],
        fire_rate=vision_result["fire_rate"],
        estimated_loss_tl=vision_result["estimated_loss_tl"],
        detections=[Detection(**d) for d in vision_result["detections"]],
        agent_report=agent_summary,
        quality_report=quality_report,
        supplier_email=pipeline_result["supplier_email"],
        logistics_routing=pipeline_result["logistics_routing"],
    )

# Sabit veri (Pazartesi gerçek DB'ye taşırsak iyi olur)
SUPPLIERS = [
    {"id": "sup_001", "name": "Yıldız Üretim A.Ş."},
    {"id": "sup_002", "name": "Akdeniz Tarım Kooperatifi"},
    {"id": "sup_003", "name": "Egemen Sebze Meyve"},
    {"id": "sup_004", "name": "Antalya Sera Ürünleri"},
]

FACILITIES = [
    {"id": "fac_salca", "type": "salça", "name": "Salça Fabrikası", "accepts": ["ezik", "lekeli"]},
    {"id": "fac_suyu", "type": "meyve_suyu", "name": "Meyve Suyu Fabrikası", "accepts": ["ezik"]},
    {"id": "fac_tursu", "type": "tursu", "name": "Turşu Fabrikası", "accepts": ["lekeli"]},
    {"id": "fac_kompost", "type": "kompost", "name": "Kompost Tesisi", "accepts": ["cürük"]},
]

# In-memory mail log (Pazartesi SQLite'a taşıyacağız)
SENT_EMAILS = []


@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers():
    """Tedarikçi listesi — Flutter dropdown'ı için."""
    return SUPPLIERS


@app.get("/facilities", response_model=List[Facility])
def list_facilities():
    """İşleme tesisleri listesi — sıfır atık yönlendirmesi için."""
    return FACILITIES


@app.post("/email/send", response_model=EmailSendResponse)
async def send_email(req: EmailSendRequest):
    """
    Onaylanmış mail taslağını 'gönderir' (demo için log + kayıt).
    Gerçek SMTP entegrasyonu Pazartesi eklenecek.
    """
    supplier = next((s for s in SUPPLIERS if s["id"] == req.supplier_id), None)
    if supplier is None:
        raise HTTPException(status_code=404, detail=f"Tedarikçi bulunamadı: {req.supplier_id}")

    timestamp = datetime.now().isoformat()
    record = {
        "supplier_id": req.supplier_id,
        "supplier_name": supplier["name"],
        "subject": req.subject,
        "body": req.body,
        "email_type": req.email_type,
        "timestamp": timestamp,
    }
    SENT_EMAILS.append(record)
    print(f"[EMAIL SENT] {supplier['name']} → {req.subject}")

    return EmailSendResponse(
        status="sent",
        timestamp=timestamp,
        supplier_name=supplier["name"],
    )


@app.get("/email/history")
def email_history():
    """Gönderilen mail geçmişi (yönetici paneli için bonus)."""
    return SENT_EMAILS