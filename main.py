import pygame
import sys

import evaluation
import client
from model import ModelManager

# furintures 모듈을 임포트 (리스트는 pygame.init() 후에 로드해야 함)
import furnitures 

# ========= 상수 정의 =========
GRID_SIZE = 72  # 각 격자 크기
ROOM_WIDTH_GRID = 10  # 가로 칸 수
ROOM_HEIGHT_GRID = 8 # 세로 칸 수

# UI 영역을 위한 여백
UI_MARGIN = 300
GAME_AREA_WIDTH = ROOM_WIDTH_GRID * GRID_SIZE

SCREEN_WIDTH = GAME_AREA_WIDTH + UI_MARGIN
SCREEN_HEIGHT = ROOM_HEIGHT_GRID * GRID_SIZE

# 폰트 설정
FONT_PATH = "font/Ldfcomicsans.ttf"

# 배경이미지 경로
BACKGROUND_IMAGE_PATH = "assets/wood_floor.png"

# ========= pygame 초기화 =========
pygame.init()

# --- 화면 및 폰트 로드 ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Welcome To My - v0.2")

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
global_background_image = pygame.transform.scale(background_image, (GAME_AREA_WIDTH, SCREEN_HEIGHT))

# --- ModelManager 및 평가 변수 초기화 ---
# (하드코딩 테스트용)
model_manager = ModelManager()
current_request_text = client.generate_request(None) # 하드코딩된 의뢰서
request_embedding = [] # 임시 값 (E 키를 누를 때마다 갱신)
evaluation_result = None
running = True

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
        # 90도 회전 (pygame.transform.rotate는 반시계 방향)
        # 90도 회전 시 크기가 변경되므로, 원본을 회전 후 스케일링
        original_image = item["image"]
        # 원본의 0도 스케일 (64x32)
        # 90도 회전 시 (32x64)
        rotated_image = pygame.transform.rotate(original_image, 90)
        
        # 회전된 논리적 크기
        rotated_size_grid = get_rotated_size(item, rotation)
        # 회전된 픽셀 크기
        rotated_pixel_size = (rotated_size_grid[0] * GRID_SIZE, rotated_size_grid[1] * GRID_SIZE)
        
        # 회전된 이미지에 맞게 다시 스케일링
        return pygame.transform.scale(rotated_image, rotated_pixel_size)

def check_collision(new_item, new_pos, new_rot, placed_furniture):
    """새 가구가 방 경계나 다른 가구와 겹치는지 확인합니다."""
    new_size = get_rotated_size(new_item, new_rot)
    new_rect = pygame.Rect(new_pos[0], new_pos[1], new_size[0], new_size[1])

    if new_rect.left < 0 or new_rect.top < 0 or \
       new_rect.right > ROOM_WIDTH_GRID or new_rect.bottom > ROOM_HEIGHT_GRID:
        return True 

    for f in placed_furniture:
        f_size = get_rotated_size(f['item'], f['rotation'])
        f_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size[0], f_size[1])
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

# 스크롤 변수
ui_scroll_y = 0
UI_ITEM_HEIGHT = 60 # 각 가구 목록 아이템의 높이

# UI 레이아웃 상수
UI_PANEL_HELP_Y = 10
UI_PANEL_FURNITURE_Y = 80
UI_PANEL_FURNITURE_HEIGHT = 250 # 스크롤 패널의 고정 높이
UI_PANEL_REQUEST_Y = UI_PANEL_FURNITURE_Y + UI_PANEL_FURNITURE_HEIGHT + 20 # 350
UI_PANEL_FEEDBACK_Y_OFFSET = 150 # Request 패널로부터의 간격

