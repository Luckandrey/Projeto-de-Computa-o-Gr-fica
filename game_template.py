import pygame
import sys
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# ==========================================
# DADOS DAS FASES (LEVEL DESIGN)
# ==========================================
# Aqui você define a planta baixa de cada planeta.
# '#' = Parede, '.' = Corredor/Vazio, 'P' = Spawn do Jogador, 'C' = Computador (futuro)
LEVELS = {
    "Tau Ceti IV": [
        "##########",
        "#P.......#",
        "####..####",
        "#........#",
        "#.######.#",
        "#......C.#",
        "##########"
    ],
    "DEFAULT": [
        "######",
        "#P...#",
        "######"
    ]
}

BLOCK_SIZE = 4.0  # Tamanho de cada bloco (parede/corredor) no mundo 3D
WALL_HEIGHT = 4.0 # Altura das paredes

# ==========================================
# FUNÇÕES DE RENDERIZAÇÃO DO AMBIENTE
# ==========================================
def draw_cube(x, y, z, size, height):
    half = size / 2.0
    
    glBegin(GL_QUADS)
    # Cor da parede (Cinza escuro esverdeado, estilo alien/sci-fi)
    glColor3f(0.15, 0.2, 0.15)
    
    # Frente (Z+)
    glVertex3f(x - half, y,          z + half)
    glVertex3f(x + half, y,          z + half)
    glVertex3f(x + half, y + height, z + half)
    glVertex3f(x - half, y + height, z + half)
    
    # Trás (Z-)
    glVertex3f(x - half, y,          z - half)
    glVertex3f(x - half, y + height, z - half)
    glVertex3f(x + half, y + height, z - half)
    glVertex3f(x + half, y,          z - half)
    
    # Esquerda (X-)
    glVertex3f(x - half, y,          z - half)
    glVertex3f(x - half, y,          z + half)
    glVertex3f(x - half, y + height, z + half)
    glVertex3f(x - half, y + height, z - half)
    
    # Direita (X+)
    glVertex3f(x + half, y,          z - half)
    glVertex3f(x + half, y + height, z - half)
    glVertex3f(x + half, y + height, z + half)
    glVertex3f(x + half, y,          z + half)
    glEnd()

def draw_floor_and_ceiling(level_map):
    rows = len(level_map)
    cols = len(level_map[0])
    
    width = cols * BLOCK_SIZE
    depth = rows * BLOCK_SIZE
    
    # Ponto inicial ajustado para o centro do primeiro bloco
    start_x = -BLOCK_SIZE / 2.0
    start_z = -BLOCK_SIZE / 2.0
    
    glBegin(GL_QUADS)
    # Chão
    glColor3f(0.1, 0.1, 0.1)
    glVertex3f(start_x,         0.0, start_z)
    glVertex3f(start_x + width, 0.0, start_z)
    glVertex3f(start_x + width, 0.0, start_z + depth)
    glVertex3f(start_x,         0.0, start_z + depth)
    
    # Teto
    glColor3f(0.05, 0.05, 0.05)
    glVertex3f(start_x,         WALL_HEIGHT, start_z)
    glVertex3f(start_x,         WALL_HEIGHT, start_z + depth)
    glVertex3f(start_x + width, WALL_HEIGHT, start_z + depth)
    glVertex3f(start_x + width, WALL_HEIGHT, start_z)
    glEnd()

# ==========================================
# SISTEMA DE FÍSICA E COLISÃO
# ==========================================
def is_wall(x, z, level_map):
    # Arredonda a posição 3D para o índice (coluna e linha) da matriz
    col = int(round(x / BLOCK_SIZE))
    row = int(round(z / BLOCK_SIZE))
    
    # Evita que o jogo quebre se o jogador sair dos limites do mapa
    if row < 0 or row >= len(level_map) or col < 0 or col >= len(level_map[0]):
        return True
        
    return level_map[row][col] == '#'

# ==========================================
# INICIALIZAÇÃO DA CÂMERA (FPS)
# ==========================================
def init_opengl_fps(width, height):
    glViewport(0, 0, int(width), int(height))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, (width / height), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    
    # Desliga transparências antigas do hub para evitar bugs de renderização nas paredes
    glDisable(GL_BLEND)

