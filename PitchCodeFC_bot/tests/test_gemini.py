
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)

try:
    print(f"Testing Gemini: {model}")

    response = client.interactions.create(
        model=model,
        input="Reply with exactly: Gemini is working!"
    )

    print("\nGemini response:")
    print(response.output_text)

except Exception as error:
    print("\nGemini API error:")
    print(error)

finally:
    client.close()