# ========= 게임 루프 =========
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
        
        # --- 2. 스크롤 이벤트 ---
        if event.type == pygame.MOUSEWHEEL:
            # 마우스가 UI 영역에 있을 때만 스크롤
            if mouse_pos[0] > GAME_AREA_WIDTH:
                ui_scroll_y += event.y * 20 # 스크롤 속도
                
                # 스크롤 범위 제한
                total_list_height = len(FURNITURE_LIST) * UI_ITEM_HEIGHT
                max_scroll = max(0, total_list_height - UI_PANEL_FURNITURE_HEIGHT)
                
                ui_scroll_y = max(min(ui_scroll_y, 0), -max_scroll)
        
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
        
        # 클릭 이벤트
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭: 배치
                if mouse_pos[0] > GAME_AREA_WIDTH: # UI 클릭
                    # 2. 스크롤 및 3. 레이아웃: UI 가구 패널 내에서만 클릭
                    if mouse_pos[1] >= UI_PANEL_FURNITURE_Y and mouse_pos[1] < (UI_PANEL_FURNITURE_Y + UI_PANEL_FURNITURE_HEIGHT):
                        for button in ui_buttons:
                            # 버튼의 '화면상' y좌표가 클릭되었는지 확인
                            if button["rect_screen"].collidepoint(mouse_pos):
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
                    for i in range(len(placed_furniture) - 1, -1, -1):
                        f = placed_furniture[i]
                        f_size = get_rotated_size(f['item'], f['rotation'])
                        f_grid_rect = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size[0], f_size[1])
                        
                        if f_grid_rect.collidepoint(mouse_grid_x, mouse_grid_y):
                            placed_furniture.pop(i)
                            break 

    # --- 그리기 ---
    # 1. 스크린 채우기
    screen.fill((255, 255, 255))
    if global_background_image:
        screen.blit(global_background_image, (0, 0))
    else:
        # 배경 로드 실패 시 게임 영역만 흰색으로 덮기
        pygame.draw.rect(screen, (255, 255, 255), (0, 0, GAME_AREA_WIDTH, SCREEN_HEIGHT))

    # 1.1 그리드 그리기
    for x in range(ROOM_WIDTH_GRID + 1):
        pygame.draw.line(screen, (210, 140, 180), (x * GRID_SIZE, 0), (x * GRID_SIZE, SCREEN_HEIGHT))
    for y in range(ROOM_HEIGHT_GRID + 1):
        pygame.draw.line(screen, (210, 140, 180), (0, y * GRID_SIZE), (GAME_AREA_WIDTH, y * GRID_SIZE))

    # # 2. 배치된 가구 그리기 (이미지 사용)
    # for furniture in placed_furniture:
    #     item = furniture["item"]
    #     pos_x, pos_y = furniture["grid_pos"]
    #     rotation = furniture["rotation"]
        
    #     image_to_draw = get_rotated_image(item, rotation)
    #     screen.blit(image_to_draw, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))

    # # 3. 현재 선택된 가구 (고스트) 그리기 (이미지 틴트 사용)
    # if mouse_pos[0] < GAME_AREA_WIDTH: # 게임 영역 안에서만
        
    #     image_to_draw = get_rotated_image(current_item, selected_furniture_rotation)
    #     tint_color = (0, 255, 0, 100) if is_placeable else (255, 0, 0, 100)
        
    #     ghost_image = image_to_draw.copy()
    #     tint_surface = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
    #     tint_surface.fill(tint_color)
    #     ghost_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
    #     screen.blit(ghost_image, (mouse_grid_x * GRID_SIZE, mouse_grid_y * GRID_SIZE))

    # --- Z-Sorting 수정 ---
    # 2. 렌더링할 모든 객체를 하나의 리스트로 통합
    render_list = placed_furniture.copy()

    # 3. 고스트(미리보기) 가구를 렌더링 리스트에 추가
    if mouse_pos[0] < GAME_AREA_WIDTH: # 게임 영역 안에서만
        render_list.append({
            "item": current_item,
            "grid_pos": (mouse_grid_x, mouse_grid_y),
            "rotation": selected_furniture_rotation,
            "is_ghost": True # 고스트 식별용 플래그
        })
        
    # 4. Z-Sorting (Y좌표 오름차순, Y가 같으면 X좌표 오름차순)
    # Y가 작은(화면 위쪽) 객체부터 그립니다.
    sorted_render_list = sorted(render_list, key=lambda f: (f['grid_pos'][1], f['grid_pos'][0]))

    # 5. 정렬된 리스트를 순회하며 그리기
    for furniture in sorted_render_list:
        item = furniture["item"]
        pos_x, pos_y = furniture["grid_pos"]
        rotation = furniture["rotation"]
        
        image_to_draw = get_rotated_image(item, rotation)
        
        if furniture.get("is_ghost", False):
            # 고스트(미리보기)인 경우
            tint_color = (0, 255, 0, 100) if is_placeable else (255, 0, 0, 100)
            
            ghost_image = image_to_draw.copy()
            tint_surface = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
            tint_surface.fill(tint_color)
            ghost_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            screen.blit(ghost_image, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))
        else:
            # 배치된 실제 가구인 경우
            screen.blit(image_to_draw, (pos_x * GRID_SIZE, pos_y * GRID_SIZE))


    # --- 4. UI 영역 그리기 (3. 레이아웃 적용) ---
    pygame.draw.rect(screen, (245, 245, 245), (GAME_AREA_WIDTH, 0, UI_MARGIN, SCREEN_HEIGHT))   
    
    # 4.1 도움말 패널
    ui_y_offset = UI_PANEL_HELP_Y
    screen.blit(font_S.render("R: 회전, L-Click: 배치", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 25
    screen.blit(font_S.render("R-Click: 제거, E: 평가", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 30

    # 4.2 가구 목록 패널 (1. 이미지 / 2. 스크롤)
    ui_buttons.clear()
    
    # 2. 스크롤 패널의 '클리핑'을 위한 SubSurface 생성
    furniture_panel = screen.subsurface(pygame.Rect(GAME_AREA_WIDTH, UI_PANEL_FURNITURE_Y, UI_MARGIN, UI_PANEL_FURNITURE_HEIGHT))
    furniture_panel.fill((240, 240, 240)) # 스크롤 영역 배경색

    for i, item in enumerate(FURNITURE_LIST):
        # 버튼의 '논리적' Y 위치 (스크롤 적용)
        item_y_pos = (i * UI_ITEM_HEIGHT) + ui_scroll_y
        
        # 화면에 보이는 영역에만 버튼을 그림
        if item_y_pos + UI_ITEM_HEIGHT > 0 and item_y_pos < UI_PANEL_FURNITURE_HEIGHT:
            
            button_rect = pygame.Rect(10, item_y_pos, UI_MARGIN - 20, 50) # 패널 기준 x, y
            
            # 실제 화면 좌표 기준 Rect (클릭 감지용)
            button_rect_screen = pygame.Rect(GAME_AREA_WIDTH + 10, UI_PANEL_FURNITURE_Y + item_y_pos, UI_MARGIN - 20, 50)
            ui_buttons.append({"index": i, "rect_screen": button_rect_screen})
            
            # 선택된 아이템은 녹색으로 하이라이트
            button_color = (150, 255, 150) if i == selected_furniture_index else (220, 220, 220)
            pygame.draw.rect(furniture_panel, button_color, button_rect, border_radius=5)
            
            # --- 1. 가구 썸네일 이미지 ---
            try:
                # 썸네일 크기 계산 (높이 40px 기준으로)
                thumb_h = 40
                thumb_w = int(item["image"].get_width() * (thumb_h / item["image"].get_height()))
                thumb_img = pygame.transform.scale(item["image"], (thumb_w, thumb_h))
                
                furniture_panel.blit(thumb_img, (20, item_y_pos + 5))
            except Exception as e:
                print(f"썸네일 생성 오류: {e}") # (가끔 0으로 나누기 오류 방지)
            
            # 가구 이름
            furniture_panel.blit(font_M.render(item['name'], True, (0,0,0)), (120, item_y_pos + 15))

    # 4.3 고객 의뢰서 표시 (3. 레이아웃)
    ui_y_offset = UI_PANEL_REQUEST_Y
    pygame.draw.line(screen, (200,200,200), (GAME_AREA_WIDTH + 5, ui_y_offset - 10), (SCREEN_WIDTH - 5, ui_y_offset - 10), 1)
    
    screen.blit(font_M.render("고객 의뢰서:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset = draw_text_multiline(
        screen, 
        current_request_text, 
        (GAME_AREA_WIDTH + 10, ui_y_offset + 30), 
        font_M, 
        UI_MARGIN - 20, 
        (50,50,50)
    )
    
    # 4.4 평가 결과 표시 (3. 레이아웃)
    if evaluation_result:
        ui_y_offset += 20
        score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
        screen.blit(font_M.render(score_str, True, (0, 100, 0)), (GAME_AREA_WIDTH + 10, ui_y_offset))
        
        feedback_y = ui_y_offset + 40
        screen.blit(font_M.render("고객 피드백:", True, (0,0,0)), (GAME_AREA_WIDTH + 10, feedback_y))
        draw_text_multiline(
            screen,
            evaluation_result['feedback'],
            (GAME_AREA_WIDTH + 10, feedback_y + 30),
            font_M,
            UI_MARGIN - 20,
            (50,50,50)
        )
        
    # --- 업데이트 ---
    pygame.display.flip()

pygame.quit()
sys.exit()

