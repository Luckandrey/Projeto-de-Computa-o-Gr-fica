import game_template
import pygame
import sys
import json
import os
import math
from dataclasses import dataclass
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

@dataclass
class PlanetaData:
    name: str
    size: float
    rotation_speed: float
    axis_tilt: float
    color_or_texture: str
    has_rings: bool
    splash_image: str = "" 
    current_angle: float = 0.0
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    texture_id: int = None
    splash_texture_id: int = None
    is_unlocked: bool = False

def load_planets(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
            
        lista_planetas = []
        for p in dados['planetas']:
            novo_planeta = PlanetaData(
                name=p['nome'],
                size=p['tamanho'],
                rotation_speed=p['velocidade_rotacao'],
                axis_tilt=p['inclinacao_eixo'],
                color_or_texture=p['cor_ou_textura'],
                has_rings=p['possui_aneis'],
                splash_image=p.get('splash_image', "")
            )
            lista_planetas.append(novo_planeta)
            
        return lista_planetas
    
    except Exception as e:
        print(f"Erro ao carregar planetas: {e}")
        return []

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def load_texture(image_path):
    try:
        # carrega a imagem
        planet_texture = pygame.image.load(image_path)
        
        # conversão da imagem para uso
        image_data = pygame.image.tostring(planet_texture, "RGBA", True)
        width, height = planet_texture.get_size()

        # gera um id para a textura
        tex_id = glGenTextures(1)
        
        # ativa a textura para configurá-la
        glBindTexture(GL_TEXTURE_2D, tex_id)

        # suaviza a textura quando o planeta estiver muito perto ou muito longe
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        # envia para a placa de vídeo
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
        
        return tex_id
    except Exception as e:
        print(f"Erro ao carregar textura '{image_path}': {e}")
        return None

def draw_ring(internal_radius, external_radius, texture_id):
    # gerando malha com furo no meio
    quadric = gluNewQuadric()
    
    if texture_id is not None:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        gluQuadricTexture(quadric, GL_TRUE)
        # ultimo valor em 1 para garantir canal alpha (transparência)
        glColor4f(1.0, 1.0, 1.0, 1.0) 
        
    # parâmetros: quadric, raio interno, raio externo, fatias, anéis_concêntricos
    # 64 fatias deixam o anel bem redondinho O
    gluDisk(quadric, internal_radius, external_radius, 64, 1)
    
    gluDeleteQuadric(quadric)
    
    if texture_id is not None:
        glDisable(GL_TEXTURE_2D)

def draw_sphere(radius, hex_color, texture_id):
    # cria uma esfera
    quadric = gluNewQuadric()
    
    # definindo a cor
    if texture_id is not None:
        # liga o modo de textura 2D
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        gluQuadricTexture(quadric, GL_TRUE)
        # branco para não alterar a cor da textura
        glColor3f(1.0, 1.0, 1.0)
    else:
        # sem textura, pinta cor sólida
        glDisable(GL_TEXTURE_2D)
        if hex_color.startswith('#'):
            r, g, b = hex_to_rgb(hex_color)
            glColor3f(r, g, b)

    # parâmetros: quadric, raio, latitude, longitude
    # uma esfera com 32 divisões horizontais e verticais fica minimamente suave
    gluSphere(quadric, radius, 32, 32)
    
    gluDeleteQuadric(quadric)
    # dedabilita para próximo carregamento
    glDisable(GL_TEXTURE_2D)

def draw_background(texture_id):
    if texture_id is None:
        return

    # salva as matrizes atuais
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity() 

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # configurações de desenho (desliga o 3D, liga a textura)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1.0, 1.0, 1.0)

    # desenha o quad cravado nas bordas absolutas da tela
    glBegin(GL_QUADS)
    
    # mapeamento: UV da Textura (0 a 1) -> Coordenadas da Tela NDC (-1 a 1)
    # como carregamos a imagem invertida no PyGame, o UV (0,0) é embaixo
    
    # canto Inferior Esquerdo
    glTexCoord2f(0.0, 0.0); glVertex2f(-1.0, -1.0) 
    
    # canto Inferior Direito
    glTexCoord2f(1.0, 0.0); glVertex2f( 1.0, -1.0) 
    
    # canto Superior Direito
    glTexCoord2f(1.0, 1.0); glVertex2f( 1.0,  1.0) 
    
    # canto Superior Esquerdo
    glTexCoord2f(0.0, 1.0); glVertex2f(-1.0,  1.0) 
    
    glEnd()

    glDisable(GL_TEXTURE_2D)

    # restaura o controle para o 3D dos planetas
    glEnable(GL_DEPTH_TEST)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def load_background(path, width, height):
    try:
        texture = pygame.image.load(path)
        
        # redimensionamento da imagem
        texture = pygame.transform.smoothscale(texture, (width, height))
        
        image_data = pygame.image.tostring(texture, "RGBA", True)
        
        # as medidas agora são da tela, não da imagem original
        final_width, final_height = texture.get_size()

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # conserta possíveis desalinhamentos de memória
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        # envia a textura exata e sob medida para a GPU
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, final_width, final_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
        
        return tex_id
    
    except Exception as e:
        print(f"Erro ao carregar fundo: {e}")
        return None
    
def draw_tooltip(text, mouse_x, mouse_y, width, height, font, text_color):
    # renderiza o texto no PyGame (Branco com fundo cinza escuro)
    text_surface = font.render(f"  {text}  ", True, text_color, (40, 40, 40))
    text_width, text_height = text_surface.get_size()
    dados_imagem = pygame.image.tostring(text_surface, "RGBA", True)

    # gera uma textura temporária
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, dados_imagem)

    # entra no modo 2D (NDC)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, height, 0, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # desliga a profundidade para desenhar sempre por cima
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor3f(1.0, 1.0, 1.0)

    # deslocamento leve para o cursor não tampar o texto
    pos_x = mouse_x + 15
    pos_y = mouse_y + 15

    # desenha o quad com o texto
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex2f(pos_x, pos_y)
    glTexCoord2f(1.0, 1.0); glVertex2f(pos_x + text_width, pos_y)
    glTexCoord2f(1.0, 0.0); glVertex2f(pos_x + text_width, pos_y + text_height)
    glTexCoord2f(0.0, 0.0); glVertex2f(pos_x, pos_y + text_height)
    glEnd()

    # restaura o estado original
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

    # deleta a textura temporária para não estourar a memória
    glDeleteTextures(1, [tex_id])

