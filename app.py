from fastapi import FastAPI, HTTPException
from transformers import pipeline

app = FastAPI()
llm = pipeline("text-generation", model="meta-llama/Llama-3.2-1B-Instruct")

@app.post("/generate")
def generate_text(prompt: str, secret: dict):
    if secret != {"secret": "my-tds-project-secret"}:
        raise HTTPException(status_code=401, detail="Invalid secret")
    return llm(prompt, max_length=50)

@app.get("/")
def greet_json():
    return {"Hello": "World!"}
