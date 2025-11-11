import pygame

def load_scaled_image(path, size_grid, grid_size):
    """
    가구의 이미지를 로드하고 스케일링합니다.
    이 함수는 pygame.init() 이후에 호출되어야 합니다.
    """
    try:
        image = pygame.image.load(path).convert_alpha()
        # 격자 크기에 맞게 이미지 스케일 조정
        scaled_size = (size_grid[0] * grid_size, size_grid[1] * grid_size)
        return pygame.transform.scale(image, scaled_size)
    except FileNotFoundError:
        print(f"이미지 로드 실패: {path}")
        # 실패 시 빈 Surface 생성
        fallback_surface = pygame.Surface((size_grid[0] * grid_size, size_grid[1] * grid_size), pygame.SRCALPHA)
        fallback_surface.fill((255, 0, 255, 100)) # 오류 시 분홍색 투명 사각형
        return fallback_surface
    except pygame.error as e:
        print(f"Pygame 오류 (이미지 로드): {e}")
        return None

def load_furniture_data(grid_size):
    """
    모든 가구 데이터를 로드하고 이미지 Surface를 생성하여 반환합니다.
    """
    FURNITURE_LIST = [
        {
            "name": "작은 소파",
            "size": (2, 1), # 격자 2x1 크기
            "image_path": "assets/furnitures/sofa.png",
            "image": load_scaled_image("assets/furnitures/sofa.png", (2, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "큰 소파",
            "size": (3, 1),
            "image_path": "assets/furnitures/sofa_long.png",
            "image": load_scaled_image("assets/furnitures/sofa_long.png", (3, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "테이블",
            "size": (1, 1),
            "image_path": "assets/furnitures/table.png",
            "image": load_scaled_image("assets/furnitures/table.png", (1, 1), grid_size),
            "color": (150, 100, 30)
        },
        {
            "name": "식탁",
            "size": (2, 1),
            "image_path": "assets/furnitures/table_long.png",
            "image": load_scaled_image("assets/furnitures/table_long.png", (2, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "벽난로",
            "size": (2, 2),
            "image_path": "assets/furnitures/fire.png",
            "image": load_scaled_image("assets/furnitures/fire.png", (2, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "2인 침대",
            "size": (2, 3),
            "image_path": "assets/furnitures/bed_double.png",
            "image": load_scaled_image("assets/furnitures/bed_double.png", (2, 3), grid_size), # (오류 수정)
            "color": (50, 50, 120)
        },
        {
            "name": "1인 침대",
            "size": (1, 3),
            "image_path": "assets/furnitures/bed_single.png",
            "image": load_scaled_image("assets/furnitures/bed_single.png", (1, 3), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "화분",
            "size": (1, 2),
            "image_path": "assets/furnitures/plant.png",
            "image": load_scaled_image("assets/furnitures/plant.png", (1, 2), grid_size),
            "color": (30, 100, 30)
        },
        {
            "name": "책장",
            "size": (2, 2),
            "image_path": "assets/furnitures/bookshelf.png",
            "image": load_scaled_image("assets/furnitures/bookshelf.png", (2, 2), grid_size),
            "color": (30, 100, 30)
        },
        {
            "name": "옷장",
            "size": (2, 3),
            "image_path": "assets/furnitures/closet.png",
            "image": load_scaled_image("assets/furnitures/closet.png", (2, 3), grid_size),
            "color": (30, 100, 30)
        },
        {
            "name": "탁자",
            "size": (1, 1),
            "image_path": "assets/furnitures/console.png",
            "image": load_scaled_image("assets/furnitures/console.png", (1, 1), grid_size),
            "color": (30, 100, 30)
        },    
        {
            "name": "컴퓨터",
            "size": (2, 2),
            "image_path": "assets/furnitures/desk.png",
            "image": load_scaled_image("assets/furnitures/desk.png", (2, 2), grid_size),
            "color": (30, 100, 30)
        },  
        {
            "name": "전등",
            "size": (1, 2),
            "image_path": "assets/furnitures/ramp.png",
            "image": load_scaled_image("assets/furnitures/ramp.png", (1, 2), grid_size),
            "color": (30, 100, 30)
        },
        {
            "name": "선반",
            "size": (2, 2),
            "image_path": "assets/furnitures/shelf.png",
            "image": load_scaled_image("assets/furnitures/shelf.png", (2, 2), grid_size),
            "color": (30, 100, 30)
        },
        {
            "name": "시계",
            "size": (1, 2),
            "image_path": "assets/furnitures/clock.png",
            "image": load_scaled_image("assets/furnitures/clock.png", (1, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "옷걸이",
            "size": (1, 2),
            "image_path": "assets/furnitures/hanger.png",
            "image": load_scaled_image("assets/furnitures/hanger.png", (1, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "다리미판",
            "size": (1, 1),
            "image_path": "assets/furnitures/iron_plate.png",
            "image": load_scaled_image("assets/furnitures/iron_plate.png", (1, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "거울",
            "size": (1, 2),
            "image_path": "assets/furnitures/mirror.png",
            "image": load_scaled_image("assets/furnitures/mirror.png", (1, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "냉장고",
            "size": (1, 2),
            "image_path": "assets/furnitures/refridge.png",
            "image": load_scaled_image("assets/furnitures/refridge.png", (1, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "스토브",
            "size": (2, 2),
            "image_path": "assets/furnitures/stove.png",
            "image": load_scaled_image("assets/furnitures/stove.png", (2, 2), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "변기",
            "size": (1, 1),
            "image_path": "assets/furnitures/toilet.png",
            "image": load_scaled_image("assets/furnitures/toilet.png", (1, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
        {
            "name": "욕조",
            "size": (2, 1),
            "image_path": "assets/furnitures/bath.png",
            "image": load_scaled_image("assets/furnitures/bath.png", (2, 1), grid_size),
            "color": (120, 50, 50) # (평가용 임시 색상)
        },
    ]
    
    # 이미지 로드에 실패한 아이템 제거
    FURNITURE_LIST = [item for item in FURNITURE_LIST if item["image"] is not None]
    
    return FURNITURE_LIST

