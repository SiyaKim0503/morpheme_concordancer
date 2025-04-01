import streamlit as st
import re
from kiwipiepy import Kiwi
from jamo import h2j, hangul_to_jamo
from collections import Counter

st.set_page_config(page_title="형태소 콘코던서", layout="wide")
st.title("🔎 형태소 콘코던서 (Concordancer)")

st.markdown("""
**Kiwi 형태소 분석 결과 파일(.txt)을 업로드하여, 형태소 단위로 검색하고 문맥(KWIC) 정렬이 가능한 콘코던스 앱입니다.**  
- **정규표현식 검색**을 지원합니다.  
- **자소 검색**: `[초/중/종]` 형식으로 검색 가능하며, `*`은 와일드카드입니다. 예: `[*/*/ㅆ]다` → `갔다`, `봤다` 등  
- **정렬 기능**: 중심어 좌/우 형태소 기준 정렬, 빈도순 또는 가나다순

**파일 형식 예시**:
오늘/NNG 날씨/NNG 가/JKS 좋/VA 다/EF ./SF 기계/NNG 는/JX 언어/NNG 를/JKO 이해/NNG 하/XSV ㅂ니다/EF ./SF
""")

uploaded_file = st.file_uploader("📂 형태소 분석 결과 파일 (.txt, UTF-8)", type=["txt"])
regex_mode = st.checkbox("🔤 정규표현식 검색 사용")
jamo_mode = st.checkbox("🧩 자소 검색 사용")
search_query = st.text_input("검색어 입력", "")

col1, col2 = st.columns([1, 1])
with col1:
    sort_pos = st.selectbox("정렬 위치 (KWIC 기준)", options=["1L", "2L", "3L", "C", "1R", "2R", "3R"])
with col2:
    sort_mode = st.radio("정렬 방식", options=["빈도순", "가나다순"])

def decompose_syllable(syllable):
    # 한 글자를 초/중/종 분해
    code = ord(syllable) - 0xAC00
    if code < 0 or code > 11171:
        return (syllable, '', '')
    chosung = chr(0x1100 + code // 588)
    jungsung = chr(0x1161 + (code % 588) // 28)
    jongsung_index = code % 28
    jongsung = chr(0x11A7 + jongsung_index) if jongsung_index else ''
    return (chosung, jungsung, jongsung)

def jamo_match(query, word):
    """query: [초/중/종] with * support"""
    if not (query.startswith("[") and "]" in query):
        return False
    parts = query[1:query.index("]")].split("/")
    if len(parts) != 3:
        return False
    cho, jung, jong = parts
    for i in range(len(word) - 1):
        syl = word[i]
        dc = decompose_syllable(syl)
        if ((cho == "*" or cho == dc[0]) and
            (jung == "*" or jung == dc[1]) and
            (jong == "*" or jong == dc[2])):
            return True
    return False

def kwic_sort_key(entry, index):
    try:
        return entry[index]
    except IndexError:
        return ""

if uploaded_file and search_query:
    lines = uploaded_file.read().decode("utf-8").splitlines()
    results = []

    for line in lines:
        tokens = line.strip().split()
        for i, token in enumerate(tokens):
            form_tag = token.split("/")
            if len(form_tag) != 2:
                continue
            form, tag = form_tag
            matched = False

            if jamo_mode:
                matched = jamo_match(search_query, form)
            elif regex_mode:
                if re.search(search_query, form):
                    matched = True
            else:
                if search_query in form:
                    matched = True

            if matched:
                left = tokens[max(0, i - 3):i]
                center = tokens[i]
                right = tokens[i + 1:i + 4]
                results.append((left, center, right))

    # 정렬 기준 위치 지정
    sort_index_map = {
        "3L": 0, "2L": 1, "1L": 2,
        "C": 3,
        "1R": 4, "2R": 5, "3R": 6
    }

    def flatten_kwic(result):
        full = [''] * 7
        left, center, right = result
        for j in range(len(left)):
            full[2 - j] = left[-(j+1)]
        full[3] = center
        for j in range(len(right)):
            full[4 + j] = right[j]
        return full

    sorted_results = [flatten_kwic(r) for r in results]
    sort_idx = sort_index_map.get(sort_pos, 3)
    if sort_mode == "빈도순":
        count = Counter([r[sort_idx] for r in sorted_results])
        sorted_results.sort(key=lambda x: -count[x[sort_idx]])
    else:
        sorted_results.sort(key=lambda x: x[sort_idx])

    st.write(f"🔎 총 {len(sorted_results)}개 결과")

    table = []
    for row in sorted_results[:100]:  # 최대 100개까지만 화면 출력
        table.append([row[i] if row[i] else " " for i in range(7)])
    
    st.table(table)

    # 전체 텍스트 다운로드
    download_lines = ["\t".join(r) for r in sorted_results]
    download_text = "\n".join(download_lines)
    st.download_button("📥 결과 다운로드", download_text, file_name="concordance_result.txt")
else:
    st.info("📌 텍스트 파일을 업로드하고 검색어를 입력하세요.")
    
