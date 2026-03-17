from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analyze
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore  # ← 追加

firebase_credentials_json = os.environ.get("FIREBASE_CREDENTIALS")

if firebase_credentials_json is None:
    raise ValueError("FIREBASE_CREDENTIALS is not set")

cred = credentials.Certificate(json.loads(firebase_credentials_json))

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI(
    title="itukara Analytics API",
    description="育児タスクの傾向分析とアドバイス生成API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "itukara API is running."}