"""Produces an interactive air hockey game
"""

__version__ = "$Id:$"
__docformat__ = "reStructuredText"

# Python imports
import math
import random

# Library imports
import pygame
from pygame.locals import *
from pygame.color import *

# pymunk imports
import pymunk
from pymunk import Vec2d
import pymunk.pygame_util


class Hockey(object):
    def __init__(self):
        # Powerups:
        self._gravity = False
        self._speed = False
        self._friction = False
        self._powerup_types = {
            'gravity': 1,
            'speed': 2,
            'friction': 3
        }

        # Options:
        # Hit cooldown
        self.cooldown_length = 200
        self.hit_length = 20
        # Screen Size
        pygame.init()
        mode = min(pygame.display.list_modes(), key=lambda x: math.hypot(x[0] - 1920, x[1] - 1080))
        self.screen_x, self.screen_y = mode
        # Radii
        self.puck_radius = 35
        self.powerup_radius = 20
        # FPS
        self.fps = 100
        # Speed
        self.max_velocity = 1700
        self.controlled_velocity = 750

        # Hit cooldown
        self._time_to_next_hit = self.cooldown_length
        self._time_to_cooldown = self.hit_length

        # Sprites
        self._puck_img = pygame.image.load("puck.png")
        self._paddle_img = pygame.image.load("paddle.png")

        # Screen size calculations
        self._rink_x = self.screen_x-300
        self._rink_y = self._rink_x/2
        self._padding_y = (self.screen_y-self._rink_y)/2

        # Space
        self._space = pymunk.Space()
        self._space.damping = 0.8

        # Physics
        # Time step
        self._dt = 1.0 / 60.0
        # Number of physics steps per screen frame
        self._physics_steps_per_frame = 1

        # pygame
        self._screen = pygame.display.set_mode((self.screen_x, self.screen_y), pygame.FULLSCREEN)
        # self._screen = pygame.display.set_mode((self.screen_x, self.screen_y))
        self._clock = pygame.time.Clock()

        self._draw_options = pymunk.pygame_util.DrawOptions(self._screen)

        # Static walls that line the rink
        self._add_static_scenery()

        # Collision Handler
        self.colltype_puck = 1
        self.colltype_powerup = 2
        handler = self._space.add_collision_handler(self.colltype_powerup, self.colltype_puck)
        handler.begin = self.powerup

        # Create the game objects
        self._paddle_1 = self._create_paddle(self._rink_x/8+150, self.screen_y/2)
        self._paddle_2 = self._create_paddle(self.screen_x-(self._rink_x/8+150), self.screen_y/2)
        self._pucks = []
        self._powerups = {}

        # Execution control
        self._running = True
        self._cooldown = False
        self._goal = False
        self._goal_player = 0
        self._countdown = True

        # Scores
        self._score_1 = 0
        self._score_2 = 0

        # Text
        self._small_font = pygame.font.SysFont(None, 72)
        self._big_font = pygame.font.SysFont(None, 144)

        self._update_score()

        self._big_text('')

        self._cooldown_text = self._small_font.render('0', True, (0, 0, 0))
        self._cooldown_textRect = self._cooldown_text.get_rect()
        self._cooldown_textRect.top = 5
        self._cooldown_textRect.right = self.screen_x-5

        # Start time
        self._last = pygame.time.get_ticks()
        self._last_powerup = pygame.time.get_ticks()
        self._last_powerup_created = pygame.time.get_ticks()

    def powerup(self, arbiter, space, data):
        if self._powerups[arbiter.shapes[0]] == self._powerup_types['gravity']:
            self._gravity = True
        if self._powerups[arbiter.shapes[0]] == self._powerup_types['speed']:
            self._speed = True
        if self._powerups[arbiter.shapes[0]] == self._powerup_types['friction']:
            self._friction = True

        self._last_powerup = pygame.time.get_ticks()
        space.remove(arbiter.shapes[0], arbiter.shapes[0].body)
        del self._powerups[arbiter.shapes[0]]
        return True

    def _check_powerups(self):
        if self._gravity and pygame.time.get_ticks() - self._last_powerup <= 10000:
            # Enable powerup
            self._space.gravity = (0, -400)
        else:
            # Disable powerup
            self._space.gravity = (0, 0)
            self._gravity = False
        if self._speed and pygame.time.get_ticks() - self._last_powerup <= 10000:
            # Enable powerup
            self.fps = 120
        else:
            # Disable powerup
            self.fps = 60
            self._speed = False
        if self._friction and pygame.time.get_ticks() - self._last_powerup <= 10000:
            # Enable powerup
            self._space.damping = 0.2
        else:
            # Disable powerup
            self._space.damping = 0.7
            self._speed = False

    def run(self):
        """
        The main loop of the game.
        :return: None
        """
        # Main loop
        while self._running:
            # Progress time forward
            for x in range(self._physics_steps_per_frame):
                self._space.step(self._dt)

            self._process_events()
            self._check_goals()
            self._clear_screen()
            self._draw_objects()
            pygame.display.flip()
            # Delay fixed time between frames
            self._clock.tick(self.fps)
            pygame.display.set_caption("fps: " + str(self._clock.get_fps()))

    def flip_y(self, y):
        """
        Flip a y coordinate about the midline of the screen
        :return: int
        """
        return -y+self.screen_y

    def _add_static_scenery(self):
        """
        Create the static bodies.
        :return: None
        """
        static_body = self._space.static_body
        points = [
            self._rink_x / 20 + 150,
            self._rink_x * 0.95 + 150,
            150,
            self._rink_x + 150,
            self._padding_y,
            self._rink_y * 0.7 + self._padding_y,
            self._rink_y + self._padding_y,
            self._padding_y + self._rink_y * 0.3,
            self.screen_x / 2
        ]
        static_lines = [
            pymunk.Segment(static_body, (points[0], points[4]), (points[1], points[4]), 0.0),
            pymunk.Segment(static_body, (points[1], points[4]), (points[1], points[7]), 0.0),
            pymunk.Segment(static_body, (points[1], points[5]), (points[1], points[6]), 0.0),
            pymunk.Segment(static_body, (points[1], points[6]), (points[0], points[6]), 0.0),
            pymunk.Segment(static_body, (points[0], points[4]), (points[0], points[7]), 0.0),
            pymunk.Segment(static_body, (points[0], points[5]), (points[0], points[6]), 0.0),
            pymunk.Segment(static_body, (points[2], points[7]), (points[0], points[7]), 0.0),
            pymunk.Segment(static_body, (points[2], points[5]), (points[0], points[5]), 0.0),
            pymunk.Segment(static_body, (points[3], points[7]), (points[1], points[7]), 0.0),
            pymunk.Segment(static_body, (points[3], points[5]), (points[1], points[5]), 0.0),
            pymunk.Segment(static_body, (points[2], points[7]), (points[2], points[5]), 0.0),
            pymunk.Segment(static_body, (points[3], points[7]), (points[3], points[5]), 0.0),
        ]
        sensor_lines = [
            pymunk.Segment(static_body, (points[0], points[7]), (points[0], points[5]), 0.0),
            pymunk.Segment(static_body, (points[1], points[7]), (points[1], points[5]), 0.0),
            pymunk.Segment(static_body, (points[8], points[4]), (points[8], points[6]), 0.0)
        ]
        for line in static_lines:
            line.elasticity = 0.8
            line.friction = 0.2
        for line in sensor_lines:
            line.sensor = True
        self._space.add(static_lines)
        self._space.add(sensor_lines)

    def _process_events(self):
        """
        Handle game and events like keyboard input. Call once per frame only.
        :return: None
        """
        # Handle quit and screenshot
        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self._running = False
            elif event.type == KEYDOWN and event.key == K_p:
                pygame.image.save(self._screen, "hockey.png")

        # Handle powerups
        if pygame.time.get_ticks() - self._last_powerup_created >= 10000:
            if random.randint(1,1000) == 1:
                x = random.randint(150, 150+self._rink_x)
                y = random.randint(self._padding_y, self._padding_y+self._rink_y)
        #        self._create_powerup(x, y, self.powerup_radius, random.randint(1, len(self._powerup_types)))
        # self._check_powerups()

        # Set velocity of Player 1
        mouse_y = pygame.mouse.get_pos()[1]
        max_y = self._padding_y+self._rink_y-(self.puck_radius-5)
        min_y = self._padding_y+(self.puck_radius-5)
        limited_mouse_y = max(min(max_y, mouse_y), min_y)
        limited_mouse_y = self.flip_y(limited_mouse_y)
        mouse_x = pygame.mouse.get_pos()[0]
        max_x = self.screen_x/2-(self.puck_radius-5)
        min_x = self._rink_x*0.05+150+(self.puck_radius-5)
        limited_mouse_x = max(min_x, min(max_x, mouse_x))
        velocity_x = limited_mouse_x-self._paddle_1.body.position[0]
        velocity_y = limited_mouse_y-self._paddle_1.body.position[1]
        scaled_velocity_x = velocity_x*(self.max_velocity/20)
        scaled_velocity_y = velocity_y*(self.max_velocity/20)
        magnitude = math.sqrt(round(velocity_x)**2+round(velocity_y)**2)
        if magnitude > 20:
            scaled_velocity_x = (velocity_x/magnitude)*1700
            scaled_velocity_y = (velocity_y/magnitude)*1700
        self._paddle_1.body.velocity = (scaled_velocity_x, scaled_velocity_y)

        # Set velocity of Player 2 by WASD keys
        velocity_x = 0
        velocity_y = 0
        key = pygame.key.get_pressed()
        if key[K_w] and self._paddle_2.body.position[1] <= self._padding_y+self._rink_y-(self.puck_radius-5):
            velocity_y = self.controlled_velocity
        if key[K_a] and self._paddle_2.body.position[0] >= self.screen_x/2+(self.puck_radius-5):
            velocity_x = -self.controlled_velocity
        if key[K_s] and self._paddle_2.body.position[1] >= self._padding_y+(self.puck_radius-5):
            velocity_y = -self.controlled_velocity
        if key[K_d] and self._paddle_2.body.position[0] <= self._rink_x*0.95+150-(self.puck_radius-5):
            velocity_x = self.controlled_velocity

        # Update cooldown text
        if self._time_to_next_hit <= 0:
            self._time_to_next_hit = 0
        self._cooldown_text = self._small_font.render(str(round(self._time_to_next_hit/6)), True, (0, 0, 0))
        self._cooldown_textRect = self._cooldown_text.get_rect()
        self._cooldown_textRect.top = 5
        self._cooldown_textRect.right = self.screen_x-5

        # Set velocity of Player 2 by Q key
        if key[K_q] and self._time_to_next_hit <= 0 <= self._time_to_cooldown and self._goal is False:
            self._time_to_cooldown -= 1
            velocity_x = (self._pucks[0].body.position[0]-self._paddle_2.body.position[0])
            velocity_y = (self._pucks[0].body.position[1]-self._paddle_2.body.position[1])
            scaled_velocity_x = 0
            scaled_velocity_y = 0
            magnitude = math.sqrt(round(velocity_x)**2+round(velocity_y)**2)
            if magnitude > 20:
                scaled_velocity_x = (velocity_x/magnitude)*self.max_velocity
                scaled_velocity_y = (velocity_y/magnitude)*self.max_velocity
            if self._paddle_2.body.position[0] <= self.screen_x/2+(self.puck_radius-5) and scaled_velocity_x < 0:
                scaled_velocity_x = 0
            self._paddle_2.body.velocity = (scaled_velocity_x, scaled_velocity_y)
            self._cooldown = True
        else:
            if self._cooldown:
                self._cooldown = False
                self._time_to_next_hit = self.cooldown_length
            self._paddle_2.body.velocity = (velocity_x, velocity_y)
            self._time_to_next_hit -= 1
            self._time_to_cooldown = self.hit_length

    def _check_goals(self):
        """
        Check for goals. Call once per frame only.
        :return: None
        """
        pucks_to_remove = []
        for puck in self._pucks:
            if puck.body.position.x < 185 or puck.body.position.x > self._rink_x + 115:
                pucks_to_remove.append(puck)
        for puck in pucks_to_remove:
            self._space.remove(puck, puck.body)
            self._pucks.remove(puck)
            if puck.body.position.x < 185:
                self._score_2 += 1
                self._goal_player = 2
            else:
                self._score_1 += 1
                self._goal_player = 1
            self._goal = True
            self._update_score()
            self._last = pygame.time.get_ticks()
            self._big_text('Goal!')

        # Handle wins
        if self._score_1 >= 7:
            self._win_1 = True
            self._win_2 = False
        elif self._score_2 >= 7:
            self._win_2 = True
            self._win_1 = False
        else:
            self._win_2 = False
            self._win_1 = False
        if self._win_1 or self._win_2:
            if self._goal and pygame.time.get_ticks() - self._last >= 1000:
                if self._win_1:
                    text = 'Player 1 Wins!'
                else:
                    text = 'Player 2 Wins!'
                self._big_text(text)
                if pygame.time.get_ticks() - self._last >= 2000:
                    self._goal_player = 2
                    self._reset()
                    self._score_1 = 0
                    self._score_2 = 0
                    self._update_score()
        else:
            if self._goal and pygame.time.get_ticks() - self._last >= 1000:
                self._reset()
        if self._countdown:
            self._start()

    def _create_puck(self, x):
        """
        Create a ball
        :return:
        """
        mass = 1
        inertia = pymunk.moment_for_circle(mass, 0, self.puck_radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        body.position = x, self.screen_y/2
        shape = pymunk.Circle(body, self.puck_radius, (0, 0))
        shape.elasticity = 0.8
        shape.friction = 0.2
        shape.collision_type = self.colltype_puck
        self._space.add(body, shape)
        self._pucks.append(shape)

    def _create_powerup(self, x, y, radius, type):
        """
        Create a powerup
        :return:
        """
        self._last_powerup_created = pygame.time.get_ticks()
        mass = 1
        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        body.position = x, y
        shape = pymunk.Circle(body, radius, (0, 0))
        shape.collision_type = self.colltype_powerup
        self._space.add(body, shape)
        self._powerups.update({shape: type})

    def _create_paddle(self, x, y):
        """
        Create a paddle
        :return: pymunk.Shape
        """
        mass = 1
        inertia = pymunk.moment_for_circle(mass, 0, self.puck_radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        body.position = x, y
        shape = pymunk.Circle(body, self.puck_radius, (0, 0))
        shape.elasticity = 0.8
        shape.friction = 0.2
        self._space.add(body, shape)
        return shape

    def _clear_screen(self):
        """
        Clears the screen.
        :return: None
        """
        self._screen.fill(THECOLORS["white"])

    def _draw_objects(self):
        """
        Draw the objects.
        :return: None
        """
        self._space.debug_draw(self._draw_options)

        # Draw text
        self._screen.blit(self._score_text, self._score_textRect)
        self._screen.blit(self._goal_text, self._goal_textRect)
        self._screen.blit(self._cooldown_text, self._cooldown_textRect)

        # Draw puck image
        for puck in self._pucks:
            p = puck.body.position
            p = Vec2d(p.x, -p.y+self.screen_y)
            offset = Vec2d(self._puck_img.get_size()) / 2.
            p = p - offset
            self._screen.blit(self._puck_img, p)

        # Draw paddle image
        p = self._paddle_1.body.position
        p = Vec2d(p.x, -p.y+self.screen_y)
        offset = Vec2d(self._paddle_img.get_size()) / 2.
        p = p - offset
        self._screen.blit(self._paddle_img, p)

        p = self._paddle_2.body.position
        p = Vec2d(p.x, -p.y+self.screen_y)
        offset = Vec2d(self._paddle_img.get_size()) / 2.
        p = p - offset
        self._screen.blit(self._paddle_img, p)

    def _reset(self):
        """
        Reset the puck after a goal.
        :return: None
        """
        self._goal = False
        self._big_text('')
        if self._goal_player == 2:
            y = self._rink_x/4+150
        else:
            y = self._rink_x*0.75+150
        self._create_puck(y)

    def _start(self):
        """
        Start the game with a countdown.
        :return: None
        """
        now = pygame.time.get_ticks()
        if now-self._last >= 4500:
            self._countdown = False
            self._big_text('')
        elif now-self._last >= 4000:
            self._big_text('GO!')
            if self._create_puck_on_count:
                self._create_puck(self._rink_x/4+150)
                self._create_puck_on_count = False
        elif now-self._last >= 3500:
            self._big_text('1')
            self._create_puck_on_count = True
        elif now-self._last >= 3000:
            self._big_text('2')
        elif now-self._last >= 2500:
            self._big_text('3')

    def _big_text(self, text):
        """
        Draw large, centered text on the screen.
        :return: None
        """
        self._goal_text = self._big_font.render(text, True, (0, 0, 0))
        self._goal_textRect = self._goal_text.get_rect()
        self._goal_textRect.center = (self.screen_x/2, self.screen_y/2)

    def _update_score(self):
        """
        Update the scoreboard.
        :return: None
        """
        score = 'Score: ' + str(self._score_1) + ' - ' + str(self._score_2)
        self._score_text = self._small_font.render(score, True, (0, 0, 0))
        self._score_textRect = self._score_text.get_rect()
        self._score_textRect.left = 5
        self._score_textRect.top = 5


if __name__ == '__main__':
    game = Hockey()
    game.run()
