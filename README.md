# SK네트웍스 Family AI 캠프 17기 하브루타

AI와 함께하는 하브루타 대화 학습 프로젝트

## 프로젝트 소개

이 프로젝트는 **하브루타(질문과 토론 중심 학습법)**를 AI와 함께 체험할 수 있도록 만든 스트림릿 기반 애플리케이션입니다.

- 사용자는 음성 또는 텍스트로 질문/주장을 입력합니다.
- AI는 동의/부분 동의 → 근거 → 반례/한계 → 반문 질문의 구조로 응답합니다.
- 모든 대화는 인스타그램 DM 스타일 UI로 표현되며, 텍스트 + 음성(TTS) 출력이 동시에 제공됩니다.
- "종료"라고 말하면 세션이 종료되고 로그가 저장됩니다.

## 주요 기능

- 음성 입력 : speech_recognition의 Google STT로 텍스트 변환 (OpenAI 토큰 절약)
- AI 대화 : OpenAI GPT-4o 모델 기반 하브루타 대화 파트너
- 음성 출력 : OpenAI TTS(gpt-4o-mini-tts)로 자동 생성 & 재생
- UI/UX : 인스타그램 DM 스타일 채팅창 (Streamlit + CSS 커스텀)
- 로그 저장 : 모든 대화를 .md / .jsonl 형식으로 저장

### 실행 전 설치해야하는 라이브러리와 실행

app.py 파일을 다운하고 같은 경로에 .env파일을 만들어 OPENAI_API_KEY를 입력해줍니다.

pip install streamlit python-dotenv openai speechrecognition streamlit-mic-recorder pydub 를 진행해 라이브러리를 설치해줍니다.

python -m streamlit run app.py 를 통해서 스트림릿을 실행합니다.

## 사용 방법

1. 파일과 라이브러리 설치 후 파일 경로로 가서 python -m streamlit run app.py를 실행해 줍니다.
2. 실행을 하면 스트림릿이 나옵니다.
<img width="742" height="593" alt="image" src="https://github.com/user-attachments/assets/ce74cc32-bc1b-4396-8e7e-150313507e5d" />

3. "녹음" 버튼을 누르고 진행할 하브루타 내용을 말하고 "종료,자동 전송" 버튼을 누릅니다.
4. 기다리게 되면 화면과 같이 사용자가 질문과 챗봇의 답변 내용이 나오게 됩니다.
<img width="728" height="639" alt="image" src="https://github.com/user-attachments/assets/c50504ad-2f38-43d1-b841-776a63d42101" />

5. 대화를 이어가게 되며, 대화를 하지 못할 경우에는 입력창으로 통해 대화를 진행할 수 있습니다.
<img width="725" height="752" alt="image" src="https://github.com/user-attachments/assets/b3afa389-0127-4a87-979d-cd0560df1db2" />
