import pygame
import sys

import evaluation
import client
from model import ModelManager

# furintures 모듈을 임포트 (아직 리스트를 가져오지 않음)
import furintures 

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

# --- pygame 초기화 (가장 먼저 실행) ---
pygame.init()

# --- 화면 및 폰트 로드 ---
screen = pygame.display.set_mode((GAME_AREA_WIDTH + UI_MARGIN, ROOM_HEIGHT_GRID * GRID_SIZE))
pygame.display.set_caption("Welcome To My")

try:
    font_L = pygame.font.Font(FONT_PATH, 18) # 큰
    font_M = pygame.font.Font(FONT_PATH, 15) # 중간
    font_S = pygame.font.Font(FONT_PATH, 12) # 작은
except FileNotFoundError:
    print(f"폰트 '{FONT_PATH}' 로드 실패. 기본 폰트로 실행합니다.")
    font_L = pygame.font.Font(None, 24)
    font_M = pygame.font.Font(None, 20)
    font_S = pygame.font.Font(None, 16)
except pygame.error as e:
    print(f"폰트 로딩 오류: {e}")
    pygame.quit()
    sys.exit()

# --- 가구 리스트 로드 (pygame.init() 이후) ---
FURNITURE_LIST = furintures.load_furniture_data(GRID_SIZE)
if not FURNITURE_LIST:
    print("가구 리스트 로드 실패. assets 폴더를 확인하세요.")
    pygame.quit()
    sys.exit()


# --- ModelManager 및 평가 변수 초기화 ---
model_manager = None
current_request_text = ""
request_embedding = []
evaluation_result = None
running = True

# (하드코딩 테스트용)
model_manager = None
current_request_text = client.generate_request(None) # 하드코딩된 의뢰서
request_embedding = [0.1] * 128 # 임시 값

# (Ollama 활성화 시 코드 - 현재 주석 처리)
# try:
#     model_manager = ModelManager()
#     if not model_manager.is_ready:
#         print("모델이 준비되지 않았습니다")
#         current_request_text = "테스트: 소파 1개와 테이블 1개를 놓으세요."
#         request_embedding = [0.1] * 128
#     else:
#         current_request_text = client.generate_request(model_manager)
#         print(f"요구사항\n {current_request_text}")
#         request_embedding = model_manager.get_embedding(current_request_text)
#         if not request_embedding:
#             print("요구사항 임베딩 실패!")
#             running = False
# except Exception as e:
#     print(f"🚨 모델 초기화 실패: {e}")
#     current_request_text = "테스트 (모델 실패): 소파 1개를 놓으세요."
#     request_embedding = [0.1] * 128


# --- 헬퍼 함수 (겹치지 않음 / 회전) ---
def get_rotated_size(item, rotation):
    """가구의 현재 회전 상태에 따른 크기(w, h)를 반환합니다."""
    size = item['size']
    if rotation % 2 == 1: # 90도
        return (size[1], size[0]) # 너비와 높이를 교환
    return size

def get_rotated_image(item, rotation):
    """가구의 원본 이미지를 회전시켜 반환합니다."""
    if rotation == 0:
        return item["image"]
    else:
        # 90도 회전 (pygame.transform.rotate는 반시계 방향)
        return pygame.transform.rotate(item["image"], 90)

def check_collision(new_item, new_pos, new_rot, placed_furniture):
    """새 가구가 방 경계나 다른 가구와 겹치는지 확인합니다."""
    new_size = get_rotated_size(new_item, new_rot)
    new_rect = pygame.Rect(new_pos[0], new_pos[1], new_size[0], new_size[1])

    # 1. 방 경계 확인
    if new_rect.left < 0 or new_rect.top < 0 or \
       new_rect.right > ROOM_WIDTH_GRID or new_rect.bottom > ROOM_HEIGHT_GRID:
        return True # 방을 벗어남

    # 2. 다른 가구와 겹침 확인
    for f in placed_furniture:
        f_size = get_rotated_size(f['item'], f['rotation'])
        f_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size[0], f_size[1])
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
placed_furniture = []
selected_furniture_index = 0
selected_furniture_rotation = 0 # 0: 기본, 1: 90도
ui_buttons = []
clock = pygame.time.Clock() # FPS를 위한 시계

