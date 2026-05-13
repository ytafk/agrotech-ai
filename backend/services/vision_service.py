"""
Vision Service.
YOLOv8 modeli (ultralytics) ile fotoğraftan kalite tespiti yapar.
Üye 1'in eğittiği özel modeli kullanır.
"""
import os
import tempfile
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/rotten_detector_v1.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE", "0.50"))

ASSUMED_UNIT_PRICE_TL = 12.0
ASSUMED_WEIGHT_KG_PER_ITEM = 0.15

# !!! Üye 1'in modelinin sınıf isimleri geldikten sonra burayı güncelle !!!
# Modelin name'lerine bakıp "çürük/hasarlı" anlamına gelen kelimeleri buraya yaz
DAMAGED_KEYWORDS = ["bad", "rotten", "damaged", "spoiled"]
FRESH_KEYWORDS = ["good", "fresh", "healthy", "ripe"]

_model = None  # Lazy load — model ilk istekte yüklenir, startup yavaşlamaz


def _get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(
                f"YOLO modeli bulunamadı: {MODEL_PATH}. "
                f"Üye 1'den .pt dosyasını al, models/ klasörüne koy."
            )
        _model = YOLO(MODEL_PATH)
        print(f"[VisionService] Model yüklendi: {MODEL_PATH}, sınıflar: {list(_model.names.values())}")
    return _model


def detect_quality(image_bytes: bytes) -> Dict[str, Any]:
    """Görsel byte'larını alır, YOLO ile tespit yapıp yapılandırılmış sonuç döner."""
    model = _get_model()

    # ultralytics dosya yolu istiyor, geçici dosyaya yaz
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        results = model.predict(source=tmp_path, conf=CONFIDENCE_THRESHOLD, verbose=False)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    fresh_count = 0
    damaged_count = 0
    detections = []

    for box in results[0].boxes:
        class_id = int(box.cls[0])
        class_name = model.names[class_id].lower()
        conf = float(box.conf[0])

        xywh = box.xywh[0].tolist()
        x = xywh[0] - xywh[2] / 2
        y = xywh[1] - xywh[3] / 2
        w = xywh[2]
        h = xywh[3]

        if any(kw in class_name for kw in DAMAGED_KEYWORDS):
            damaged_count += 1
            mapped = "damaged"
        elif any(kw in class_name for kw in FRESH_KEYWORDS):
            fresh_count += 1
            mapped = "fresh"
        else:
            # Sınıf eşleşmedi — varsayılan olarak hasarlı say (logla)
            damaged_count += 1
            mapped = f"unknown_{class_name}"
            print(f"[VisionService] UYARI: Bilinmeyen sınıf '{class_name}', hasarlı sayıldı")

        detections.append({
            "class_name": mapped,
            "confidence": conf,
            "bbox": [x, y, w, h],
        })

    total = fresh_count + damaged_count
    fire_rate = (damaged_count / total) if total > 0 else 0.0
    estimated_loss = damaged_count * ASSUMED_WEIGHT_KG_PER_ITEM * ASSUMED_UNIT_PRICE_TL

    print(f"[VisionService] {total} tespit: {fresh_count} taze, {damaged_count} hasarlı")

    return {
        "total_items": total,
        "fresh": fresh_count,
        "damaged": damaged_count,
        "fire_rate": round(fire_rate, 3),
        "estimated_loss_tl": round(estimated_loss, 2),
        "detections": detections,
    }


# Test için: python -m backend.services.vision_service <image_path>
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python -m backend.services.vision_service path/to/image.jpg")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        result = detect_quality(f.read())
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))