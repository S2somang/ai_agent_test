import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from main import app as langgraph_app 
from jira_handler import build_knowledge_base

# 전역 변수 vs 초기화
vs = None

# Lifespan: 서버 시작할 때 지라 동기화, 종료할 때 자원 해제
@asynccontextmanager
async def lifespan(app: FastAPI):
    global vs
    print("⏳ 지라 데이터 동기화 중입니다... 잠시만 기다려주세요.")
    vs = build_knowledge_base() # 여기서 vs를 전역 변수로 할당
    import main
    main.vs = vs # main.py에 있는 vs도 같이 업데이트
    print("✅ 동기화 완료! 서버가 준비되었습니다.")
    yield
    print("👋 서버를 종료합니다.")

api = FastAPI(title="소망 AI API", lifespan=lifespan)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    mall: str
    content: str

@api.post("/chat")
async def chat_endpoint(request: QueryRequest):
    try:
        inputs = {"target_mall": request.mall, "user_query": request.content}
        result = langgraph_app.invoke(inputs)
        return {"answer": result.get("final_guide", "결과를 생성할 수 없습니다.")}
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 여기서 서버를 실행합니다!
    uvicorn.run("api_server:api", host="0.0.0.0", port=8000, reload=True)