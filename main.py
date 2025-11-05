import pygame
import sys
import math
import threading
import random

import evaluation
import client
from model import ModelManager

# furintures 모듈을 임포트 (리스트는 아래에서 가져옴)
import furnitures 

# ========= 상수 정의 =========
GRID_SIZE = 64  # 각 격자 크기
ROOM_WIDTH_GRID = 10 # 가로 칸 수
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
clock = pygame.time.Clock() # FPS를 위한 시계

# --- 화면 및 폰트 로드 ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Welcome To My - v0.3 (New Layout)")

font_XL = pygame.font.Font(FONT_PATH, 48) # 큰
font_L = pygame.font.Font(FONT_PATH, 22) # 큰
font_M = pygame.font.Font(FONT_PATH, 18) # 중간
font_S = pygame.font.Font(FONT_PATH, 14) # 작은

DOOR_COLOR = (101, 67, 33) # 문 색: 짙은 갈색

# --- 스플래시 스크린 ---
def run_splash_screen(screen, clock, font):
    """
    Fade-in / Fade-out 스플래시 스크린을 실행합니다.
    """
    # 로고 또는 텍스트 설정
    text_surf = font.render("SKN19 LLM Project", True, (80, 80, 80)) # 어두운 회색
    text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    
    fade_duration_frames = 60 # 1초 (60 FPS 기준)
    alpha_step = 255 / fade_duration_frames
    
    # --- Fade-in ---
    alpha = 0
    while alpha < 255:
        # 이벤트 처리 (스킵)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                return # 스킵

        alpha += alpha_step
        if alpha > 255: alpha = 255
        
        screen.fill((255, 255, 255)) # 흰색 배경
        text_surf.set_alpha(int(alpha))
        screen.blit(text_surf, text_rect)
        
        pygame.display.flip()
        clock.tick(60)

    # --- Hold (1초 대기) ---
    hold_start_time = pygame.time.get_ticks()
    while pygame.time.get_ticks() - hold_start_time < 1000:
        # 이벤트 처리 (스킵)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                return # 스킵
        clock.tick(60) # 이벤트 루프를 위해 tick은 유지

    # --- Fade-out ---
    alpha = 255
    while alpha > 0:
        # 이벤트 처리 (스킵)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                return # 스킵

        alpha -= alpha_step
        if alpha < 0: alpha = 0
        
        screen.fill((255, 255, 255)) # 흰색 배경
        text_surf.set_alpha(int(alpha))
        screen.blit(text_surf, text_rect)
        
        pygame.display.flip()
        clock.tick(60)

# ========= 리소스 로딩 스레드 함수 =========
def load_game_resources(results_dict, completion_event, progress_tracker):
    """
    (백그라운드 스레드) 모든 무거운 리소스(이미지, 모델)를 로드합니다.
    (수정) progress_tracker를 업데이트하여 진행률을 알립니다.
    """
    try:
        total_steps = 5 # 총 5단계 작업
        progress_tracker["total_steps"] = total_steps
        
        # 1. 가구 이미지 로드
        progress_tracker["status"] = "가구 에셋 로드 중..."
        results_dict['FURNITURE_LIST'] = furnitures.load_furniture_data(GRID_SIZE)
        progress_tracker["step"] = 1
        
        # 2. 배경 이미지 로드
        progress_tracker["status"] = "배경 이미지 로드 중..."
        background_image = pygame.image.load(BACKGROUND_IMAGE_PATH).convert()
        results_dict['background_image'] = pygame.transform.scale(background_image, (GAME_AREA_WIDTH, GAME_AREA_HEIGHT))
        progress_tracker["step"] = 2
        
        # 3. 모델 매니저 초기화 (가장 오래 걸리는 작업)
        progress_tracker["status"] = "AI 모델 서버에 연결 중... (Ollama)"
        model_manager = ModelManager()
        results_dict['model_manager'] = model_manager
        progress_tracker["step"] = 3

        # persona, wishlist, request_text = client.generate_request(model_manager)
        # results_dict['current_persona'] = persona
        # results_dict['request_text'] = request_text
        
        if not model_manager.is_ready:
             raise Exception("모델 매니저 로드 실패 (Ollama 서버 확인)")
        
        # 4. 첫 번째 의뢰서 생성 (네트워크 통신)
        progress_tracker["status"] = "새로운 고객 의뢰서 생성 중..."
        persona, wishlist, request_text = client.generate_request(model_manager)
        
        results_dict['current_persona'] = persona
        results_dict['internal_wishlist'] = wishlist
        results_dict['request_text'] = request_text
        progress_tracker["step"] = 4
        
        # 5. 첫 번째 임베딩 생성 (네트워크 통신)
        progress_tracker["status"] = "고객 의뢰서 분석 중... (EEVE)"
        request_embedding = model_manager.get_embedding(request_text)
        results_dict['request_embedding'] = request_embedding
        progress_tracker["step"] = 5

        progress_tracker["status"] = "로드 완료!"
        
        if not request_embedding:
            raise Exception("의뢰서 임베딩 실패")
            
    except Exception as e:
        print(f"리소스 로딩 중 오류 (테스트 모드로 전환): {e}")
        # 실패 시 테스트 모드로 폴백
        progress_tracker["status"] = f"오류 발생: {e}. 테스트 모드로 전환합니다."
        results_dict['FURNITURE_LIST'] = results_dict.get('FURNITURE_LIST') or furnitures.load_furniture_data(GRID_SIZE)
        if 'background_image' not in results_dict:
             results_dict['background_image'] = None # 배경 로드 실패
        results_dict['model_manager'] = None
        persona, request_text = client.generate_request(None)
        results_dict['current_persona'] = persona
        results_dict['request_text'] = request_text
        results_dict['request_embedding'] = [0.1] * 128
    finally:
        # 메인 스레드에 로딩 완료 신호 전송
        completion_event.set()

