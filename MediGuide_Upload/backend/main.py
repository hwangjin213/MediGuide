import os
import logging
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

from mcp_server import search_guidelines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medical-backend")
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE" else None

app = FastAPI(title="One-click Medical AI Agent Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DiagnoseRequest(BaseModel):
    symptom: str
    lang: Optional[str] = "ko"

class DiagnoseResponse(BaseModel):
    status: str
    ai_analysis: str
    guidelines_found: bool

def search_medical_guidelines_db(query: str) -> str:
    return search_guidelines(query)

@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose_patient(payload: DiagnoseRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key missing or invalid.")

    symptom_text = payload.symptom.strip()
    target_lang = payload.lang.strip().lower() if payload.lang else "ko"
    
    if not symptom_text:
        raise HTTPException(status_code=400, detail="Symptoms input cannot be empty.")
        
    if target_lang == "en":
        lang_instruction = "IMPORTANT: You MUST write the entire final output report in ENGLISH."
        user_prompt = f"Symptoms: '{symptom_text}'. Use search_medical_guidelines_db tool to search and write a professional markdown report in English."
    else:
        lang_instruction = "중요: 최종 분석 보고서의 모든 텍스트는 반드시 한국어(KOREAN)로 작성해야 합니다."
        user_prompt = f"환자 증상: '{symptom_text}'. search_medical_guidelines_db 도구를 사용하여 전문적인 마크다운 임상 보고서를 한국어로 작성하세요."
        
    config = types.GenerateContentConfig(
        system_instruction=(
            "당신은 AI 임상 진단 어시스턴트입니다. 증상을 정밀 분석하고 데이터베이스를 조회하세요.\n\n"
            f"{lang_instruction}\n\n"
            "보고서 구조:\n"
            "1. 🩺 **의심 질환군 및 매칭 요약**\n"
            "2. ⚠️ **가장 주의해야 할 핵심 위험 징후 (Red Flags)**\n"
            "3. 🏥 **추천 검사 및 즉시 조치 가이드라인**\n"
            "4. 📘 **참조 표준 가이드라인 정보**"
        ),
        tools=[search_medical_guidelines_db],
        temperature=0.2,
    )
    
    # --- [추가됨] 자동 3회 재시도 (Auto-Retry) 로직 ---
    max_retries = 3
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-8b']
    last_error = None
    
    for attempt in range(max_retries):
        model_name = models_to_try[attempt % len(models_to_try)]
        try:
            logger.info(f"Attempt {attempt+1}: Requesting AI with model {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config
            )
            return DiagnoseResponse(
                status="success",
                ai_analysis=response.text,
                guidelines_found=True
            )
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt+1} failed with {model_name}. Error: {last_error}")
            if attempt < max_retries - 1:
                # 실패하면 2초 동안 숨 고르기 후 재시도
                await asyncio.sleep(2)
                
    # 3번의 재시도(총 6초 대기) 후에도 실패하면 최종 에러 반환
    raise HTTPException(
        status_code=429, 
        detail=f"API 과부하로 자동 3회 재시도했으나 실패했습니다. 잠시 후 다시 시도해 주세요. 상세: {last_error}"
    )

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)