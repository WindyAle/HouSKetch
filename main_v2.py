import pygame
import sys
import math

import evaluation
import client
from model import ModelManager

# furintures 모듈을 임포트 (리스트는 아래에서 가져옴)
import furnitures 

# ========= 상수 정의 =========
GRID_SIZE = 64  # 각 격자 크기
ROOM_WIDTH_GRID = 10  # 가로 칸 수
ROOM_HEIGHT_GRID = 8 # 세로 칸 수

# --- 레이아웃 상수 ---
GAME_AREA_WIDTH = ROOM_WIDTH_GRID * GRID_SIZE    # 600
GAME_AREA_HEIGHT = ROOM_HEIGHT_GRID * GRID_SIZE  # 480

RIGHT_UI_MARGIN = 300  # 오른쪽 UI 패널 너비
BOTTOM_UI_MARGIN = 170 # 하단 UI 패널 높이 (새로운 UI_ITEM_HEIGHT * 2 + 여백 30)

SCREEN_WIDTH = GAME_AREA_WIDTH + RIGHT_UI_MARGIN   # 900
SCREEN_HEIGHT = GAME_AREA_HEIGHT + BOTTOM_UI_MARGIN # 650

# 폰트 설정
FONT_PATH = "font/NanumGothic-Regular.ttf"

# 배경이미지 경로
BACKGROUND_IMAGE_PATH = "assets/wood_floor.png" 

# ========= pygame 초기화 =========
pygame.init()

# --- 화면 및 폰트 로드 ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Welcome To My - v0.3 (New Layout)")

font_L = pygame.font.Font(FONT_PATH, 22) # 큰
font_M = pygame.font.Font(FONT_PATH, 18) # 중간
font_S = pygame.font.Font(FONT_PATH, 14) # 작은

# --- 가구 리스트 로드 ---
FURNITURE_LIST = furnitures.load_furniture_data(GRID_SIZE)
if not FURNITURE_LIST:
    print("가구 리스트 로드 실패. assets 폴더를 확인하세요.")
    pygame.quit()
    sys.exit()

# --- 배경 이미지 로드 ---
global_background_image = None
background_image = pygame.image.load(BACKGROUND_IMAGE_PATH).convert()
# 게임 영역 크기에 맞게 스케일
global_background_image = pygame.transform.scale(background_image, (GAME_AREA_WIDTH, GAME_AREA_HEIGHT))
print(f"'{BACKGROUND_IMAGE_PATH}' 배경 이미지 로드 성공.")

# --- ModelManager 및 평가 변수 초기화 ---
model_manager = None
current_request_text = ""
request_embedding = []
evaluation_result = None
running = True

try:
    model_manager = ModelManager()
    print("모델 준비 완료. 라이브 모드로 실행합니다.")
    current_request_text = client.generate_request(model_manager)
    print(f"새로운 요구사항: {current_request_text}")
    request_embedding = model_manager.get_embedding(current_request_text)
    if not request_embedding:
        print("요구사항 임베딩 실패! 테스트 모드로 전환합니다.")
        current_request_text = client.generate_request(None)
        request_embedding = [0.1] * 128
except Exception as e:
    print(f"🚨 모델 초기화 실패: {e}")
    print("Ollama 서버가 실행 중인지 확인하세요. 테스트 모드로 실행합니다.")

# --- 헬퍼 함수 (회전 + 겹치지 않음) ---
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
        original_image = item["image"]
        rotated_image = pygame.transform.rotate(original_image, 90)
        rotated_size_grid = get_rotated_size(item, rotation)
        rotated_pixel_size = (rotated_size_grid[0] * GRID_SIZE, rotated_size_grid[1] * GRID_SIZE)
        return pygame.transform.scale(rotated_image, rotated_pixel_size)

def check_collision(new_item, new_pos, new_rot, placed_furniture):
    """(수정) 충돌 판정은 '바닥 격자'(높이 1)만 검사합니다."""
    new_size_visual = get_rotated_size(new_item, new_rot)
    new_rect = pygame.Rect(new_pos[0], new_pos[1], new_size_visual[0], 1) # 높이 1

    if new_rect.left < 0 or new_rect.top < 0 or \
       new_rect.right > ROOM_WIDTH_GRID or new_rect.bottom > ROOM_HEIGHT_GRID:
        return True 

    for f in placed_furniture:
        f_size_visual = get_rotated_size(f['item'], f['rotation'])
        f_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size_visual[0], 1) # 높이 1
        if new_rect.colliderect(f_rect):
            return True 

    return False 

# --- UI 텍스트 줄바꿈 ---
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

# ========= 변수 초기화 (게임 루프 전) =========
placed_furniture = []
selected_furniture_index = 0
selected_furniture_rotation = 0 # 0: 기본, 1: 90도
ui_buttons = []

# (수정) 하단 UI 스크롤 변수
ui_scroll_x = 0
UI_ITEM_WIDTH = 180 # 각 가구 목록 아이템의 너비
UI_ITEM_HEIGHT = 70 # 각 가구 목록 아이템의 높이

