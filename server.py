from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import uvicorn
import os
import requests

# ----------------------------
# 0️⃣ Load environment variables
# ----------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

# ----------------------------
# 1️⃣ Project secret
# ----------------------------
EXPECTED_SECRET = "my-tds-project-secret"

# ----------------------------
# 2️⃣ Pydantic models for request
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
# 3️⃣ Initialize FastAPI
# ----------------------------
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from LLM Code Deployment API!"}

# ----------------------------
# 4️⃣ API Endpoint to receive tasks
# ----------------------------
@app.post("/api-endpoint")
async def receive_task(request: TaskRequest):
    # 4.1️⃣ Verify secret
    if request.secret != EXPECTED_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 4.2️⃣ Print received task for debugging
    print("Received task request:")
    print(f"Email: {request.email}")
    print(f"Task: {request.task}")
    print(f"Round: {request.round}")
    print(f"Nonce: {request.nonce}")
    print(f"Brief: {request.brief}")
    print(f"Checks: {request.checks}")
    print(f"Attachments: {request.attachments}")

    # 4.3️⃣ GitHub repo creation
    from github import Github
    g = Github(GITHUB_TOKEN)
    user = g.get_user()
    repo_name = f"{request.task}-{request.round}"

    # 4.4️⃣ Create repo (public, auto-init with README)
    repo = user.create_repo(
        name=repo_name,
        description=request.brief,
        private=False,
        auto_init=True
    )

    # 4.5️⃣ Add index.html
    index_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{request.task}</title>
    </head>
    <body>
        <h1>{request.brief}</h1>
    </body>
    </html>
    """
    repo.create_file(
        path="index.html",
        message="Add index.html",
        content=index_content
    )

    # 4.6️⃣ Add README.md
    readme_content = f"# {repo_name}\n\n{request.brief}\n\n## License\nMIT License"
    repo.create_file(
        path="README.md",
        message="Add README.md",
        content=readme_content
    )

    # 4.7️⃣ Add MIT LICENSE
    mit_license = f"""MIT License

Copyright (c) 2025 {GITHUB_USERNAME}

Permission is hereby granted, free of charge, to any person obtaining a copy
... (rest of MIT text)
"""
    repo.create_file(
        path="LICENSE",
        message="Add MIT License",
        content=mit_license
    )

    # 4.8️⃣ Enable GitHub Pages (optional for classic token)
    repo.update(branch="main", description=request.brief)
    pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

    # 4.9️⃣ Notify evaluation server
    payload = {
        "email": request.email,
        "task": request.task,
        "round": request.round,
        "nonce": request.nonce,
        "repo_url": repo.html_url,
        "commit_sha": repo.get_commits()[0].sha,
        "pages_url": pages_url
    }
    try:
        r = requests.post(request.evaluation_url, json=payload, headers={"Content-Type": "application/json"})
        print("Evaluation server response:", r.status_code, r.text)
    except Exception as e:
        print("Error notifying evaluation server:", e)

    # 4.🔟 Respond back
    return JSONResponse({
        "status": "ok",
        "message": "Task received and repo created successfully",
        "task": request.task,
        "round": request.round,
        "repo_url": repo.html_url,
        "pages_url": pages_url
    })

# ----------------------------
# 5️⃣ Run server
# ----------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
