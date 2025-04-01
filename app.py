import streamlit as st
import re

# 자모 리스트
CHOSUNG_LIST = [chr(x) for x in range(0x1100, 0x1113)]
JUNGSUNG_LIST = [chr(x) for x in range(0x1161, 0x1176)]
JONGSUNG_LIST = [None] + [chr(x) for x in range(0x11A8, 0x11C3)]

compat_to_modern = {
    'ㄱ': 'ᄀ', 'ㄲ': 'ᄁ', 'ㄴ': 'ᄂ', 'ㄷ': 'ᄃ', 'ㄸ': 'ᄄ', 'ㄹ': 'ᄅ',
    'ㅁ': 'ᄆ', 'ㅂ': 'ᄇ', 'ㅃ': 'ᄈ', 'ㅅ': 'ᄉ', 'ㅆ': 'ᄊ', 'ㅇ': 'ᄋ',
    'ㅈ': 'ᄌ', 'ㅉ': 'ᄍ', 'ㅊ': 'ᄎ', 'ㅋ': 'ᄏ', 'ㅌ': 'ᄐ', 'ㅍ': 'ᄑ', 'ㅎ': 'ᄒ',
    'ㅏ': 'ᅡ', 'ㅐ': 'ᅢ', 'ㅑ': 'ᅣ', 'ㅒ': 'ᅤ', 'ㅓ': 'ᅥ', 'ㅔ': 'ᅦ', 'ㅕ': 'ᅧ',
    'ㅖ': 'ᅨ', 'ㅗ': 'ᅩ', 'ㅛ': 'ᅭ', 'ㅜ': 'ᅮ', 'ㅠ': 'ᅲ', 'ㅡ': 'ᅳ', 'ㅣ': 'ᅵ',
    'ㅘ': 'ᅪ', 'ㅙ': 'ᅫ', 'ㅚ': 'ᅬ', 'ㅝ': 'ᅯ', 'ㅞ': 'ᅰ', 'ㅟ': 'ᅱ', 'ㅢ': 'ᅴ'
}

def convert_to_modern(jamo):
    return compat_to_modern.get(jamo, jamo)

def split_jamo(char):
    BASE = 0xAC00
    CHOSUNG = 588
    JUNGSUNG = 28
    if not ('가' <= char <= '힣'):
        return char, None, None
    code = ord(char) - BASE
    cho = code // CHOSUNG
    jung = (code % CHOSUNG) // JUNGSUNG
    jong = (code % CHOSUNG) % JUNGSUNG
    return CHOSUNG_LIST[cho], JUNGSUNG_LIST[jung], JONGSUNG_LIST[jong]

def parse_pattern(pattern):
    m = re.match(r"(.*?)\[(\*|[^\]/])/(*|[^\]/])/(*|[^\]/])\](.*)", pattern)
    if not m:
        raise ValueError("패턴 형식이 잘못되었습니다. 예: 최[ㅈ/*/*], [ㅎ/*/*]다 등")
    pre, cho, jung, jong, post = m.groups()
    return pre, convert_to_modern(cho), convert_to_modern(jung), convert_to_modern(jong), post

def match_with_jamo(word, pre, cho_pat, jung_pat, jong_pat, post):
    idx = len(pre)
    if not word.startswith(pre) or not word.endswith(post):
        return False
    if len(word) <= idx:
        return False
    target_char = word[idx]
    c, j, jj = split_jamo(target_char)

    def match(jamo, pattern):
        return pattern == '*' or (jamo == pattern)

    return match(c, cho_pat) and match(j, jung_pat) and (jong_pat == '*' or match(jj, jong_pat))

def style(word, index):
    styles = {
        0: "<span style='color:blue; font-weight:bold'>",  # 중심어
        1: "<span style='color:red'>",
        2: "<span style='color:green'>",
        3: "<span style='color:purple'>"
    }
    reset = "</span>"
    color = styles.get(index, "")
    return f"{color}{word}{reset}"

def get_kwic(lines, pattern, context_size=10, sort='left'):
    pre, cho, jung, jong, post = parse_pattern(pattern)
    results = []
    for line in lines:
        words = line.strip().split()
        for i, word in enumerate(words):
            if match_with_jamo(word, pre, cho, jung, jong, post):
                left = words[max(0, i - context_size):i]
                right = words[i+1:i+1+context_size]
                center = word
                results.append((left, center, right))

    if sort == 'left':
        results.sort(key=lambda x: x[0][-1] if x[0] else '')
    elif sort == 'right':
        results.sort(key=lambda x: x[2][0] if x[2] else '')

    display = []
    for left, center, right in results:
        left_str = ' '.join([style(w, len(left)-i) for i, w in enumerate(left)]) if left else ''
        right_str = ' '.join([style(w, i+1) for i, w in enumerate(right)]) if right else ''
        display.append(f"{left_str} {style(center, 0)} {right_str}")
    return display

# Streamlit 인터페이스
st.title("🔍 자소 기반 KWIC 검색기")

uploaded_file = st.file_uploader("텍스트 파일 업로드", type=["txt"])
pattern = st.text_input("자소 패턴 (예: 최[ㅈ/*/*] 또는 [ㅎ/*/*]다)")
sort = st.radio("정렬 기준", options=["left", "right"], index=0)

if uploaded_file and pattern:
    lines = uploaded_file.getvalue().decode('utf-8-sig').splitlines()
    try:
        results = get_kwic(lines, pattern, context_size=10, sort=sort)
        st.markdown("---")
        st.markdown(f"총 {len(results)}건 결과")
        for line in results:
            st.markdown(line, unsafe_allow_html=True)
    except Exception as e:
        st.error(str(e))
