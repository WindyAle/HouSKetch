import pygame
import sys

import evaluation
import client
from model import ModelManager

# 가구 리스트
from furintures import FURNITURE_LIST

# --- 상수 정의 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 32  # 각 격자 칸의 픽셀 크기
ROOM_WIDTH_GRID = 15  # 방의 격자 가로 크기
ROOM_HEIGHT_GRID = 10 # 방의 격자 세로 크기

# UI 영역을 위한 여백
UI_MARGIN = 200 
GAME_AREA_WIDTH = ROOM_WIDTH_GRID * GRID_SIZE

# 폰트 설정
FONT_PATH = "font/NanumGothic-Regular.ttf"

# --- pygame 초기화 ---
pygame.init()
screen = pygame.display.set_mode((GAME_AREA_WIDTH + UI_MARGIN, ROOM_HEIGHT_GRID * GRID_SIZE))
pygame.display.set_caption("Welcome To My")

font_L = pygame.font.Font(FONT_PATH, 18) # 큰
font_M = pygame.font.Font(FONT_PATH, 15) # 중간
font_S = pygame.font.Font(FONT_PATH, 12) # 작은

# --- ModelManager 및 평가 변수 초기화 ---
model_manager = None
current_request_text = ""  # <-- 2. 동적으로 채워질 예정
request_embedding = []
# {"score": ..., "description": ..., "feedback": ...}
evaluation_result = None

try:
    model_manager = ModelManager()
    if not model_manager.is_ready:
        print("모델이 준비되지 않았습니다")
        running = False
    else:
        # 3. 하드코딩된 의뢰서 대신, LLM으로 동적 생성
        current_request_text = client.generate_request(model_manager)
        
        print(f"요구사항\n {current_request_text}")
        request_embedding = model_manager.get_embedding(current_request_text)
        print("[테스트] 요구사항 임베딩 완료")
        print(len(request_embedding), type(request_embedding))
        if not request_embedding:
            print("요구사항 임베딩 실패!")
            running = False
except Exception as e:
    print(f"🚨 모델 초기화 실패: {e}")
    running = False

# --- 헬퍼 함수 (겹치지 않음 / 회전) ---
def get_rotated_size(item, rotation):
    """가구의 현재 회전 상태에 따른 크기(w, h)를 반환합니다."""
    size = item['size']
    if rotation % 2 == 1: # 90도 또는 270도 회전 시
        return (size[1], size[0]) # 너비와 높이를 교환
    return size

def check_collision(new_item, new_pos, new_rot, placed_furniture):
    """새 가구가 방 경계나 다른 가구와 겹치는지 확인합니다."""
    new_size = get_rotated_size(new_item, new_rot)
    new_rect = pygame.Rect(new_pos[0], new_pos[1], new_size[0], new_size[1])

    # 1. 방 경계 확인
    if new_rect.right > ROOM_WIDTH_GRID or new_rect.bottom > ROOM_HEIGHT_GRID:
        return True # 방을 벗어남

    # 2. 다른 가구와 겹침 확인
    for f in placed_furniture:
        f_item = f['item']
        f_pos = f['grid_pos']
        f_rot = f['rotation']
        f_size = get_rotated_size(f_item, f_rot)
        f_rect = pygame.Rect(f_pos[0], f_pos[1], f_size[0], f_size[1])
        
        if new_rect.colliderect(f_rect):
            return True # 다른 가구와 겹침

    return False # 겹치지 않음

def draw_text_multiline(surface, text, pos, font, max_width, color):
    """UI 영역에 자동 줄바꿈 텍스트를 그립니다."""
    x, y = pos
    words = text.split(' ')
    line = ""
    for word in words:
        if font.size(line + " " + word)[0] < max_width:
            line += " " + word
        else:
            surface.blit(font.render(line.strip(), True, color), (x, y))
            y += font.get_linesize()
            line = word
    surface.blit(font.render(line.strip(), True, color), (x, y))
    return y + font.get_linesize()

# --- 변수 초기화 (게임 루프 전) ---
placed_furniture = [] # ({"name": "sofa", "grid_pos": (x, y), "rotation": 0}, ...)
selected_furniture_index = 0 # 기본으로 0번(sofa) 선택
selected_furniture_rotation = 0 # 0: 기본, 1: 90도
ui_buttons = []

