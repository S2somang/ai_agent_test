import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from jira_handler import build_knowledge_base  # 파일명 변경 반영
from policy_handler import get_mall_policy  # MD 파일 읽는 함수

# 1. 상태 정의 (쇼핑몰명 필드 추가)
class AgentState(TypedDict):
    user_query: str      # 전체 문의 내용
    target_mall: str     # 입력받은 쇼핑몰명 (예: 29cm, 이지웰)
    related_jira: str    # 검색된 지라 내용
    final_guide: str     # 최종 안내 메시지

# 2. 노드 구현: 지라 검색 노드 (쇼핑몰명을 검색 키워드에 포함)
def retrieve_info_node(state: AgentState):
    global vs

    mall = state["target_mall"]
    query = state["user_query"]
    
    print(f"🔍 [{mall}] 관련 정보를 수집 중입니다...")
    
    # [A] 과거 지라 기록 검색 (Vector DB)
    search_query = f"[{mall}] {query}"
    jira_results = vs.similarity_search(search_query, k=1)
    jira_info = f"📌 과거 지라 기록:\n{jira_results[0].page_content}" if jira_results else "📌 관련 지라 기록 없음"
    
    # [B] 최신 쇼핑몰 정책 검색 (MD 파일)
    policy_info = get_mall_policy(mall)  # policy_handler.py에서 구현한 함수
    
    # [C] 두 정보를 하나로 합쳐서 다음 노드(guide)로 전달
    combined_context = f"{jira_info}\n\n📌 최신 쇼핑몰 정책:\n{policy_info}"
    
    # 💥 여기서 데이터가 잘 오는지 터미널에 찍어보세요!
    print(f"--- [DEBUG] 정책 읽기 결과 ---")
    print(policy_info[:100]) # 앞부분 100자만 출력
    print(f"----------------------------")
    
    combined_context = f"{jira_info}\n\n📌 최신 쇼핑몰 정책:\n{policy_info}"
    return {"related_jira": combined_context}



# 3. 노드 구현: 답변 생성 노드
def generate_guide_node(state: AgentState):
    llm = ChatOpenAI(model="gpt-4o")
    
    prompt = f"""
    너는 쇼핑몰 유지보수 개발자 소망의 AI 비서야. 
    과거 지라(Jira) 티켓과 쇼핑몰 정책(MD)을 뒤져서 운영팀의 질문에 가장 적절한 '근거'를 찾아내야 해.

    [상황]
    - 대상 쇼핑몰: {state['target_mall']}
    - 운영팀 문의: {state['user_query']}
    - 분석할 데이터:
    {state['related_jira']}
    
    [가이드라인]
    1. **적극적 분석**: 질문과 100% 일치하지 않더라도, 과거 지라 기록에 유사한 현상이나 시스템 제한 사항이 있다면 이를 근거로 답변해.
    2. **출처 필수**: 
       - 지라에서 찾았다면 (출처: Jira [티켓번호])
       - 정책에서 찾았다면 (출처: 쇼핑몰 정책 참고)
    3. **답변 구성**: 
       - 현상에 대한 원인/이유 (과거 기록 근거)
       - 운영팀이 안내하거나 조치해야 할 사항
    4. **TMI 제거**: 질문과 아예 상관없는 '6개월 이력'이나 '카탈로그' 같은 내용은 언급하지 마.

    [답변 시작 예시]
    "해당 현상은 현재 시스템 정책상 ~한 이유로 발생합니다." 또는 "과거 기록에 따르면 ~"
    """
    
    response = llm.invoke(prompt)
    return {"final_guide": response.content}


# 4. 그래프 빌드
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_info_node)
workflow.add_node("guide", generate_guide_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "guide")
workflow.add_edge("guide", END)
app = workflow.compile()

# 5. 실행 로직
if __name__ == "__main__":
    global vs
    print("⏳ 지라 데이터를 동기화 중입니다...")
    vs = build_knowledge_base()
    
    print("\n✅ 준비 완료! [쇼핑몰명], [문의내용] 형식으로 입력해 주세요.")
    print("👉 입력 후 엔터를 두 번 치면 분석을 시작합니다. (종료하려면 'q' 입력)")
    
    while True:
        print("\n" + "="*30 + " 입 력 창 " + "="*30)
        lines = []
        
        # 첫 번째 줄 입력 받기
        first_line = input()
        
        # 첫 줄에 바로 q나 Q를 치면 즉시 종료!
        if first_line.lower().strip() == 'q':
            print("👋 프로그램을 종료합니다. 고생하셨어요, 소망님!")
            break
            
        lines.append(first_line)
        
        # 여러 줄 입력을 위한 루프
        while True:
            line = input()
            if not line.strip(): # 빈 줄이 들어오면 입력 끝
                break
            lines.append(line)
        
        full_input = "\n".join(lines).strip()
        if not full_input: # 아무것도 입력 안 하고 엔터만 친 경우
            continue

        # [쇼핑몰명], [내용] 분리 로직
        if ',' in full_input:
            mall, content = full_input.split(',', 1)
            mall = mall.strip()
            content = content.strip()
        else:
            print("⚠️ '쇼핑몰명, 내용' 형식을 지켜주세요! (쉼표 필수)")
            continue

        # 2. 그래프 실행
        print(f"\n🔍 [{mall}] 관련 정보를 분석 중입니다...")
        result = app.invoke({
            "target_mall": mall,
            "user_query": content
        })
        
        print("\n" + "✨" * 30)
        print(f"🤖 [{mall}] 운영팀 안내 가이드")
        print("-" * 60)
        print(result["final_guide"])
        print("✨" * 30)