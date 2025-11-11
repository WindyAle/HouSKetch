# evaluation.py (Refactored)
import numpy as np
import re

from .model import ModelManager

def _get_design_facts(placed_furniture: list, room_width: int, room_height: int) -> str:
    """
    (내부 헬퍼 함수)
    가구 배치 리스트와 방 크기를 기반으로,
    LLM이 평가할 '사실 데이터'를 텍스트로 생성합니다.
    (기존 describe_design의 로직과 동일)
    """
    if not placed_furniture:
        return "방이 완전히 비어 있습니다. 텅 빈 공간입니다."

    # --- 1. 항목별 개수 요약 ---
    item_counts = {}
    total_base_cells = 0 # 가구가 차지하는 바닥 면적
    
    for f in placed_furniture:
        name = f['item']['name']
        item_counts[name] = item_counts.get(name, 0) + 1
        
        # (신규) Z-Sorting 로직을 위한 'base_size' 참조
        base_size = f['item'].get('base_size', (1, 1)) # 없으면 (1,1)
        rotation = f.get('rotation', 0)
        
        if rotation % 2 == 1: # 90도 회전
            total_base_cells += base_size[1] * base_size[0]
        else:
            total_base_cells += base_size[0] * base_size[1]

    item_list_str = ", ".join([f"{count}개의 {name}" for name, count in item_counts.items()])
    description = f"이 방에는 총 {len(placed_furniture)}개의 가구가 있습니다. (종류: {item_list_str})\n"

    # --- 2. 구역별 배치 분석 ---
    wall_items = []
    center_items = []
    entrance_items = [] # y가 큰 쪽 (아래쪽)

    # 구역 정의 (ROOM_WIDTH=10, ROOM_HEIGHT=8 기준 예시)
    entrance_line = room_height - 2 # y=6, 7
    # 벽에서 2칸 안쪽을 '중앙'으로 정의
    center_x_start, center_x_end = 2, room_width - 2 # x=2~7
    center_y_start, center_y_end = 2, room_height - 2 # y=2~5

    for f in placed_furniture:
        name = f['item']['name']
        x, y = f['grid_pos']
        
        # 가구의 '바닥' 격자 위치 기준
        if y >= entrance_line:
            entrance_items.append(f"{name} ({x},{y})")
        elif (x < center_x_start or x >= center_x_end or 
              y < center_y_start or y >= center_y_end):
            wall_items.append(f"{name} ({x},{y})")
        else:
            center_items.append(f"{name} ({x},{y})")

    # --- 3. 묘사 생성 ---
    description += "\n[ 공간 배치 분석 ]\n"
    
    if not center_items and not wall_items and not entrance_items and placed_furniture:
        description += "- 모든 가구가 한 곳에 뭉쳐있습니다.\n"

    if center_items:
        description += f"- 방의 중앙부에는 {', '.join(center_items)} 등이 배치되어 공간의 중심을 잡고 있습니다.\n"
    else:
        description += "- 방의 중앙부는 비어있어 개방감이 느껴집니다.\n"
    
    if wall_items:
        description += f"- 벽가에는 {', '.join(wall_items)} 등이 배치되었습니다.\n"
    
    if entrance_items:
        description += f"- 입구(아래쪽) 근처에는 {', '.join(entrance_items)} 등이 놓여 있습니다.\n"

    # --- 4. 밀도/여백 묘사 (신규) ---
    total_cells = room_width * room_height
    density_ratio = total_base_cells / total_cells
    
    description += "\n[ 밀도 및 인상 ]\n"
    if density_ratio == 0:
        pass # "비어 있음"은 첫 줄에서 이미 처리
    elif density_ratio < 0.1: # 10% 미만
        description += "- 전반적으로 방이 매우 넓고 여백이 많아 미니멀한 인상을 줍니다."
    elif density_ratio > 0.4: # 40% 초과
        description += "- 전반적으로 방이 가구로 빽빽하게 채워져 있어 동선이 복잡해 보입니다."
    else:
        description += "- 가구들이 적절한 간격을 두고 균형 있게 배치되어 있습니다."
            
    # print("[상세 디자인 묘사 (모델에게 넘겨주는 프롬프트)]")
    # print(description)
    return description

