# -*- coding: utf-8 -*-
import os, io, re, time, json, base64, hashlib, datetime, pathlib, traceback
from typing import Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# ─────────────────────────────────────────────────────────────
# 초기 설정
# ─────────────────────────────────────────────────────────────
load_dotenv()
st.set_page_config(page_title="Havruta · DM", page_icon="💬", layout="centered")

RUN_DIR = pathlib.Path("havruta_runs")
RUN_DIR.mkdir(parents=True, exist_ok=True)

def init_state():
    if "chat" not in st.session_state:
        # 각 메시지: {"role": "user"|"assistant"|"system", "text": str, "wav_b64": Optional[str]}
        st.session_state.chat: List[Dict] = []
    if "topic" not in st.session_state:
        st.session_state.topic: Optional[str] = None
    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None
    if "run_stamp" not in st.session_state:
        st.session_state.run_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if "log_md" not in st.session_state:
        s = st.session_state.run_stamp
        st.session_state.log_md = RUN_DIR / f"havruta_{s}.md"
        st.session_state.log_jsonl = RUN_DIR / f"havruta_{s}.jsonl"

init_state()

# OpenAI (LLM/TTS)
API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY) if API_KEY else None
MODEL_GEN  = "gpt-4o"
MODEL_TTS  = "gpt-4o-mini-tts"
VOICE      = "alloy"
TEMPERATURE= 0.4
MAX_TOKENS = 600

STOP_WORDS = {"종료", "그만", "끝내", "끝내자"}

# ─────────────────────────────────────────────────────────────
# 하브루타 시스템 프롬프트 (쉬운 난이도)
# ─────────────────────────────────────────────────────────────
HABRUTA_SYSTEM = """
너는 하브루타 대화 파트너다. 오늘 대화는 '쉬운 질문' 위주로 진행한다.

원칙:
1) 사용자의 첫 발화는 '주제'로 간주한다. 그 주제를 한 줄로 재진술하고 아주 쉬운 확인 질문 1개로 시작한다.
2) 매 턴, 사용자의 말에 대해 '맞/틀'을 간단히 판단한다. (예: "대체로 맞아요", "여기엔 오해가 있어요")
3) 근거는 1~2개로 짧게, 반례 또는 한계는 1개만 짧게 언급한다.
4) 마지막은 항상 쉬운 되묻기 질문으로 끝난다.
5) 한국어, 부드러운 구어체, 3~5문장.

출력 형식:
- 한 문단 대화체. 마지막은 반드시 물음표로 끝난다.
"""

# ─────────────────────────────────────────────────────────────
# 스타일 (DM + 중앙정렬 + 높이 자동)
# ─────────────────────────────────────────────────────────────
DM_CSS = """
<style>
/* 스트림릿 기본 컨테이너 폭 제한 해제 + 가운데 */
.main .block-container {
    max-width: 100% !important;
    padding-top: 8px;
}

/* 중앙 정렬 래퍼 – 혹시 사이에 래퍼가 끼더라도 영향 받도록 */
.center {
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;   /* 가로 중앙 */
    justify-content: flex-start !important;
}

/* 상단 타이틀 */
.hero {
    text-align: center; color: #000; font-size: 26px; font-weight: 800;
    margin: 16px 0 8px 0;
}

/* 채팅 상자 – 스스로도 중앙 정렬 유지(보조 안전장치) */
.chat-wrap {
    width: 520px;
    max-width: 96vw;
    margin: 10px auto 12px auto !important;   /* ← 좌우 자동 */
    background: #fff;
    border-radius: 18px;
    box-shadow: 0 12px 30px rgba(0,0,0,.08);
    overflow: hidden;
    border: 1px solid #eee;
}

/* 헤더 */
.header {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 14px; border-bottom: 1px solid #eee; background: #fff;
}
.header .name { font-weight: 700; }

/* 채팅 영역: 높이 자동(최소/최대만) */
.chat {
    max-height: min(64vh, 1000px);
    min-height: 220px;
    overflow-y: auto; padding: 14px; background: #fff;
}

/* 말풍선 */
.msg { display:flex; margin:8px 0; align-items:flex-end; }
.msg .bubble { max-width:85%; padding:10px 14px; border-radius:18px; line-height:1.45; font-size:15px; }
.msg.user { justify-content:flex-end; }
.msg.user .bubble { background:#3797f0; color:#fff; border-bottom-right-radius:6px; }
.msg.assistant { justify-content:flex-start; }
.msg.assistant .bubble { background:#fff; color:#111; border:1px solid #e6e6e6; border-bottom-left-radius:6px; }
.avatar { width:28px; height:28px; border-radius:50%; background:#ddd; display:flex; align-items:center; justify-content:center;
          margin:0 8px; font-weight:600; color:#555; font-size:13px; }
.msg.assistant .avatar { order:-1; }
.small { font-size:12px; color:#777; margin-top:4px; }

/* 입력 컴포저 – 스스로도 중앙 정렬(보조 안전장치) */
.composer {
    width: 520px;
    max-width: 92vw;
    margin: 6px auto 16px auto !important;   /* ← 좌우 자동 */
    background: #fff;
    border-radius: 14px;
    border: 1px solid #eee;
    box-shadow: 0 8px 22px rgba(0,0,0,.06);
}
.composer-inner { padding: 10px 12px; }
.composer .stTextInput>div>div>input {
    padding: 10px 12px; border-radius: 10px; border: 1px solid #e6e6e6;
}
.btn-row { margin-top: 6px; }
</style>
"""


