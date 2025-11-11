# ========= 기본 설정 =========
GRID_SIZE = 72       # 각 격자 크기
ROOM_WIDTH_GRID = 10 # 가로 칸 수
ROOM_HEIGHT_GRID = 8 # 세로 칸 수

# ========= 레이아웃 상수 =========
GAME_AREA_WIDTH = ROOM_WIDTH_GRID * GRID_SIZE    # 720
GAME_AREA_HEIGHT = ROOM_HEIGHT_GRID * GRID_SIZE  # 576

RIGHT_UI_MARGIN = 300  # 오른쪽 UI 패널 너비
BOTTOM_UI_MARGIN = 170 # 하단 UI 패널 높이

SCREEN_WIDTH = GAME_AREA_WIDTH + RIGHT_UI_MARGIN    # 1020
SCREEN_HEIGHT = GAME_AREA_HEIGHT + BOTTOM_UI_MARGIN # 746

# ========= 폰트 경로 =========
FONT_PATH = "assets/font/NanumGothic-Regular.ttf"
PENCIL_FONT_PATH = "assets/font/MaplestoryLight.ttf"

# ========= 이미지 경로 =========
BACKGROUND_IMAGE_PATH = "assets/wood_floor.png"
LOADING_BG_PATH = "assets/background.png"
START_BUTTON_PATH = "assets/start_button.png"
POST_IT_PATH = "assets/post.png"
STAR_FULL_PATH = "assets/star.png"
STAR_HALF_PATH = "assets/star_half.png"
STAR_EMPTY_PATH = "assets/star_empty.png"

# ========= 색상 =========
DOOR_COLOR = (101, 67, 33) # 문 색: 짙은 갈색
GRID_LINE_COLOR = (197, 150, 94, 50) # 그리드 선 색상
RIGHT_UI_BG_COLOR = (250, 248, 240)
BOTTOM_UI_BG_COLOR = (240, 240, 240)
RESET_BTN_COLOR = (200, 80, 80)
RESET_BTN_HOVER_COLOR = (255, 100, 100)
EXIT_BTN_COLOR = (200, 80, 80)
EXIT_BTN_HOVER_COLOR = (255, 100, 100)

# ========= 하단 UI (가구 목록) =========
UI_ITEM_WIDTH = 180 # 각 가구 목록 아이템의 너비
UI_ITEM_HEIGHT = 80 # 각 가구 목록 아이템의 높이

# 5열 배치를 위한 좌우 여백 계산
TOTAL_ITEMS_WIDTH = 5 * UI_ITEM_WIDTH
BOTTOM_UI_PADDING_X = (SCREEN_WIDTH - TOTAL_ITEMS_WIDTH) // 2 # (1020 - 900) / 2 = 60

# ========= 오른쪽 UI (고객) =========
REROLL_BTN_COLOR = (100, 100, 100)
REROLL_BTN_HOVER_COLOR = (130, 130, 130)
EVAL_BTN_COLOR = (0, 150, 0)
EVAL_BTN_HOVER_COLOR = (0, 180, 0)
EVAL_BTN_DISABLED_COLOR = (100, 100, 100)
STAR_SIZE = (28, 28)

# ========= 팝업 =========
POPUP_TOGGLE_BTN_COLOR = (100, 100, 100)
POPUP_TOGGLE_BTN_HOVER_COLOR = (130, 130, 130)
POPUP_CLOSE_BTN_COLOR = (150, 0, 0)
POPUP_CLOSE_BTN_HOVER_COLOR = (180, 0, 0)