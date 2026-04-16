import sys
import random
import math

try:
    import pygame
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    import pygame

# --- Configuración ---
WIDTH, HEIGHT = 800, 500
FPS = 60
SHIP_SPEED = 5
ASTEROID_BASE_MIN_SPEED = 3
ASTEROID_BASE_MAX_SPEED = 6
ASTEROID_SPAWN_INTERVAL_START = 1200  # ms al inicio
ASTEROID_SPAWN_INTERVAL_MIN   = 400   # ms mínimo (tope de dificultad)
TUBE_MARGIN = 60

# Colores
DARK_GRAY   = (30, 30, 40)
WHITE       = (255, 255, 255)
TUBE_COLOR  = (20, 80, 120)
TUBE_LINE   = (40, 140, 200)
SHIP_COLOR  = (0, 220, 255)
EXHAUST     = (255, 160, 0)
ASTEROID_C  = (160, 100, 60)
ASTEROID_H  = (120, 70, 40)
SCORE_COLOR = (255, 255, 100)


def draw_ship(surface, x, y):
    body = [
        (x + 30, y),
        (x - 10, y - 12),
        (x - 20, y),
        (x - 10, y + 12),
    ]
    pygame.draw.polygon(surface, SHIP_COLOR, body)
    pygame.draw.circle(surface, WHITE, (x + 10, y), 7)
    pygame.draw.circle(surface, (100, 200, 255), (x + 10, y), 5)
    pygame.draw.polygon(surface, EXHAUST, [
        (x - 20, y - 5),
        (x - 32, y),
        (x - 20, y + 5),
    ])


