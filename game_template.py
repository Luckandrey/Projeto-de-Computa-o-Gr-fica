import pygame
import sys
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from core.renderer import draw_cube, draw_floor_tile, draw_u_stairs, draw_computer
from core.physics_engine import (BLOCK_SIZE, WALL_HEIGHT, is_wall, 
                                 has_ramp_below, get_target_y)

# iniciando uma "câmera" em primeira pessoa
def init_opengl_fps(width, height):
    glViewport(0, 0, int(width), int(height))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, (width / height), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    
    # desliga transparências antigas do hub para evitar bugs de renderização nas paredes
    glDisable(GL_BLEND)

# loop principal
def start(planet):
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    
    # garante que o contexto OpenGL está limpo e focado
    pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    
    init_opengl_fps(screen_width, screen_height)
    
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    clock = pygame.time.Clock()
    FPS = 60

    current_map = planet.layout
    
    # encontra o '@' (spawn) varrendo a matriz 3D
    for y_index, andar in enumerate(current_map):
        for z_index, linha in enumerate(andar):
            for x_index, char in enumerate(linha):
                if char == '@':
                    cam_x = x_index * BLOCK_SIZE
                    cam_y = (y_index * WALL_HEIGHT) + 2.0 # altura da câmera baseada no andar
                    cam_z = z_index * BLOCK_SIZE
    
    # cria a variável de altura lógica copiando a altura inicial
    player_y = cam_y

    yaw = 0.0   
    pitch = 0.0 
    
    mouse_sensitivity = 0.15
    move_speed = 0.15
    player_radius = 0.5 # tamanho do "corpo" do jogador para colisão não ficar muito justa na parede

    running = True
    result_state = "MENU" # q que será retornado ao hub (vitória, quit, derrota)

    while running:
        # leitor de eventos
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False # encerra o loop e volta pro Hub

        # movimento do mouse na câmera
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        yaw += mouse_dx * mouse_sensitivity
        pitch += mouse_dy * mouse_sensitivity
        
        if pitch > 89.0: pitch = 89.0
        if pitch < -89.0: pitch = -89.0

        # movimento do teclado e colisão
        keys = pygame.key.get_pressed()
        yaw_rad = math.radians(yaw)
        
        # vetores de direção matemática
        front_x = math.sin(yaw_rad)
        front_z = -math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)

        # variáveis temporárias para testar a colisão antes de mover a câmera oficial
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

        # verificação de colisão eixo por eixo (permite andar encostado na parede)
        # testa o eixo X
        if not is_wall(next_x + (player_radius if next_x > cam_x else -player_radius), player_y, cam_z, current_map):
            cam_x = next_x
            
        # testa o eixo Z
        if not is_wall(cam_x, player_y, next_z + (player_radius if next_z > cam_z else -player_radius), current_map):
            cam_z = next_z

        # aplicação da lógica usada nas escadas e na gravidade
        player_y = get_target_y(cam_x, player_y, cam_z, current_map)
        
        # a câmera visual persegue a física real suavemente (cálculos ficam divididos da visão)
        cam_y += (player_y - cam_y) * 0.15

        # renderização
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glRotatef(pitch, 1, 0, 0) 
        glRotatef(yaw, 0, 1, 0)   
        glTranslatef(-cam_x, -cam_y, -cam_z)

        # percorre a matriz 3D de layout do mapa
        for y_index, andar in enumerate(current_map):
            for z_index, linha in enumerate(andar):
                for x_index, char in enumerate(linha):
                    
                    # ignora espaço vazio
                    if char == ' ':
                        continue

                    block_x = x_index * BLOCK_SIZE
                    block_y = y_index * WALL_HEIGHT
                    block_z = z_index * BLOCK_SIZE

                    # renderização do chão
                    # mas se não houver uma rampa no bloco exatamente abaixo
                    if not has_ramp_below(y_index, z_index, x_index, current_map):
                        draw_floor_tile(block_x, block_y, block_z, BLOCK_SIZE)

                    # renderização da parede
                    if char == 'P':
                        draw_cube(block_x, block_y, block_z, BLOCK_SIZE, WALL_HEIGHT)

                    # TODO: draw_cube com textura transparente de vidro
                    elif char == 'V':
                        pass
                    
                    # renderização da escada
                    # passamos o 'char' (a direção) para orientar a escada
                    elif char in ['<', '>', '^', 'v']:
                        draw_u_stairs(block_x, block_y, block_z, BLOCK_SIZE, WALL_HEIGHT, char)

                    elif char == 'M':
                        draw_computer(block_x, block_y, block_z, BLOCK_SIZE, WALL_HEIGHT)

        pygame.display.flip()
        clock.tick(FPS)

    return result_state