# ==========================================
# LOOP PRINCIPAL DO MOTOR (ENGINE)
# ==========================================
def start(planet_name):
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    
    # Garante que o contexto OpenGL está limpo e focado
    pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    
    init_opengl_fps(screen_width, screen_height)
    
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    clock = pygame.time.Clock()
    FPS = 60

    # 1. CARREGAMENTO DO MAPA
    # Busca o mapa do planeta no dicionário, se não achar, carrega o DEFAULT
    current_map = LEVELS.get(planet_name, LEVELS["DEFAULT"])
    
    # 2. VARIÁVEIS DO JOGADOR
    cam_x, cam_y, cam_z = 0.0, 2.0, 0.0  # y=2.0 é a altura dos olhos
    yaw = 0.0   
    pitch = 0.0 
    
    mouse_sensitivity = 0.15
    move_speed = 0.15
    player_radius = 0.5 # Tamanho do "corpo" do jogador para colisão não ficar muito justa na parede

    # Encontra o 'P' (Spawn) no mapa para colocar a câmera lá
    for row_index, row_string in enumerate(current_map):
        for col_index, char in enumerate(row_string):
            if char == 'P':
                cam_x = col_index * BLOCK_SIZE
                cam_z = row_index * BLOCK_SIZE

    running = True
    result_state = "MENU" # O que será retornado ao Hub

    while running:
        # --- A. EVENTOS ---
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False # Encerra o loop e volta pro Hub

        # --- B. OLHAR (MOUSE) ---
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        yaw += mouse_dx * mouse_sensitivity
        pitch += mouse_dy * mouse_sensitivity
        
        if pitch > 89.0: pitch = 89.0
        if pitch < -89.0: pitch = -89.0

        # --- C. MOVIMENTO E COLISÃO (WASD) ---
        keys = pygame.key.get_pressed()
        yaw_rad = math.radians(yaw)
        
        # Vetores de direção matemática
        front_x = math.sin(yaw_rad)
        front_z = -math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)

        # Variáveis temporárias para testar a colisão antes de mover a câmera oficial
        next_x = cam_x
        next_z = cam_z

        if keys[K_w]:
            next_x += front_x * move_speed
            next_z += front_z * move_speed
        if keys[K_s]:
            next_x -= front_x * move_speed
            next_z -= front_z * move_speed
        if keys[K_a]:
            next_x -= right_x * move_speed
            next_z -= right_z * move_speed
        if keys[K_d]:
            next_x += right_x * move_speed
            next_z += right_z * move_speed

        # Verificação de Colisão Eixo por Eixo (Permite deslizar na parede)
        # Testa o eixo X
        if not is_wall(next_x + (player_radius if next_x > cam_x else -player_radius), cam_z, current_map):
            cam_x = next_x
            
        # Testa o eixo Z
        if not is_wall(cam_x, next_z + (player_radius if next_z > cam_z else -player_radius), current_map):
            cam_z = next_z

        # --- D. RENDERIZAÇÃO ---
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Rotaciona a câmera (inverso da visão)
        glRotatef(pitch, 1, 0, 0) 
        glRotatef(yaw, 0, 1, 0)   
        # Move a câmera (inverso da posição)
        glTranslatef(-cam_x, -cam_y, -cam_z)

        # 1. Desenha o chão e teto globais
        draw_floor_and_ceiling(current_map)

        # 2. Percorre a matriz e desenha uma parede 3D onde houver um '#'
        for row_index, row_string in enumerate(current_map):
            for col_index, char in enumerate(row_string):
                if char == '#':
                    block_x = col_index * BLOCK_SIZE
                    block_z = row_index * BLOCK_SIZE
                    draw_cube(block_x, 0, block_z, BLOCK_SIZE, WALL_HEIGHT)
                
                # if char == 'C':
                #   futuramente chamaremos um draw_computer() aqui

        pygame.display.flip()
        clock.tick(FPS)

    return result_state

if __name__ == "__main__":
    pygame.init()
    start("Terra")