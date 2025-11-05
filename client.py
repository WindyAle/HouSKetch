# client.py
import random
import re

from model import ModelManager
from personas import PERSONAS

DEFAULT_PERSONA = PERSONAS[0] 

# LLM이 선택할 수 있는 가구 목록
FURNITURE_NAMES_LIST = "소파, 테이블, 침대, 화분, 책장, 옷장, 탁자, 컴퓨터, 전등, 선반"

# --- 1. 동적 의뢰서 생성 ---
def generate_request(model_manager: ModelManager) -> str:
    """
    ModelManager의 채팅 모델을 사용해
    독특하고 창의적인 고객 의뢰서를 생성합니다.
    """
    print("고객 요구사항 생성 중...\n")
    
    # AI에게 '고객' 역할을 부여하는 시스템 프롬프트
    # 페르소나 무작위 선택
    selected_persona = random.choice(PERSONAS)
    
    # 페르소나 기반 시스템 프롬프트
    # 사용 가능한 가구 목록을 가져옵니다. (LLM이 선택할 수 있도록)
    FURNITURE_NAMES_LIST = "소파, 테이블, 침대, 화분, 책장, 옷장, 탁자, 컴퓨터, 전등, 선반" 

    # 페르소나를 주입
    system_prompt = (
        f"당신은 고객 '{selected_persona['name']}'입니다. 당신의 상세 정보는 다음과 같습니다:\n"
        f"- 취향: {selected_persona['taste']}\n"
        f"- 성향: {selected_persona['tendency']}\n"
        f"- 말투: {selected_persona['tone']}\n\n"
        "당신은 지금부터 디자이너에게 방을 의뢰할 것입니다. 다음 3단계에 따라 행동하세요.\n\n"
        
        "1. [내면의 생각] : 당신의 취향과 성향에 따라, 다음 가구 목록에서 '반드시 있었으면 하는' 가구 2~3개를 **마음 속으로** 정합니다. 이것은 당신의 '비밀 요구사항(Wishlist)'입니다.\n"
        f"<가구 목록>: {FURNITURE_NAMES_LIST}\n\n"
        
        "2. [디자이너에게 할 말] : 1번에서 고른 가구의 **이름을 절대 직접 말하지 마세요.** 대신, 그 가구들이 암시하는 '분위기', '느낌', '목적'을 당신의 말투(tone)로 **모호하고 불명확하게** 1-2 문장으로 묘사합니다. (예: '침대' 대신 '하루의 끝에 편히 쉴 곳', '책장' 대신 '지식의 무게가 느껴지는...')\n\n"
        
        "3. [출력 형식] : 다른 말은 절대 하지 말고, 오직 다음 형식으로만 응답하세요:\n"
        "[WISHLIST]\n"
        "(여기에 1번에서 고른 가구 이름들을 쉼표로 구분하여 작성. 예: 침대, 책장)\n"
        "[REQUEST]\n"
        "(여기에 2번에서 생성한 모호한 의뢰서 내용을 작성)"
    )
    
    # 간단한 사용자 프롬프트
    user_prompt = (
        "당신의 성격과 취향에 100% 몰입해서, "
        "당신이 원하는 방을 의뢰하기 위한 [WISHLIST]와 [REQUEST]를 지시사항 형식에 맞게 생성하세요."
    )
    
    try:
        raw_response = model_manager.get_chat_response(system_prompt, user_prompt)
        
        # (신규) LLM 응답 파싱
        wishlist_match = re.search(r"\[WISHLIST\]\n(.*?)\n\[REQUEST\]", raw_response, re.DOTALL)
        request_match = re.search(r"\[REQUEST\]\n(.*?)$", raw_response, re.DOTALL)
        
        if wishlist_match and request_match:
            # 파싱 성공
            wishlist_str = wishlist_match.group(1).strip()
            # 쉼표로 구분하고, 공백 제거, 리스트화
            internal_wishlist = [item.strip() for item in wishlist_str.split(',') if item.strip()]
            
            request_text = request_match.group(1).strip().replace('"', '')
            
            print(f"[생성된 비밀 위시리스트: {internal_wishlist}]")
            return selected_persona, internal_wishlist, request_text
        else:
            # 파싱 실패 시 Fallback
            raise ValueError("LLM 응답이 지정된 형식을 따르지 않음.")

    except Exception as e:
        print(f"LLM 의뢰서 생성 실패 ({e}). 테스트 의뢰서로 대체합니다.")
 
        request_text = "저는 아늑한 스타일의 거실을 원해요. 반드시 소파 1개와 테이블 1개가 있어야 합니다."
        internal_wishlist = ["소파", "테이블"] # 테스트용 위시리스트

        print(f"   [테스트 위시리스트: {internal_wishlist}]")
        return selected_persona, internal_wishlist, request_text

# --- 2. 상세 피드백 생성 ---

def generate_feedback(model_manager: ModelManager, persona: dict, request: str, internal_wishlist: list, design_description: str, score: float) -> str:
    """
    ModelManager의 채팅 모델을 사용해
    점수에 기반한 상세한 고객 피드백을 생성합니다.
    """
    print("📄 고객 피드백 생성 중...")
    
    # AI에게 '평가자' 역할을 부여하는 시스템 프롬프트
    # (신규) 페르소나 기반 시스템 프롬프트
    system_prompt = (
        f"당신은 고객 '{persona['name']}'입니다. "
        f"당신의 성격과 말투는 다음과 같습니다: {persona['tendency']}\n"
        "당신은 방금 디자이너의 작업에 점수를 매겼습니다. "
        "당신의 성격과 말투에 100% 몰입하여, '왜' 그 점수를 주었는지 1-2문장의 구체적인 피드백을 한글로 작성하세요. "
        "점수가 높으면 당신의 방식대로 칭찬하고, 낮으면 당신의 방식대로 비판하세요."
    )
    
    wishlist_str = ", ".join(internal_wishlist) if internal_wishlist else "특별히 없음"
    
    user_prompt = (
        f"나의 원래 요구사항: \"{request}\"\n"
        f"(내가 마음 속으로 원했던 것: {wishlist_str})\n" # <-- (신규) LLM에게 비밀 정보 제공
        f"디자이너의 결과물: \"{design_description}\"\n"
        f"내 평점: {score:.1f} / 5.0\n\n"
        "이것을 참고하여 고객으로서 디자이너에게 피드백을 작성하세요. (만약 내 비밀 요구사항이 충족되지 않았다면 그 점을 불만스럽게 지적하세요.)"
    )
    
    feedback_text = model_manager.get_chat_response(system_prompt, user_prompt)
    feedback_text = feedback_text.strip().replace('"', '')
        
    print("[ 피드백 ]")
    return feedback_text