import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import our MongoDB search logic to expose directly as Gemini tools
from mcp_server import search_guidelines, get_all_diseases

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medical-backend")

# Load environment variables
load_dotenv()

# Set up Gemini API via the cutting-edge google-genai SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    logger.warning("GEMINI_API_KEY is not configured yet! Please update backend/.env file.")

# Initialize the modern GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="One-click Medical AI Agent Backend",
    description="FastAPI orchestrator linking Chrome Extension with Google Cloud GenAI and MongoDB guidelines database.",
    version="1.0.0"
)

# Enable CORS for Chrome Extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/development ease
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DiagnoseRequest(BaseModel):
    symptom: str
    lang: Optional[str] = "ko"  # "ko" or "en" supported

class DiagnoseResponse(BaseModel):
    status: str
    ai_analysis: str
    guidelines_found: bool

# Define our function calling tool according to google-genai specs
def search_medical_guidelines_db(query: str) -> str:
    """
    Find official medical guidelines, recommendations, and matched diseases 
    stored in our clinical database using symptoms or disease terms.
    
    Args:
        query: Symptoms or disease words to look up (e.g., '고열', '천식').
    """
    logger.info(f"[Tool Execution] Searching MongoDB guidelines for: {query}")
    return search_guidelines(query)

@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose_patient(payload: DiagnoseRequest):
    """
    Receives symptom text and language choice, runs modern Gemini GenAI model with automated tool routing, 
    and synthesizes a detailed clinical guidance report in the requested language.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        raise HTTPException(
            status_code=500,
            detail="Gemini API Key is missing. Please set GEMINI_API_KEY in the backend/.env file."
        )
        
    symptom_text = payload.symptom.strip()
    target_lang = payload.lang.strip().lower() if payload.lang else "ko"
    
    if not symptom_text:
        raise HTTPException(status_code=400, detail="Symptoms input cannot be empty.")
        
    try:
        logger.info(f"Received symptom analysis request: '{symptom_text}' in language: '{target_lang}'")
        
        # Format custom prompts depending on requested language
        if target_lang == "en":
            lang_instruction = "IMPORTANT: You MUST write the entire final output report in ENGLISH."
            user_prompt = (
                f"The patient is reporting the following symptoms: '{symptom_text}'. "
                "Use the search_medical_guidelines_db tool to search our database, and synthesize a professional "
                "clinical guidelines report in English."
            )
        else:
            lang_instruction = "중요: 최종 분석 보고서의 모든 텍스트는 반드시 한국어(KOREAN)로 작성해야 합니다."
            user_prompt = (
                f"환자가 다음과 같은 증상을 호소하고 있습니다: '{symptom_text}'. "
                "search_medical_guidelines_db 도구를 호출하여 관련 정보를 검색하고, "
                "그 결과값을 기반으로 전문적인 최종 임상 보고서를 반드시 한국어로 작성해 주십시오."
            )
            
        # Configure generating content with modern GenAI configuration
        config = types.GenerateContentConfig(
            system_instruction=(
                "당신은 최고 수준의 전문 AI 임상 진단 어시스턴트입니다. "
                "환자의 증상을 정밀 분석하고, 반드시 제공된 도구(search_medical_guidelines_db)를 사용해 "
                "우리 내부 데이터베이스에 등록된 표준 임상 가이드라인과 매칭되는 질환이 있는지 조회하십시오. "
                "질의 시 핵심 단어(예: 고열, 마른기침, 마비)를 정밀하게 추출하여 조회해야 합니다.\n\n"
                f"{lang_instruction}\n\n"
                "데이터베이스에서 결과를 찾은 경우, 환자에게 다음과 같은 프리미엄 다크 테마에 어울리는 "
                "구조화된 마크다운 보고서를 완성하여 주십시오 (지정된 언어로 번역 및 작성할 것):\n"
                "1. 🩺 **의심 질환군 및 매칭 요약** (일치 확률 지표 언급)\n"
                "2. ⚠️ **가장 주의해야 할 핵심 위험 징후 (Red Flags)**\n"
                "3. 🏥 **추천 검사 및 즉시 조치 가이드라인** (데이터베이스 내용을 적극 반영)\n"
                "4. 📘 **참조 표준 가이드라인 정보**\n\n"
                "만약 내부 데이터베이스에서 일치하는 정보를 찾지 못했다면, 일반적인 의료 조언을 조심스럽게 "
                "제공하되 반드시 실제 전문의 진료를 받아야 함을 강조하십시오."
            ),
            # Bind our helper search tool
            tools=[search_medical_guidelines_db],
        )
        
        # Request generation using the verified active model 'gemini-2.5-flash'
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=config
        )
        
        ai_response_text = response.text
        logger.info("Successfully completed modern GenAI model execution.")
        
        # Check if function calling was triggered during the response
        guidelines_found = False
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            guidelines_found = True
                            break
                            
        return DiagnoseResponse(
            status="success",
            ai_analysis=ai_response_text or "분석 보고서 생성에 실패했습니다.",
            guidelines_found=guidelines_found
        )
        
    except Exception as e:
        logger.error(f"Error during modern GenAI execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"의료 에이전트 실행 중 내부 에러가 발생했습니다: {str(e)}"
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "One-click Medical AI Agent FastAPI Server is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
