import pygame
import sys
import math
import threading

import config
from modules import evaluation, client, loading, utils

# ========= pygame 초기화 =========
pygame.init()
clock = pygame.time.Clock() # FPS를 위한 시계

# --- 화면 및 폰트 로드 ---
screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
pygame.display.set_caption("Well... come to my Home")

font_XL = pygame.font.Font(config.FONT_PATH, 48) # 아주 큰
font_L = pygame.font.Font(config.FONT_PATH, 22)  # 큰
font_M = pygame.font.Font(config.FONT_PATH, 18)  # 중간
font_S = pygame.font.Font(config.FONT_PATH, 14)  # 작은

# 손글씨 폰트
font_Pencil_L = pygame.font.Font(config.PENCIL_FONT_PATH, 20)
font_Pencil_M = pygame.font.Font(config.PENCIL_FONT_PATH, 16)

# 로딩 스크린 함수들을 loading.py로 이동
# 헬퍼 함수들을 utils.py로 이동

# ========= 로딩 실행 =========
loaded_resources = loading.run_loading_screen(screen, clock, font_L, font_M)

# ========= 리소스 전역 변수 할당 =========
FURNITURE_LIST = loaded_resources.get('FURNITURE_LIST')
global_background_image = loaded_resources.get('background_image')
model_manager = loaded_resources.get('model_manager')
current_persona = loaded_resources.get('current_persona') 
internal_wishlist = loaded_resources.get('internal_wishlist')
current_request_text = loaded_resources.get('request_text')
request_embedding = loaded_resources.get('request_embedding')
door_position = None # 문 위치 변수

# ========= 별점 및 종이 이미지 애셋 로드 =========
try:
    # 포스트잇 (페르소나 + 의뢰서)
    post_it_img = pygame.image.load(config.POST_IT_PATH).convert_alpha()
    post_it_img = pygame.transform.scale(post_it_img, (config.RIGHT_UI_MARGIN - 20, 300))
except Exception as e:
    print(f"UI 에셋 로드 실패 (post.png): {e}")
    post_it_img = None

# 3. 별점 이미지
star_full_img = None
star_half_img = None
star_empty_img = None
try:
    star_full_img = pygame.image.load(config.STAR_FULL_PATH).convert_alpha()
    star_full_img = pygame.transform.scale(star_full_img, config.STAR_SIZE)
    
    star_half_img = pygame.image.load(config.STAR_HALF_PATH).convert_alpha()
    star_half_img = pygame.transform.scale(star_half_img, config.STAR_SIZE)

    star_empty_img = pygame.image.load(config.STAR_EMPTY_PATH).convert_alpha()
    star_empty_img = pygame.transform.scale(star_empty_img, config.STAR_SIZE)
    
except Exception as e:
    print(f"UI 에셋 로드 실패 (star.png / star_empty.png): {e}. 텍스트 점수로 대체합니다.")
    star_full_img = star_half_img = star_empty_img = None

print(current_request_text)

if not FURNITURE_LIST:
    print("가구 리스트 로드 실패. assets 폴더를 확인하세요.")
    pygame.quit()
    sys.exit()

# --- UI 헬퍼 함수 ---
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

# --- UI 헬퍼 함수 ---
def draw_star_rating(surface, score, pos, star_full, star_half, star_empty):
    """주어진 점수에 맞춰 5개의 별을 그립니다."""
    x, y = pos
    star_width = star_full.get_width()
    star_spacing = 4 # 별 사이 간격
    
    for i in range(5):
        star_x = x + i * (star_width + star_spacing)
        
        if score >= i + 1:
            surface.blit(star_full, (star_x, y))
        elif score >= i + 0.5:
            surface.blit(star_half, (star_x, y))
        else:
            surface.blit(star_empty, (star_x, y))

# --- 게임 로직 함수 ---
def trigger_evaluation():
    """'E' 키 또는 '디자인 완료' 버튼 클릭 시 평가를 실행합니다."""
    global evaluation_result, is_evaluating, show_feedback_popup
    
    print("평가 스레드 시작")
    # utils.py로 이동하지 않음. evaluation 모듈 사용
    eval_data = evaluation.evaluate_design(
        model_manager, 
        current_request_text,
        internal_wishlist,
        placed_furniture,
        config.ROOM_WIDTH_GRID,
        config.ROOM_HEIGHT_GRID
    )
    
    feedback_text = client.generate_feedback(
        model_manager,
        current_persona,
        current_request_text,
        internal_wishlist,
        eval_data['description'],
        eval_data['score']
    )
    
    # 평가 완료 후 메인 스레드에서 팝업을 띄우도록 상태 변경
    evaluation_result = {
        "score": eval_data['score'],
        "description": eval_data['description'],
        "feedback": feedback_text
    }
    is_evaluating = False
    show_feedback_popup = True
    print("평가 스레드 완료")

