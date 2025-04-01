import streamlit as st
import re
from kiwipiepy import Kiwi
from jamo import h2j
from collections import Counter

st.set_page_config(page_title="형태소 콘코던스", layout="wide")
st.title("🔎 형태소 콘코던서 (Concordancer)")

st.markdown("""
**형태소 분석 결과 파일을 기반으로 정규표현식 검색, 자소 검색, KWIC 정렬이 가능한 형태소 콘코던서입니다.**  
- 검색어 예: `하`, `.*다`, `[ㅎ/ㅏ/*]다`  
- 정렬 위치, 품사 필터링, 자소 검색 기능을 함께 활용해보세요.
""")

kiwi = Kiwi()

# --- 업로드 및 설정 영역 ---
uploaded_file = st.file_uploader("📂 형태소 분석 결과 파일 (.txt, UTF-8)", type=["txt"])
search_col1, search_col2 = st.columns([2, 1])
with search_col1:
    search_query = st.text_input("검색어 입력", "")
with search_col2:
    search_button = st.button("🔍 검색")

regex_mode = st.checkbox("🔤 정규표현식 검색", value=False)
jamo_mode = st.checkbox("🧩 자소 검색", value=False)
pos_filter = st.text_input("🎯 품사 필터 (예: VV, NNG, JKS 등 / 쉼표로 구분)", "")

col1, col2 = st.columns([1, 1])
with col1:
    sort_pos = st.selectbox("정렬 위치", options=["3L", "2L", "1L", "C", "1R", "2R", "3R"])
with col2:
    sort_mode = st.radio("정렬 기준", options=["빈도순", "가나다순"])

# --- 자소 검색 처리 ---
def decompose_syllable(syllable):
    code = ord(syllable) - 0xAC00
    if code < 0 or code > 11171:
        return (syllable, '', '')
    chosung = chr(0x1100 + code // 588)
    jungsung = chr(0x1161 + (code % 588) // 28)
    jongsung_index = code % 28
    jongsung = chr(0x11A7 + jongsung_index) if jongsung_index else ''
    return (chosung, jungsung, jongsung)

def jamo_match(query, word):
    if not (query.startswith("[") and "]" in query):
        return False
    parts = query[1:query.index("]")].split("/")
    if len(parts) != 3:
        return False
    cho, jung, jong = parts
    for syl in word:
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

# --- 검색 처리 ---
if uploaded_file and search_button and search_query:
    lines = uploaded_file.read().decode("utf-8").splitlines()
    results = []

    pos_filters = [p.strip() for p in pos_filter.split(",") if p.strip()]

    for line in lines:
        tokens = line.strip().split()
        for i, token in enumerate(tokens):
            form_tag = token.split("/")
            if len(form_tag) != 2:
                continue
            form, tag = form_tag

            if pos_filters and tag not in pos_filters:
                continue

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
                left = tokens[max(0, i - 10):i]
                center = tokens[i]
                right = tokens[i + 1:i + 11]
                results.append((left, center, right))

    # 정렬
    sort_index_map = {
        "3L": 0, "2L": 1, "1L": 2,
        "C": 3,
        "1R": 4, "2R": 5, "3R": 6
    }

    def flatten_kwic(result):
        full = [''] * 21
        left, center, right = result
        for j in range(len(left)):
            full[10 - len(left) + j] = left[j]
        full[10] = center
        for j in range(len(right)):
            full[11 + j] = right[j]
        return full

    sorted_results = [flatten_kwic(r) for r in results]
    sort_idx = sort_index_map.get(sort_pos, 10)
    if sort_mode == "빈도순":
        count = Counter([r[sort_idx] for r in sorted_results])
        sorted_results.sort(key=lambda x: -count[x[sort_idx]])
    else:
        sorted_results.sort(key=lambda x: x[sort_idx])

    # --- 결과 출력 ---
    st.write(f"🔎 총 {len(sorted_results)}개 결과")

    def color_token(tok, idx):
        if not tok or tok == "": return ""
        if idx == 10:
            return f"<span style='color:blue'><b>{tok}</b></span>"
        elif 7 <= idx <= 9 or 11 <= idx <= 13:
            return f"<span style='color:gray'>{tok}</span>"
        else:
            return tok

    html_lines = []
    for row in sorted_results[:100]:
        colored = [color_token(row[i], i) for i in range(21)]
        html_lines.append(" ".join(colored))

    st.markdown("<br>".join(html_lines), unsafe_allow_html=True)

    # 다운로드용 텍스트
    download_lines = ["\t".join(r) for r in sorted_results]
    download_text = "\n".join(download_lines)
    st.download_button("📥 결과 다운로드", download_text, file_name="concordance_result.txt")
else:
    st.info("🔽 파일을 업로드하고 검색어를 입력한 뒤, [검색] 버튼을 눌러주세요.")
