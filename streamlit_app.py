import streamlit as st
import psycopg2
import urllib.request
import json

DB_URL = st.secrets["DB_URL"]
API_KEY = st.secrets["API_KEY"]
MODEL = "google/gemma-4-31b-it"

st.set_page_config(page_title="수업안 생성기", layout="wide")

st.markdown("""
<style>
.lesson-plan {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 2rem;
    margin: 1rem 0;
    border: 1px solid #e0e0e0;
}
.lesson-plan h1 { font-size: 1.6rem; color: #1a1a2e; border-bottom: 3px solid #4361ee; padding-bottom: 8px; margin-top: 0; }
.lesson-plan h2 { font-size: 1.3rem; color: #4361ee; margin-top: 1.8rem; border-left: 4px solid #4361ee; padding-left: 10px; }
.lesson-plan h3 { font-size: 1.1rem; color: #2d3142; margin-top: 1.2rem; }
.lesson-plan h4 { font-size: 1rem; color: #4a4e6b; margin-top: 0.8rem; }
.lesson-plan p { line-height: 1.7; margin: 0.4rem 0; }
.lesson-plan ul, .lesson-plan ol { line-height: 1.8; }
.lesson-plan table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.lesson-plan th { background: #4361ee; color: white; padding: 10px 14px; text-align: left; }
.lesson-plan td { padding: 10px 14px; border-bottom: 1px solid #ddd; }
.lesson-plan tr:nth-child(even) { background: #f1f3f5; }
.lesson-plan blockquote { border-left: 4px solid #4361ee; background: #eef0ff; padding: 12px 16px; margin: 1rem 0; border-radius: 4px; }
.lesson-plan hr { border: none; border-top: 2px dashed #d0d0d0; margin: 1.5rem 0; }
.lesson-plan strong { color: #1a1a2e; }
.plan-card {
    background: white; border-radius: 12px; padding: 1.5rem; margin: 1.2rem 0;
    border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border-top: 4px solid #4361ee;
}
.plan-card h3 { margin-top: 0; color: #4361ee; }
.session-badge {
    display: inline-block; background: #4361ee; color: white;
    padding: 4px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.title("📝 수업안 생성기")
st.caption("성취기준을 선택하고 주제를 입력하면 AI가 상세한 수업안을 작성합니다.")

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

with st.container(border=True):
    col1, col2 = st.columns([1, 1.2])

    with col1:
        grade_groups = [r[0] for r in query("SELECT DISTINCT grade_group FROM seongchwigijun ORDER BY grade_group")]
        grade_group = st.selectbox("📚 학년군 선택", grade_groups, index=None, placeholder="학년군을 선택하세요")

        subjects = []
        if grade_group:
            subjects = [r[0] for r in query(
                "SELECT DISTINCT subject FROM seongchwigijun WHERE grade_group = %s ORDER BY subject",
                (grade_group,)
            )]
        subject = st.selectbox("📖 교과 선택", subjects, index=None, placeholder="교과를 선택하세요")

        standards = []
        if grade_group and subject:
            standards = query(
                "SELECT id, standard_code, standard FROM seongchwigijun WHERE grade_group = %s AND subject = %s ORDER BY standard_code",
                (grade_group, subject)
            )
        standard_options = {}
        if standards:
            for sid, code, text in standards:
                label = text[:60] + "..." if len(text) > 60 else text
                standard_options[f"[{code}] {label}"] = (sid, code, text)
        selected_label = st.selectbox("🎯 성취기준 선택", list(standard_options.keys()) if standard_options else [], index=None, placeholder="성취기준을 선택하세요")

    with col2:
        if selected_label:
            sid, scode, stext = standard_options[selected_label]
            row = query("SELECT * FROM seongchwigijun WHERE id = %s", (sid,))[0]

            st.markdown(f"""
            <div style="background:#eef0ff;border-radius:10px;padding:1.2rem 1.5rem;border-left:4px solid #4361ee;margin-bottom:1rem;">
                <div style="font-size:0.8rem;color:#666;">성취기준 코드</div>
                <div style="font-size:1.1rem;font-weight:700;color:#1a1a2e;">{row[5]}</div>
                <div style="font-size:0.9rem;color:#333;margin-top:6px;">{row[6]}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📊 성취수준", expanded=False):
                tabs = st.tabs(["A (상)", "B (중)", "C (하)"])
                with tabs[0]: st.write(row[7] or "-")
                with tabs[1]: st.write(row[8] or "-")
                with tabs[2]: st.write(row[9] or "-")

            with st.expander("💡 해설"):
                st.write(row[10] or "-")

            with st.expander("⚠️ 적용시 주의사항"):
                st.write(row[11] or "-")

st.divider()

topic = st.text_input("✏️ 수업 주제", placeholder="예: 봄 풍경 그림일기 쓰기, 분수의 덧셈과 뺄셈, 계절에 따른 날씨 변화")
sessions = st.number_input("⏱️ 차시 (1차시 = 40분)", min_value=1, max_value=10, value=1)

generate = st.button("🚀 수업안 생성", type="primary", use_container_width=True)

if generate:
    if not topic:
        st.error("수업 주제를 입력해주세요.")
    elif not selected_label:
        st.error("성취기준을 선택해주세요.")
    else:
        sid, scode, stext = standard_options[selected_label]
        row = query("SELECT * FROM seongchwigijun WHERE id = %s", (sid,))[0]

        session_plural = "차시" if sessions == 1 else f"차시 (총 {sessions * 40}분)"
        session_detail = ""
        for i in range(1, sessions + 1):
            session_detail += f"""
### {i}차시 (40분)"""
            if sessions > 1:
                session_detail += f"""
학습 목표:
- [목표 1]
- [목표 2]

| 단계 (시간) | 교수·학습 활동 | 유의점 및 자료 |
|---|---|---|
| 도입 (5분) | | |
| 전개 (30분) | | |
| 정리 (5분) | | |

**평가 방법:**
- [평가 기준 및 방법]

"""
            else:
                session_detail += f"""
학습 목표:
- [목표 1]
- [목표 2]

| 단계 (시간) | 교수·학습 활동 | 유의점 및 자료 |
|---|---|---|
| 도입 (5분) | | |
| 전개① (10분) | | |
| 전개② (10분) | | |
| 전개③ (10분) | | |
| 정리 (5분) | | |

**평가 방법:**
- [평가 기준 및 방법]

"""
        prompt = f"""당신은 20년 경력의 초중등 교육 전문가입니다. 아래 정보를 바탕으로 매우 상세하고 현장감 있는 수업안을 작성해주세요.

## 대상 정보
- 학년군: {row[1]}
- 교과: {row[2]}
- 영역: {row[3]}
- 성취기준 코드: {row[5]}
- 성취기준: {row[6]}

## 성취수준
- A (상): {row[7] or '없음'}
- B (중): {row[8] or '없음'}
- C (하): {row[9] or '없음'}

## 해설
{row[10] or '없음'}

## 적용시 주의사항
{row[11] or '없음'}

## 수업 개요
- 수업 주제: {topic}
- 총 차시: {sessions}차시 (1차시 = 40분)

## 요구사항
1. 각 차시는 도입(5분) → 전개(30분) → 정리(5분)로 구성해주세요.
2. 전개 단계는 2~3개의 세부 활동으로 나누어 구체적인 교사 발문과 학생 활동을 포함해주세요.
3. 차시별로 다음을 반드시 포함해주세요:
   - 학습 목표 (2~3개, 구체적이고 측정 가능하게)
   - 교수·학습 활동 (표 형식: 단계/시간, 교수·학습 활동, 유의점 및 자료)
   - 평가 방법 (평가 기준, 평가 방법, 피드백 계획)
   - 준비물 및 자료
4. 학습자의 수준(성취수준 A/B/C)을 고려한 **수준별 지도 방법**을 포함해주세요.
5. 현장 교사가 바로 활용할 수 있도록 구체적인 발문 예시와 예상 학생 반응을 포함해주세요.
6. {sessions}개 차시가 유기적으로 연결되도록 차시 간 연계성을 고려해주세요.

## 출력 형식
- 마크다운 형식으로 작성해주세요.
- 각 차시는 `---` 구분선으로 나누어주세요.
- 표는 반드시 마크다운 테이블로 작성해주세요.
"""

        with st.spinner("📋 수업안을 생성 중입니다... (약 30~60초 소요)"):
            body = json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8192,
                "temperature": 0.6,
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
                resp = urllib.request.urlopen(req, timeout=180)
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"]

                with st.container():
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
                        <span style="font-size:1.4rem;">📋</span>
                        <div>
                            <div style="font-size:1.2rem;font-weight:700;">{topic}</div>
                            <div style="font-size:0.85rem;color:#666;">{row[1]} · {row[2]} · [{row[5]}] · 총 {sessions}차시</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f'<div class="lesson-plan">{content}</div>', unsafe_allow_html=True)

                st.success("✅ 수업안이 생성되었습니다. 필요시 다시 생성하거나 주제를 수정해보세요.")
            except Exception as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {e}")
