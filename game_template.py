import os
import pygame
import sys
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *


from core.renderer import draw_cube, draw_floor_tile, draw_u_stairs, draw_computer
from core.physics_engine import (BLOCK_SIZE, WALL_HEIGHT, is_wall, 
                                 has_ramp_below, get_target_y)
from core.ui import Button, Title
import core.save_manager as save_manager

# configura o OpenGL para desenhar em pixels (2D)
def prepare_2d(width, height):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, height, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

# restaura o OpenGL para o modo perspectiva (3D)
def prepare_3d():
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

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
def start(planet, saved_state=None):
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
    spawn_x, spawn_y, spawn_z = 0, 0, 0
    for y_index, andar in enumerate(current_map):
        for z_index, linha in enumerate(andar):
            for x_index, char in enumerate(linha):
                if char == '@':
                    spawn_x = x_index * BLOCK_SIZE
                    spawn_y = (y_index * WALL_HEIGHT) + 2.0 # altura da câmera baseada no andar
                    spawn_z = z_index * BLOCK_SIZE
                    
    # Verificação de posição inicial: Se tiver save state, aplica as coordenadas dele. Senão, vai no spawn padrao
    if saved_state:
        cam_x = saved_state['cam_x']
        cam_y = saved_state['cam_y']
        cam_z = saved_state['cam_z']
        player_y = saved_state['player_y']
        yaw = saved_state['yaw']
        pitch = saved_state['pitch']
    else:
        cam_x, cam_y, cam_z = spawn_x, spawn_y, spawn_z
        player_y = cam_y
        yaw = 0.0   
        pitch = 0.0 
    
    mouse_sensitivity = 0.15
    move_speed = 0.15
    player_radius = 0.5 # tamanho do "corpo" do jogador para colisão não ficar muito justa na parede

    pygame.font.init()
    
    script_path = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_path, 'Assets', 'Fonts', 'united-sans-reg-bold.otf')
    
    fonte_botao = pygame.font.Font(font_path, 28)
    fonte_titulo = pygame.font.SysFont('Arial', 72, bold=True)

    button_color = (0, 0, 0, 0)
    font_button_color = (95, 198, 139, 255)
    hover_button_color = (95, 198, 139, 150)

    title_pause = Title(
        screen_width // 2 - 300, screen_height // 2 - 200, 600, 100,
        "PAUSADO", fonte_titulo, bg_color=(0, 0, 0, 0),
        text_color=(255, 255, 255, 255), align="center"
    )

    running = True
    is_paused = False
    result_state = "MENU"

    def cb_continuar():
        nonlocal is_paused
        is_paused = False
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()
        
    def cb_salvar_jogo():
        save_manager.save_level_state(cam_x, cam_y, cam_z, player_y, yaw, pitch, planet.name)
        # Retorna ao jogo logo em seguida para um fluxo suave
        cb_continuar()
        
    def cb_carregar_jogo():
        nonlocal running, result_state
        result_state = "LOAD_GAME"
        running = False

    def cb_voltar_menu():
        nonlocal running, result_state
        result_state = "MENU"
        running = False
        
    def cb_sair_desktop():
        pygame.quit()
        sys.exit()

    btn_continue = Button(
        screen_width // 2 - 200, screen_height // 2 - 120, 450, 50, "CONTINUAR",
        fonte_botao, cb_continuar, base_color=button_color,
        hover_color=hover_button_color, text_color=font_button_color
    )
    btn_save_game = Button(
        screen_width // 2 - 200, screen_height // 2 - 50, 450, 50, "SALVAR JOGO",
        fonte_botao, cb_salvar_jogo, base_color=button_color,
        hover_color=hover_button_color, text_color=font_button_color
    )
    btn_load_game = Button(
        screen_width // 2 - 200, screen_height // 2 + 20, 450, 50, "CARREGAR JOGO",
        fonte_botao, cb_carregar_jogo, base_color=button_color,
        hover_color=hover_button_color, text_color=font_button_color
    )
    btn_back_menu = Button(
        screen_width // 2 - 200, screen_height // 2 + 90, 450, 50, "SAIR PARA SELEÇÃO DE PLANETAS",
        fonte_botao, cb_voltar_menu, base_color=button_color,
        hover_color=hover_button_color, text_color=font_button_color
    )
    btn_exit_desktop = Button(
        screen_width // 2 - 200, screen_height // 2 + 160, 450, 50, "SAIR PARA ÁREA DE TRABALHO",
        fonte_botao, cb_sair_desktop, base_color=button_color,
        hover_color=hover_button_color, text_color=font_button_color
    )

    while running:
        # leitor de eventos
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
                
            if is_paused:
                btn_continue.handle_event(event)
                btn_save_game.handle_event(event)
                btn_load_game.handle_event(event)
                btn_back_menu.handle_event(event)
                btn_exit_desktop.handle_event(event)

            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if is_paused:
                        cb_continuar()
                    else:
                        is_paused = True
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                
                if is_paused and event.key == K_q:
                    running = False # encerra o loop e volta pro Hub
        
        if is_paused:
            mouse_pos = pygame.mouse.get_pos()
            btn_continue.check_hover(mouse_pos)
            btn_save_game.check_hover(mouse_pos)
            btn_load_game.check_hover(mouse_pos)
            btn_back_menu.check_hover(mouse_pos)
            btn_exit_desktop.check_hover(mouse_pos)

        if not is_paused:
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

        if is_paused:
            prepare_2d(screen_width, screen_height)
            glDisable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Fundo escuro transparente
            glColor4f(0, 0, 0, 0.6)
            glBegin(GL_QUADS)
            glVertex2f(0, 0); glVertex2f(screen_width, 0)
            glVertex2f(screen_width, screen_height); glVertex2f(0, screen_height)
            glEnd()
            
            title_pause.draw()
            btn_continue.draw()
            btn_save_game.draw()
            btn_load_game.draw()
            btn_back_menu.draw()
            btn_exit_desktop.draw()
            
            # Remove o estado do blend para nao afetar o loop nas proximas iteracoes e reseta cor
            glColor4f(1, 1, 1, 1)
            glDisable(GL_BLEND)
            prepare_3d()

        pygame.display.flip()
        clock.tick(FPS)

    return result_state