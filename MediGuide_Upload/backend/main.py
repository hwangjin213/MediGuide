import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

from mcp_server import search_guidelines, get_all_diseases

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
        
    # 언어에 따른 프롬프트 동적 생성
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
    
    try:
        # 1. 찐 AI 통신: 메인 모델 (2.5-flash) 시도
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=config
        )
        ai_response_text = response.text
        
    except Exception as primary_error:
        logger.warning(f"2.5-flash failed (Quota/Error). Trying 1.5-flash-8b... Error: {primary_error}")
        try:
            # 2. 찐 AI 통신: 백업 모델 (1.5-flash-8b) 시도
            response = client.models.generate_content(
                model='gemini-1.5-flash-8b',
                contents=user_prompt,
                config=config
            )
            ai_response_text = response.text
            
        except Exception as secondary_error:
            # 둘 다 뻗으면 프론트엔드로 진짜 429 에러를 던져서 "잠시 대기" 팝업을 띄움
            logger.error(f"Both models failed. Error: {secondary_error}")
            raise HTTPException(
                status_code=429, 
                detail=f"RESOURCE_EXHAUSTED: {secondary_error}"
            )
            
    return DiagnoseResponse(
        status="success",
        ai_analysis=ai_response_text,
        guidelines_found=True
    )

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)