def draw_fade_overlay(width, height, alpha):
    # so desenha se houver alguma opacidade
    if alpha <= 0.0:
        return

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, height, 0, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # desliga a profundidade e desliga texturas para desenhar cor solida
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_TEXTURE_2D)
    
    # cor preta com o canal alpha (transparencia) variavel
    glColor4f(0.0, 0.0, 0.0, alpha)

    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(width, 0)
    glVertex2f(width, height)
    glVertex2f(0, height)
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

# prepara a cena e as regras de renderização 3D.
def start_opengl(height, width):
    # define a área exata da tela
    glViewport(0, 0, int(width), int(height))

    # define a perspectiva (câmera)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    
    # parâmetros: FOV (45 graus), Aspect Ratio (largura/altura), Near Clipping Plane, Far Clipping Plane
    # tudo que estiver mais perto que 0.1 ou mais longe que 1000 não será renderizado
    gluPerspective(45, (width / height), 0.1, 1000.0)
    
    # retorna para a matriz de visualização de modelos
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # afasta a câmera no eixo Z para podermos ver o centro do espaço
    glTranslatef(0.0, 0.0, -50.0)
    
    # ativa o Z-Buffer (teste de profundidade)
    # fundamental para que modelos 3D não sejam desenhados de dentro para fora
    glEnable(GL_DEPTH_TEST)

    # suporte de canal alpha (transparência)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

