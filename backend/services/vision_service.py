"""
Roboflow Universe modelini kullanarak görsel analiz yapan servis.
Cumartesi placeholder, Pazar Üye 1 gerçek modeli buraya bağlayacak.
"""
import os
import base64
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Birim fiyat varsayımları (demo için, gerçekçi değerlerle değiştirin)
ASSUMED_UNIT_PRICE_TL = 12.0
ASSUMED_WEIGHT_KG_PER_ITEM = 0.15  # ortalama bir domates ~150g

# Roboflow modelinden gelen sınıf isimlerini bizim 'fresh'/'damaged' kategorisine çevirir
FRESH_CLASSES = {"fresh", "healthy", "good", "ripe"}
DAMAGED_CLASSES = {"rotten", "damaged", "spoiled", "bad"}


def detect_quality(image_bytes: bytes) -> Dict[str, Any]:
    """
    Görsel byte'larını alır, Roboflow inference yapar, yapılandırılmış sonuç döner.

    Args:
        image_bytes: JPEG/PNG formatında resim baytları

    Returns:
        {
            "total_items": int,
            "fresh": int,
            "damaged": int,
            "fire_rate": float,
            "estimated_loss_tl": float,
            "detections": [{"class_name", "confidence", "bbox"}, ...]
        }

    Raises:
        RuntimeError: Eğer ROBOFLOW_MODEL_ID .env'de tanımlı değilse
    """
    model_id = os.getenv("ROBOFLOW_MODEL_ID")
    if not model_id:
        raise RuntimeError(
            "ROBOFLOW_MODEL_ID .env'de tanımlı değil. "
            "Üye 1 Roboflow Universe'ten model seçip ekleyecek."
        )

    # Lazy import — paket yüklenmemişse sadece bu fonksiyon çağrıldığında patlar
    from inference_sdk import InferenceHTTPClient

    client = InferenceHTTPClient(
        api_url=os.getenv("ROBOFLOW_API_URL", "https://detect.roboflow.com"),
        api_key=os.getenv("ROBOFLOW_API_KEY"),
    )

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    raw = client.infer(image_b64, model_id=model_id)

    predictions = raw.get("predictions", [])

    fresh_count = 0
    damaged_count = 0
    detections = []

    for p in predictions:
        cls_lower = p["class"].lower()
        conf = float(p["confidence"])
        # Roboflow center-x, center-y verir; biz top-left'e çeviriyoruz
        x = p["x"] - p["width"] / 2
        y = p["y"] - p["height"] / 2
        w = p["width"]
        h = p["height"]

        if any(fc in cls_lower for fc in FRESH_CLASSES):
            fresh_count += 1
            mapped_class = "fresh"
        elif any(dc in cls_lower for dc in DAMAGED_CLASSES):
            damaged_count += 1
            mapped_class = "damaged"
        else:
            damaged_count += 1
            mapped_class = f"unknown_{cls_lower}"

        detections.append({
            "class_name": mapped_class,
            "confidence": conf,
            "bbox": [x, y, w, h],
        })

    total = fresh_count + damaged_count
    fire_rate = (damaged_count / total) if total > 0 else 0.0
    estimated_loss = damaged_count * ASSUMED_WEIGHT_KG_PER_ITEM * ASSUMED_UNIT_PRICE_TL

    return {
        "total_items": total,
        "fresh": fresh_count,
        "damaged": damaged_count,
        "fire_rate": round(fire_rate, 3),
        "estimated_loss_tl": round(estimated_loss, 2),
        "detections": detections,
    }