# --- 1. 디자인 설명서 생성 (로직 동일) ---
def describe_design(model_manager: ModelManager, placed_furniture: list, room_width: int, room_height: int) -> str:
    """
    LLM을 호출하여, 배치된 가구의 '사실'을 '자연스러운' 문장으로 묘사합니다.
    """
    
    # 1. 먼저, 프로그램적으로 사실 데이터를 수집합니다.
    design_facts = _get_design_facts(placed_furniture, room_width, room_height)
    
    # 2. LLM이 준비되지 않았거나, 방이 비어있으면 LLM을 호출할 필요가 없습니다.
    if not model_manager or not model_manager.is_ready or not placed_furniture:
        print(design_facts)
        return design_facts # 사실 데이터(기존 묘사)를 그대로 반환

    # 3. LLM에게 '자연스러운 묘사'를 요청하는 프롬프트
    system_prompt = (
        "당신은 인테리어 디자이너 또는 공간 비평가입니다. "
        "당신은 딱딱한 '데이터 리포트'를 받아서, 그것을 '감성적이고 자연스러운' 묘사 문장(1-2 문단)으로 재작성해야 합니다. "
        "사실을 왜곡하지 말고, 긍정/부정 판단도 하지 마세요. 오직 '묘사'만 하세요. "
        "(예: '방이 빽빽합니다' -> '가구들이 공간을 알차게 채우고 있네요.')"
    )
    
    user_prompt = (
        f"다음은 이 방에 대한 '사실 데이터'입니다. 이 데이터를 기반으로 자연스러운 묘사 글을 한국어로 작성하세요:\n\n"
        f"--- 데이터 리포트 ---\n{design_facts}\n---"
    )
    
    try:
        natural_description = model_manager.get_chat_response(system_prompt, user_prompt)
        
        # LLM이 응답에 붙일 수 있는 불필요한 따옴표 제거
        natural_description = natural_description.strip().replace('"', '')

        print("[상세 디자인 묘사]")
        print(natural_description)
        return natural_description

    except Exception as e:
        print(f"LLM 묘사 생성 실패 ({e}). 사실 데이터(Fallback)를 반환합니다.")
        print(design_facts)
        return design_facts # 실패 시 팩트 리포트 반환

# --- 2. 유사도 계산 (로직 동일) ---

def calculate_similarity_score(vec_a: list[float], vec_b: list[float]) -> float:
    """
    두 벡터(A:요구사항, B:디자인)의 코사인 유사도를 계산하여 0~5점 척도로 반환합니다.
    """

    vec_a_np = np.array(vec_a)
    vec_b_np = np.array(vec_b)

    cosine_similarity = np.dot(vec_a_np, vec_b_np) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    print(cosine_similarity)
    
    score = ((cosine_similarity + 1) / 2) * 5.0
    return score

