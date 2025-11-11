# client.py
import random

from .model import ModelManager
from templates.personas import PERSONAS

DEFAULT_PERSONA = PERSONAS[0] 

# LLM이 선택할 수 있는 가구 목록
FURNITURE_NAMES_LIST = "작은 소파, 큰 소파, 테이블, 1인 침대, 2인 침대, 화분, 책장, 옷장, 탁자, 컴퓨터, 전등, 변기, 욕조, 스토브, 냉장고, 다리미판, 거울, 선반, 옷걸이, 식탁"

FURNITURE_LIST_AS_LIST = [item.strip() for item in FURNITURE_NAMES_LIST.split(',') if item.strip()]

# --- 1. 동적 의뢰서 생성 ---
def generate_request(model_manager: ModelManager) -> str:
    """
    (수정) 2단계 순서 변경. 위시리스트를 먼저 뽑고, 그에 맞는 의뢰서를 생성합니다.
    1. [사실] '비밀 위시리스트' (가구 3~5개)를 무작위로 선정합니다.
    2. [창의] 페르소나에 몰입해, 이 위시리스트를 '암시'하는 '모호한 의뢰서'를 생성합니다.
    """
    print("고객 요구사항 생성 중... (위시리스트 우선 생성)\n")
    
    # --- 테스트 모드 처리 (기존 로직) ---
    if not model_manager or not model_manager.is_ready:
        print(f"LLM 사용 불가. 테스트 의뢰서로 대체합니다.")
        selected_persona = random.choice(PERSONAS)
        # 테스트용 위시리스트 및 의뢰서
        internal_wishlist = ["작은 소파", "테이블"] 
        request_text = "저는 아늑한 스타일의 거실을 원해요. 편안히 기댈 곳과 찻잔을 둘 곳이 필요합니다."
        print(f"   [테스트 위시리스트: {internal_wishlist}]")
        return selected_persona, internal_wishlist, request_text

    try:
        # --- 1단계: (신규) 비밀 위시리스트 무작위 선정 ---
        k = random.randint(3, 5) # 3~5개
        internal_wishlist = random.sample(FURNITURE_LIST_AS_LIST, k)
        print(f"  [1단계] 비밀 위시리스트 생성: {internal_wishlist}")

        # --- 2단계: (신규) 위시리스트 기반 '모호한 의뢰서' 생성 ---
        print("  [2단계] 위시리스트 기반 의뢰서 생성 중...")
        selected_persona = random.choice(PERSONAS)
        
        system_prompt = (
            f"당신은 고객 '{selected_persona['name']}'입니다. 당신의 상세 정보는 다음과 같습니다:\n"
            f"- 취향: {selected_persona['taste']}\n"
            f"- 성향: {selected_persona['tendency']}\n"
            f"- 말투: {selected_persona['tone']}\n\n"
            "당신은 지금 디자이너에게 방을 의뢰할 것입니다. 당신이 **마음 속으로 원하는 가구**는 다음과 같습니다.\n"
            f"[비밀 위시리스트]: {', '.join(internal_wishlist)}\n\n"
            "**당신의 임무:**\n"
            "1. 이 [비밀 위시리스트]의 **가구 이름을 절대 직접 말하지 마세요.**\n"
            "2. 대신, 그 가구들이 왜 필요한지 '목적'이나 '행위'를 암시하는 방식으로 **매우 모호하게** 1-2 문장으로 묘사하세요.\n"
            "3. 당신의 페르소나 말투({selected_persona['tone']})를 완벽하게 반영하세요.\n"
            "4. **다른 말은 절대 하지 마세요.** 오직 당신의 말투로 된 '모호한 의뢰서' 텍스트만 반환하세요.\n\n"
            "   (예: '소파' -> '편안히 기댈 곳이 필요해요.')\n"
            "   (예: '소파' -> '편안한 느낌이 좋아요.')\n"
            "   (예: '소파' -> '앉을 곳이 있으면 좋겠어요.')\n"
            "   (예: '스토브' -> '집에서 요리하는 것을 좋아합니다.')\n"
            "   (예: '스토브' -> '가족이 모여 식사할 수 있는 곳')\n"
            "   (예: '냉장고' -> '부엌이 중요합니다.')\n"
            "   (예: '냉장고' -> '사람은 먹어야 하니까요.')\n"
            "   (예: '옷걸이' -> '옷을 정리할 수 있는 공간이 필요해요.')\n"
            "   (예: '옷장' -> '저는 옷이 많기 때문에 정리 공간이 필요해요.')\n"
            "   (예: '욕조' -> '저는 물에 들어가 멍때리는 것을 좋아해요.')\n"
            "   (예: '벽난로' -> '따뜻하고 편안해야 해요.')\n"
            "   (예: '식탁' -> '가족들이 모여 대화할 수 있는 공간이 필요해요.')\n"
            "   (예: '시계' -> '고급적인 장식이 있으면 좋아요.')\n"
            "   (예: '시계' -> '나는 시간이 중요한 사람이에요.')\n"
            "   (예: '다리미판' -> '저는 패션에 관심이 많아요.')\n"
            "   (예: '다리미판' -> '매일 옷 입는 것을 걱정해요.')\n"
            "   (예: '거울' -> '저는 패션에 관심이 많아요.')\n"
            "   (예: '거울' -> '매일 옷 입는 것을 걱정해요.')\n"
            "   (예: '화분' -> '마음을 진정시켜줄 친구가 필요해요.')\n"
            "   (예: '화분' -> '저는 평화로운 느낌이 좋아요.')\n"
            "   (예: '선반' -> '제 물건이 많아서 이걸 정리해야 해요.')\n"
            "   (예: '선반' -> '여러 물건을 올릴 수 있으면 좋겠다.')\n"
            "   (예: '컴퓨터', '책장' -> '밤에 조용히 작업할 공간이 필요해요.')\n"
            "   (예: '책장' -> '나의 지식을 보관할 장소가 있으면 좋겠어요.')\n\n"
        )
        
        user_prompt = "당신의 페르소나와 [비밀 위시리스트]에 100% 몰입하여, 지금 바로 '모호한 의뢰서' 텍스트만 작성하세요."

        # (신규) LLM 호출 (1회)
        request_text = model_manager.get_chat_response(system_prompt, user_prompt)
        request_text = request_text.strip().replace('"', '') # 따옴표 제거
        
        if not request_text or "🚨" in request_text:
             raise Exception("2단계 의뢰서 텍스트 생성 실패")
             
        print(f"  [2단계] 생성된 의뢰서: {request_text}")
        
        # (성공) 모든 데이터 반환
        return selected_persona, internal_wishlist, request_text
        
    except Exception as e:
        # (실패) LLM 호출이 실패한 경우
        print(f"LLM 의뢰서 생성 실패 ({e}). 재시도를 위해 None을 반환합니다.")
        return None, None, None # main.py의 재시도 로직이 처리

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
        f"(내가 마음 속으로 원했던 것: {wishlist_str})\n"
        f"디자이너의 결과물 (상세 묘사): \"{design_description}\"\n" # <--- 이 묘사에 밀도/공간 정보가 포함됨
        f"내 평점: {score:.1f} / 5.0\n\n"
        "이것을 참고하여 고객으로서 디자이너에게 피드백을 작성하세요.\n"
        "1. (필수) 내 비밀 요구사항(Wishlist)이 충족되지 않았다면 그 점을 불만스럽게 지적하세요.\n"
        "2. (필수) '디자이너의 결과물' 묘사를 보고, 방의 '밀도'나 '공간 배치'(중앙부, 벽가 등)에 대해서도 한마디 언급하세요.\n"
        "(예: '중앙부가 비어있어 좋네요', '너무 빽빽해서 답답해요', '입구 근처에 가구가 많아 불편해요')"
    )
    
    feedback_text = model_manager.get_chat_response(system_prompt, user_prompt)
    feedback_text = feedback_text.strip()
        
    # "Translation" 태그가 있는지 확인하고, 있다면 그 앞부분만 잘라냄
    # .split('Translation')은 태그가 없으면 [전체 텍스트]를,
    # 태그가 있으면 ['태그 앞 텍스트', '태그 뒤 텍스트']를 반환합니다.
    # [0]을 선택하면 두 경우 모두 원하는 결과를 얻을 수 있습니다.
    feedback_text = feedback_text.split('T')[0]
    
    # 3. (기존) 불필요한 따옴표를 제거하고, 잘라낸 후 남았을지 모를 공백을 다시 제거
    feedback_text = feedback_text.replace('"', '').strip()
    # ---
        
    print("[ 피드백 ]")
    return feedback_text