import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def auto_format_from_file(input_file="쇼핑몰정책.txt", output_file="mall_policies.md"):
    # 1. 원문 파일 읽기
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' 파일이 없습니다. 파일을 먼저 만들어주세요!")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()

    if not raw_text:
        print("⚠️ 파일 내용이 비어있습니다.")
        return

    llm = ChatOpenAI(model="gpt-4o")
    
    # 2. AI에게 정리 요청 (쇼핑몰 이름도 스스로 찾게 함)
    prompt = f"""
    아래 [원문 데이터]를 분석해서 우리가 약속한 마크다운 형식으로 정리해줘.
    
    [가이드라인]
    - 첫 줄은 반드시 '## 쇼핑몰이름' 형식이어야 함. (원문에서 쇼핑몰 이름을 찾아낼 것)
    - 소제목은 '### [항목명]' 형식을 사용함.
    - **중요한 제한사항, 숫자, 불가/필수** 단어는 **볼드체**로 강조함.
    - 불필요한 수식어는 빼고 개발자/운영팀이 바로 읽기 좋게 리스트(- )로 정리함.
    - 마지막에 '### 추가이슈' 섹션을 만들어 특이사항이 있다면 넣고, 없으면 생략함.

    [원문 데이터]
    {raw_text}
    """
    
    print("⏳ AI가 정책을 분석하고 마크다운으로 변환 중입니다...")
    response = llm.invoke(prompt)
    formatted_md = response.content

    # 3. 결과 저장 (기존 파일 뒤에 추가)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write("\n\n" + formatted_md)
    
    print(f"✅ 정리가 완료되었습니다! '{output_file}' 파일을 확인해보세요.")

if __name__ == "__main__":
    auto_format_from_file()