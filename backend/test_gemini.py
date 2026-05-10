import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Selam Gemini, sen bir tarım kalite kontrol ajanı olsaydın kendini nasıl tanıtırdın? Tek cümle Türkçe."
)

print(response.text)