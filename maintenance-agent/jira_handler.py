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
    jql_query = 'project = "ENG" AND status IN (Done, "(재)Done") ORDER BY created DESC'
    issues = jira.search_issues(jql_query, maxResults=50)
    
    documents = []
    
    for issue in issues:
        summary = issue.fields.summary # 제목
        description = issue.fields.description or "내용 없음" # 본문
        
        # 모든 댓글을 하나의 텍스트로 합치기
        comments = jira.comments(issue)
        all_comments = "\n".join([c.body for c in comments]) if comments else "댓글 없음"
        # AI가 읽을 텍스트 데이터 구성 (모든 댓글 포함)
        combined_text = f"제목: {summary}\n문의내용: {description}\n[상세코멘트]:\n{all_comments}"
        
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


def fetch_realtime_jira(mall, query):
    # JQL: 해당 쇼핑몰 언급 + 최근 순 (상태 상관없이 모든 티켓 조회 추천)
    jql_query = f'project = "ENG" AND (summary ~ "{mall}" OR description ~ "{mall}") AND status IN (Done, "(재)Done") ORDER BY updated DESC'
    issues = jira.search_issues(jql_query, maxResults=10)
    
    jira_entries = []
    for issue in issues:
        summary = issue.fields.summary
        desc = issue.fields.description or "내용 없음"
        # 댓글 전체말고 최신 3~5개만
        comments = jira.comments(issue)[-5:]
        all_comments = "\n".join([c.body[:500] for c in comments]) # 댓글당 500자 제한        
        url = f"{JIRA_SERVER}/browse/{issue.key}"
        
        entry = f"### [Jira: {issue.key}]\n- 링크: {url}\n- 제목: {summary}\n- 코멘트내용: {all_comments}"
        jira_entries.append(entry)
        
    return "\n\n".join(jira_entries) if jira_entries else "관련된 최신 지라 기록이 없습니다."



# # 실행 및 테스트
# vs = build_knowledge_base()
# query = "29cm 옵션 수정 관련 지라 있어?"
# results = vs.similarity_search(query, k=1)

# if results:
#     print(f"✅ 가장 유사한 티켓 발견!")
#     print(f"티켓번호: {results[0].metadata['key']}")
#     print(f"내용 요약: {results[0].page_content[:100]}...")
#     print(f"링크: {results[0].metadata['url']}")