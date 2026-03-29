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
    # 사용자의 질문에서 핵심 키워드만 뽑아서 검색 쿼리 생성
    # 예: "29cm 마진율 수정 실패"
    query = state['user_query']
    
    print(f"🔍 [{mall}] 관련 정보를 수집 중입니다...")
    
    # [A] 과거 지라 기록 검색 (Vector DB)
    search_query = f"[{mall}] {query}"
    # 1. 지라 데이터 검색 (키워드 매칭 확률을 높이기 위해 query 다듬기)
    # 팁: 쇼핑몰 이름과 에러 메시지 키워드를 포함하면 더 정확해집니다.
    jira_docs = vs.similarity_search(f"{state['target_mall']} {query}", k=3)
    
    
    jira_list = []
    for doc in jira_docs:
        key = doc.metadata.get("key", "Unknown")
        url = doc.metadata.get("url", "No Link")
        # 🔴 이 텍스트 안에 '내용'뿐만 아니라 '링크'와 '키'가 반드시 포함되어야 AI가 답변에 씁니다!
        jira_list.append(f"### [Jira Ticket: {key}]\n- 티켓링크: {url}\n- 기록된 내용: {doc.page_content}")

    jira_info = "\n\n".join(jira_list) if jira_list else "검색된 지라 기록이 없습니다."


    # [B] 최신 쇼핑몰 정책 검색 (MD 파일)
    policy_info = get_mall_policy(mall)  # policy_handler.py에서 구현한 함수
    
    # 🔴 AI에게 주는 최종 컨텍스트를 아주 명확하게 구분합니다.
    full_context = f"""
    [데이터 소스 1: 과거 Jira 대응 기록]
    {jira_info}

    [데이터 소스 2: 쇼핑몰 운영 정책 문서]
    {policy_info}
    """

    return {"related_jira":full_context}



# 3. 노드 구현: 답변 생성 노드
def generate_guide_node(state: AgentState):
    llm = ChatOpenAI(model="gpt-4o")
    
    # 🔴 프롬프트 튜닝: 지라 티켓의 구체적인 코멘트를 절대 놓치지 않도록 강조
    prompt = f"""
    너는 쇼핑몰 유지보수 개발자 소망의 AI 비서야.
    제공된 [과거 Jira 대응 기록]과 [쇼핑몰 정책(MD)]을 분석해서 운영팀의 질문에 답변해줘.

    [운영팀 문의]
    - 쇼핑몰: {state['target_mall']}
    - 질문 내용: {state['user_query']}

    [분석 데이터]
    {state['related_jira']}
    
    [답변 가이드라인 - 필독]
    1. **지라 기록 최우선**: [데이터 소스 1]에 사용자의 에러 메시지나 특정 필드(예: 마진율)와 관련된 구체적인 코멘트가 있다면, **그것을 정답으로 간주하고 가장 먼저 설명해.** 일반적인 추측은 절대 금지야.
    
    2. **출처 명시 규칙**:
       - 지라 기록 인용 시: 반드시 문장 끝에 `(출처: Jira [티켓번호])`를 적고, 바로 아래 줄에 해당 티켓의 **링크**를 출력해.
       - 정책 문서 인용 시: 반드시 `(출처: {state['target_mall']} 정책 가이드)`라고 명시해.
    
    3. **내용 구체화**: "스크래핑이라 수정 불가"나 "파트너 권한 제한" 같은 지라 속 핵심 원인을 운영팀이 이해하기 쉽게 전달해줘.

    4. **답변 구성**:
       - [원인 및 결론]: 지라/정책 근거를 바탕으로 한 답변
       - [운영팀 조치사항]: 운영팀이 업체나 고객에게 어떻게 안내해야 하는지
       - [근거 자료]: 티켓 링크 및 정책 출처
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


vs = build_knowledge_base() # 서버 시작시 지라 데이터 딱 한번만 긁어와!!
# # 5. 실행 로직
# if __name__ == "__main__":
#     global vs
#     print("⏳ 지라 데이터를 동기화 중입니다...")
#     vs = build_knowledge_base()
    
#     print("\n✅ 준비 완료! [쇼핑몰명], [문의내용] 형식으로 입력해 주세요.")
#     print("👉 입력 후 엔터를 두 번 치면 분석을 시작합니다. (종료하려면 'q' 입력)")
    
#     while True:
#         print("\n" + "="*30 + " 입 력 창 " + "="*30)
#         lines = []
        
#         # 첫 번째 줄 입력 받기
#         first_line = input()
        
#         # 첫 줄에 바로 q나 Q를 치면 즉시 종료!
#         if first_line.lower().strip() == 'q':
#             print("👋 프로그램을 종료합니다. 고생하셨어요, 소망님!")
#             break
            
#         lines.append(first_line)
        
#         # 여러 줄 입력을 위한 루프
#         while True:
#             line = input()
#             if not line.strip(): # 빈 줄이 들어오면 입력 끝
#                 break
#             lines.append(line)
        
#         full_input = "\n".join(lines).strip()
#         if not full_input: # 아무것도 입력 안 하고 엔터만 친 경우
#             continue

#         # [쇼핑몰명], [내용] 분리 로직
#         if ',' in full_input:
#             mall, content = full_input.split(',', 1)
#             mall = mall.strip()
#             content = content.strip()
#         else:
#             print("⚠️ '쇼핑몰명, 내용' 형식을 지켜주세요! (쉼표 필수)")
#             continue

#         # 2. 그래프 실행
#         print(f"\n🔍 [{mall}] 관련 정보를 분석 중입니다...")
#         result = app.invoke({
#             "target_mall": mall,
#             "user_query": content
#         })
        
#         print("\n" + "✨" * 30)
#         print(f"🤖 [{mall}] 운영팀 안내 가이드")
#         print("-" * 60)
#         print(result["final_guide"])
#         print("✨" * 30)