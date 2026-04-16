import sys
import random
import math

try:
    import pygame
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    import pygame

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
WIDTH, HEIGHT   = 900, 520
FPS             = 60
TUBE_MARGIN     = 65
TUBE_TOP        = TUBE_MARGIN
TUBE_BOTTOM     = HEIGHT - TUBE_MARGIN

SHIP_SPEED_H    = 4      # horizontal (adelante/atrás)
SHIP_SPEED_V    = 5      # vertical
SHIP_MIN_X      = 60
SHIP_MAX_X      = 320
SHIP_RADIUS     = 17
BULLET_SPEED    = 12
BULLET_COOLDOWN = 200    # ms entre disparos
MAX_LIVES       = 3
INVINCIBLE_TIME = 2000   # ms de invencibilidad tras golpe

SPLIT_RADIUS    = 24     # los asteroides >= este radio se parten al destruirse

AST_SPAWN_START = 1300
AST_SPAWN_MIN   = 380

# Colores
BG          = (18, 18, 30)
TUBE_C      = (15, 60, 100)
TUBE_L      = (35, 120, 180)
STAR_C      = (200, 200, 220)
SHIP_C      = (0, 210, 255)
EXHAUST_C   = (255, 150, 0)
BULLET_C    = (255, 80, 80)
BULLET_GL   = (255, 180, 180)
AST_C       = (150, 95, 55)
AST_H       = (110, 65, 35)
AST_CRACK   = (80, 40, 20)
SCORE_C     = (255, 230, 80)
LIFE_C      = (255, 80, 80)
WHITE       = (255, 255, 255)
FLASH_C     = (255, 255, 255)
PARTICLE_C  = [(255,180,60),(255,120,40),(255,60,20),(200,200,200)]


