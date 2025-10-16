# test_gemini.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')  # Updated to gemini-2.5-flash
response = model.generate_content("Generate a simple HTML page.")
print(response.text)