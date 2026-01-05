import os
from dotenv import load_dotenv

load_dotenv()
print("Environment variables loaded.")

HF_TOKEN = os.getenv("HF_TOKEN")
print(f"Environment variables loaded.{' HF_TOKEN found.' if HF_TOKEN else ' HF_TOKEN missing!'}")
API_URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}