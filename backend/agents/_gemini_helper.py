"""
Gemini API çağrıları için ortak helper.
- Retry logic (3 deneme, exponential backoff)
- Yapılandırılmış JSON çıktı zorlaması
- Tüm ajanlar bunu kullanır
"""
import os
import json
import time
from typing import Optional, Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 2  # ilk denemeden sonra bekleme süresi


def generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
) -> Optional[Dict]:
    """
    Gemini'ye yapılandırılmış JSON cevap için istek atar.
    503/429/timeout gibi geçici hatalarda 3 kez dener.
    Başarılıysa parse edilmiş dict, başarısızsa None döner (caller fallback'e geçer).
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            parsed = json.loads(response.text)
            if attempt > 1:
                print(f"[GeminiHelper] {attempt}. denemede başarılı")
            return parsed

        except json.JSONDecodeError as e:
            # JSON parse hatası — tekrar denemek anlamlı değil
            print(f"[GeminiHelper] JSON parse hatası: {e}")
            return None

        except Exception as e:
            last_error = e
            error_msg = str(e)
            # Sadece geçici hatalarda tekrar dene
            is_retryable = any(code in error_msg for code in ["503", "429", "UNAVAILABLE", "timeout", "deadline"])

            if not is_retryable or attempt == MAX_RETRIES:
                print(f"[GeminiHelper] Deneme {attempt}/{MAX_RETRIES} başarısız (kalıcı): {e}")
                return None

            backoff = INITIAL_BACKOFF_SEC * (2 ** (attempt - 1))  # 2s, 4s, 8s
            print(f"[GeminiHelper] Deneme {attempt}/{MAX_RETRIES} başarısız ({error_msg[:60]}...), {backoff}s sonra tekrar")
            time.sleep(backoff)

    print(f"[GeminiHelper] Tüm denemeler tükendi, son hata: {last_error}")
    return None


# Hızlı test
if __name__ == "__main__":
    result = generate_json(
        system_prompt="Sen kısa cevaplar veren bir asistansın. Cevaplarını JSON formatında ver.",
        user_prompt='Bana iki Türk şehrinin adını JSON dizisi olarak ver. Format: {"cities": ["...", "..."]}',
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))