# --- 게임 루프 ---
while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_grid_x = mouse_pos[0] // GRID_SIZE
    mouse_grid_y = mouse_pos[1] // GRID_SIZE

    current_item = FURNITURE_LIST[selected_furniture_index]

    is_placeable = not check_collision(
        current_item, 
        (mouse_grid_x, mouse_grid_y), 
        selected_furniture_rotation, 
        placed_furniture
    ) and mouse_pos[0] < GAME_AREA_WIDTH

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # --- 이벤트 처리 ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: # 'R' 키로 회전
                selected_furniture_rotation = (selected_furniture_rotation + 1) % 2
            
            if event.key == pygame.K_e: # 'E' 키로 평가
                # (하드코딩된 모듈 호출)
                eval_data = evaluation.evaluate_design(
                    model_manager, 
                    request_embedding, 
                    placed_furniture
                )
                
                feedback_text = client.generate_feedback(
                    model_manager,
                    current_request_text,
                    eval_data['description'],
                    eval_data['score']
                )
                
                evaluation_result = {
                    "score": eval_data['score'],
                    "description": eval_data['description'],
                    "feedback": feedback_text
                }
        
        # 클릭 이벤트
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭: 배치
                if mouse_pos[0] > GAME_AREA_WIDTH: # UI 클릭
                    for button in ui_buttons:
                        if button["rect"].collidepoint(mouse_pos):
                            selected_furniture_index = button["index"]
                            selected_furniture_rotation = 0
                            break
                else: # 겹치지 않게 배치
                    if is_placeable:
                        placed_furniture.append({
                            "item": current_item,
                            "grid_pos": (mouse_grid_x, mouse_grid_y),
                            "rotation": selected_furniture_rotation
                        })
            
            if event.button == 3: # 우클릭: 가구 제거
                if mouse_pos[0] < GAME_AREA_WIDTH:
                    # 클릭된 가구를 찾기 위해 리스트를 역순으로 순회
                    for i in range(len(placed_furniture) - 1, -1, -1):
                        f = placed_furniture[i]
                        f_size = get_rotated_size(f['item'], f['rotation'])
                        # 픽셀이 아닌 그리드 좌표로 Rect 생성
                        f_grid_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size[0], f_size[1])
                        
                        # 마우스 그리드 좌표와 충돌하는지 확인
                        if f_grid_rect.collidepoint(mouse_grid_x, mouse_grid_y):
                            placed_furniture.pop(i)
                            break 

    # --- 그리기 ---
    # 1. 스크린 채우기
    screen.fill((255, 255, 255))
    
    # 1.1 그리드 그리기
    for x in range(ROOM_WIDTH_GRID + 1):
        pygame.draw.line(screen, (240, 240, 240), (x * GRID_SIZE, 0), (x * GRID_SIZE, ROOM_HEIGHT_GRID * GRID_SIZE))
    for y in range(ROOM_HEIGHT_GRID + 1):
        pygame.draw.line(screen, (240, 240, 240), (0, y * GRID_SIZE), (GAME_AREA_WIDTH, y * GRID_SIZE))

    # 2. 배치된 가구 그리기 (수정: 이미지 사용)
    for furniture in placed_furniture:
        item = furniture["item"]
        pos_x, pos_y = furniture["grid_pos"]
        rotation = furniture["rotation"]
        
        # 회전된 이미지 가져오기
        image_to_draw = get_rotated_image(item, rotation)
        
        # 이미지 blit
        screen.blit(image_to_draw, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))

    # 3. 현재 선택된 가구 (고스트) 그리기 (수정: 이미지 틴트 사용)
    if mouse_pos[0] < GAME_AREA_WIDTH: # 게임 영역 안에서만
        
        # 회전된 이미지 가져오기
        image_to_draw = get_rotated_image(current_item, selected_furniture_rotation)
        
        # 틴트(tint) 색상 결정
        tint_color = (0, 255, 0, 100) if is_placeable else (255, 0, 0, 100) # (R, G, B, Alpha)
        
        # 틴트를 적용할 새 Surface 생성
        ghost_image = image_to_draw.copy()
        tint_surface = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
        tint_surface.fill(tint_color)
        
        # 틴트 적용 (BLEND_RGBA_MULT: 이미지 색상과 틴트 색상을 곱함)
        ghost_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        screen.blit(ghost_image, (mouse_grid_x * GRID_SIZE, mouse_grid_y * GRID_SIZE))


    # 4. UI 영역 그리기
    pygame.draw.rect(screen, (245, 245, 245), (GAME_AREA_WIDTH, 0, UI_MARGIN, SCREEN_HEIGHT))   
    
    # 4.1 UI 가구 리스트
    ui_buttons.clear() 
    ui_y_offset = 10
    
    screen.blit(font_S.render("R: 회전, L-Click: 배치", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 30
    screen.blit(font_S.render("R-Click: 제거, E: 평가", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 40

    for i, item in enumerate(FURNITURE_LIST):
        button_rect = pygame.Rect(GAME_AREA_WIDTH + 10, ui_y_offset, UI_MARGIN - 20, 40)
        ui_buttons.append({"index": i, "rect": button_rect})
        
        button_color = (150, 255, 150) if i == selected_furniture_index else (220, 220, 220)
        pygame.draw.rect(screen, button_color, button_rect, border_radius=5)
        
        screen.blit(font_M.render(item['name'], True, (0,0,0)), (GAME_AREA_WIDTH + 20, ui_y_offset + 10))
        ui_y_offset += 50
    
    # 4.2 고객 의뢰서 표시 (중복 제거)
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
    
    # 4.3 평가 결과 표시
    if evaluation_result:
        ui_y_offset += 20
        score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
        screen.blit(font_L.render(score_str, True, (0, 100, 0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
        ui_y_offset += 35

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
    clock.tick(60) # 60 FPS 제한

pygame.quit()
sys.exit()

