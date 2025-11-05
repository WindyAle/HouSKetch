# evaluation.py (Refactored)
import numpy as np

# --- 1. 디자인 설명서 생성 (로직 동일) ---

def describe_design(placed_furniture: list, room_width: int, room_height: int) -> str:
    """
    가구 배치 리스트와 방 크기를 기반으로,
    LLM이 이해할 수 있는 풍부한 자연어 묘사를 생성합니다.
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
        # furnitures.py에 'base_size'가 정의되어 있다고 가정
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
    
    if not center_items and not wall_items and not entrance_items:
        description += "- 모든 가구가 한 곳에 뭉쳐있습니다.\n" # (위 로직으로는 이 분기 Trivial, 하지만 예시)

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
            
    print("[상세 디자인 묘사 (모델에게 넘겨주는 프롬프트)]")
    print(description)
    return description

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

# --- 3. 평가 실행 (NEW: ModelManager를 인자로 받음) ---

def evaluate_design(model_manager, request_embedding: list, placed_furniture: list, room_width: int, room_height: int):
    """
    전체 평가 프로세스를 실행하고 점수와 설명을 반환합니다.
    
    Args:
        model_manager (ModelManager): Ollama 통신을 위한 객체
        request_embedding (list): 미리 계산된 고객 요구사항 벡터 (A)
        placed_furniture (list): Pygame에서 전달된 가구 목록
        
    Returns:
        dict: 점수와 디자인 설명을 포함한 결과
    """
    print("\n--- [ 고객 평가 ] ---")
    
    # 1. 현재 디자인(B)을 자연어로 변환
    design_desc = describe_design(placed_furniture, room_width, room_height)
    
    # 2. 디자인(B)을 EEVE 벡터로 변환 (ModelManager 사용)
    design_embedding = model_manager.get_embedding(design_desc)
    
    if not design_embedding:
        print("🚨 임베딩 실패 (design_embedding)")
        return {"score": 0.0, "description": "Evaluation failed."}

    # 3. 점수 계산
    score = calculate_similarity_score(request_embedding, design_embedding)
    
    result = {
        "score": score,
        "description": design_desc
    }
    
    print(f"제 점수는요... {score:.1f} / 5.0")
    return result