# --- 게임 루프 ---
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    # 마우스 위치를 그리드 좌표로 변환
    mouse_grid_x = mouse_pos[0] // GRID_SIZE
    mouse_grid_y = mouse_pos[1] // GRID_SIZE

    # 현재 선택된 가구 정보
    current_item = FURNITURE_LIST[selected_furniture_index]

    # 현재 마우스 위치에 배치 가능한지 확인 (고스트 색상 변경용)
    is_placeable = not check_collision(
        current_item, 
        (mouse_grid_x, mouse_grid_y), 
        selected_furniture_rotation, 
        placed_furniture
    ) and mouse_pos[0] < GAME_AREA_WIDTH

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        
        # --- 이벤트 처리 ---
        # 키다운 이벤트
        if event.type == pygame.KEYDOWN:
            # UI 클릭으로 대체
            # if event.key == pygame.K_1: # 1번: 소파
            #     selected_furniture_index = 0
            # if event.key == pygame.K_2: # 2번: 테이블
            #     selected_furniture_index = 1
            # if event.key == pygame.K_3: # 3번: 침대
            #     selected_furniture_index = 2

            # 'R' 키로 회전
            if event.key == pygame.K_r:
                selected_furniture_rotation = (selected_furniture_rotation + 1) % 2 # 0, 1 (0도, 90도)
            
            # 'E' 키로 평가 진행
            if event.key == pygame.K_e:
                if model_manager and request_embedding:
                    # 점수 계산 (evaluation.py 호출)
                    eval_data = evaluation.evaluate_design(
                        model_manager, 
                        request_embedding, 
                        placed_furniture
                    )
                    
                    # 상세 피드백 생성 (client.py 호출)
                    feedback_text = client.generate_feedback(
                        model_manager,
                        current_request_text,
                        eval_data['description'],
                        eval_data['score']
                    )
                    
                    # 결과 통합
                    evaluation_result = {
                        "score": eval_data['score'],
                        "description": eval_data['description'],
                        "feedback": feedback_text
                    }
                
        
        # 클릭 이벤트
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭: 배치
                # --- UI 클릭 ---
                if mouse_pos[0] > GAME_AREA_WIDTH:
                    for button in ui_buttons:
                        if button["rect"].collidepoint(mouse_pos):
                            selected_furniture_index = button["index"]
                            selected_furniture_rotation = 0 # 새 가구 선택 시 회전 초기화
                            break
                # --- 겹치지 않게 배치 ---
                else:
                    if is_placeable:
                        placed_furniture.append({
                            "item": current_item,
                            "grid_pos": (mouse_grid_x, mouse_grid_y),
                            "rotation": selected_furniture_rotation # 3. 회전값 저장
                        })
            
            # 우클릭: 가구 제거 (클릭한 위치)
            if event.button == 3:
                if mouse_pos[0] < GAME_AREA_WIDTH:
                    # 클릭된 가구를 찾기 위해 리스트를 역순으로 순회
                    for i in range(len(placed_furniture) - 1, -1, -1):
                        f = placed_furniture[i]
                        f_size = get_rotated_size(f['item'], f['rotation'])
                        f_rect = pygame.Rect(
                            f['grid_pos'][0] * GRID_SIZE, 
                            f['grid_pos'][1] * GRID_SIZE, 
                            f_size[0] * GRID_SIZE, 
                            f_size[1] * GRID_SIZE
                        )
                        
                        if f_rect.collidepoint(mouse_pos):
                            placed_furniture.pop(i) # 가구 제거
                            break # 하나만 제거

    # --- 그리기 ---
    # 1. 스크린 채우기
    screen.fill((255, 255, 255))

    # 2. 배치된 가구 그리기 (3. 회전 적용)
    for furniture in placed_furniture:
        item = furniture["item"]
        pos_x, pos_y = furniture["grid_pos"]
        rotation = furniture["rotation"]
        size_rotated = get_rotated_size(item, rotation) # 회전된 크기
        color = item["color"]
        
        pygame.draw.rect(screen, color, 
                         (pos_x * GRID_SIZE, pos_y * GRID_SIZE, 
                          size_rotated[0] * GRID_SIZE, size_rotated[1] * GRID_SIZE))

    # 3. 현재 선택된 가구 (고스트) 그리기 (2. 겹침 / 3. 회전 적용)
    if mouse_pos[0] < GAME_AREA_WIDTH: # 게임 영역 안에서만
        current_size_rotated = get_rotated_size(current_item, selected_furniture_rotation)
        color = current_item["color"]
        
        # 2. 겹치거나 밖에 나가면 빨간색, 아니면 반투명
        ghost_color = (*color, 128) if is_placeable else (255, 0, 0, 128)
        
        ghost_surface = pygame.Surface((current_size_rotated[0] * GRID_SIZE, current_size_rotated[1] * GRID_SIZE), pygame.SRCALPHA)
        ghost_surface.fill(ghost_color)
        screen.blit(ghost_surface, (mouse_grid_x * GRID_SIZE, mouse_grid_y * GRID_SIZE))

    # 4. UI 영역 그리기
    pygame.draw.rect(screen, (245, 245, 245), (GAME_AREA_WIDTH, 0, UI_MARGIN, SCREEN_HEIGHT))   
    
    # 4.1 UI 가구 리스트 (4. UI 클릭)
    ui_buttons.clear() # 매 프레임 버튼 리스트 초기화
    ui_y_offset = 10
    
    # 도움말
    screen.blit(font_S.render("R: 회전, L-Click: 배치", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 30
    screen.blit(font_S.render("R-Click: 제거, E: 평가", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 40

    for i, item in enumerate(FURNITURE_LIST):
        button_rect = pygame.Rect(GAME_AREA_WIDTH + 10, ui_y_offset, UI_MARGIN - 20, 40)
        ui_buttons.append({"index": i, "rect": button_rect})
        
        # 선택된 아이템은 녹색으로 하이라이트
        button_color = (150, 255, 150) if i == selected_furniture_index else (220, 220, 220)
        pygame.draw.rect(screen, button_color, button_rect, border_radius=5)
        
        # 가구 이름
        screen.blit(font_M.render(item['name'], True, (0,0,0)), (GAME_AREA_WIDTH + 20, ui_y_offset + 10))
        ui_y_offset += 50
    
    # 4.2 고객 의뢰서 표시 (1. 한글 폰트)
    ui_y_offset += 20 # 구분선
    pygame.draw.line(screen, (200,200,200), (GAME_AREA_WIDTH + 5, ui_y_offset), (SCREEN_WIDTH - 5, ui_y_offset), 1)
    ui_y_offset += 10
    
    screen.blit(font_L.render("고객 의뢰서:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset = draw_text_multiline(
        screen, 
        current_request_text, 
        (GAME_AREA_WIDTH + 10, ui_y_offset + 30), 
        font_M, 
        UI_MARGIN - 20, 
        (50,50,50)
    )

# 4.2 고객 의뢰서 표시 (1. 한글 폰트)
    ui_y_offset += 20 # 구분선
    pygame.draw.line(screen, (200,200,200), (GAME_AREA_WIDTH + 5, ui_y_offset), (SCREEN_WIDTH - 5, ui_y_offset), 1)
    ui_y_offset += 10
    
    screen.blit(font_L.render("고객 의뢰서:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset = draw_text_multiline(
        screen, 
        current_request_text, 
        (GAME_AREA_WIDTH + 10, ui_y_offset + 30), 
        font_M, 
        UI_MARGIN - 20, 
        (50,50,50)
    )
    
    # 4.3 평가 결과 표시 (1. 한글 폰트)
    if evaluation_result:
        ui_y_offset += 20
        # 점수 표시
        score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
        screen.blit(font_L.render(score_str, True, (0, 100, 0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
        ui_y_offset += 35

        # 피드백 표시
        screen.blit(font_L.render("고객 피드백:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
        ui_y_offset = draw_text_multiline(
            screen,
            evaluation_result['feedback'],
            (GAME_AREA_WIDTH + 10, ui_y_offset + 30),
            font_M,
            UI_MARGIN - 20,
            (50,50,50)
        )
        
    # --- 업데이트 ---
    pygame.display.flip()

pygame.quit()