# ---------------------------------------------------------------------------
# Clases
# ---------------------------------------------------------------------------
class Asteroid:
    def __init__(self, x, y, radius, vx, ax, vy, ay):
        self.x, self.y  = float(x), float(y)
        self.r          = radius
        self.vx, self.ax = vx, ax
        self.vy, self.ay = vy, ay
        self.seed       = random.randint(0, 99999)
        self.alive      = True

    def update(self):
        self.vx += self.ax
        if self.vx > -1.0:
            self.vx = -1.0
        self.x += self.vx

        self.vy += self.ay
        self.vy = max(-7.0, min(7.0, self.vy))
        self.y += self.vy

        if self.y - self.r < TUBE_TOP:
            self.y = TUBE_TOP + self.r
            self.vy = abs(self.vy)
        elif self.y + self.r > TUBE_BOTTOM:
            self.y = TUBE_BOTTOM - self.r
            self.vy = -abs(self.vy)

    def draw(self, surface):
        rng = random.Random(self.seed)
        pts = []
        n = 11
        for i in range(n):
            angle = 2 * math.pi * i / n
            r = self.r + rng.randint(-self.r // 4, self.r // 4)
            pts.append((int(self.x + r * math.cos(angle)),
                        int(self.y + r * math.sin(angle))))
        pygame.draw.polygon(surface, AST_C, pts)
        pygame.draw.polygon(surface, AST_H, pts, 2)
        # grietas decorativas
        rng2 = random.Random(self.seed + 1)
        for _ in range(2):
            ang = rng2.uniform(0, 2 * math.pi)
            length = rng2.randint(self.r // 3, self.r // 2)
            x1 = int(self.x + math.cos(ang) * 4)
            y1 = int(self.y + math.sin(ang) * 4)
            x2 = x1 + int(math.cos(ang) * length)
            y2 = y1 + int(math.sin(ang) * length)
            pygame.draw.line(surface, AST_CRACK, (x1, y1), (x2, y2), 1)

    def collides_with(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy < (self.r + other.r) ** 2

    def split(self):
        """Devuelve dos asteroides más pequeños si el radio lo permite."""
        if self.r < SPLIT_RADIUS:
            return []
        new_r = self.r // 2
        children = []
        for sign in (+1, -1):
            perp_vx = -self.vy * 0.4
            perp_vy =  self.vx * 0.4 * sign
            child = Asteroid(
                self.x + sign * new_r,
                self.y + sign * new_r,
                new_r,
                self.vx * 0.8 + perp_vx,
                self.ax * 0.5,
                self.vy * 0.8 + perp_vy,
                self.ay * 0.5,
            )
            children.append(child)
        return children


class Bullet:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.alive = True

    def update(self):
        self.x += BULLET_SPEED
        if self.x > WIDTH + 10:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, BULLET_GL, (int(self.x), int(self.y)), 6)
        pygame.draw.circle(surface, BULLET_C,  (int(self.x), int(self.y)), 4)


class Particle:
    def __init__(self, x, y, color=None):
        self.x, self.y = float(x), float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 5.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(18, 35)
        self.max_life = self.life
        self.color = color or random.choice(PARTICLE_C)
        self.r = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= 1

    def draw(self, surface):
        alpha = self.life / self.max_life
        r = int(self.color[0] * alpha)
        g = int(self.color[1] * alpha)
        b = int(self.color[2] * alpha)
        pygame.draw.circle(surface, (r, g, b), (int(self.x), int(self.y)), self.r)


class Ship:
    def __init__(self):
        self.x = float(120)
        self.y = float(HEIGHT // 2)
        self.vx = 0.0
        self.vy = 0.0

    def update(self, keys):
        if keys[pygame.K_UP]:
            self.vy = -SHIP_SPEED_V
        elif keys[pygame.K_DOWN]:
            self.vy = SHIP_SPEED_V
        else:
            self.vy = 0

        if keys[pygame.K_RIGHT]:
            self.vx = SHIP_SPEED_H
        elif keys[pygame.K_LEFT]:
            self.vx = -SHIP_SPEED_H
        else:
            self.vx = 0

        self.x = max(SHIP_MIN_X, min(SHIP_MAX_X, self.x + self.vx))
        self.y = max(TUBE_TOP + SHIP_RADIUS, min(TUBE_BOTTOM - SHIP_RADIUS, self.y + self.vy))

    def draw(self, surface, invincible, now):
        # Parpadeo al ser invencible
        if invincible and (now // 120) % 2 == 0:
            return
        x, y = int(self.x), int(self.y)
        body = [(x+32,y),(x-10,y-13),(x-22,y),(x-10,y+13)]
        pygame.draw.polygon(surface, SHIP_C, body)
        # cabina
        pygame.draw.circle(surface, WHITE, (x+10, y), 8)
        pygame.draw.circle(surface, (80, 190, 255), (x+10, y), 6)
        # tobera
        pygame.draw.polygon(surface, EXHAUST_C, [(x-22,y-5),(x-36,y),(x-22,y+5)])
        # ala superior
        pygame.draw.polygon(surface, (0,150,200), [(x+5,y-13),(x-8,y-24),(x-18,y-13)])
        # ala inferior
        pygame.draw.polygon(surface, (0,150,200), [(x+5,y+13),(x-8,y+24),(x-18,y+13)])

    def nose_x(self):
        return int(self.x) + 32

    def nose_y(self):
        return int(self.y)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def spawn_asteroid(difficulty):
    r = random.randint(16, 40)
    y = random.randint(TUBE_TOP + r, TUBE_BOTTOM - r)
    vx = -(3 + random.random() * 3 + difficulty * 5)
    ax = random.choice([-1, 0, 0, 1]) * random.uniform(0, 0.03 + difficulty * 0.07)
    vy = random.uniform(-(0.5 + difficulty * 2), 0.5 + difficulty * 2)
    ay = random.choice([-1, 0, 0, 1]) * random.uniform(0, 0.02 + difficulty * 0.06)
    return Asteroid(WIDTH + r, y, r, vx, ax, vy, ay)


def resolve_asteroid_collision(a, b):
    """Rebote elástico simplificado entre dos asteroides."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        dist = 0.1
    nx, ny = dx / dist, dy / dist
    # separar para que no se solapen
    overlap = (a.r + b.r) - dist
    a.x -= nx * overlap / 2
    a.y -= ny * overlap / 2
    b.x += nx * overlap / 2
    b.y += ny * overlap / 2
    # intercambiar componente normal de velocidad
    a_dot = a.vx * nx + a.vy * ny
    b_dot = b.vx * nx + b.vy * ny
    a.vx += (b_dot - a_dot) * nx
    a.vy += (b_dot - a_dot) * ny
    b.vx += (a_dot - b_dot) * nx
    b.vy += (a_dot - b_dot) * ny


def draw_tube(surface, scroll):
    pygame.draw.rect(surface, TUBE_C, (0, 0, WIDTH, TUBE_MARGIN))
    pygame.draw.line(surface, TUBE_L, (0, TUBE_MARGIN), (WIDTH, TUBE_MARGIN), 3)
    pygame.draw.rect(surface, TUBE_C, (0, TUBE_BOTTOM, WIDTH, TUBE_MARGIN))
    pygame.draw.line(surface, TUBE_L, (0, TUBE_BOTTOM), (WIDTH, TUBE_BOTTOM), 3)
    # remaches animados
    for i in range(-1, WIDTH // 80 + 2):
        ox = (i * 80 - scroll % 80)
        pygame.draw.rect(surface, TUBE_L, (ox, TUBE_MARGIN - 9, 38, 6))
        pygame.draw.rect(surface, TUBE_L, (ox + 18, TUBE_BOTTOM + 3, 38, 6))


def draw_stars(surface, stars, scroll):
    for sx, sy, br, layer in stars:
        x = (sx - scroll * layer) % WIDTH
        pygame.draw.circle(surface, (br, br, br), (int(x), sy), 1)


def draw_hud(surface, score, lives, diff_pct, font_score, font_small):
    # Puntuación
    surface.blit(font_score.render(f"Puntuación: {score}", True, SCORE_C), (10, 10))
    # Vidas (corazones)
    for i in range(MAX_LIVES):
        color = LIFE_C if i < lives else (60, 60, 80)
        cx = WIDTH - 30 - i * 34
        cy = 22
        pygame.draw.circle(surface, color, (cx - 7, cy - 3), 8)
        pygame.draw.circle(surface, color, (cx + 7, cy - 3), 8)
        pts = [(cx - 15, cy - 1), (cx, cy + 14), (cx + 15, cy - 1)]
        pygame.draw.polygon(surface, color, pts)
    # Dificultad
    diff_color = (int(100 + 155 * diff_pct / 100), int(255 - 200 * diff_pct / 100), 50)
    diff_surf = font_small.render(f"Dificultad: {diff_pct}%", True, diff_color)
    surface.blit(diff_surf, (WIDTH - diff_surf.get_width() - 10, 44))
    # Controles
    ctrl = font_small.render("Flechas: mover  |  SPACE: disparar", True, (120, 120, 160))
    surface.blit(ctrl, (10, HEIGHT - TUBE_MARGIN + 18))


def draw_overlay(surface, font_big, font_small, score, is_go):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))
    title = "GAME OVER" if is_go else "PAUSADO"
    t_surf = font_big.render(title, True, (255, 60, 60) if is_go else WHITE)
    surface.blit(t_surf, t_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 70)))
    sc = font_small.render(f"Puntuación: {score}", True, SCORE_C)
    surface.blit(sc, sc.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    hint = font_small.render("R - reiniciar    ESC - salir", True, WHITE)
    surface.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spaceship - Tube Shooter")
    clock = pygame.time.Clock()

    font_big   = pygame.font.SysFont("Arial", 58, bold=True)
    font_small = pygame.font.SysFont("Arial", 22)
    font_score = pygame.font.SysFont("Arial", 30, bold=True)

    # Estrellas con parallax (layer = velocidad relativa)
    stars = [
        (random.randint(0, WIDTH),
         random.randint(TUBE_TOP, TUBE_BOTTOM),
         random.randint(60, 200),
         random.choice([0.1, 0.2, 0.4]))
        for _ in range(100)
    ]

    def reset():
        now = pygame.time.get_ticks()
        return dict(
            ship        = Ship(),
            asteroids   = [],
            bullets     = [],
            particles   = [],
            score       = 0,
            lives       = MAX_LIVES,
            last_spawn  = now,
            start_ticks = now,
            last_bullet = 0,
            invincible_until = 0,
            scroll      = 0,
            flash       = 0,   # frames de flash de pantalla al golpear
            game_over   = False,
        )

    state = reset()

    running = True
    while running:
        dt  = clock.tick(FPS)
        now = pygame.time.get_ticks()
        s   = state

        # ---- Eventos ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if s["game_over"] and event.key == pygame.K_r:
                    state = reset()
                    s = state

        if not s["game_over"]:
            keys = pygame.key.get_pressed()

            # ---- Nave ----
            s["ship"].update(keys)

            # ---- Disparo ----
            if keys[pygame.K_SPACE] and now - s["last_bullet"] > BULLET_COOLDOWN:
                s["bullets"].append(Bullet(s["ship"].nose_x(), s["ship"].nose_y()))
                s["last_bullet"] = now
                # partícula de retroceso
                for _ in range(4):
                    s["particles"].append(Particle(s["ship"].x - 22, s["ship"].y, EXHAUST_C))

            # ---- Dificultad ----
            elapsed_s  = (now - s["start_ticks"]) / 1000.0
            difficulty = min(elapsed_s / 120.0, 1.0)
            spawn_int  = AST_SPAWN_START - difficulty * (AST_SPAWN_START - AST_SPAWN_MIN)

            # ---- Spawn asteroides ----
            if now - s["last_spawn"] > spawn_int:
                s["asteroids"].append(spawn_asteroid(difficulty))
                s["last_spawn"] = now

            # ---- Física asteroides ----
            for ast in s["asteroids"]:
                ast.update()

            # ---- Colisiones entre asteroides ----
            asts = s["asteroids"]
            for i in range(len(asts)):
                for j in range(i + 1, len(asts)):
                    if asts[i].alive and asts[j].alive and asts[i].collides_with(asts[j]):
                        resolve_asteroid_collision(asts[i], asts[j])

            # ---- Balas vs asteroides ----
            new_asts = []
            for ast in s["asteroids"]:
                if not ast.alive:
                    continue
                hit = False
                for blt in s["bullets"]:
                    if not blt.alive:
                        continue
                    dx = blt.x - ast.x
                    dy = blt.y - ast.y
                    if dx * dx + dy * dy < (ast.r + 5) ** 2:
                        blt.alive = False
                        hit = True
                        break
                if hit:
                    for _ in range(18):
                        s["particles"].append(Particle(ast.x, ast.y))
                    children = ast.split()
                    new_asts.extend(children)
                    s["score"] += max(1, 40 // ast.r)
                else:
                    new_asts.append(ast)
            s["asteroids"] = new_asts

            # ---- Balas fuera de pantalla ----
            for blt in s["bullets"]:
                blt.update()
            s["bullets"] = [b for b in s["bullets"] if b.alive]

            # ---- Asteroides fuera de pantalla ----
            s["asteroids"] = [a for a in s["asteroids"] if a.x + a.r > 0]

            # ---- Colisión nave-asteroide ----
            invincible = now < s["invincible_until"]
            if not invincible:
                for ast in s["asteroids"]:
                    dx = s["ship"].x - ast.x
                    dy = s["ship"].y - ast.y
                    if dx * dx + dy * dy < (SHIP_RADIUS + ast.r - 5) ** 2:
                        s["lives"] -= 1
                        s["flash"] = 10
                        for _ in range(30):
                            s["particles"].append(Particle(s["ship"].x, s["ship"].y, SHIP_C))
                        if s["lives"] <= 0:
                            s["game_over"] = True
                        else:
                            s["invincible_until"] = now + INVINCIBLE_TIME
                        break

            # ---- Partículas ----
            for p in s["particles"]:
                p.update()
            s["particles"] = [p for p in s["particles"] if p.life > 0]

            # ---- Puntuación por tiempo ----
            s["score"] += 1

            # ---- Scroll ----
            s["scroll"] += 3

        # ================================================================
        # Dibujo
        # ================================================================
        if s["flash"] > 0:
            screen.fill(FLASH_C)
            s["flash"] -= 1
        else:
            screen.fill(BG)

        draw_stars(screen, stars, s["scroll"])
        draw_tube(screen, s["scroll"])

        for p in s["particles"]:
            p.draw(screen)

        for ast in s["asteroids"]:
            ast.draw(screen)

        for blt in s["bullets"]:
            blt.draw(screen)

        invincible = now < s["invincible_until"]
        s["ship"].draw(screen, invincible, now)

        # HUD
        diff_pct = int(min((now - s["start_ticks"]) / 1200.0, 100))
        draw_hud(screen, s["score"] // 10, s["lives"], diff_pct, font_score, font_small)

        if s["game_over"]:
            draw_overlay(screen, font_big, font_small, s["score"] // 10, True)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
