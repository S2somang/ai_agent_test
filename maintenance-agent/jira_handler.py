import os
from jira import JIRA
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# 1. 지라 접속 설정
JIRA_SERVER = "https://playautogmpproject.atlassian.net"
JIRA_EMAIL = "s2somang@cowave.kr"
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

def build_knowledge_base():
    # 2. JQL로 티켓 검색 (최근 완료된 유지보수 티켓 50개)
    # 소망님 보드의 프로젝트 키가 'ENG'이므로 이를 기준입니다.
    jql_query = 'project = "ENG" AND status = "완료" ORDER BY updated DESC'
    issues = jira.search_issues(jql_query, maxResults=50)
    
    documents = []
    
    for issue in issues:
        summary = issue.fields.summary # 제목
        description = issue.fields.description or "내용 없음" # 본문
        
        # 댓글 중 마지막 해결책 추출
        comments = jira.comments(issue)
        solution = comments[-1].body if comments else "해결책 기록 없음"
        
        # AI가 읽을 텍스트 데이터 구성
        combined_text = f"제목: {summary}\n문의내용: {description}\n최종해결: {solution}"
        
        # 검색 결과로 보여줄 메타데이터 (지라 링크 등)
        doc = Document(
            page_content=combined_text,
            metadata={
                "key": issue.key,
                "url": f"{JIRA_SERVER}/browse/{issue.key}",
                "title": summary
            }
        )
        documents.append(doc)
    
    # 3. 벡터 DB 생성 (메모리형)
    vector_store = InMemoryVectorStore.from_documents(
        documents, 
        embedding=OpenAIEmbeddings()
    )
    return vector_store

# 실행 및 테스트
vs = build_knowledge_base()
query = "29cm 옵션 수정 관련 지라 있어?"
results = vs.similarity_search(query, k=1)

if results:
    print(f"✅ 가장 유사한 티켓 발견!")
    print(f"티켓번호: {results[0].metadata['key']}")
    print(f"내용 요약: {results[0].page_content[:100]}...")
    print(f"링크: {results[0].metadata['url']}")