def draw_asteroid(surface, ax, ay, radius, seed):
    rng = random.Random(seed)
    points = []
    num_points = 10
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        r = radius + rng.randint(-radius // 4, radius // 4)
        points.append((ax + int(r * math.cos(angle)), ay + int(r * math.sin(angle))))
    pygame.draw.polygon(surface, ASTEROID_C, points)
    pygame.draw.polygon(surface, ASTEROID_H, points, 2)


def draw_tube(surface):
    pygame.draw.rect(surface, TUBE_COLOR, (0, 0, WIDTH, TUBE_MARGIN))
    pygame.draw.line(surface, TUBE_LINE, (0, TUBE_MARGIN), (WIDTH, TUBE_MARGIN), 3)
    pygame.draw.rect(surface, TUBE_COLOR, (0, HEIGHT - TUBE_MARGIN, WIDTH, TUBE_MARGIN))
    pygame.draw.line(surface, TUBE_LINE, (0, HEIGHT - TUBE_MARGIN), (WIDTH, HEIGHT - TUBE_MARGIN), 3)
    for x in range(0, WIDTH, 80):
        pygame.draw.rect(surface, TUBE_LINE, (x, TUBE_MARGIN - 8, 40, 5))
        pygame.draw.rect(surface, TUBE_LINE, (x + 20, HEIGHT - TUBE_MARGIN + 3, 40, 5))


def draw_stars(surface, stars):
    for sx, sy, brightness in stars:
        pygame.draw.circle(surface, (brightness, brightness, brightness), (sx, sy), 1)


def game_over_screen(surface, font_big, font_small, score):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))
    surface.blit(font_big.render("GAME OVER", True, (255, 60, 60)),
                 font_big.render("GAME OVER", True, (255, 60, 60)).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
    surface.blit(font_small.render(f"Puntuación: {score}", True, SCORE_COLOR),
                 font_small.render(f"Puntuación: {score}", True, SCORE_COLOR).get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    surface.blit(font_small.render("Pulsa R para reiniciar o ESC para salir", True, WHITE),
                 font_small.render("Pulsa R para reiniciar o ESC para salir", True, WHITE).get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spaceship - Esquiva los asteroides")
    clock = pygame.time.Clock()

    font_big   = pygame.font.SysFont("Arial", 56, bold=True)
    font_small = pygame.font.SysFont("Arial", 28)
    font_score = pygame.font.SysFont("Arial", 32, bold=True)

    stars = [
        (random.randint(0, WIDTH), random.randint(TUBE_MARGIN, HEIGHT - TUBE_MARGIN), random.randint(80, 200))
        for _ in range(80)
    ]

    def reset():
        now = pygame.time.get_ticks()
        return {
            "ship_y": float(HEIGHT // 2),
            # Cada asteroide: [x, y, radius, vx, ax, vy, ay, seed]
            "asteroids": [],
            "score": 0,
            "last_spawn": now,
            "start_ticks": now,
            "alive": True,
        }

    state = reset()
    SHIP_X = 100
    SHIP_RADIUS = 18

    running = True
    while running:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if not state["alive"] and event.key == pygame.K_r:
                    state = reset()

        if state["alive"]:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                state["ship_y"] -= SHIP_SPEED
            if keys[pygame.K_DOWN]:
                state["ship_y"] += SHIP_SPEED
            state["ship_y"] = max(TUBE_MARGIN + SHIP_RADIUS,
                                  min(HEIGHT - TUBE_MARGIN - SHIP_RADIUS, state["ship_y"]))

            elapsed_s = (now - state["start_ticks"]) / 1000.0
            difficulty = min(elapsed_s / 120.0, 1.0)

            spawn_interval = ASTEROID_SPAWN_INTERVAL_START - difficulty * (
                ASTEROID_SPAWN_INTERVAL_START - ASTEROID_SPAWN_INTERVAL_MIN)

            # Spawn
            if now - state["last_spawn"] > spawn_interval:
                r = random.randint(18, 38)
                spawn_y = random.randint(TUBE_MARGIN + r, HEIGHT - TUBE_MARGIN - r)
                vx = -(ASTEROID_BASE_MIN_SPEED
                       + random.random() * (ASTEROID_BASE_MAX_SPEED - ASTEROID_BASE_MIN_SPEED)
                       + difficulty * 5)
                ax_range = 0.03 + difficulty * 0.07
                ax = random.choice([-1, 0, 0, 1]) * random.uniform(0, ax_range)
                vy_range = 0.5 + difficulty * 2.0
                vy = random.uniform(-vy_range, vy_range)
                ay_range = 0.02 + difficulty * 0.06
                asteroid_ay = random.choice([-1, 0, 0, 1]) * random.uniform(0, ay_range)
                seed = random.randint(0, 99999)
                state["asteroids"].append([float(WIDTH + r), float(spawn_y), r, vx, ax, vy, asteroid_ay, seed])
                state["last_spawn"] = now

            # Física
            tube_top, tube_bottom = TUBE_MARGIN, HEIGHT - TUBE_MARGIN
            for ast in state["asteroids"]:
                ast[3] += ast[4]
                if ast[3] > -1.0:
                    ast[3] = -1.0
                ast[0] += ast[3]
                ast[5] += ast[6]
                ast[5] = max(-6.0, min(6.0, ast[5]))
                ast[1] += ast[5]
                r = ast[2]
                if ast[1] - r < tube_top:
                    ast[1] = tube_top + r
                    ast[5] = abs(ast[5])
                elif ast[1] + r > tube_bottom:
                    ast[1] = tube_bottom - r
                    ast[5] = -abs(ast[5])

            state["asteroids"] = [a for a in state["asteroids"] if a[0] + a[2] > 0]
            state["score"] += 1

            # Colisión
            for ast in state["asteroids"]:
                dx = SHIP_X - ast[0]
                dy = state["ship_y"] - ast[1]
                if dx * dx + dy * dy < (SHIP_RADIUS + ast[2] - 6) ** 2:
                    state["alive"] = False
                    break

        # --- Dibujo ---
        screen.fill(DARK_GRAY)
        draw_stars(screen, stars)
        draw_tube(screen)

        for ast in state["asteroids"]:
            draw_asteroid(screen, int(ast[0]), int(ast[1]), ast[2], ast[7])

        if state["alive"]:
            draw_ship(screen, SHIP_X, int(state["ship_y"]))

        # HUD — puntuación
        screen.blit(font_score.render(f"Puntuación: {state['score'] // 10}", True, SCORE_COLOR), (10, 10))

        # HUD — dificultad
        if state["alive"]:
            diff_pct = int(min((now - state["start_ticks"]) / 1200.0, 100))
            diff_color = (int(100 + 155 * diff_pct / 100), int(255 - 200 * diff_pct / 100), 50)
            diff_surf = font_small.render(f"Dificultad: {diff_pct}%", True, diff_color)
            screen.blit(diff_surf, (WIDTH - diff_surf.get_width() - 10, 10))

        if not state["alive"]:
            game_over_screen(screen, font_big, font_small, state["score"] // 10)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