# (수정) UI 레이아웃 Rect 정의
game_area_rect = pygame.Rect(0, 0, GAME_AREA_WIDTH, GAME_AREA_HEIGHT)
right_ui_rect = pygame.Rect(GAME_AREA_WIDTH, 0, RIGHT_UI_MARGIN, GAME_AREA_HEIGHT)
bottom_ui_rect = pygame.Rect(0, GAME_AREA_HEIGHT, SCREEN_WIDTH, BOTTOM_UI_MARGIN)

clock = pygame.time.Clock() # FPS를 위한 시계

# ========= 게임 루프 =========
while running:
    mouse_pos = pygame.mouse.get_pos()
    
    # (수정) 마우스 좌표 변환 (게임 영역 기준)
    mouse_grid_x = mouse_pos[0] // GRID_SIZE
    mouse_grid_y = mouse_pos[1] // GRID_SIZE

    current_item = FURNITURE_LIST[selected_furniture_index]

    # (수정) is_placeable은 게임 영역 내에서만 계산
    is_placeable = False
    if game_area_rect.collidepoint(mouse_pos):
        is_placeable = not check_collision(
            current_item, 
            (mouse_grid_x, mouse_grid_y), 
            selected_furniture_rotation, 
            placed_furniture
        )

    # ========= 이벤트 처리 =========
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        
        # --- (수정) 하단 패널 횡방향 스크롤 ---
        if event.type == pygame.MOUSEWHEEL:
            # 마우스가 하단 UI 영역에 있을 때만 스크롤
            if bottom_ui_rect.collidepoint(mouse_pos):
                ui_scroll_x += event.y * 30 # (event.y가 횡방향 스크롤을 제어)
                
                # 스크롤 범위 제한
                total_list_width = math.ceil(len(FURNITURE_LIST) / 2) * UI_ITEM_WIDTH
                max_scroll = max(0, total_list_width - SCREEN_WIDTH)
                
                ui_scroll_x = max(min(ui_scroll_x, 0), -max_scroll)
        
        # --- 키다운 이벤트 ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: # 'R' 키로 회전
                selected_furniture_rotation = (selected_furniture_rotation + 1) % 2
            
            if event.key == pygame.K_e: # 'E' 키로 평가
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
        
        # 클릭 이벤트 (수정)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭
                # 1. 하단 UI(가구 목록) 클릭
                if bottom_ui_rect.collidepoint(mouse_pos):
                    for button in ui_buttons:
                        if button["rect_screen"].collidepoint(mouse_pos):
                            selected_furniture_index = button["index"]
                            selected_furniture_rotation = 0
                            break
                # 2. 게임 영역(배치) 클릭
                elif game_area_rect.collidepoint(mouse_pos):
                    if is_placeable:
                        placed_furniture.append({
                            "item": current_item,
                            "grid_pos": (mouse_grid_x, mouse_grid_y),
                            "rotation": selected_furniture_rotation
                        })
            
            if event.button == 3: # 우클릭: 가구 제거
                if game_area_rect.collidepoint(mouse_pos):
                    sorted_for_click = sorted(placed_furniture, key=lambda f: (f['grid_pos'][1], f['grid_pos'][0]), reverse=True)
                    
                    for f in sorted_for_click:
                        f_size_visual = get_rotated_size(f['item'], f['rotation'])
                        f_grid_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size_visual[0], 1) # 높이 1
                        
                        if f_grid_rect.collidepoint(mouse_grid_x, mouse_grid_y):
                            placed_furniture.remove(f)
                            break 

    # ========= 그리기 =========
    
    # 1. 스크린 채우기 (배경)
    screen.fill((255, 255, 255)) # 기본 흰색 배경
    
    # --- 1.1 오른쪽/하단 UI 배경 그리기 ---
    pygame.draw.rect(screen, (245, 245, 245), right_ui_rect)
    pygame.draw.rect(screen, (240, 240, 240), bottom_ui_rect) # 하단 배경색

    # --- 1.2 게임 영역 그리기 (배경/그리드) ---
    if global_background_image:
        screen.blit(global_background_image, (0, 0))
    else:
        pygame.draw.rect(screen, (255, 255, 255), game_area_rect) # 흰색

    for x in range(ROOM_WIDTH_GRID + 1):
        pygame.draw.line(screen, (210, 140, 180, 100), (x * GRID_SIZE, 0), (x * GRID_SIZE, GAME_AREA_HEIGHT))
    for y in range(ROOM_HEIGHT_GRID + 1):
        pygame.draw.line(screen, (210, 140, 180, 100), (0, y * GRID_SIZE), (GAME_AREA_WIDTH, y * GRID_SIZE))

    # --- 2. Z-Sorting 및 가구 그리기 (게임 영역) ---
    render_list = placed_furniture.copy()
    if game_area_rect.collidepoint(mouse_pos): # 게임 영역 안에서만
        render_list.append({
            "item": current_item,
            "grid_pos": (mouse_grid_x, mouse_grid_y),
            "rotation": selected_furniture_rotation,
            "is_ghost": True 
        })
        
    sorted_render_list = sorted(render_list, key=lambda f: (f['grid_pos'][1], f['grid_pos'][0]))

    for furniture in sorted_render_list:
        item = furniture["item"]
        pos_x, pos_y = furniture["grid_pos"]
        rotation = furniture["rotation"]
        
        image_to_draw = get_rotated_image(item, rotation)
        
        if furniture.get("is_ghost", False):
            tint_color = (0, 255, 0, 100) if is_placeable else (255, 0, 0, 100)
            ghost_image = image_to_draw.copy()
            tint_surface = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
            tint_surface.fill(tint_color)
            ghost_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(ghost_image, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))
        else:
            screen.blit(image_to_draw, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))

    # --- 3. 오른쪽 UI 그리기 ---
    # 3.1 도움말 패널
    ui_y_offset = 10 # 오른쪽 패널 상단 기준
    screen.blit(font_S.render("R: 회전, L-Click: 배치", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 25
    screen.blit(font_S.render("R-Click: 제거, E: 평가", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 30

    # 3.2 고객 의뢰서 표시
    ui_y_offset += 20 
    pygame.draw.line(screen, (200,200,200), (GAME_AREA_WIDTH + 5, ui_y_offset), (SCREEN_WIDTH - 5, ui_y_offset), 1)
    ui_y_offset += 10
    
    screen.blit(font_L.render("고객 요구사항:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset = draw_text_multiline(
        screen, 
        current_request_text, 
        (GAME_AREA_WIDTH + 10, ui_y_offset + 30), 
        font_M, 
        RIGHT_UI_MARGIN - 20, 
        (50,50,50)
    )
    
    # 3.3 평가 결과 표시
    if evaluation_result:
        ui_y_offset += 20
        score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
        screen.blit(font_L.render(score_str, True, (0, 100, 0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
        
        feedback_y = ui_y_offset + 40
        screen.blit(font_L.render("고객 피드백:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, feedback_y))
        draw_text_multiline(
            screen,
            evaluation_result['feedback'],
            (GAME_AREA_WIDTH + 10, feedback_y + 30),
            font_M,
            RIGHT_UI_MARGIN - 20,
            (50,50,50)
        )

    # --- 4. 하단 UI 그리기 (가구 목록) ---
    # 클리핑을 위한 SubSurface
    bottom_panel = screen.subsurface(bottom_ui_rect)
    
    ui_buttons.clear()
    
    for i, item in enumerate(FURNITURE_LIST):
        # 2줄 배치 로직
        row = i % 2
        col = i // 2
        
        # (수정) 버튼의 '논리적' X, Y 위치 (스크롤 적용 및 여백)
        item_x_pos = (col * UI_ITEM_WIDTH) + ui_scroll_x + 10 # 10px 좌측 여백
        item_y_pos = (row * UI_ITEM_HEIGHT) + 10 # 10px 상단 여백
        
        # (수정) 버튼 크기 (가로 145, 세로 60)
        button_rect = pygame.Rect(item_x_pos, item_y_pos, UI_ITEM_WIDTH - 10, UI_ITEM_HEIGHT - 10) # 10px, 10px 여백
        
        # 화면에 보이는 영역에만 버튼을 그림
        if item_x_pos + UI_ITEM_WIDTH > 0 and item_x_pos < SCREEN_WIDTH:
            
            # 실제 화면 좌표 기준 Rect (클릭 감지용)
            button_rect_screen = pygame.Rect(item_x_pos, item_y_pos + GAME_AREA_HEIGHT, UI_ITEM_WIDTH - 10, UI_ITEM_HEIGHT - 10)
            ui_buttons.append({"index": i, "rect_screen": button_rect_screen})
            
            # 선택된 아이템은 녹색으로 하이라이트
            button_color = (150, 255, 150) if i == selected_furniture_index else (220, 220, 220)
            pygame.draw.rect(bottom_panel, button_color, button_rect, border_radius=5)
            
            # 가구 썸네일 이미지
            try:
                # (수정) 썸네일 크기 (가로 50, 세로 50)
                thumb_h = 50
                thumb_w = 50
                thumb_img = pygame.transform.smoothscale(item["image"], (thumb_w, thumb_h))
                bottom_panel.blit(thumb_img, (item_x_pos + 10, item_y_pos + 5)) # (y + 5 상하중앙정렬)
            except Exception as e:
                print(f"썸네일 생성 오류: {e}")
            
            # (수정) 가구 이름 (썸네일 오른쪽으로 이동)
            name_x_pos = item_x_pos + 70 # 10(여백) + 50(썸네일) + 10(여백)
            bottom_panel.blit(font_M.render(item['name'], True, (0,0,0)), (name_x_pos + 20, item_y_pos + 20)) # (y + 20 상하중앙정렬)

    # --- 업데이트 ---
    pygame.display.flip()
    clock.tick(60) # 60 FPS 제한

pygame.quit()
sys.exit()

