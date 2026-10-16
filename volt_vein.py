#!/usr/bin/env python3
"""Volt Vein — neon light-cycle arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/workspace/artifacts/VOLT_VEIN_ElbowOS.mp4")
TITLE, HANDLE = "VOLT VEIN", "x.com/ElbowOS"
VOID = (6, 2, 16)
CYAN = (0, 255, 255)
MAG = (255, 0, 180)
LIME = (80, 255, 60)
GOLD = (255, 220, 40)
WHITE = (240, 250, 255)
ORANGE = (255, 120, 20)
SPEED = 6.5
TRAIL_THICK = 14

class Cycle:
    def __init__(self, x, y, color, is_player=False):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = 0, -SPEED if is_player else random.choice([-SPEED, SPEED, 0])
        if self.vx == 0 and self.vy == 0:
            self.vy = -SPEED
        self.trail = [(x, y)]
        self.alive = True
        self.is_player = is_player
        self.turn_cd = 0

    def update(self):
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        self.trail.append((self.x, self.y))
        if len(self.trail) > 400:
            self.trail.pop(0)
        # bounds
        if self.x < 40 or self.x > W - 40 or self.y < 120 or self.y > H - 180:
            self.alive = False
        self.turn_cd = max(0, self.turn_cd - 1)

    def draw(self, surf):
        if len(self.trail) > 1:
            pygame.draw.lines(surf, self.color, False, [(int(p[0]), int(p[1])) for p in self.trail], TRAIL_THICK)
            pygame.draw.lines(surf, WHITE, False, [(int(p[0]), int(p[1])) for p in self.trail[-8:]], 3)
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 16)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 8)

class Orb:
    def __init__(self):
        self.x = random.randint(100, W - 100)
        self.y = random.randint(200, H - 300)
        self.r = 18
        self.alive = True

    def draw(self, surf):
        if self.alive:
            pygame.draw.circle(surf, GOLD, (int(self.x), int(self.y)), self.r)
            pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.r - 6, 2)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        self.font_lg = pygame.font.SysFont("dejavusans", 68, bold=True)
        self.font_md = pygame.font.SysFont("dejavusans", 46, bold=True)
        self.font_sm = pygame.font.SysFont("dejavusans", 34)
        self.player = Cycle(W // 2, H - 300, CYAN, True)
        self.enemies = [
            Cycle(200, 400, MAG),
            Cycle(W - 200, 600, LIME),
            Cycle(400, 800, ORANGE),
        ]
        self.orbs = [Orb() for _ in range(6)]
        self.score = 0
        self.frame = 0
        self.auto_dir = 0

    def collide_trails(self, c):
        for other in [self.player] + self.enemies:
            if other is c or not other.alive:
                continue
            for px, py in other.trail[:-10]:
                if abs(c.x - px) < TRAIL_THICK and abs(c.y - py) < TRAIL_THICK:
                    return True
        # own trail (skip recent)
        for px, py in c.trail[:-15]:
            if abs(c.x - px) < TRAIL_THICK - 2 and abs(c.y - py) < TRAIL_THICK - 2:
                return True
        return False

    def auto_control(self):
        p = self.player
        if p.turn_cd > 0:
            return
        # simple dodge: prefer up, turn if wall or trail ahead
        dirs = [(0, -SPEED), (SPEED, 0), (-SPEED, 0), (0, SPEED)]
        safe = []
        for vx, vy in dirs:
            nx, ny = p.x + vx * 8, p.y + vy * 8
            if 50 < nx < W - 50 and 150 < ny < H - 200:
                hit = False
                for other in [self.player] + self.enemies:
                    for px, py in other.trail[-80:]:
                        if abs(nx - px) < 20 and abs(ny - py) < 20:
                            hit = True
                            break
                    if hit:
                        break
                if not hit:
                    safe.append((vx, vy))
        if safe:
            vx, vy = random.choice(safe)
            if (vx, vy) != (p.vx, p.vy):
                p.vx, p.vy = vx, vy
                p.turn_cd = 8

    def update(self, keys=None):
        self.frame += 1
        if RECORD or not PLAY:
            self.auto_control()
        elif keys and self.player.alive and self.player.turn_cd == 0:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.player.vx, self.player.vy = -SPEED, 0
                self.player.turn_cd = 6
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.player.vx, self.player.vy = SPEED, 0
                self.player.turn_cd = 6
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                self.player.vx, self.player.vy = 0, -SPEED
                self.player.turn_cd = 6
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.player.vx, self.player.vy = 0, SPEED
                self.player.turn_cd = 6
        self.player.update()
        if self.collide_trails(self.player):
            self.player.alive = False
        for e in self.enemies:
            if e.alive and e.turn_cd == 0 and random.random() < 0.04:
                e.vx, e.vy = random.choice([(0, -SPEED), (0, SPEED), (SPEED, 0), (-SPEED, 0)])
                e.turn_cd = 12
            e.update()
            if self.collide_trails(e):
                e.alive = False
        # collect orbs
        for o in self.orbs:
            if o.alive and abs(self.player.x - o.x) < 30 and abs(self.player.y - o.y) < 30:
                o.alive = False
                self.score += 150
                self.orbs.append(Orb())
        if self.player.alive:
            self.score += 1
        # respawn enemies slowly
        if self.frame % 90 == 0:
            self.enemies.append(Cycle(random.randint(100, W - 100), random.randint(200, 500), random.choice([MAG, LIME, ORANGE])))

    def draw(self):
        self.screen.fill(VOID)
        # faint grid
        for x in range(0, W, 60):
            pygame.draw.line(self.screen, (18, 8, 36), (x, 0), (x, H), 1)
        for y in range(0, H, 60):
            pygame.draw.line(self.screen, (18, 8, 36), (0, y), (W, y), 1)
        for o in self.orbs:
            o.draw(self.screen)
        for e in self.enemies:
            if e.alive:
                e.draw(self.screen)
        if self.player.alive:
            self.player.draw(self.screen)
        # overlays
        title = self.font_lg.render(TITLE, True, CYAN)
        self.screen.blit(title, title.get_rect(center=(W // 2, 70)))
        sc = self.font_md.render(f"SCORE {self.score}", True, GOLD)
        self.screen.blit(sc, sc.get_rect(center=(W // 2, 150)))
        handle = self.font_sm.render(HANDLE, True, WHITE)
        self.screen.blit(handle, handle.get_rect(center=(W // 2, H - 50)))
        if PLAY:
            hint = self.font_sm.render("ARROWS / WASD steer", True, (160, 170, 190))
            self.screen.blit(hint, hint.get_rect(center=(W // 2, H - 110)))
        pygame.display.flip()

    def play_interactive(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
            keys = pygame.key.get_pressed()
            self.update(keys)
            self.draw()
            clock.tick(FPS)
        pygame.quit()

    def record(self):
        os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = FPS * SECS
        try:
            for _ in range(frames):
                self.update()
                self.draw()
                raw = pygame.image.tostring(self.screen, "RGB")
                proc.stdin.write(raw)
            proc.stdin.close()
            err = proc.stderr.read().decode()
            rc = proc.wait()
            if rc != 0:
                raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
            print("wrote", OUT)
        except Exception as e:
            proc.kill()
            raise
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
