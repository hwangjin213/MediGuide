import os
import json
import logging
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medical-mcp-server")

# Initialize FastMCP Server
mcp = FastMCP("MedicalGuidelinesServer")

# MongoDB connection settings
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "medical_db"
COLLECTION_NAME = "guidelines"

# In-memory database fallback to guarantee 100% success during hackathon
fallback_db = []
use_fallback = False

def init_fallback_data():
    """Loads dummy data from JSON as in-memory fallback list."""
    global fallback_db
    try:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "medical_dummy_data.json")
        if not os.path.exists(data_path):
            data_path = os.path.join(os.path.dirname(__file__), "data", "medical_dummy_data.json")
            
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                fallback_db = json.load(f)
            logger.info(f"Successfully loaded {len(fallback_db)} mock records into In-Memory Fallback DB.")
        else:
            # Hardcoded absolute emergency fallback records
            fallback_db = [
                {
                    "symptom": "지속적인 마른 기침, 호흡 곤란, 쌕쌕거림(천명음), 밤에 심해지는 기침",
                    "disease": "기관지 천식 (Bronchial Asthma)",
                    "recommendations": ["폐기능 검사(PFT) 권장", "흡입용 코르티코스테로이드 치료", "유발 물질 회피"],
                    "guidelines": "GINA 2025 가이드라인 준수"
                },
                {
                    "symptom": "급격한 고열, 오한, 누런 가래를 동반한 기침, 가슴 통증, 호흡 시 통증",
                    "disease": "세균성 폐렴 (Bacterial Pneumonia)",
                    "recommendations": ["흉부 X-ray 촬영", "경험적 항생제 즉시 투여", "산소포화도 유지"],
                    "guidelines": "대한감염학회 지역사회획득폐렴 가이드라인 준수"
                }
            ]
            logger.info("Created fallback records inside memory.")
    except Exception as e:
        logger.error(f"Failed to load fallback data: {e}")

# Pre-load fallback data
init_fallback_data()

def get_db_collection():
    """Establishes connection to MongoDB and returns collection. Raises error if down."""
    # Set short connection timeout to fail fast and trigger fallback
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    # Trigger active server validation
    client.admin.command('ping') 
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def check_mongodb_status():
    """Checks if local MongoDB is up and seeds it if needed; otherwise enables In-Memory Fallback."""
    global use_fallback
    try:
        collection = get_db_collection()
        use_fallback = False
        logger.info("✅ MongoDB is online. Operating in production database mode.")
        
        # Auto-seed MongoDB if empty
        if collection.count_documents({}) == 0:
            logger.info("MongoDB guidelines collection is empty. Seeding dummy data...")
            if fallback_db:
                collection.insert_many(fallback_db)
                logger.info("Successfully seeded MongoDB guidelines database.")
    except Exception as e:
        use_fallback = True
        logger.warning(f"⚠️ Local MongoDB offline or not installed ({e}). GRACEFULLY SWITCHED TO IN-MEMORY FALLBACK DB MODE.")

# Run database configuration checks
check_mongodb_status()

@mcp.tool()
def search_guidelines(symptom_query: str) -> str:
    """
    Search clinical guidelines and recommendations in MongoDB (or Fallback DB) using patient symptoms.
    
    Args:
        symptom_query (str): Symptoms or key words to search (e.g., '고열', '기침', '마비').
    """
    logger.info(f"Searching guidelines tool invoked with query: '{symptom_query}' (Fallback Mode: {use_fallback})")
    
    # Pre-process query: Split into clean words to form an OR regex pattern (e.g., '명치|신물|기침')
    clean_query = symptom_query.replace(",", " ").replace(".", " ").replace("?", " ").strip()
    words = [w.strip() for w in clean_query.split() if len(w.strip()) > 1]
    
    if not words:
        words = [symptom_query.strip()]
        
    regex_pattern = "|".join(words)
    logger.info(f"Formulated search regex pattern: '{regex_pattern}'")
    
    # 1. MongoDB Mode
    if not use_fallback:
        try:
            collection = get_db_collection()
            query = {"symptom": {"$regex": regex_pattern, "$options": "i"}}
            results = list(collection.find(query))
            
            if not results:
                # Fallback search by disease name
                results = list(collection.find({"disease": {"$regex": regex_pattern, "$options": "i"}}))
                
            if results:
                return format_clinical_results(results)
        except Exception as e:
            logger.error(f"MongoDB search failed, falling back to memory search: {e}")
            
    # 2. In-Memory Fallback Mode (Guarantee 100% Uptime!)
    matched_results = []
    
    for item in fallback_db:
        # Check if any of the query words appear in symptom or disease fields
        symptom_text = item.get("symptom", "").lower()
        disease_text = item.get("disease", "").lower()
        
        match_found = False
        for word in words:
            word_lower = word.lower()
            if word_lower in symptom_text or word_lower in disease_text:
                match_found = True
                break
                
        if match_found:
            matched_results.append(item)
            
    if matched_results:
        return format_clinical_results(matched_results)
        
    return f"입력된 증상 및 질환 정보 '{symptom_query}'에 정밀 매칭되는 임상 가이드라인 가이드를 발견하지 못했습니다. 전문 의료진의 상세 소견을 구하십시오."


def format_clinical_results(records) -> str:
    """Helper to convert records into readable clinical guidelines markdown."""
    formatted_results = []
    for idx, item in enumerate(records, 1):
        recs = "\n".join([f"  - {r}" for r in item.get("recommendations", [])])
        markdown_item = (
            f"### {idx}. 질환명: {item.get('disease')}\n"
            f"- **주요 증상**: {item.get('symptom')}\n"
            f"- **권장 검사 및 조치**:\n{recs}\n"
            f"- **진료 가이드라인**: {item.get('guidelines')}\n"
            f"- *(운영 상태: {'로컬 메모리 안전모드' if use_fallback else 'MongoDB 실시간 연동'})*"
        )
        formatted_results.append(markdown_item)
    return "\n---\n".join(formatted_results)

@mcp.tool()
def get_all_diseases() -> str:
    """
    Retrieve all clinical disease guidelines stored in the active database.
    """
    records = fallback_db if use_fallback else []
    
    if not use_fallback:
        try:
            collection = get_db_collection()
            records = list(collection.find({}, {"disease": 1, "symptom": 1, "_id": 0}))
        except Exception as e:
            logger.error(f"Failed to fetch from MongoDB, using fallback list: {e}")
            records = fallback_db
            
    if not records:
        return "현재 데이터베이스에 등록된 질환 정보가 없습니다."
        
    disease_list = []
    for idx, item in enumerate(records, 1):
        disease_list.append(f"{idx}. {item.get('disease')} (증상군: {item.get('symptom')})")
        
    status_msg = "로컬 메모리 안전모드" if use_fallback or not records else "MongoDB 라이브 모드"
    return f"### 데이터베이스 등록 질환 목록 ({status_msg}):\n" + "\n".join(disease_list)

if __name__ == "__main__":
    mcp.run()
