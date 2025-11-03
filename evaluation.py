# evaluation.py (Refactored)

import numpy as np

# --- 1. 디자인 설명서 생성 (로직 동일) ---

def describe_design(placed_furniture: list) -> str:
    """
    Pygame의 가구 배치 리스트를 자연어 설명으로 변환합니다.
    """
    if not placed_furniture:
        return "방에 아무것도 없습니다!"

    item_counts = {}
    for furniture in placed_furniture:
        name = furniture['item']['name']
        item_counts[name] = item_counts.get(name, 0) + 1
        
    description = "이 집은... "
    items = [f"{count} {name}" for name, count in item_counts.items()]
    description += ", ".join(items)
    description += "."
    
    print("[완성된 디자인]")
    print(description)

    return description

# --- 2. 유사도 계산 (로직 동일) ---

def calculate_similarity_score(vec_a: list[float], vec_b: list[float]) -> float:
    """
    두 벡터(A:요구사항, B:디자인)의 코사인 유사도를 계산하여 0~5점 척도로 반환합니다.
    """
    if not vec_a or not vec_b:
        return 0.0

    vec_a_np = np.array(vec_a)
    vec_b_np = np.array(vec_b)
    
    # 0으로 나누기 방지
    norm_a = np.linalg.norm(vec_a_np)
    norm_b = np.linalg.norm(vec_b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    cosine_similarity = np.dot(vec_a_np, vec_b_np) / (norm_a * norm_b)
    
    score = (cosine_similarity + 1) / 2 * 5.0
    return score

# --- 3. 평가 실행 (NEW: ModelManager를 인자로 받음) ---

def evaluate_design(model_manager, request_embedding: list, placed_furniture: list):
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
    design_desc = describe_design(placed_furniture)
    
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