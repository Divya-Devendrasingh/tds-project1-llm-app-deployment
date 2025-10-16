---
title: Tds Project1 Llm
emoji: 👁
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
short_description: Project for LLM App Deployment
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
# TDS Project 1: LLM App Deployment

## Overview
This repo contains the source code for my LLM-powered FastAPI app, deployed on Hugging Face Spaces. It includes text generation endpoints with secret-based authentication.

## Deployment
- Live API: https://divyads-tds-project1-llm.hf.space/
- Test the root: GET `/` → `{"Hello": "World!"}`
- LLM Endpoint: POST `/generate` with JSON body `{"prompt": "Your text", "secret": {"secret": "my-tds-project-secret"}}`

## Setup Locally
1. Clone: `git clone https://github.com/Divya-Devendrasingh/tds-project1-llm-app-deployment.git`
2. Install deps: `pip install -r requirements.txt`
3. Run: `uvicorn app:app --host 0.0.0.0 --port 7860`
4. Docker Build: `docker build -t tds-llm . && docker run -p 7860:7860 tds-llm`

## Tech Stack
- FastAPI for API
- Transformers + Torch for LLM (e.g., Llama-3.2-1B)
- Docker for containerization

## Secret Validation
All sensitive endpoints require: `{"secret": "my-tds-project-secret"}`

## License
MIT License
