import os
from dotenv import load_dotenv

load_dotenv()
import re

def get_mall_policy(mall_name):
    try:
        with open("mall_policies.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        # '## '로 시작하는 섹션들을 찾습니다. (공백 무관하게)
        sections = re.split(r'\n## ', "\n" + content)
        
        for section in sections:
            if not section.strip(): continue
            
            lines = section.split("\n")
            header = lines[0].strip().lower()
            
            # 쇼핑몰 이름 매칭
            if mall_name.lower() in header:
                return section.strip()
        
        return f"⚠️ '{mall_name}'에 대한 정책을 찾지 못했습니다."
    except Exception as e:
        return f"❌ 오류: {e}"