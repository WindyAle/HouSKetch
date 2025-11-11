import pygame
import sys
import threading

# 프로젝트 모듈 임포트
from . import client
from .model import ModelManager
from templates import furnitures
import config

# ========= 리소스 로딩 스레드 함수 =========
def load_game_resources(results_dict, completion_event, progress_tracker):
    """
    (백그라운드 스레드) 모든 무거운 리소스(이미지, 모델)를 로드합니다.
    """
    try:
        total_steps = 5 # 총 5단계 작업
        progress_tracker["total_steps"] = total_steps
        
        # 1. 가구 이미지 로드
        progress_tracker["status"] = "가구 에셋 로드 중..."
        results_dict['FURNITURE_LIST'] = furnitures.load_furniture_data(config.GRID_SIZE)
        progress_tracker["step"] = 1
        
        # 2. 배경 이미지 로드
        progress_tracker["status"] = "배경 이미지 로드 중..."
        background_image = pygame.image.load(config.BACKGROUND_IMAGE_PATH).convert()
        results_dict['background_image'] = pygame.transform.scale(background_image, (config.GAME_AREA_WIDTH, config.GAME_AREA_HEIGHT))
        progress_tracker["step"] = 2
        
        # 3. 모델 매니저 초기화 (가장 오래 걸리는 작업)
        progress_tracker["status"] = "AI 모델 서버에 연결 중... (Ollama)"
        model_manager = ModelManager()
        results_dict['model_manager'] = model_manager
        progress_tracker["step"] = 3

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
        results_dict['FURNITURE_LIST'] = results_dict.get('FURNITURE_LIST') or furnitures.load_furniture_data(config.GRID_SIZE)
        if 'background_image' not in results_dict:
             results_dict['background_image'] = None # 배경 로드 실패
        results_dict['model_manager'] = None
        persona, wishlist, request_text = client.generate_request(None)
        results_dict['current_persona'] = persona
        results_dict['request_text'] = request_text
        results_dict['request_embedding'] = [0.1] * 128
    finally:
        # 메인 스레드에 로딩 완료 신호 전송
        completion_event.set()

# ========= 로딩 스크린 함수 =========
def run_loading_screen(screen, clock, font_l, font_m):
    """
    (메인 스레드) 'background.png' 배경과 'start_button.png'를 사용하는
    새로운 로딩 스크린을 실행합니다.
    """
    
    # --- 1. 로딩 스크린 자체 에셋 로드 ---
    try:
        loading_bg_image = pygame.image.load(config.LOADING_BG_PATH).convert()
        loading_bg_image = pygame.transform.scale(loading_bg_image, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    except Exception as e:
        print(f"로딩 배경 로드 실패 (background.png): {e}")
        loading_bg_image = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        loading_bg_image.fill((255, 255, 255)) # 흰색으로 대체

    try:
        start_button_image = pygame.image.load(config.START_BUTTON_PATH).convert_alpha()
        start_button_image = pygame.transform.scale(start_button_image, (350, 145))
    except Exception as e:
        print(f"시작 버튼 로드 실패 (start_button.png): {e}")
        start_button_image = pygame.Surface((200, 80), pygame.SRCALPHA)
        start_button_image.fill((0, 200, 0, 150)) # 임시 녹색 버튼
        # 임시 버튼에 텍스트 그리기
        temp_text = font_l.render("START", True, (255, 255, 255))
        temp_rect = temp_text.get_rect(center=start_button_image.get_rect().center)
        start_button_image.blit(temp_text, temp_rect)

    # --- 2. 리소스 로딩 스레드 시작 ---
    loading_results = {}
    loading_complete_event = threading.Event()
    progress_tracker = {"step": 0, "total_steps": 5, "status": "초기화 중..."}
    
    loader_thread = threading.Thread(
        target=load_game_resources, 
        args=(
            loading_results, 
            loading_complete_event, 
            progress_tracker,
        )
    )
    loader_thread.start()
    
    # --- 3. UI 위치 계산 (하단) ---
    bar_width = 400
    bar_height = 30
    bar_x = (config.SCREEN_WIDTH - bar_width) // 2
    bar_y = config.SCREEN_HEIGHT - 100 # (수정) 화면 하단으로 이동
    
    # 시작 버튼 위치 (로딩 바와 동일한 위치)
    start_button_rect = start_button_image.get_rect(center=(config.SCREEN_WIDTH // 2, bar_y + bar_height // 2))

    # --- 4. 로딩 루프 (상태 관리) ---
    current_progress = 0.0 
    target_progress = 0.0 
    is_fully_loaded = False # (신규) 로딩 완료 상태
    
    running_loading_screen = True
    while running_loading_screen:
        
        # (신규) 스레드가 완료되었는지 확인
        if not is_fully_loaded and loading_complete_event.is_set():
            is_fully_loaded = True
            current_progress = 1.0 # 100%로 강제
            progress_tracker["status"] = "로드 완료! 시작 버튼을 누르세요."

        # --- 이벤트 처리 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # (신규) 로딩 완료 후 시작 버튼 클릭 감지
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if is_fully_loaded:
                    if start_button_rect.collidepoint(event.pos):
                        running_loading_screen = False # 루프 종료

        # --- 그리기 ---
        # 1. 배경 이미지
        screen.blit(loading_bg_image, (0, 0))
        
        if is_fully_loaded:
            # 2a. 로딩 완료: 시작 버튼 표시
            screen.blit(start_button_image, start_button_rect)
            
        else:
            # 2b. 로딩 중: 로딩 바 표시
            target_progress = progress_tracker["step"] / progress_tracker["total_steps"]
            if current_progress < target_progress:
                current_progress += 0.01 
                if current_progress > target_progress:
                    current_progress = target_progress
            
            # 로딩 바 (배경)
            pygame.draw.rect(screen, (50, 50, 50, 200), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
            
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
        
    loader_thread.join() # 스레드가 종료될 때까지 대기
    return loading_results