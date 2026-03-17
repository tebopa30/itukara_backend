from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analyze

app = FastAPI(
    title="itukara Analytics API",
    description="育児タスクの傾向分析とアドバイス生成API",
    version="1.0.0"
)

# CORS対応 (Flutter Webでのデバッグ等用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "itukara API is running."}