# ========= 로딩 스크린 함수 =========
def run_loading_screen(screen, clock, font_l, font_m):
    """
    (메인 스레드) 리소스가 로드되는 동안 0-100% 게이지 바를 표시합니다.
    """
    loading_results = {}
    loading_complete_event = threading.Event()
    # 진행률 추적 딕셔너리
    progress_tracker = {"step": 0, "total_steps": 5, "status": "초기화 중..."}
    
    # 백그라운드 스레드 시작
    loader_thread = threading.Thread(
        target=load_game_resources, 
        args=(loading_results, loading_complete_event, progress_tracker)
    )
    loader_thread.start()
    
    bar_width = 400 # (수정) 전체 바 너비
    bar_height = 30
    bar_x = (SCREEN_WIDTH - bar_width) // 2
    bar_y = (SCREEN_HEIGHT - bar_height) // 2 + 50
    
    current_progress = 0.0 # (수정) 현재 게이지 (0.0 ~ 1.0)
    target_progress = 0.0 # (수정) 스레드가 보고한 목표 게이지

    while not loading_complete_event.is_set():
        # 메인 스레드는 이벤트 루프를 계속 실행
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        # 부드러운 게이지 애니메이션
        target_progress = progress_tracker["step"] / progress_tracker["total_steps"]
        # 현재 게이지가 목표 게이지를 따라가도록 부드럽게 증가
        if current_progress < target_progress:
            current_progress += 0.01 # 부드럽게 차오르는 속도
            if current_progress > target_progress:
                current_progress = target_progress

        screen.fill((255, 255, 255)) # 흰색 배경
        
        # (수정) 로딩 상태 텍스트
        status_text = progress_tracker["status"]
        text_surf = font_m.render(status_text, True, (80, 80, 80))
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        screen.blit(text_surf, text_rect)
        
        # 로딩 바 (배경)
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        
        # 로딩 바 (채워지는 부분)
        current_bar_width = int(bar_width * current_progress)
        if current_bar_width > 0:
            pygame.draw.rect(screen, (0, 150, 0), (bar_x, bar_y, current_bar_width, bar_height), border_radius=5)
        
        # 퍼센트 텍스트
        percent_text = font_m.render(f"{int(current_progress * 100)}%", True, (255, 255, 255))
        percent_rect = percent_text.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))
        screen.blit(percent_text, percent_rect)
        
        pygame.display.flip()
        clock.tick(60)
        
    loader_thread.join() # 스레드가 완전히 종료될 때까지 대기
    return loading_results

# ========= 스플래시 및 로딩 실행 =========
# run_splash_screen(screen, clock, font_XL)
loaded_resources = run_loading_screen(screen, clock, font_L, font_M)

# ========= 리소스 전역 변수 할당 =========
FURNITURE_LIST = loaded_resources.get('FURNITURE_LIST')
global_background_image = loaded_resources.get('background_image')
model_manager = loaded_resources.get('model_manager')
current_persona = loaded_resources.get('current_persona') 
internal_wishlist = loaded_resources.get('internal_wishlist')
current_request_text = loaded_resources.get('request_text')
request_embedding = loaded_resources.get('request_embedding')
door_position = None # 문 위치 변수

print(current_request_text)