# --- 게임 로직 함수 ---
def run_evaluation_thread():
    """'trigger_evaluation'을 별도 스레드에서 실행하고 상태를 업데이트합니다."""
    # 전역 변수 사용
    global evaluation_result, is_evaluating, show_feedback_popup
    
    eval_thread = threading.Thread(target=trigger_evaluation, daemon=True)
    eval_thread.start()


# --- 게임 로직 함수 ---
def reset_game(eval=False):
    """'초기화' 버튼 클릭 시 게임 상태를 리셋합니다."""
    global current_persona, current_request_text, request_embedding, placed_furniture, evaluation_result, internal_wishlist, door_position, is_evaluating, show_feedback_popup, is_feedback_hidden
    print("--- 게임 초기화 ---")
    
    # 1. 가구 배치 초기화
    placed_furniture = []

    if eval:
        # 2. 평가 결과 초기화
        evaluation_result = None
        is_evaluating = False
        show_feedback_popup = False
        is_feedback_hidden = False

        # 3. 새 문 생성 (수정: utils 사용)
        # --- (수정) config 모듈 자체를 전달 ---
        door_position = utils.create_new_door(config)
        
        # 4. 새 고객 생성
        current_persona, internal_wishlist, current_request_text = client.generate_request(model_manager)

        # 5. 새 임베딩 생성
        if model_manager and model_manager.is_ready:
            request_embedding = model_manager.get_embedding(current_request_text)
        else:
            request_embedding = [0.1] * 128
            
        print(f"새로운 고객: {current_persona['name']}")
        print(f"[요구 가구]: {internal_wishlist}")
        print(f"새로운 의뢰서: {current_request_text}")

# ========= 변수 초기화 (게임 루프 전) =========
placed_furniture = []
selected_furniture_index = 0
selected_furniture_rotation = 0 # 0: 기본, 1: 90도
ui_buttons = []

# 하단 UI 스크롤 변수
ui_scroll_y = 0

# UI 레이아웃 Rect 정의
game_area_rect = pygame.Rect(0, 0, config.GAME_AREA_WIDTH, config.GAME_AREA_HEIGHT)
right_ui_rect = pygame.Rect(config.GAME_AREA_WIDTH, 0, config.RIGHT_UI_MARGIN, config.GAME_AREA_HEIGHT)
bottom_ui_rect = pygame.Rect(0, config.GAME_AREA_HEIGHT, config.SCREEN_WIDTH, config.BOTTOM_UI_MARGIN)

evaluation_result = None
evaluate_button_rect = None
reset_button_rect = None
exit_button_rect = None
reroll_customer_button_rect = None

# 평가/팝업 상태 변수
is_evaluating = False
show_feedback_popup = False
is_feedback_hidden = False
popup_close_button_rect = None
popup_toggle_button_rect = None

eval = False
# utils 사용
door_position = utils.create_new_door(config)

running = True