# (신규) AI 평가자(LLM-as-Judge)를 호출하는 함수
def get_llm_judge_score(model_manager, request_text, internal_wishlist, design_description):
    """
    채팅 모델(LLM)을 '평가자'로 사용하여, 
    요구사항, 위시리스트, 실제 디자인을 복합적으로 평가하여 0~5점 사이의 점수를 반환합니다.
    """
    print("AI 평가자가 점수 계산 중...")

    system_prompt = (
        "당신은 까다로운 인테리어 디자인 평가자입니다. "
        "당신은 0.0에서 5.0 사이의 소수점 한 자리 점수(예: '3.5')만을 반환해야 합니다. "
        "다른 말은 절대 하지 마세요. 오직 숫자만 응답하세요."
    )
    
    wishlist_str = ", ".join(internal_wishlist) if internal_wishlist else "없음"

    user_prompt = (
        "다음은 평가 자료입니다.\n\n"
        f"--- 1. 고객의 공개 의뢰서 (분위기 점수 40% 반영) ---\n"
        f"\"{request_text}\"\n\n"
        
        f"--- 2. 고객의 비밀 위시리스트 (사실 점수 60% 반영) ---\n"
        f"[{wishlist_str}]\n\n"
        
        f"--- 3. 실제 디자인 결과 (묘사) ---\n"
        f"\"{design_description}\"\n\n"
        
        "--- 평가 가이드라인 ---\n"
        "1. [사실(60%)] '디자인 결과(3)'에 '비밀 위시리스트(2)'의 가구가 포함되어 있습니까? (가장 중요)\n"
        "2. [분위기(40%)] '디자인 결과(3)'가 '공개 의뢰서(1)'의 모호한 분위기(예: 아늑함, 모던함)를 만족시킵니까?\n"
        "3. [감점] '디자인 결과(3)' 묘사 중 '빽빽하게', '복잡해' 등의 부정적 표현이 있다면 감점하세요.\n\n"
        "이 모든 것을 고려하여 0.0~5.0 사이의 최종 점수(숫자)만 반환하세요:"
    )
    
    try:
        raw_score = model_manager.get_chat_response(system_prompt, user_prompt)
        # LLM이 반환한 텍스트에서 숫자만 추출 (예: "4.5점입니다" -> 4.5)
        score_match = re.search(r"(\d\.\d)", raw_score)
        if score_match:
            return float(score_match.group(1))
        else:
            # LLM이 이상한 답을 줬을 때 Fallback
            return float(raw_score.strip())
    except Exception as e:
        print(f"🚨 AI 평가자 점수 변환 실패: {e}")
        return 0.0

# --- 3. 평가 실행 (NEW: ModelManager를 인자로 받음) ---
def evaluate_design(model_manager, request_text: str, internal_wishlist: list, placed_furniture: list, room_width: int, room_height: int):
    """
    (수정) LLM-as-Judge 방식으로 전체 평가 프로세스를 실행합니다.
    
    Args:
        model_manager (ModelManager): Ollama 통신 객체
        request_embedding (list): (더 이상 사용되지 않지만, 호환성을 위해 남겨둘 수 있음)
        request_text (str): (신규) A - 공개 의뢰서
        internal_wishlist (list): (신규) Secret - 비밀 위시리스트
        placed_furniture (list): B - 배치된 가구
    """
    print("\n--- [ 고객 평가 (LLM-Judge) ] ---")
    
    # 1. 현재 디자인(B)을 자연어로 변환
    # (⭐️ 수정 ⭐️): model_manager를 describe_design에 전달
    design_desc = describe_design(
        model_manager, # <-- (신규) LLM 호출을 위해 전달
        placed_furniture, 
        room_width, 
        room_height
    )
    
    # 2. LLM-Judge 호출
    base_score = get_llm_judge_score(
        model_manager,
        request_text,      # (A) 공개 의뢰서
        internal_wishlist, # (Secret) 비밀 위시리스트
        design_desc        # (B) 실제 디자인
    )

    # --- 3. 위시리스트 페널티 계산 ---
    penalty = 0.0
    missing_items = []

    # 현재 배치된 모든 가구의 이름 (중복 제거)
    placed_names = set([f['item']['name'] for f in placed_furniture])
    
    for item in internal_wishlist:
        # 위시리스트의 아이템(예: "소파")이
        # 배치된 가구 이름(예: "작은 소파", "큰 소파")에 포함되는지 확인
        if item not in placed_names:
            print(f"   [페널티] 요구 가구 '{item}' 누락.")
            missing_items.append(item)
            penalty += 0.5
            
    # 4. 최종 점수 계산
    final_score = max(0.0, base_score - penalty) # 0점 미만 방지
    
    result = {
        "score": final_score,
        "description": design_desc
    }
    
    print(f"점수: {final_score:.1f}")
    return result