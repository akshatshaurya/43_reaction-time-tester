
import array
import math
import pygame

from .round import Round


WHITE = (255, 255, 255)
BLACK = (20, 24, 32)
GRAY = (90, 90, 90)
GREEN = (40, 180, 90)
BLUE = (50, 90, 170)
RED = (190, 55, 55)
YELLOW = (220, 170, 50)


DIFFICULTIES = {
    "Easy": {
        "rounds": 3,
        "min_wait": 1800,
        "max_wait": 3500,
    },
    "Medium": {
        "rounds": 5,
        "min_wait": 1000,
        "max_wait": 3000,
    },
    "Hard": {
        "rounds": 7,
        "min_wait": 1500,
        "max_wait": 4000,
    },
}


class GameEngine:
    def __init__(
        self,
        width,
        height,
        rounds_total=5,
        min_wait_ms=1000,
        max_wait_ms=3000,
    ):
        self.width = width
        self.height = height

        self.default_settings = {
            "rounds": rounds_total,
            "min_wait": min_wait_ms,
            "max_wait": max_wait_ms,
        }

        self.difficulty = "Medium"

        self.font = pygame.font.SysFont("Arial", 23)
        self.big_font = pygame.font.SysFont("Arial", 38)
        self.small_font = pygame.font.SysFont("Arial", 18)

        self.sounds = {}
        self._init_sounds()

        self.start_session(self.default_settings)
        self.screen = "menu"

    def _init_sounds(self):
        """Generate short sound effects without external audio files."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=22050,
                    size=-16,
                    channels=1,
                )

            sample_rate = 22050

            def make_sound(frequency, duration, volume=0.25):
                samples = array.array("h")
                count = int(sample_rate * duration)

                for i in range(count):
                    fade = min(
                        1.0,
                        (count - i) / (sample_rate * 0.03),
                    )
                    value = int(
                        32767
                        * volume
                        * fade
                        * math.sin(
                            2 * math.pi * frequency * i / sample_rate
                        )
                    )
                    samples.append(value)

                return pygame.mixer.Sound(
                    buffer=samples.tobytes()
                )

            self.sounds["go"] = make_sound(880, 0.15)
            self.sounds["false"] = make_sound(220, 0.25)
            self.sounds["end"] = make_sound(660, 0.35)

        except (pygame.error, OSError):
            # The game can still run if audio is unavailable.
            self.sounds = {}

    def play_sound(self, name):
        sound = self.sounds.get(name)

        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def start_session(self, settings=None):
        settings = settings or self.default_settings

        self.rounds_total = settings["rounds"]
        self.min_wait_ms = settings["min_wait"]
        self.max_wait_ms = settings["max_wait"]

        self.round = Round(
            self.min_wait_ms,
            self.max_wait_ms,
        )

        self.reaction_times = []
        self.attempt_results = []
        self.false_starts = 0

        self.result_shown_at = None
        self.result_pause_ms = 900

        self.game_over = False
        self.last_message = ""
        self.last_color = BLUE
        self.end_sound_played = False

        self.screen = "playing"

    def choose_difficulty(self, name):
        if name not in DIFFICULTIES:
            return

        self.difficulty = name
        self.start_session(DIFFICULTIES[name])

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.screen = "quit"
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.screen == "playing":
                    self.screen = "menu"
                elif self.screen == "results":
                    self.screen = "menu"
                elif self.screen == "menu":
                    self.screen = "quit"
                return

        if self.screen == "menu":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.choose_difficulty("Easy")
                elif event.key == pygame.K_2:
                    self.choose_difficulty("Medium")
                elif event.key == pygame.K_3:
                    self.choose_difficulty("Hard")
            return

        if self.screen == "results":
            if event.type == pygame.KEYDOWN:
                if event.key in (
                    pygame.K_r,
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    self.screen = "menu"
                elif event.key == pygame.K_q:
                    self.screen = "quit"
            return

        if self.screen != "playing":
            return

        is_click = event.type == pygame.MOUSEBUTTONDOWN
        is_space = (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_SPACE
        )

        if not (is_click or is_space):
            return

        if self.round.state not in ("waiting", "go"):
            return

        reaction_ms = self.round.register_input()
        self.result_shown_at = pygame.time.get_ticks()

        if reaction_ms is None:
            self.false_starts += 1
            self.attempt_results.append(None)

            self.last_message = "False start! Wait for green."
            self.last_color = RED
            self.play_sound("false")

        else:
            self.reaction_times.append(reaction_ms)
            self.attempt_results.append(reaction_ms)

            self.last_message = f"{reaction_ms} ms"
            self.last_color = BLUE

    def handle_input(self):
        # Mouse clicks and Space are handled as individual events.
        pass

    def update(self):
        if self.screen != "playing":
            return

        self.round.update()

        if (
            self.round.state == "go"
            and not self.round._go_sound_played
        ):
            self.play_sound("go")
            self.round._go_sound_played = True

        if (
            self.round.state == "result"
            and self.result_shown_at is not None
        ):
            now = pygame.time.get_ticks()

            if now - self.result_shown_at >= self.result_pause_ms:
                self._start_next_round()

    def _start_next_round(self):
        if len(self.attempt_results) >= self.rounds_total:
            self.game_over = True
            self.screen = "results"

            if not self.end_sound_played:
                self.play_sound("end")
                self.end_sound_played = True

            return

        self.round = Round(
            self.min_wait_ms,
            self.max_wait_ms,
        )
        self.result_shown_at = None

    def average_reaction_ms(self):
        if not self.reaction_times:
            return 0

        return round(
            sum(self.reaction_times) / len(self.reaction_times)
        )

    def draw_text(
        self,
        screen,
        text,
        font,
        color,
        y,
    ):
        surface = font.render(text, True, color)
        rect = surface.get_rect(
            center=(self.width // 2, y)
        )
        screen.blit(surface, rect)

    def render_menu(self, screen):
        screen.fill(BLACK)

        self.draw_text(
            screen,
            "REACTION TIME TESTER",
            self.big_font,
            WHITE,
            75,
        )
        self.draw_text(
            screen,
            "Choose difficulty",
            self.font,
            YELLOW,
            140,
        )
        self.draw_text(
            screen,
            "1 - Easy  |  3 rounds",
            self.font,
            WHITE,
            195,
        )
        self.draw_text(
            screen,
            "2 - Medium  |  5 rounds",
            self.font,
            WHITE,
            235,
        )
        self.draw_text(
            screen,
            "3 - Hard  |  7 rounds",
            self.font,
            WHITE,
            275,
        )
        self.draw_text(
            screen,
            "Press a number to start | ESC to exit",
            self.small_font,
            WHITE,
            335,
        )

    def render_results(self, screen):
        screen.fill(BLACK)

        self.draw_text(
            screen,
            "SESSION COMPLETE",
            self.big_font,
            GREEN,
            40,
        )

        # All supported difficulty levels fit on the results screen.
        y = 100

        for index, reaction in enumerate(
            self.attempt_results,
            start=1,
        ):
            if reaction is None:
                label = f"Round {index}: False start"
                color = RED
            else:
                label = f"Round {index}: {reaction} ms"
                color = WHITE

            self.draw_text(
                screen,
                label,
                self.font,
                color,
                y,
            )
            y += 29

        self.draw_text(
            screen,
            f"Average: {self.average_reaction_ms()} ms",
            self.font,
            YELLOW,
            325,
        )
        self.draw_text(
            screen,
            f"False starts: {self.false_starts}",
            self.small_font,
            RED,
            350,
        )
        self.draw_text(
            screen,
            "R / ENTER: Replay menu     Q: Quit",
            self.small_font,
            WHITE,
            380,
        )

    def render_game(self, screen):
        if self.round.state == "waiting":
            background = GRAY
            message = "Wait for green..."

        elif self.round.state == "go":
            background = GREEN
            message = "CLICK NOW!"

        else:
            background = self.last_color
            message = self.last_message

        screen.fill(background)

        self.draw_text(
            screen,
            message,
            self.big_font,
            WHITE,
            self.height // 2,
        )

        current_round = len(self.attempt_results) + 1

        self.draw_text(
            screen,
            f"Round {current_round}/{self.rounds_total}",
            self.font,
            WHITE,
            25,
        )

        self.draw_text(
            screen,
            f"Average: {self.average_reaction_ms()} ms",
            self.font,
            WHITE,
            58,
        )

        self.draw_text(
            screen,
            f"Difficulty: {self.difficulty}",
            self.small_font,
            WHITE,
            self.height - 25,
        )

    def render(self, screen):
        if self.screen == "menu":
            self.render_menu(screen)

        elif self.screen == "results":
            self.render_results(screen)

        elif self.screen == "playing":
            self.render_game(screen)
