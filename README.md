# Well... come to my Home 😒

LLM 기반 인테리어 배치 게임

## 🕹️ 게임 방법

### 1. 고객 의뢰 (LLM)

- 모델이 무작위 페르소나(직업, 성격, 취향)를 기반으로 고객이 되어 인테리어 의뢰서를 제공한다.
- '고객'은 마음 속으로 **원하는** 가구가 있다.
- 고객은 자신이 원하는 것을 **모호하게** 설명한다.
    - 예: 책장 → "책 읽는 걸 좋아해요"

### 2. 가구 배치 (Human)

- 플레이어는 고객의 모호한 의뢰를 보고 적절한 가구를 적절하게 배치한다.

### 3. 디자인 평가 (LLM)

- 가구의 배치 상태를 설명하는 **설명 문장**을 내부적으로 생성
- LLM에게 맨 처음의 의뢰서와 설명 문장을 프롬프트로 주어 비교 

### 4. 상세 피드백 (LLM)
점수와 함께 LLM이 날카로운 피드백을 돌려준다.

- 이때 LLM이 처음 정해둔 '원하는 가구'를 공개하여 피드백 근거로 활용한다.
    - 예: "제 지식을 보관할 선반이 빠져있어서 아쉽네요."

## 디자인 평가 요소
- 배치된 가구
    - **어떤** 가구가 있는가?
    - 고객이 원하던 특정 가구를 캐치하지 못했다면 감점 위험
- 가구의 위치
    - **어디에** 가구가 있는가?
    - 가구의 좌표를 계산하여 가구의 위치를 LLM이 파악
        - "문 앞에 침대는 좀 아니지 않나요?"
- 공간 밀도
    - **어떻게** 가구가 있는가?
    - 방 안에 가구가 밀집되어 있는지 혹은 너무 휑한지
        - 전체 칸 수 대비 오브젝트가 놓인 칸 수 비율
        - "중앙이 너무 넓어요"

## 🛠️ 기술 스택
- Game Client: PyGame
- LLM Provider: Ollama
- LLM Hosting: RunPod (Ollama 서버 실행)
- Model: EEVE-Korean-10.8B
- Language: Python 3.12

## 🔎 참고 작품
- 심즈 4
- 스타듀밸리
- GatherTown

## 🗃️ 애셋

- **Itch.io**
    - [Top-Down Retro Interior by Penzilla](https://penzilla.itch.io/top-down-retro-interior)
    - [Modern Interiors by Limezu](https://limezu.itch.io/moderninteriors)