if not FURNITURE_LIST:
    print("가구 리스트 로드 실패. assets 폴더를 확인하세요.")
    pygame.quit()
    sys.exit()

# # --- 배경 이미지 로드 ---
# global_background_image = None
# background_image = pygame.image.load(BACKGROUND_IMAGE_PATH).convert()
# # 게임 영역 크기에 맞게 스케일
# global_background_image = pygame.transform.scale(background_image, (GAME_AREA_WIDTH, GAME_AREA_HEIGHT))

# # --- ModelManager 및 평가 변수 초기화 ---
# model_manager = None
# current_request_text = ""
# request_embedding = []

# running = True

# try:
#     model_manager = ModelManager()

#     current_request_text = client.generate_request(model_manager)
#     print(f"요구사항: {current_request_text}")
#     request_embedding = model_manager.get_embedding(current_request_text)
#     if not request_embedding:
#         print("요구사항 임베딩 실패! 스트 모드로 전환합니다.")
#         current_request_text = client.generate_request(None)
#         request_embedding = [0.1] * 128
# except Exception as e:
#     print(f"🚨 모델 초기화 실패: {e}")
#     print("Ollama 서버가 실행 중인지 확인하세요. 테스트 모드로 실행합니다.")

# --- 헬퍼 함수 (문 생성) ---
def create_new_door():
    """벽면(모서리 제외)에 무작위로 문 위치를 생성합니다."""
    side = random.choice(['top', 'bottom', 'left', 'right'])
    
    if side == 'top':
        x = random.randint(1, ROOM_WIDTH_GRID - 1)
        y = 0
    elif side == 'bottom':
        x = random.randint(1, ROOM_WIDTH_GRID - 1)
        y = ROOM_HEIGHT_GRID - 1
    elif side == 'left':
        x = 0
        y = random.randint(1, ROOM_HEIGHT_GRID - 1)
    else: # 'right'
        x = ROOM_WIDTH_GRID - 1
        y = random.randint(1, ROOM_HEIGHT_GRID - 1)
        
    print(f"새로운 문 생성: ({x}, {y})")
    return (x, y)

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
    # 가구의 시각적(화면에 표시되는) 크기
    new_size_visual = get_rotated_size(new_item, new_rot)
    new_rect_full = pygame.Rect(new_pos[0], new_pos[1], new_size_visual[0], new_size_visual[1])
    # 1. 방 경계 확인
    if new_rect_full.left < 0 or new_rect_full.top < 0 or \
       new_rect_full.right > ROOM_WIDTH_GRID or new_rect_full.bottom > ROOM_HEIGHT_GRID:
        return True 

    # 2. 다른 가구와 겹치는 여부 확인
    new_rect_base = pygame.Rect(new_pos[0], new_pos[1], new_size_visual[0], 1)

    for f in placed_furniture:
        f_size_visual = get_rotated_size(f['item'], f['rotation'])
        f_rect_base = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size_visual[0], 1) # 높이 1
        if new_rect_base.colliderect(f_rect_base):
            return True 
    
    # 3. 문과의 겹치는 여부 확인
    if door_position:
        # 문은 1x1 크기
        door_rect = pygame.Rect(door_position[0], door_position[1], 1, 1)
        if new_rect_full.colliderect(door_rect):
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

# --- 평가 트리거 함수 ---
def trigger_evaluation():
    """'E' 키 또는 '디자인 완료' 버튼 클릭 시 평가를 실행합니다."""
    print("평가 시작...")
    eval_data = evaluation.evaluate_design(
        model_manager, 
        request_embedding, 
        placed_furniture,
        ROOM_WIDTH_GRID,
        ROOM_HEIGHT_GRID
    )
    
    feedback_text = client.generate_feedback(
        model_manager,
        current_persona,
        current_request_text,
        internal_wishlist,
        eval_data['description'],
        eval_data['score']
    )
    
    # evaluation_result를 업데이트하여 UI에 표시
    return {
        "score": eval_data['score'],
        "description": eval_data['description'],
        "feedback": feedback_text
    }

# --- (신규) 게임 초기화 함수 ---
def reset_game():
    """(신규) '초기화' 버튼 클릭 시 게임 상태를 리셋합니다."""
    global current_persona, current_request_text, request_embedding, placed_furniture, evaluation_result, internal_wishlist, door_position
    print("--- 게임 초기화 ---")
    
    # 1. 가구 배치 초기화
    placed_furniture = []
    # 2. 평가 결과 초기화
    evaluation_result = None

    # 3. 새 문 생성
    door_position = create_new_door()
    
    # 4. 새 고객 생성
    current_persona, internal_wishlist, current_request_text = client.generate_request(model_manager)

    # 5. 새 임베딩 생성
    if model_manager and model_manager.is_ready:
        request_embedding = model_manager.get_embedding(current_request_text)
    else:
        request_embedding = [0.1] * 128
        
    print(f"새로운 고객: {current_persona['name']}")
    print(f"새로운 의뢰서: {current_request_text}")

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

