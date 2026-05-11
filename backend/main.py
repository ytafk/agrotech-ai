from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

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
    Fotoğraf alır, vision + quality agent ile analiz yapar.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Sadece görüntü dosyaları kabul edilir"
        )

    image_bytes = await file.read()
    print(f"[/analyze] Fotoğraf alındı: {file.filename}, "
          f"{len(image_bytes) / 1024:.1f} KB")

    # 1. Vision analizi
    vision_result = None
    try:
        from backend.services import vision_service
        vision_result = vision_service.detect_quality(image_bytes)
        print(f"[/analyze] Vision sonucu: total={vision_result['total_items']}")
    except Exception as e:
        print(f"[/analyze] Vision hatası, dummy döndürülüyor: {e}")

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

    # 2. Quality Agent
    quality_report = None
    agent_summary = None
    try:
        from backend.agents import quality_agent
        quality_report = quality_agent.analyze_quality(vision_result)
        agent_summary = quality_report.get("summary")
        print(f"[/analyze] Quality Agent: {agent_summary[:80] if agent_summary else 'none'}...")
    except Exception as e:
        print(f"[/analyze] Quality Agent hatası: {e}")

        # 3. Communication Agent — sadece severity yüksekse mail draft et
    supplier_email = None
    if quality_report and quality_report.get("severity") in ("medium", "high"):
        try:
            from backend.agents import communication_agent
            supplier_email = communication_agent.draft_supplier_email(
                quality_report, vision_result, "Tedarikçi A.Ş.", "Agrotech Kooperatifi"
            )
            print(f"[/analyze] Mail taslağı hazır: {supplier_email['subject']}")
        except Exception as e:
            print(f"[/analyze] Communication Agent hatası: {e}")

    return AnalysisResult(
        total_items=vision_result["total_items"],
        fresh=vision_result["fresh"],
        damaged=vision_result["damaged"],
        fire_rate=vision_result["fire_rate"],
        estimated_loss_tl=vision_result["estimated_loss_tl"],
        detections=[Detection(**d) for d in vision_result["detections"]],
        agent_report=agent_summary,
        quality_report=quality_report,
        supplier_email=supplier_email,
    )