st.markdown(DM_CSS, unsafe_allow_html=True)
st.markdown('<div class="hero">SK네트웍스 Family AI 캠프 17기 하브루타</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def b64_wav(b: bytes) -> str: return base64.b64encode(b).decode("utf-8")
def audio_hash(b: bytes) -> str: return hashlib.sha1(b).hexdigest()
KOREAN = re.compile(r"[가-힣]")

def log_write(role: str, text: str):
    ts = time.time()
    with open(st.session_state.log_md, "a", encoding="utf-8") as f:
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n**{role} [{t}]**\n\n{text}\n")
    with open(st.session_state.log_jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": role, "text": text, "time": ts}, ensure_ascii=False) + "\n")

def push_msg(role: str, text: str, wav_b64: Optional[str] = None):
    st.session_state.chat.append({"role": role, "text": text, "wav_b64": wav_b64})
    log_write(role, text)

# ─────────────────────────────────────────────────────────────
# 렌더링
# ─────────────────────────────────────────────────────────────
def render_chat():
    # chat-wrap + header + chat (한 번만 생성)
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="header"><div class="avatar">봇</div><div class="name">Havruta</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="chat">', unsafe_allow_html=True)

    for m in st.session_state.chat:
        role = m["role"]
        text = (m["text"] or "").replace("\n", "<br/>")
        wav = m.get("wav_b64")

        if role == "user":
            st.markdown(f'''
            <div class="msg user">
              <div class="bubble">{text}</div>
              <div class="avatar">나</div>
            </div>''', unsafe_allow_html=True)
            if wav:
                st.markdown(f'''
                <div class="msg user">
                  <div class="bubble" style="background:#e7f1ff;color:#222">
                    <audio controls src="data:audio/wav;base64,{wav}"></audio>
                    <div class="small">내 녹음</div>
                  </div>
                </div>''', unsafe_allow_html=True)

        elif role == "assistant":
            st.markdown(f'''
            <div class="msg assistant">
              <div class="avatar">봇</div>
              <div class="bubble">{text}</div>
            </div>''', unsafe_allow_html=True)
            if wav:
                st.markdown(f'''
                <div class="msg assistant">
                  <div class="avatar">🔊</div>
                  <div class="bubble">
                    <audio controls autoplay src="data:audio/wav;base64,{wav}"></audio>
                    <div class="small">봇 음성</div>
                  </div>
                </div>''', unsafe_allow_html=True)

        else:
            st.markdown(f'''
            <div class="msg assistant">
              <div class="avatar">ℹ</div>
              <div class="bubble" style="opacity:.85">{text}</div>
            </div>''', unsafe_allow_html=True)

    # 오토스크롤
    st.markdown("""
    <script>
      const box = window.parent.document.querySelector('.chat');
      if (box) { box.scrollTop = box.scrollHeight; }
    </script>
    """, unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)  # .chat, .chat-wrap 닫기

def render_composer():
    st.markdown('<div class="composer"><div class="composer-inner">', unsafe_allow_html=True)
    typed = st.text_input("텍스트로 보내기…", key="typed", label_visibility="collapsed", placeholder="텍스트로 보내기…")

    st.markdown('<div class="btn-row">', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="small")
    with c1:
        audio_dict = mic_recorder(
            start_prompt="🎤 녹음",
            stop_prompt="⏹️ 종료·자동전송",
            just_once=False,
            format="wav",
            key="mic",
        )
    with c2:
        send = st.button("보내기", use_container_width=True)
    st.markdown('</div></div></div>', unsafe_allow_html=True)

    return audio_dict, typed, send

# ─────────────────────────────────────────────────────────────
# STT / LLM / TTS
# ─────────────────────────────────────────────────────────────
def valid_kr(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and len(t) >= 2 and bool(KOREAN.search(t))

def google_stt_from_wav(wav_bytes: bytes, language="ko-KR") -> str:
    rec = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = rec.record(source)
    try:
        return rec.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        push_msg("system", f"(Google STT 오류) {e}")
        return ""

def llm_reply(user_text: str) -> str:
    if not client:
        raise RuntimeError("OPENAI_API_KEY 미설정")
    sys_prompt = HABRUTA_SYSTEM
    if st.session_state.topic:
        sys_prompt += f"\n\n[현재 주제]: {st.session_state.topic}\n"
    resp = client.chat.completions.create(
        model=MODEL_GEN,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_text}
        ]
    )
    return resp.choices[0].message.content.strip()

def tts_wav_b64(text: str) -> str:
    if not client:
        raise RuntimeError("OPENAI_API_KEY 미설정")
    audio = client.audio.speech.create(
        model=MODEL_TTS,
        voice=VOICE,
        input=text,
        response_format="wav",
    )
    wav_bytes = getattr(audio, "content", None) or getattr(audio, "read", lambda: None)()
    if not wav_bytes:
        raise RuntimeError("TTS 실패: 바이트 없음")
    return base64.b64encode(wav_bytes).decode("utf-8")

# ─────────────────────────────────────────────────────────────
# 페이지 구성 & 동작
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="center">', unsafe_allow_html=True)
render_chat()
audio_dict, typed, send = render_composer()
st.markdown('</div>', unsafe_allow_html=True)

# 1) 녹음 종료 → 자동 전송
if audio_dict and "bytes" in audio_dict and audio_dict["bytes"]:
    wav = audio_dict["bytes"]
    h = audio_hash(wav)
    if h != st.session_state.last_audio_hash:
        st.session_state.last_audio_hash = h
        try:
            text = google_stt_from_wav(wav, "ko-KR").strip()
            if not valid_kr(text):
                push_msg("system", f"(무시된 인식) '{text}'")
                st.rerun()

            # 첫 발화 → 주제 저장
            if st.session_state.topic is None:
                st.session_state.topic = text
                push_msg("system", f"(오늘의 주제) {st.session_state.topic}")

            # 사용자 메시지(텍스트+오디오)
            push_msg("user", text, b64_wav(wav))

            # 종료어
            if text in STOP_WORDS:
                bye = "대화를 종료합니다. 좋은 하루 보내세요."
                bot_b64 = tts_wav_b64(bye) if client else None
                push_msg("assistant", bye, bot_b64)
                st.rerun()

            # LLM 응답 + TTS
            reply = llm_reply(text)
            bot_b64 = tts_wav_b64(reply)
            push_msg("assistant", reply, bot_b64)
        except Exception as e:
            push_msg("system", f"(STT/LLM/TTS 오류) {e}")
        st.rerun()

# 2) 텍스트 전송
if send and typed.strip():
    text = typed.strip()
    if st.session_state.topic is None:
        st.session_state.topic = text
        push_msg("system", f"(오늘의 주제) {st.session_state.topic}")

    push_msg("user", text, None)

    if text in STOP_WORDS:
        bye = "대화를 종료합니다. 좋은 하루 보내세요."
        bot_b64 = tts_wav_b64(bye) if client else None
        push_msg("assistant", bye, bot_b64)
        st.rerun()

    try:
        reply = llm_reply(text)
        bot_b64 = tts_wav_b64(reply)
        push_msg("assistant", reply, bot_b64)
    except Exception as e:
        push_msg("system", f"(LLM/TTS 오류) {e}")
    st.rerun()