evaluation_result = None    # 평가 결과
evaluate_button_rect = None # 평가 버튼
reset_button_rect = None    # reset 버튼

door_position = create_new_door() 

running = True

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
                if not evaluation_result: # 평가가 아직 안됐을 때만
                            evaluation_result = trigger_evaluation()
        
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
                # 3. 오른쪽 UI 버튼 클릭
                elif right_ui_rect.collidepoint(mouse_pos):
                    # 디자인 완료
                    if evaluate_button_rect and evaluate_button_rect.collidepoint(mouse_pos):
                        if not evaluation_result: # 평가가 아직 안됐을 때만
                            evaluation_result = trigger_evaluation()
                    # 초기화
                    if reset_button_rect and reset_button_rect.collidepoint(mouse_pos):
                        reset_game()
            
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

    # --- (신규) 1.3 문 그리기 ---
    if door_position:
        door_rect_pixels = pygame.Rect(
            door_position[0] * GRID_SIZE, 
            door_position[1] * GRID_SIZE, 
            GRID_SIZE, 
            GRID_SIZE
        )
        pygame.draw.rect(screen, DOOR_COLOR, door_rect_pixels) # 짙은 갈색
        pygame.draw.rect(screen, (0,0,0), door_rect_pixels, 3) # 검은색 테두리

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

    # (신규) 초기화 버튼 그리기
    reset_button_rect = pygame.Rect(GAME_AREA_WIDTH + RIGHT_UI_MARGIN - 80, ui_y_offset, 70, 30) # 오른쪽 상단
    mouse_over_reset = reset_button_rect.collidepoint(mouse_pos)
    reset_btn_color = (255, 100, 100) if mouse_over_reset else (200, 80, 80)
    pygame.draw.rect(screen, reset_btn_color, reset_button_rect, border_radius=5)
    reset_text = font_M.render("초기화", True, (255, 255, 255))
    screen.blit(reset_text, reset_text.get_rect(center=reset_button_rect.center))

    screen.blit(font_S.render("R: 회전 / E: 평가", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 25
    screen.blit(font_S.render("L-Click: 배치 / R-Click: 제거", True, (100,100,100)), (GAME_AREA_WIDTH + 10, ui_y_offset))
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
    
    # 3.3 '디자인 완료' 버튼 또는 '평가 결과' 표시
    ui_y_offset += 20 # 의뢰서와 버튼/결과 사이 여백
    
    if evaluation_result:
        # --- 평가가 완료된 경우 ---
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
    else:
        # 평가 전, '디자인 완료' 버튼 표시
        evaluate_button_rect = pygame.Rect(GAME_AREA_WIDTH + 10, ui_y_offset, RIGHT_UI_MARGIN - 20, 50)
        
        # 마우스 호버 효과
        mouse_over_button = evaluate_button_rect.collidepoint(mouse_pos)
        button_color = (0, 180, 0) if mouse_over_button else (0, 150, 0) # 호버 시 밝게
            
        pygame.draw.rect(screen, button_color, evaluate_button_rect, border_radius=5)
        
        btn_text = font_L.render("디자인 완료(E)", True, (255, 255, 255))
        btn_text_rect = btn_text.get_rect(center=evaluate_button_rect.center)
        screen.blit(btn_text, btn_text_rect)

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
                # 썸네일 크기 (가로 50, 세로 50)
                thumb_h = 50
                thumb_w = 50
                thumb_img = pygame.transform.smoothscale(item["image"], (thumb_w, thumb_h))
                bottom_panel.blit(thumb_img, (item_x_pos + 10, item_y_pos + 5)) # (y + 5 상하중앙정렬)
            except Exception as e:
                print(f"썸네일 생성 오류: {e}")
            
            # 가구 이름 (썸네일 오른쪽으로 이동)
            name_x_pos = item_x_pos + 70 # 10(여백) + 50(썸네일) + 10(여백)
            bottom_panel.blit(font_M.render(item['name'], True, (0,0,0)), (name_x_pos + 20, item_y_pos + 20)) # (y + 20 상하중앙정렬)

    # --- 업데이트 ---
    pygame.display.flip()

pygame.quit()
sys.exit()

