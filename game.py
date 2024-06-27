import sys

import pygame
import random
import math
from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Machine, Water
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark


class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption("hidratate")
        self.liters = 3000
        self.destroyed = 0

        self.screen = pygame.display.set_mode((640, 480))
        self.display = pygame.Surface((320, 240))

        self.clock = pygame.time.Clock()

        self.movement = [False, False]

        self.assets = {
            "decor": load_images("tiles/decor"),
            "grass": load_images("tiles/grass"),
            "large_decor": load_images("tiles/large_decor"),
            "stone": load_images("tiles/stone"),
            "player": load_image("entities/player.png"),
            "background": load_image("background.png"),
            "machine/idle": Animation(load_images("entities/machine/idle"), img_dur=6),
            "clouds": load_images("clouds"),
            "player/idle": Animation(load_images("entities/player/idle"), img_dur=6),
            "player/run": Animation(load_images("entities/player/run"), img_dur=4),
            "player/jump": Animation(load_images("entities/player/jump")),
            "player/slide": Animation(load_images("entities/player/slide")),
            "player/wall_slide": Animation(load_images("entities/player/wall_slide")),
            "particle/leaf": Animation(
                load_images("particles/leaf"), img_dur=20, loop=False
            ),
            "particle/particle": Animation(
                load_images("particles/particle"), img_dur=6, loop=False
            ),
            "soda": load_image("soda.png"),
            "water": load_image("water_bottle.png"),
            "liters": load_image("water.png"),
            "target": load_image("target.png"),
        }

        self.clouds = Clouds(self.assets["clouds"], count=16)

        self.player = Player(self, (50, 50), (8, 15))

        self.tilemap = Tilemap(self, tile_size=16)
        self.load_level(0)
        self.screenshake = 0

    def load_level(self, map_id):
        self.tilemap.load("data/maps/" + str(map_id) + ".json")
        self.leaf_spawners = []
        for tree in self.tilemap.extract([("large_decor", 2)], keep=True):
            self.leaf_spawners.append(
                pygame.Rect(4 + tree["pos"][0], 4 + tree["pos"][1], 23, 13)
            )

        self.machines = []

        self.bottles = []

        for spawner in self.tilemap.extract([("spawners", 0), ("spawners", 1)]):
            if spawner["variant"] == 0:
                self.player.pos = spawner["pos"]
                self.player.air_time = 0
            else:
                self.machines.append(Machine(self, spawner["pos"], (8, 15)))

        for bottle in self.tilemap.extract([("water", 0)]):
            if bottle["variant"] == 0:
                self.bottles.append(Water(self, bottle["pos"], (8, 15)))

        self.sodas = []
        self.particles = []
        self.font = pygame.font.Font(None, 20)
        self.sparks = []
        self.scroll = [0, 0]
        self.dead = 0

    def run(self):
        score = 0
        score_by_bottle = self.liters / len(self.bottles)
        while True:
            self.display.blit(self.assets["background"], (0, 0))
            self.screenshake = max(0, self.screenshake - 1)

            if self.dead:
                self.dead += 1
                if self.dead > 40:
                    score = 0
                    self.destroyed = 0
                    self.load_level(0)

            self.scroll[0] += (
                self.player.rect().centerx
                - self.display.get_width() / 2
                - self.scroll[0]
            ) / 30
            self.scroll[1] += (
                self.player.rect().centery
                - self.display.get_height() / 2
                - self.scroll[1]
            ) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (
                        rect.x + random.random() * rect.width,
                        rect.y + random.random() * rect.height,
                    )
                    self.particles.append(
                        Particle(
                            self,
                            "particle",
                            pos,
                            velocity=[-0.1, 0.3],
                            frame=random.randint(0, 20),
                        )
                    )

            self.clouds.update()
            self.clouds.render(self.display, offset=render_scroll)

            self.tilemap.render(self.display, offset=render_scroll)

            for machine in self.machines.copy():
                kill = machine.update(self.tilemap, (0, 0))
                machine.render(self.display, offset=render_scroll)
                if kill:
                    self.machines.remove(machine)
                    self.destroyed += 1

            for bottle in self.bottles.copy():
                catch = bottle.update()
                bottle.render(self.display, offset=render_scroll)
                if catch:
                    self.bottles.remove(bottle)
                    score += score_by_bottle
            if not self.dead:
                self.player.update(
                    self.tilemap, (self.movement[1] - self.movement[0], 0)
                )
                self.player.render(self.display, offset=render_scroll)

            # [position,direction,time]
            for soda in self.sodas.copy():
                soda[0][0] += soda[1]
                soda[2] += 1
                img = self.assets["soda"]
                self.display.blit(
                    img,
                    (
                        soda[0][0] - img.get_width() / 2 - render_scroll[0],
                        soda[0][1] - img.get_height() / 2 - render_scroll[1],
                    ),
                )
                if self.tilemap.solid_check(soda[0]):
                    self.sodas.remove(soda)
                    for i in range(4):
                        self.sparks.append(
                            Spark(
                                soda[0],
                                random.random() - 0.5 + (math.pi if soda[1] > 0 else 0),
                                2 + random.random(),
                            )
                        )
                elif soda[2] > 360:
                    self.sodas.remove(soda)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().collidepoint(soda[0]):
                        self.sodas.remove(soda)
                        self.dead += 1
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(
                                Spark(
                                    self.player.rect().center,
                                    angle,
                                    2 + random.random(),
                                )
                            )
                            self.particles.append(
                                Particle(
                                    self,
                                    "particle",
                                    self.player.rect().center,
                                    velocity=[
                                        math.cos(angle + math.pi) * speed * 0.5,
                                        math.sin(angle + math.pi) * speed * 0.5,
                                    ],
                                    frame=random.randint(0, 7),
                                )
                            )
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == "leaf":
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.movement[0] = True
                    if event.key == pygame.K_RIGHT:
                        self.movement[1] = True
                    if event.key == pygame.K_UP:
                        self.player.jump()
                    if event.key == pygame.K_x:
                        self.player.dash()
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT:
                        self.movement[0] = False
                    if event.key == pygame.K_RIGHT:
                        self.movement[1] = False

            target_text = self.font.render(f"{self.destroyed}", True, (255, 255, 255))
            score_text = self.font.render(f"{score} mL", True, (255, 255, 255))
            screenshake_offset = (
                random.random() * self.screenshake - self.screenshake / 2,
                random.random() * self.screenshake - self.screenshake / 2,
            )
            self.display.blit(score_text, (32, 32))
            self.display.blit(self.assets["liters"], (10, 30))
            self.display.blit(target_text, (32, 55))
            self.display.blit(self.assets["target"], (10, 50))
            self.screen.blit(
                pygame.transform.scale(self.display, self.screen.get_size()),
                screenshake_offset,
            )

            pygame.display.update()
            self.clock.tick(60)


Game().run()
