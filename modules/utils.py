import pygame
import random

import config

# --- 헬퍼 함수 (문 생성) ---
def create_new_door(config):
    """벽면(모서리 제외)에 무작위로 문 위치를 생성합니다."""
    side = random.choice(['top', 'bottom', 'left', 'right'])
    
    if side == 'top':
        x = random.randint(1, config.ROOM_WIDTH_GRID - 1)
        y = 0
    elif side == 'bottom':
        x = random.randint(1, config.ROOM_WIDTH_GRID - 1)
        y = config.ROOM_HEIGHT_GRID - 1
    elif side == 'left':
        x = 0
        y = random.randint(1, config.ROOM_HEIGHT_GRID - 1)
    else: # 'right'
        x = config.ROOM_WIDTH_GRID - 1
        y = random.randint(1, config.ROOM_HEIGHT_GRID - 1)
        
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
        rotated_pixel_size = (rotated_size_grid[0] * config.GRID_SIZE, rotated_size_grid[1] * config.GRID_SIZE)
        return pygame.transform.scale(rotated_image, rotated_pixel_size)

def check_collision(new_item, new_pos, new_rot, placed_furniture, door_position):
    """(수정) 충돌 판정은 '바닥 격자'(높이 1)만 검사합니다."""
    # 가구의 시각적(화면에 표시되는) 크기
    new_size_visual = get_rotated_size(new_item, new_rot)
    new_rect_full = pygame.Rect(new_pos[0], new_pos[1], new_size_visual[0], new_size_visual[1])
    # 1. 방 경계 확인
    if new_rect_full.left < 0 or new_rect_full.top < 0 or \
       new_rect_full.right > config.ROOM_WIDTH_GRID or new_rect_full.bottom > config.ROOM_HEIGHT_GRID:
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