def main():
    # inicialização do pygame
    pygame.init()

    # incialização de fonte
    pygame.font.init() # Inicializa o renderizador de fontes
    fonte_tooltip = pygame.font.SysFont('Arial', 24, bold=True)

    # obtém as informações do monitor atual
    screen_info = pygame.display.Info()
    screen_height = screen_info.current_h
    screen_width = screen_info.current_w

    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Tau Ceti Wars")

    start_opengl(screen_height, screen_width)

    # relógio para controle de fps
    clock = pygame.time.Clock()
    FPS = 60

    # pega o diretório do arquivo .py atual
    script_path = os.path.dirname(os.path.abspath(__file__))

    # pega o diretório com o nome do arquivo json
    json_path = os.path.join(script_path, 'planetas.json')
    
    print(f"\nBuscando arquivo json em:\n-> {json_path}")

    # carrega planetas no diretório encontrado
    star_system = load_planets(json_path)

    # se a lista estiver vazia, encerra o jogo
    if not star_system:
        print("\nA lista de planetas está vazia ou o arquivo não foi lido.")
        pygame.quit()
        sys.exit()

    # se o arquivo foi carregado, imprime os planetas lidos
    print("\nPlanetas carregados:")
    for planeta in star_system:
        print(f" -> {planeta.name} (Tamanho: {planeta.size} | Cor: {planeta.color_or_texture})")

    pasta_texturas = os.path.join(script_path, 'Texturas') # pega a pasta de texturas

    for planet in star_system:
        # verifica se o campo parece ser um arquivo de imagem
        if planet.color_or_texture.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(pasta_texturas, planet.color_or_texture)
            planet.texture_id = load_texture(image_path)
            status = f"Textura carregada (ID {planet.texture_id})" if planet.texture_id else "Falha na textura"
            print(f" -> {planet.name}: {status}")
        else:
            print(f" -> {planet.name}: Usando cor sólida ({planet.color_or_texture})")

        # carrega as splash arts dos planetas
        if planet.splash_image:
            splash_path = os.path.join(pasta_texturas, planet.splash_image)
            planet.splash_texture_id = load_background(splash_path, screen_width, screen_height)

    # caminho da textura do anel
    ring_image_path = os.path.join(pasta_texturas, 'anel.png')

    ring_texture_id = load_texture(ring_image_path)

    if ring_texture_id:
        print(" -> Textura dos aneis planetários carregada com sucesso!")
    else:
        print(" -> Textura 'anel.png' não encontrada")

    background_image_path = os.path.join(pasta_texturas, 'fundo_espacial.png')

    background_texture_id = load_background(background_image_path, screen_width, screen_height)

    if background_texture_id:
        print(" -> Textura de fundo carregada com sucesso!")
    else:
        print(" -> Textura 'fundo_espacial.png' não encontrada")

    # posições em que cada planeta vai ficar na cena
    planet_positions = [
        (-30.0, -10.0, 0.0), # Slot 1: fundo esquerda, mais baixo
        (-15.0,  -5.0, 0.0), # Slot 2
        (  0.0,   0.0, 0.0), # Slot 3: centro exato da tela
        ( 15.0,   5.0, 0.0), # Slot 4
        ( 30.0,  10.0, 0.0)  # Slot 5: frente direita, mais alto
    ]

    for i, planet in enumerate(star_system):
        if i < len(planet_positions):
            planet.pos_x, planet.pos_y, planet.pos_z = planet_positions[i]
        else:
            print(f"Aviso: Não há slots de posição suficientes para {planet.name}.")

    # progresso linear: desbloqueia apenas o primeiro planeta inicialmente
    if star_system:
        star_system[0].is_unlocked = True

    # variaveis de controle de camera
    cam_x, cam_y, cam_z = 0.0, 0.0, -50.0

    # velocidade da câmera durante a transição
    cam_speed = 0.015
    
    # variaveis da maquina de estados da transicao
    # estados: IDLE, PULLBACK, APPROACH, FADE_OUT, SPLASH, START_LEVEL
    transition_state = "IDLE" 
    target_planet = None
    fade_alpha = 0.0
    splash_timer = 0

    # variável de controle do loop de jogo
    running = True

    while running:
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                running = False
            
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    running = False
                
                if evento.key == pygame.K_k:
                    for planet in star_system:
                        planet.is_unlocked = True
                    print("\nTodos os planetas foram desbloqueados")
            
            # detecta o clique do mouse no planeta
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                # so permite clicar se estiver livre (IDLE), tiver um planeta no foco, e ele for desbloqueado
                if transition_state == "IDLE" and focused_planet and focused_planet.is_unlocked:
                    target_planet = focused_planet
                    transition_state = "PULLBACK"

        # lógicas de estados de transição
        if transition_state == "PULLBACK":
            # Movimento simultâneo: Recua (Z) e Centraliza (X e Y) ao mesmo tempo.
            # Como usamos interpolação (cam_speed), isso cria um arco suave.
            target_z = -60.0
            target_x = -target_planet.pos_x
            target_y = -target_planet.pos_y
            
            cam_x += (target_x - cam_x) * cam_speed
            cam_y += (target_y - cam_y) * cam_speed
            cam_z += (target_z - cam_z) * cam_speed
            
            # quando estiver quase no ponto máximo de recuo e centralizado, vai para a frente
            if abs(cam_z - target_z) < 0.5 and abs(cam_x - target_x) < 0.5:
                transition_state = "APPROACH"
                
        elif transition_state == "APPROACH":
            # vai na direção do planeta alvo
            target_z = -target_planet.pos_z - (target_planet.size * 3.5) 
            cam_z += (target_z - cam_z) * cam_speed
            
            # verifica se a distância até o planeta é menor que 15 unidades
            distancia_restante = abs(cam_z - target_z)
            if distancia_restante < 15.0:
                fade_alpha += 0.03 # um pouco mais rápido para fechar antes de bater
                
                # quando a tela fica 100% preta, passa para a arte
                if fade_alpha >= 1.0:
                    fade_alpha = 1.0
                    transition_state = "SPLASH_FADE_IN"
                
        elif transition_state == "SPLASH_FADE_IN":
            # reduz o alpha do quadrado preto para revelar a arte suavemente.
            fade_alpha -= 0.02
            
            if fade_alpha <= 0.0:
                fade_alpha = 0.0
                transition_state = "SPLASH_WAIT"
                splash_timer = pygame.time.get_ticks() # começa a contar tempo de "loading" aqui
                
        elif transition_state == "SPLASH_WAIT":
            # aguarda o tempo da arte da transição
            current_time = pygame.time.get_ticks()
            if current_time - splash_timer > 3000:
                transition_state = "START_LEVEL"
                
        elif transition_state == "START_LEVEL":
            print(f"\nIniciando fase: {target_planet.name}!")
            
            # chama a fase escolhida
            resultado_fase = game_template.start(target_planet.name)
            
            # retorno da fase para menu
            print(f"\nFase concluída: {target_planet.name}!")
            
            # Desbloqueia o próximo planeta se tiver vencido (Lógica simplificada)
            # if resultado_fase == "VITORIA":
                # liberar_proximo_planeta()
            
            # reseta todas as variáveis de visualização
            transition_state = "IDLE"
            fade_alpha = 0.0
            target_planet = None
            cam_x, cam_y, cam_z = 0.0, 0.0, -50.0
            
            # destrava o mouse
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if background_texture_id:
            draw_background(background_texture_id)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity() 
        
        # variáveis de movimento da câmera
        glTranslatef(cam_x, cam_y, cam_z) 

        mouse_x, mouse_y = pygame.mouse.get_pos()
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        focused_planet = None

        for planet in star_system:
            planet.current_angle += planet.rotation_speed
            if planet.current_angle >= 360.0:
                planet.current_angle -= 360.0

            # o mouse picking so funciona se o jogador nao estiver no meio de qualquer transição 
            if transition_state == "IDLE":
                try:
                    win_x, win_y, win_z = gluProject(planet.pos_x, planet.pos_y, planet.pos_z, 
                                                     modelview, projection, viewport)
                    x_limit, _, _ = gluProject(planet.pos_x + planet.size, planet.pos_y, planet.pos_z, 
                                               modelview, projection, viewport)
                    screen_radius = abs(x_limit - win_x)
                    win_y_inverted = screen_height - win_y
                    distance = math.hypot(mouse_x - win_x, mouse_y - win_y_inverted)

                    if distance < screen_radius:
                        focused_planet = planet
                except ValueError:
                    pass 

            glPushMatrix() 
            glTranslatef(planet.pos_x, planet.pos_y, planet.pos_z) 
            glRotatef(-90.0, 1, 0, 0)
            glRotatef(planet.axis_tilt, 1, 0, 0) 

            if planet.has_rings:
                draw_ring(planet.size * 1.2, planet.size * 1.9, ring_texture_id)

            glRotatef(planet.current_angle, 0, 0, 1)
            draw_sphere(planet.size, planet.color_or_texture, planet.texture_id)
            glPopMatrix() 

        # desenha a UI apenas se estiver parado e com o mouse em cima
        if focused_planet and transition_state == "IDLE":
            if focused_planet.is_unlocked:
                texto_ui = focused_planet.name
                cor_texto = (255, 255, 255) # branco para liberado
            else:
                texto_ui = f"{focused_planet.name} (BLOQUEADO)"
                cor_texto = (255, 80, 80) # vermelho suave para bloqueado
                
            draw_tooltip(texto_ui, mouse_x, mouse_y, screen_width, screen_height, fonte_tooltip, cor_texto)

        # máquina de estados visuais de transição
        if transition_state in ["SPLASH_FADE_IN", "SPLASH_WAIT"]:
            if target_planet and target_planet.splash_texture_id:
                draw_background(target_planet.splash_texture_id)

        if fade_alpha > 0.0:
            draw_fade_overlay(screen_width, screen_height, fade_alpha)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()