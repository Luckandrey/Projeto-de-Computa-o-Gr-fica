import os
import pygame
import sys
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from core.renderer import draw_cube, draw_floor_tile, draw_computer, draw_door
from core.physics_engine import BLOCK_SIZE, WALL_HEIGHT, is_wall
from core.ui import Button, Title
import core.save_manager as save_manager
import copy

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

def init_opengl_fps(width, height):
    glViewport(0, 0, int(width), int(height))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(75, (width / height), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_BLEND)

def start(planet, saved_state=None):
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    
    pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL | FULLSCREEN)
    init_opengl_fps(screen_width, screen_height)
    
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    clock = pygame.time.Clock()
    FPS = 60

    current_map = planet.layout
    
    cam_x, cam_y, cam_z = 0.0, 2.0, 0.0
    yaw, pitch = 0.0, 0.0
    # Precisamos ter player_y para o save_manager
    player_y = cam_y
    
    computers_data = []
    doors_data = []

    # encontra o '@' (spawn) varrendo a matriz 3D
    for y_index, andar in enumerate(current_map):
        for z_index, linha in enumerate(andar):
            for x_index, char in enumerate(linha):
                world_x = x_index * BLOCK_SIZE
                world_y = y_index * WALL_HEIGHT
                world_z = z_index * BLOCK_SIZE

                if char == '@':
                    cam_x = world_x
                    cam_y = world_y + 2.0
                    cam_z = world_z
                    player_y = cam_y
                elif char == 'M':
                    computers_data.append({
                        'x': world_x,
                        'y': world_y,
                        'z': world_z,
                        'grid_y': y_index,
                        'grid_z': z_index,
                        'grid_x': x_index
                    })
                elif char == 'D':
                    doors_data.append({
                        'x': world_x,
                        'y': world_y,
                        'z': world_z,
                        'grid_y': y_index,
                        'grid_z': z_index,
                        'grid_x': x_index,
                        'is_open': False
                    })

    # As 2 portas mais próximas iniciam abertas
    doors_data.sort(key=lambda d: math.hypot(d['x'] - cam_x, d['z'] - cam_z))
    for i in range(min(2, len(doors_data))):
        doors_data[i]['is_open'] = True

    collision_map = copy.deepcopy(current_map)
    for y_index, andar in enumerate(collision_map):
        for z_index, linha in enumerate(andar):
            linha_list = list(linha)
            for x_index, char in enumerate(linha_list):
                if char == '@':
                    linha_list[x_index] = '.'
            collision_map[y_index][z_index] = "".join(linha_list)
            
    def update_collision_map():
        for d in doors_data:
            linha = list(collision_map[d['grid_y']][d['grid_z']])
            linha[d['grid_x']] = '.' if d['is_open'] else 'P'
            collision_map[d['grid_y']][d['grid_z']] = "".join(linha)
            
    update_collision_map()

    if saved_state:
        cam_x = saved_state['cam_x']
        cam_y = saved_state['cam_y']
        cam_z = saved_state['cam_z']
        yaw = saved_state['yaw']
        pitch = saved_state['pitch']
        player_y = saved_state.get('player_y', cam_y)

    mouse_sensitivity = 0.15
    move_speed = 0.2
    player_radius = 0.5
    
    # --- UI DO PAUSE ---
    pygame.font.init()
    script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    
    hud_font = pygame.font.SysFont("consolas", 24, bold=True)

    running = True
    is_paused = False
    result_state = "MENU"
    esc_held = False

    def cb_continuar():
        nonlocal is_paused
        is_paused = False
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()
        
    def cb_salvar_jogo():
        save_manager.save_level_state(cam_x, cam_y, cam_z, player_y, yaw, pitch, planet.name)
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
        keys = pygame.key.get_pressed()
        
        near_comp = None
        for comp in computers_data:
            dist_xz = math.hypot(cam_x - comp['x'], cam_z - comp['z'])
            dist_y = abs(cam_y - (comp['y'] + 2.0))
            if dist_xz < 3.0 and dist_y < 2.0:
                near_comp = comp
                break
        
        if (keys[K_ESCAPE] or keys[K_p]) and not esc_held:
            esc_held = True
            if is_paused:
                cb_continuar()
            else:
                is_paused = True
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
        elif not (keys[K_ESCAPE] or keys[K_p]):
            esc_held = False
            
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
                if event.key == K_p:
                    if is_paused:
                        cb_continuar()
                    else:
                        is_paused = True
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                elif is_paused and event.key == K_q:
                    running = False
                elif not is_paused and event.key == K_m:
                    return "win"
                elif not is_paused and event.key == K_e:
                    if near_comp and len(doors_data) > 0:
                        # 1. Encontra portas da "sala" (na mesma linha/coluna sem paredes no caminho)
                        room_doors = []
                        for d in doors_data:
                            if d['grid_y'] != near_comp['grid_y']:
                                continue
                            if d['grid_x'] == near_comp['grid_x'] or d['grid_z'] == near_comp['grid_z']:
                                has_wall = False
                                if d['grid_x'] == near_comp['grid_x']:
                                    z_min = min(d['grid_z'], near_comp['grid_z'])
                                    z_max = max(d['grid_z'], near_comp['grid_z'])
                                    for z in range(z_min + 1, z_max):
                                        if current_map[d['grid_y']][z][d['grid_x']] == 'P':
                                            has_wall = True
                                            break
                                else:
                                    x_min = min(d['grid_x'], near_comp['grid_x'])
                                    x_max = max(d['grid_x'], near_comp['grid_x'])
                                    for x in range(x_min + 1, x_max):
                                        if current_map[d['grid_y']][d['grid_z']][x] == 'P':
                                            has_wall = True
                                            break
                                            
                                if not has_wall:
                                    room_doors.append(d)
                        
                        if room_doors:
                            # 2. Ordena de forma previsível
                            room_doors.sort(key=lambda d: (d['grid_z'], d['grid_x']))
                            
                            # 3. Descobre qual porta dessa sala está aberta no momento
                            open_idx = -1
                            for i, d in enumerate(room_doors):
                                if d['is_open']:
                                    open_idx = i
                                    break
                            
                            # 4. Fecha a que estava aberta, e abre a PRÓXIMA na roda
                            if open_idx != -1:
                                room_doors[open_idx]['is_open'] = False
                                nxt = (open_idx + 1) % len(room_doors)
                                room_doors[nxt]['is_open'] = True
                            else:
                                room_doors[0]['is_open'] = True
                                
                        update_collision_map()
        
        if is_paused:
            mouse_pos = pygame.mouse.get_pos()
            btn_continue.check_hover(mouse_pos)
            btn_save_game.check_hover(mouse_pos)
            btn_load_game.check_hover(mouse_pos)
            btn_back_menu.check_hover(mouse_pos)
            btn_exit_desktop.check_hover(mouse_pos)
            
        if not is_paused:
            mouse_dx, mouse_dy = pygame.mouse.get_rel()
            yaw += mouse_dx * mouse_sensitivity
            pitch += mouse_dy * mouse_sensitivity
            
            if pitch > 89.0: pitch = 89.0
            if pitch < -89.0: pitch = -89.0
            
            yaw_rad = math.radians(yaw)
            
            front_x = math.sin(yaw_rad)
            front_z = -math.cos(yaw_rad)
            right_x = math.cos(yaw_rad)
            right_z = math.sin(yaw_rad)
            
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
                
            if not is_wall(next_x + (player_radius if next_x > cam_x else -player_radius), cam_y, cam_z, collision_map):
                cam_x = next_x
                
            if not is_wall(cam_x, cam_y, next_z + (player_radius if next_z > cam_z else -player_radius), collision_map):
                cam_z = next_z
            
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glRotatef(pitch, 1, 0, 0)
        glRotatef(yaw, 0, 1, 0)
        glTranslatef(-cam_x, -cam_y, -cam_z)
        
        for y_index, andar in enumerate(current_map):
            for z_index, linha in enumerate(andar):
                for x_index, char in enumerate(linha):
                    if char == ' ': continue
                    
                    block_x = x_index * BLOCK_SIZE
                    block_y = y_index * WALL_HEIGHT
                    block_z = z_index * BLOCK_SIZE
                    
                    if char in ('P', 'D'):
                        if char == 'P':
                            draw_cube(block_x, block_y, block_z, BLOCK_SIZE, WALL_HEIGHT, color=(0.2, 0.4, 0.6))
                        else:
                            # Se a porta estiver aberta, o chao eh desenhado antes ou pelo D cair no blocão?
                            # Espera, 'D' aqui será tratado pra desenhar chão
                            pass
                    
                    if char != 'P':
                        draw_floor_tile(block_x, block_y, block_z, BLOCK_SIZE, color=(0.1, 0.2, 0.3))
        
        for comp in computers_data:
            draw_computer(comp['x'], comp['y'], comp['z'], 4.0, 4.0, screen_color=(0.8, 0.1, 0.1))

        for d in doors_data:
            if not d['is_open']:
                draw_door(d['x'], d['y'], d['z'], 4.0, 4.0, color=(0.4, 0.55, 0.6))

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
            
            prepare_3d()
            
        if not is_paused and near_comp:
            prepare_2d(screen_width, screen_height)
            prompt_surf = hud_font.render("Aperte [E] para hackear portas", True, (255, 215, 120))
            p_w, p_h = prompt_surf.get_size()
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glRasterPos2f((screen_width - p_w) // 2, screen_height - 100)
            glDrawPixels(p_w, p_h, GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring(prompt_surf, "RGBA", True))
            prepare_3d()
            
        pygame.display.flip()
        clock.tick(FPS)
        
    return result_state
