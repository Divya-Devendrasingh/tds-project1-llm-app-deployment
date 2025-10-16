# server.py - FastAPI app for LLM Code Deployment Project

import os
import base64
import time
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from github import Github
import google.generativeai as genai
from huggingface_hub import InferenceClient
import uvicorn

# ----------------------------
# 0️⃣ Load environment variables
# ----------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EXPECTED_SECRET = os.getenv("EXPECTED_SECRET")
HF_TOKEN = os.getenv("HF_TOKEN")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# MIT License template
MIT_LICENSE = """
MIT License

Copyright (c) 2025 Divya-Devendrasingh

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""".strip()

# ----------------------------
# 1️⃣ Pydantic models for request
# ----------------------------
class Attachment(BaseModel):
    name: str
    url: str

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: str
    attachments: Optional[List[Attachment]] = []

# ----------------------------
# 2️⃣ Initialize FastAPI
# ----------------------------
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from LLM Code Deployment API!"}

# ----------------------------
# 3️⃣ Helper Functions
# ----------------------------
def generate_app_code(brief: str, attachments: List[Attachment], existing_code: Optional[str] = None) -> str:
    attach_contents = ""
    for attach in attachments:
        if attach.url.startswith("data:"):
            _, data = attach.url.split(",", 1)
            try:
                content = base64.b64decode(data).decode("utf-8", errors="ignore")[:100]
                attach_contents += f"\nAttachment {attach.name}: {content}..."
            except:
                attach_contents += f"\nAttachment {attach.name}: [Binary data]..."

    prompt = f"Generate a single index.html file with inline CSS and JS to implement this brief: {brief}. Use attachments if needed: {attach_contents}. Make it a complete, functional single-page app."
    if existing_code:
        prompt = f"Modify the existing index.html to incorporate: {brief}. Existing code: {existing_code}. Output only the modified index.html."

    # Try Gemini
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip("```html").strip("```")
    except Exception as e:
        print(f"Gemini failed: {e}")

    # Fallback to Hugging Face
    try:
        client = InferenceClient(token=os.getenv("HF_TOKEN"))
        output = client.text_generation(
            prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_new_tokens=1000,
            temperature=0.7
        )
        return output.strip("```html").strip("```")
    except Exception as e:
        print(f"Hugging Face failed: {e}")

    # Final fallback
    return f"""<!DOCTYPE html>
<html><head><title>{brief}</title></head><body><h1>{brief}</h1></body></html>"""

def generate_readme(brief: str, checks: List[str], task: str, round: int) -> str:
    checks_str = "\n".join([f"- {check}" for check in checks])
    return f"""
# {task}-{round}

## Summary
This repository implements a single-page application based on the provided brief: {brief}

## Setup
1. Clone the repository.
2. Open `index.html` in a browser or visit the GitHub Pages URL.

## Usage
Visit the GitHub Pages URL to interact with the app. The app fulfills the following requirements:
{checks_str}

## Code Explanation
The application is implemented in `index.html` with inline CSS and JavaScript to meet the brief's requirements. The code is structured to be minimal yet functional, leveraging external libraries (e.g., Bootstrap, marked) as needed.

## License
MIT License
""".strip()

def enable_github_pages(repo):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo.name}/pages"
    data = {"source": {"branch": "main", "path": "/"}}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        print(f"Error enabling GitHub Pages: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable GitHub Pages")

def post_to_evaluation_url(url: str, payload: dict, retries: int = 4):
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            response.raise_for_status()
            print("Evaluation server response:", response.status_code, response.text)
            return response
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1, 2, 4, 8 seconds
            else:
                print(f"Error notifying evaluation server after {retries} attempts: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to notify evaluation server: {e}")

# ----------------------------
# 4️⃣ API Endpoint to receive tasks
# ----------------------------
@app.post("/api-endpoint")
async def receive_task(request: TaskRequest, background_tasks: BackgroundTasks):
    # 4.1️⃣ Verify secret
    if request.secret != EXPECTED_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 4.2️⃣ Log received task
    print("Received task request:")
    print(f"Email: {request.email}")
    print(f"Task: {request.task}")
    print(f"Round: {request.round}")
    print(f"Nonce: {request.nonce}")
    print(f"Brief: {request.brief}")
    print(f"Checks: {request.checks}")
    print(f"Attachments: {request.attachments}")

    # 4.3️⃣ Add processing to background task
    background_tasks.add_task(process_task, request)

    # 4.4️⃣ Immediate response
    return JSONResponse({"status": "received"})

async def process_task(request: TaskRequest):
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        repo_name = f"{request.task}-{request.round}"

        # 4.5️⃣ Check if repo exists (for round 2)
        repo = None
        try:
            repo = user.get_repo(repo_name)
        except:
            if request.round == 1:
                # Create new repo for round 1
                repo = user.create_repo(
                    name=repo_name,
                    description=request.brief,
                    private=False,
                    auto_init=True
                )

        if not repo:
            raise HTTPException(status_code=500, detail="Failed to find or create repository")

        # 4.6️⃣ Generate or update app code
        existing_code = None
        if request.round == 2:
            try:
                index_file = repo.get_contents("index.html")
                existing_code = base64.b64decode(index_file.content).decode("utf-8")
            except:
                pass

        index_content = generate_app_code(request.brief, request.attachments, existing_code)

        # 4.7️⃣ Update or create files
        # README
        readme_content = generate_readme(request.brief, request.checks, request.task, request.round)
        try:
            readme_file = repo.get_contents("README.md")
            repo.update_file(
                path=readme_file.path,
                message=f"Update README.md for round {request.round}",
                content=readme_content,
                sha=readme_file.sha
            )
        except:
            repo.create_file(
                path="README.md",
                message="Add README.md",
                content=readme_content
            )

        # index.html
        try:
            index_file = repo.get_contents("index.html")
            repo.update_file(
                path=index_file.path,
                message=f"Update index.html for round {request.round}",
                content=index_content,
                sha=index_file.sha
            )
        except:
            repo.create_file(
                path="index.html",
                message="Add index.html",
                content=index_content
            )

        # LICENSE (only for round 1)
        if request.round == 1:
            repo.create_file(
                path="LICENSE",
                message="Add MIT License",
                content=MIT_LICENSE.format(username=GITHUB_USERNAME)
            )

        # 4.8️⃣ Enable GitHub Pages for round 1
        if request.round == 1:
            enable_github_pages(repo)

        # 4.9️⃣ Get commit SHA
        commit_sha = repo.get_commits()[0].sha

        # 4.10️⃣ GitHub Pages URL
        pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

        # 4.11️⃣ Notify evaluation server
        payload = {
            "email": request.email,
            "task": request.task,
            "round": request.round,
            "nonce": request.nonce,
            "repo_url": repo.html_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        post_to_evaluation_url(request.evaluation_url, payload)

    except Exception as e:
        print(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# 5️⃣ Run server
# ----------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)