# ========= 게임 루프 =========
while running:
    mouse_pos = pygame.mouse.get_pos()
    
    mouse_grid_x = -1
    mouse_grid_y = -1
    is_placeable = False
    
    if not is_evaluating and not show_feedback_popup:
        mouse_grid_x = mouse_pos[0] // config.GRID_SIZE
        mouse_grid_y = mouse_pos[1] // config.GRID_SIZE
        current_item = FURNITURE_LIST[selected_furniture_index]

        if game_area_rect.collidepoint(mouse_pos):
            # utils 사용
            is_placeable = not utils.check_collision(
                current_item, 
                (mouse_grid_x, mouse_grid_y), 
                selected_furniture_rotation, 
                placed_furniture,
                door_position
            )

    # ========= 이벤트 처리 =========
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        
        # --- 하단 패널 종방향 스크롤 ---
        if event.type == pygame.MOUSEWHEEL:
            if not is_evaluating and not show_feedback_popup:
                if bottom_ui_rect.collidepoint(mouse_pos):
                    ui_scroll_y += event.y * 30 # Y축 스크롤
                    
                    # 스크롤 범위 제한
                    total_rows = math.ceil(len(FURNITURE_LIST) / 5) # 5열 기준
                    total_list_height = total_rows * config.UI_ITEM_HEIGHT
                    max_scroll = max(0, total_list_height - config.BOTTOM_UI_MARGIN)
                    
                    ui_scroll_y = max(min(ui_scroll_y, 0), -max_scroll)
        
        # --- 키다운 이벤트 ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: # 'R' 키로 회전
                selected_furniture_rotation = (selected_furniture_rotation + 1) % 2
            
            if event.key == pygame.K_e: # 'E' 키로 평가
                if not evaluation_result and not is_evaluating:
                    is_evaluating = True
                    run_evaluation_thread() # 함수 호출
        
        # 클릭 이벤트
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 좌클릭
                # 0. 팝업이 켜져있으면 팝업 클릭만 처리
                if show_feedback_popup:
                    eval = True

                    if popup_toggle_button_rect and popup_toggle_button_rect.collidepoint(mouse_pos):
                        is_feedback_hidden = not is_feedback_hidden
                    
                    elif not is_feedback_hidden and popup_close_button_rect and popup_close_button_rect.collidepoint(mouse_pos):
                        reset_game(eval)
                
                # 1. 평가 중이면 모든 클릭 무시
                elif is_evaluating:
                    pass 

                # 2. 하단 UI(가구 목록) 클릭
                elif bottom_ui_rect.collidepoint(mouse_pos):
                    for button in ui_buttons:
                        if button["rect_screen"].collidepoint(mouse_pos):
                            selected_furniture_index = button["index"]
                            selected_furniture_rotation = 0
                            break
                # 3. 게임 영역(배치) 클릭
                elif game_area_rect.collidepoint(mouse_pos):
                    if is_placeable:
                        placed_furniture.append({
                            "item": current_item,
                            "grid_pos": (mouse_grid_x, mouse_grid_y),
                            "rotation": selected_furniture_rotation
                        })
                # 4. 오른쪽 UI 버튼 클릭
                elif right_ui_rect.collidepoint(mouse_pos):
                    if exit_button_rect and exit_button_rect.collidepoint(mouse_pos):
                        running = False

                    elif reroll_customer_button_rect and reroll_customer_button_rect.collidepoint(mouse_pos):
                        print("--- 고객 다시 받기 ---")
                        reset_game(eval=True)

                    elif evaluate_button_rect and evaluate_button_rect.collidepoint(mouse_pos):
                        if not evaluation_result and not is_evaluating:
                            is_evaluating = True
                            run_evaluation_thread() # 함수 호출

                    elif reset_button_rect and reset_button_rect.collidepoint(mouse_pos):
                        reset_game()
            
            if event.button == 3: # 우클릭: 가구 제거
                if not is_evaluating and not show_feedback_popup:
                    if game_area_rect.collidepoint(mouse_pos):
                        sorted_for_click = sorted(placed_furniture, key=lambda f: (f['grid_pos'][1], f['grid_pos'][0]), reverse=True)
                        
                        for f in sorted_for_click:
                            # utils 사용
                            f_size_visual = utils.get_rotated_size(f['item'], f['rotation'])
                            f_rect_base = pygame.Rect(f['grid_pos'][0], f['grid_pos'][1], f_size_visual[0], 1)
                            
                            if f_rect_base.collidepoint(mouse_grid_x, mouse_grid_y):
                                placed_furniture.remove(f)
                                break 

    # ========= 그리기 =========
    
    # 1. 스크린 채우기 (배경)
    screen.fill((255, 255, 255)) 
    pygame.draw.rect(screen, config.RIGHT_UI_BG_COLOR, right_ui_rect)
    pygame.draw.rect(screen, config.BOTTOM_UI_BG_COLOR, bottom_ui_rect)

    # 1.2 게임 영역 그리기 (배경/그리드)
    if global_background_image:
        screen.blit(global_background_image, (0, 0))
    else:
        pygame.draw.rect(screen, (255, 255, 255), game_area_rect)

    for x in range(config.ROOM_WIDTH_GRID + 1):
        pygame.draw.line(screen, config.GRID_LINE_COLOR, (x * config.GRID_SIZE, 0), (x * config.GRID_SIZE, config.GAME_AREA_HEIGHT))
    for y in range(config.ROOM_HEIGHT_GRID + 1):
        pygame.draw.line(screen, config.GRID_LINE_COLOR, (0, y * config.GRID_SIZE), (config.GAME_AREA_WIDTH, y * config.GRID_SIZE))

    # 1.3 문 그리기
    if door_position:
        door_rect_pixels = pygame.Rect(
            door_position[0] * config.GRID_SIZE, 
            door_position[1] * config.GRID_SIZE, 
            config.GRID_SIZE, 
            config.GRID_SIZE
        )
        pygame.draw.rect(screen, config.DOOR_COLOR, door_rect_pixels)
        pygame.draw.rect(screen, (0,0,0), door_rect_pixels, 3)

    # 2. Z-Sorting 및 가구 그리기 (게임 영역)
    render_list = placed_furniture.copy()
    if not is_evaluating and not show_feedback_popup:
        if game_area_rect.collidepoint(mouse_pos):
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

        # --- (수정) 불필요한 인수 제거 ---
        image_to_draw = utils.get_rotated_image(item, rotation)
        
        if furniture.get("is_ghost", False):
            tint_color = (0, 255, 0, 100) if is_placeable else (255, 0, 0, 100)
            ghost_image = image_to_draw.copy()
            tint_surface = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
            tint_surface.fill(tint_color)
            ghost_image.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(ghost_image, (pos_x * config.GRID_SIZE, pos_y * config.GRID_SIZE))
        else:
            screen.blit(image_to_draw, (pos_x * config.GRID_SIZE, pos_y * config.GRID_SIZE))

    # --- 3. 오른쪽 UI 그리기 ---
    ui_y_offset = 10
    screen.blit(font_S.render("R: 회전 / E: 평가", True, (100,100,100)), (config.GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 25
    screen.blit(font_S.render("L-Click: 배치 / R-Click: 제거", True, (100,100,100)), (config.GAME_AREA_WIDTH + 10, ui_y_offset))
    ui_y_offset += 30

    # 종료 버튼
    exit_button_rect = pygame.Rect(config.SCREEN_WIDTH - 70, 10, 60, 30)
    mouse_over_exit = exit_button_rect.collidepoint(mouse_pos)
    exit_btn_color = config.EXIT_BTN_HOVER_COLOR if mouse_over_exit else config.EXIT_BTN_COLOR
    pygame.draw.rect(screen, exit_btn_color, exit_button_rect, border_radius=5)
    exit_text = font_S.render("Exit", True, (255, 255, 255))
    screen.blit(exit_text, exit_text.get_rect(center=exit_button_rect.center))

    # 3.2 페르소나 정보 및 고객 의뢰서
    ui_y_offset += 20 
    pygame.draw.line(screen, (220,220,220), (config.GAME_AREA_WIDTH + 10, ui_y_offset), (config.SCREEN_WIDTH - 20, ui_y_offset), 2)
    ui_y_offset += 15

    if post_it_img:
        post_it_rect = post_it_img.get_rect(topleft=(config.GAME_AREA_WIDTH + 10, ui_y_offset))
        screen.blit(post_it_img, post_it_rect)
        
        text_x = post_it_rect.x + 20
        text_y = post_it_rect.y + 25
        
        persona_name_text = font_Pencil_M.render(current_persona['name'], True, (30,30,30))
        screen.blit(persona_name_text, (text_x, text_y))

        # 고객 다시 받기 버튼
        reroll_btn_x = text_x + persona_name_text.get_width() + 10
        reroll_btn_y = text_y
        if reroll_btn_x + 80 > post_it_rect.right - 20:
             reroll_btn_x = post_it_rect.right - 100
             
        reroll_customer_button_rect = pygame.Rect(reroll_btn_x, reroll_btn_y, 80, 22)
        
        mouse_over_reroll = reroll_customer_button_rect.collidepoint(mouse_pos)
        reroll_btn_color = config.REROLL_BTN_HOVER_COLOR if mouse_over_reroll else config.REROLL_BTN_COLOR
        pygame.draw.rect(screen, reroll_btn_color, reroll_customer_button_rect, border_radius=5)
        
        reroll_text = font_S.render("다시 받기", True, (255, 255, 255))
        reroll_text_rect = reroll_text.get_rect(center=reroll_customer_button_rect.center)
        screen.blit(reroll_text, reroll_text_rect)

        persona_info_str = f"{current_persona['job']}"
        persona_info_text = font_Pencil_M.render(persona_info_str, True, (80, 80, 80))
        screen.blit(persona_info_text, (text_x, text_y + 30))

        request_y_start = text_y + 75
        
        pygame.draw.line(screen, (200,200,200), 
                         (post_it_rect.x + 15, request_y_start - 10), 
                         (post_it_rect.right - 15, request_y_start - 10), 1)
        
        ui_y_offset = draw_text_multiline(
            screen, 
            current_request_text, 
            (text_x, request_y_start + 30),
            font_Pencil_M,
            post_it_rect.width - 40,
            (40, 40, 40)
        )
        ui_y_offset = post_it_rect.bottom

    # 3.3 '디자인 완료' 버튼 또는 '평가 결과'
    ui_y_offset += 20
    
    # 리셋 버튼
    reset_button_rect = pygame.Rect(config.GAME_AREA_WIDTH + 10, ui_y_offset, config.RIGHT_UI_MARGIN - 20, 40)
    mouse_over_reset = reset_button_rect.collidepoint(mouse_pos)
    reset_btn_color = config.RESET_BTN_HOVER_COLOR if mouse_over_reset else config.RESET_BTN_COLOR
    pygame.draw.rect(screen, reset_btn_color, reset_button_rect, border_radius=5)
    reset_text = font_M.render("Reset", True, (255, 255, 255))
    screen.blit(reset_text, reset_text.get_rect(center=reset_button_rect.center))
    
    ui_y_offset += 50 

    if not evaluation_result:
        evaluate_button_rect = pygame.Rect(config.GAME_AREA_WIDTH + 10, ui_y_offset, config.RIGHT_UI_MARGIN - 20, 50)
        mouse_over_button = evaluate_button_rect.collidepoint(mouse_pos)
        
        if is_evaluating:
            button_color = config.EVAL_BTN_DISABLED_COLOR
        else:
            button_color = config.EVAL_BTN_HOVER_COLOR if mouse_over_button else config.EVAL_BTN_COLOR
            
        pygame.draw.rect(screen, button_color, evaluate_button_rect, border_radius=5)
        
        btn_text_str = "Complete (E)"
        if is_evaluating:
            btn_text_str = "평가 중..."
            
        btn_text = font_L.render(btn_text_str, True, (255, 255, 255))
        btn_text_rect = btn_text.get_rect(center=evaluate_button_rect.center)
        screen.blit(btn_text, btn_text_rect)

    # --- 4. 하단 UI 그리기 (가구 목록) ---
    bottom_panel = screen.subsurface(bottom_ui_rect)
    ui_buttons.clear()
    
    for i, item in enumerate(FURNITURE_LIST):
        row = i // 5
        col = i % 5
        
        item_x_pos = (col * config.UI_ITEM_WIDTH) + config.BOTTOM_UI_PADDING_X
        item_y_pos = (row * config.UI_ITEM_HEIGHT) + 10 + ui_scroll_y
        
        button_rect = pygame.Rect(item_x_pos, item_y_pos, config.UI_ITEM_WIDTH - 10, config.UI_ITEM_HEIGHT - 10)
        
        if item_y_pos + config.UI_ITEM_HEIGHT > 0 and item_y_pos < config.BOTTOM_UI_MARGIN:
            
            button_rect_screen = pygame.Rect(item_x_pos, item_y_pos + config.GAME_AREA_HEIGHT, config.UI_ITEM_WIDTH - 10, config.UI_ITEM_HEIGHT - 10)
            ui_buttons.append({"index": i, "rect_screen": button_rect_screen})
            
            button_color = (150, 255, 150) if i == selected_furniture_index else (220, 220, 220)
            pygame.draw.rect(bottom_panel, button_color, button_rect, border_radius=5)

            try:
                thumb_h = 50
                thumb_w = 50
                thumb_img = pygame.transform.smoothscale(item["image"], (thumb_w, thumb_h))
                bottom_panel.blit(thumb_img, (item_x_pos + 10, item_y_pos + 5))
            except Exception as e:
                print(f"썸네일 생성 오류: {e}")
            
            name_x_pos = item_x_pos + 70
            bottom_panel.blit(font_M.render(item['name'], True, (0,0,0)), (name_x_pos + 20, item_y_pos + 20))

    # --- 5. 오버레이 그리기 (로딩 / 피드백 팝업) ---
    if is_evaluating or show_feedback_popup:
        dim_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surface.fill((0, 0, 0, 180))
        screen.blit(dim_surface, (0, 0))

    if is_evaluating:
        center_x, center_y = config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2
        loading_text = font_L.render("피드백 생성 중...", True, (255, 255, 255))
        loading_rect = loading_text.get_rect(center=(center_x, center_y))
        screen.blit(loading_text, loading_rect)
        
    elif show_feedback_popup:
        if evaluation_result:
            
            if not is_feedback_hidden:
                popup_width = max(400, config.SCREEN_WIDTH // 2)
                popup_height = max(500, config.SCREEN_HEIGHT - 100)
                popup_rect = pygame.Rect(0, 0, popup_width, popup_height)
                popup_rect.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
            
                popup_bg_color = (250, 248, 240)
                popup_border_radius = 15
                pygame.draw.rect(screen, popup_bg_color, popup_rect, border_radius=popup_border_radius)
                
                inner_x = popup_rect.x + 40
                inner_y = popup_rect.y + 40
                inner_width = popup_rect.width - 80

                title_text = font_L.render("고객 피드백", True, (0, 0, 0))
                screen.blit(title_text, (inner_x, inner_y))
                
                if star_full_img and star_half_img and star_empty_img:
                    draw_star_rating(
                        screen, 
                        evaluation_result['score'], 
                        (inner_x, inner_y + 50),
                        star_full_img, star_half_img, star_empty_img
                    )
                else:
                    score_str = f"Score: {evaluation_result['score']:.1f} / 5.0"
                    screen.blit(font_L.render(score_str, True, (0, 100, 0)), (inner_x, inner_y + 50))

                draw_text_multiline(
                    screen,
                    evaluation_result['feedback'],
                    (inner_x, inner_y + 100),
                    font_Pencil_M, 
                    inner_width, 
                    (40, 40, 40) 
                )

                popup_close_button_rect = pygame.Rect(popup_rect.centerx - 50, popup_rect.bottom - 70, 100, 40)
                mouse_over_close = popup_close_button_rect.collidepoint(mouse_pos)
                close_btn_color = config.POPUP_CLOSE_BTN_HOVER_COLOR if mouse_over_close else config.POPUP_CLOSE_BTN_COLOR
                
                pygame.draw.rect(screen, close_btn_color, popup_close_button_rect, border_radius=5)
                close_text = font_M.render("닫기", True, (255, 255, 255))
                screen.blit(close_text, close_text.get_rect(center=popup_close_button_rect.center))

            # (신규) 3.6 숨기기/보기 토글 버튼 (항상 표시)
            if not is_feedback_hidden:
                toggle_btn_y_pos = popup_rect.bottom - 70 - 50
                toggle_btn_center_x = popup_rect.centerx
                toggle_text_str = "숨기기"
            else:
                popup_width = max(400, config.SCREEN_WIDTH // 2)
                popup_height = max(500, config.SCREEN_HEIGHT - 100)
                popup_rect = pygame.Rect(0, 0, popup_width, popup_height)
                popup_rect.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
                toggle_btn_y_pos = popup_rect.bottom - 70
                toggle_btn_center_x = popup_rect.centerx
                toggle_text_str = "피드백 보기"

            popup_toggle_button_rect = pygame.Rect(0, 0, 120, 40)
            popup_toggle_button_rect.center = (toggle_btn_center_x, toggle_btn_y_pos)
            
            mouse_over_toggle = popup_toggle_button_rect.collidepoint(mouse_pos)
            toggle_btn_color = config.POPUP_TOGGLE_BTN_HOVER_COLOR if mouse_over_toggle else config.POPUP_TOGGLE_BTN_COLOR
            pygame.draw.rect(screen, toggle_btn_color, popup_toggle_button_rect, border_radius=5)
            
            toggle_text = font_M.render(toggle_text_str, True, (255, 255, 255))
            screen.blit(toggle_text, toggle_text.get_rect(center=popup_toggle_button_rect.center))
            
    # --- 업데이트 ---
    pygame.display.flip()

pygame.quit()
sys.exit()