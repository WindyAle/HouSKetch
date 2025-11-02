import pygame

from furintures import FURNITURE_LIST
import evaluation
from model import ModelManager

# --- 상수 정의 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 32  # 각 격자 칸의 픽셀 크기
ROOM_WIDTH_GRID = 15  # 방의 격자 가로 크기
ROOM_HEIGHT_GRID = 10 # 방의 격자 세로 크기

# UI 영역을 위한 여백
UI_MARGIN = 200 
GAME_AREA_WIDTH = ROOM_WIDTH_GRID * GRID_SIZE

# --- pygame 초기화 ---
pygame.init()
screen = pygame.display.set_mode((GAME_AREA_WIDTH + UI_MARGIN, ROOM_HEIGHT_GRID * GRID_SIZE))
pygame.display.set_caption("Step 1: 2D 인테리어 샌드박스")

# --- ModelManager 및 평가 변수 초기화 ---
model_manager = None
current_request_text = "소파와 테이블이 있는 아늑한 거실이면 좋겠어요."
request_embedding = []
evaluation_result = None

try:
    model_manager = ModelManager() # NEW: ModelManager 인스턴스 생성
    if not model_manager.is_ready:
        print("ModelManager is not ready. Exiting.")
        running = False
    else:
        # 고객 의뢰서(A)를 벡터로 변환 (ModelManager 사용)
        print(f"고객 의뢰서: {current_request_text}")
        request_embedding = model_manager.get_embedding(current_request_text)
        if not request_embedding:
            print("🚨 의뢰서 임베딩 생성 실패")
            running = False
except Exception as e:
    print(f"Failed to initialize ModelManager: {e}")
    running = False

# --- 변수 초기화 (게임 루프 전) ---
placed_furniture = [] # ({"name": "sofa", "grid_pos": (x, y), "rotation": 0}, ...)
selected_furniture_index = 0 # 기본으로 0번(sofa) 선택
font = pygame.font.SysFont(None, 24)

# --- 게임 루프 ---
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    # 마우스 위치를 그리드 좌표로 변환
    mouse_grid_x = mouse_pos[0] // GRID_SIZE
    mouse_grid_y = mouse_pos[1] // GRID_SIZE

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # --- 이벤트 처리 ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1: # 1번: 소파
                selected_furniture_index = 0
            if event.key == pygame.K_2: # 2번: 테이블
                selected_furniture_index = 1
            if event.key == pygame.K_3: # 3번: 침대
                selected_furniture_index = 2
            if event.key == pygame.K_e:
                if model_manager and request_embedding:
                    # model_manager와 request_embedding을 인자로 전달
                    evaluation_result = evaluation.evaluate_design(
                        model_manager, 
                        request_embedding, 
                        placed_furniture
                    )
                else:
                    print("Evaluation system is not ready.")
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭: 배치
                # 게임 영역 안에서만 배치
                if mouse_grid_x < ROOM_WIDTH_GRID and mouse_grid_y < ROOM_HEIGHT_GRID:
                    current_item = FURNITURE_LIST[selected_furniture_index]
                    placed_furniture.append({
                        "item": current_item,
                        "grid_pos": (mouse_grid_x, mouse_grid_y)
                    })
            if event.button == 3: # 우클릭: 가장 마지막에 놓은 가구 제거 (임시)
                if placed_furniture:
                    placed_furniture.pop()

    # --- 그리기 ---
    screen.fill((255, 255, 255)) 

    # 1. 방 그리드 그리기 (이전과 동일)
    # ... (생략) ...

    # 2. 배치된 가구 그리기
    for furniture in placed_furniture:
        item = furniture["item"]
        pos_x, pos_y = furniture["grid_pos"]
        size_x, size_y = item["size"]
        color = item["color"]
        
        pygame.draw.rect(screen, color, 
                         (pos_x * GRID_SIZE, pos_y * GRID_SIZE, 
                          size_x * GRID_SIZE, size_y * GRID_SIZE))

    # 3. 현재 선택된 가구 (고스트) 그리기
    current_item = FURNITURE_LIST[selected_furniture_index]
    size_x, size_y = current_item["size"]
    color = current_item["color"]
    
    # 반투명 효과 (Surface 사용)
    ghost_surface = pygame.Surface((size_x * GRID_SIZE, size_y * GRID_SIZE), pygame.SRCALPHA)
    ghost_surface.fill((*color, 128)) # 128 = 반투명
    screen.blit(ghost_surface, (mouse_grid_x * GRID_SIZE, mouse_grid_y * GRID_SIZE))

    # 4. UI 영역 그리기
    pygame.draw.rect(screen, (230, 230, 230), (GAME_AREA_WIDTH, 0, UI_MARGIN, SCREEN_HEIGHT))
    
    # 4.1 UI 텍스트 (기존)
    # ... (생략) ...
    info_text_3 = font.render("Press 'E' to Evaluate", True, (0, 0, 150))
    screen.blit(info_text_3, (GAME_AREA_WIDTH + 10, 100))

    # 4.2 고객 의뢰서 표시
    req_title = font.render("Client Request:", True, (0,0,0))
    screen.blit(req_title, (GAME_AREA_WIDTH + 10, 150))
    # (텍스트 자동 줄바꿈 필요하지만, 지금은 간단히)
    req_text = font.render(current_request_text[:20] + "...", True, (50,50,50))
    screen.blit(req_text, (GAME_AREA_WIDTH + 10, 180))
    
    # 4.3 평가 결과 표시
    if evaluation_result:
        score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
        score_render = font.render(score_str, True, (0, 100, 0))
        screen.blit(score_render, (GAME_AREA_WIDTH + 10, 220))

    # --- 업데이트 ---
    pygame.display.flip()

pygame.quit()