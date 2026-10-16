
import random
import pygame


class Round:
    def __init__(self, min_wait_ms=1000, max_wait_ms=3000):
        self.wait_delay_ms = random.randint(min_wait_ms, max_wait_ms)
        self.state = "waiting"
        self.start_time = pygame.time.get_ticks()
        self.go_time = None
        self.reaction_ms = None
        self.false_start = False
        self._go_sound_played = False

    def update(self):
        if self.state == "waiting":
            now = pygame.time.get_ticks()

            if now - self.start_time >= self.wait_delay_ms:
                self.state = "go"
                self.go_time = now

    def register_input(self):
        now = pygame.time.get_ticks()

        if self.state == "waiting":
            self.false_start = True
            self.state = "result"
            self.reaction_ms = None
            return None

        if self.state == "go":
            self.reaction_ms = now - self.go_time
            self.state = "result"
            return self.reaction_ms

        return None
