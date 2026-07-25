import streamlit as st
import psycopg2
import urllib.request
import json

DB_URL = "DB_URL_PLACEHOLDER"
API_KEY = "OPENROUTER_API_KEY_PLACEHOLDER"
MODEL = "google/gemma-4-31b-it"

def get_conn():
    return psycopg2.connect(DB_URL)

def query(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

st.set_page_config(page_title="수업안 생성기", layout="wide")
st.title("📝 수업안 생성기")

col1, col2 = st.columns([1, 1])

with col1:
    grade_groups = [r[0] for r in query("SELECT DISTINCT grade_group FROM seongchwigijun ORDER BY grade_group")]
    grade_group = st.selectbox("학년군 선택", grade_groups)

    subjects = [r[0] for r in query(
        "SELECT DISTINCT subject FROM seongchwigijun WHERE grade_group = %s ORDER BY subject",
        (grade_group,)
    )]
    subject = st.selectbox("교과 선택", subjects)

    standards = query(
        "SELECT id, standard_code, standard FROM seongchwigijun WHERE grade_group = %s AND subject = %s ORDER BY standard_code",
        (grade_group, subject)
    )
    standard_options = {f"{code} — {text[:50]}...": (sid, code, text) for sid, code, text in standards}
    selected_label = st.selectbox("성취기준 선택", list(standard_options.keys()))

with col2:
    if selected_label:
        sid, scode, stext = standard_options[selected_label]
        row = query("SELECT * FROM seongchwigijun WHERE id = %s", (sid,))[0]
        st.markdown(f"**성취기준 코드:** {row[5]}")
        st.markdown(f"**성취기준:** {row[6]}")
        with st.expander("성취수준 A"):
            st.write(row[7] or "-")
        with st.expander("성취수준 B"):
            st.write(row[8] or "-")
        with st.expander("성취수준 C"):
            st.write(row[9] or "-")
        with st.expander("해설"):
            st.write(row[10] or "-")
        with st.expander("적용시 주의사항"):
            st.write(row[11] or "-")

st.divider()

topic = st.text_input("수업 주제를 입력하세요", placeholder="예: 봄 풍경 그림일기 쓰기")
sessions = st.number_input("차시 (1차시 = 40분)", min_value=1, max_value=10, value=1)

if st.button("수업안 생성", type="primary", use_container_width=True):
    if not topic:
        st.error("수업 주제를 입력해주세요.")
    elif not selected_label:
        st.error("성취기준을 선택해주세요.")
    else:
        sid, scode, stext = standard_options[selected_label]
        row = query("SELECT * FROM seongchwigijun WHERE id = %s", (sid,))[0]

        prompt = f"""당신은 초중등 교육 전문가입니다. 다음 정보를 바탕으로 수업안을 작성해주세요.

[학년군] {row[1]}
[교과] {row[2]}
[영역] {row[3]}
[성취기준 코드] {row[5]}
[성취기준] {row[6]}
[성취수준 A] {row[7] or '없음'}
[성취수준 B] {row[8] or '없음'}
[성취수준 C] {row[9] or '없음'}
[해설] {row[10] or '없음'}
[적용시 주의사항] {row[11] or '없음'}
[수업 주제] {topic}
[총 차시] {sessions}차시 (1차시 = 40분)

{sessions}차시 분량의 수업안을 작성해주세요. 각 차시는 도입(5분), 전개(30분), 정리(5분) 단계로 구성하고, 차시별 학습 목표와 평가 방법을 포함해주세요.
응답은 반드시 한국어로 작성해주세요."""

        with st.spinner("수업안을 생성 중입니다..."):
            body = json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.7,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://blank-app.streamlit.app",
                }
            )
            try:
                resp = urllib.request.urlopen(req, timeout=120)
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"]
                st.markdown(content)
            except Exception as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {e}")
