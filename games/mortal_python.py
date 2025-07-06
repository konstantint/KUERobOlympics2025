import time
import board
import displayio
import random
import digitalio
from adafruit_display_text import label
import terminalio

# --- Initialisierung des Displays ---
display = board.DISPLAY
display.auto_refresh = False

# --- Initialisierung der Tasten ---
button_pins = {
    'b1': board.BUTTON_1, 'b2': board.BUTTON_2, 'b3': board.BUTTON_3,
    'up': board.SWITCH_UP, 'down': board.SWITCH_DOWN, 'left': board.SWITCH_LEFT,
    'right': board.SWITCH_RIGHT,
}
buttons = {}
button_prev_states = {}
for name, pin in button_pins.items():
    dio = digitalio.DigitalInOut(pin)
    dio.direction = digitalio.Direction.INPUT
    dio.pull = digitalio.Pull.UP
    buttons[name] = dio
    button_prev_states[name] = dio.value

# --- Spielkonstanten ---
SCREEN_WIDTH, SCREEN_HEIGHT = display.width, display.height
GROUND_Y = 220
BAR_HEIGHT = 10
GRAVITY = 350
JUMP_STRENGTH = 160

# Spielzustände
STATE_START_SCREEN, STATE_FIGHT, STATE_ROUND_OVER = 0, 1, 2

# Kämpfer-Konstanten
SPRITE_WIDTH, SPRITE_HEIGHT = 48, 80
PLAYER_SPEED = 5
MAX_HEALTH = 100
PUNCH_DAMAGE, KICK_DAMAGE, FIREBALL_DAMAGE = 5, 8, 7
BLOCK_DAMAGE_REDUCTION = 0.3
PUNCH_COOLDOWN, KICK_COOLDOWN, FIREBALL_COOLDOWN = 0.5, 0.8, 1.5

# Sprite-Indizes
S_IDLE_R, S_PUNCH_R, S_KICK_R, S_HIT_R = 0, 1, 2, 3
S_JUMP_R, S_CROUCH_R, S_BLOCK_R, S_JUMP_KICK_R, S_FIREBALL_R = 4, 5, 6, 7, 8
NUM_BASE_SPRITES = 9  # Anzahl der Basis-Sprites (für eine Richtung)

# --- Grafik-Setup ---
fighter_spritesheet = displayio.Bitmap(SPRITE_WIDTH * NUM_BASE_SPRITES * 2, SPRITE_HEIGHT, 16)
fighter_palette = displayio.Palette(10)
fighter_palette.make_transparent(0)
fighter_palette[2], fighter_palette[3], fighter_palette[4] = 0xFFFFFF, 0xFF0000, 0x0000FF
fighter_palette[5] = 0xFFA500  # Feuerball-Farbe

def fill_rect(bm, x, y, w, h, c):
    for i in range(x, x + w):
        for j in range(y, y + h):
            if 0 <= i < bm.width and 0 <= j < bm.height: bm[i, j] = c

def draw_fighter(bitmap, offset_x, color_index):
    # IDLE
    x = offset_x + S_IDLE_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 10, 24, 6, 20, 2); fill_rect(bitmap, x + 33, 24, 6, 20, 2); fill_rect(bitmap, x + 15, 52, 8, 25, 2); fill_rect(bitmap, x + 25, 52, 8, 25, 2)
    # PUNCH
    x = offset_x + S_PUNCH_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 10, 24, 6, 20, 2); fill_rect(bitmap, x + 33, 30, 14, 6, 2); fill_rect(bitmap, x + 15, 52, 8, 25, 2); fill_rect(bitmap, x + 25, 52, 8, 25, 2)
    # KICK
    x = offset_x + S_KICK_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 10, 24, 6, 20, 2); fill_rect(bitmap, x + 33, 24, 6, 20, 2); fill_rect(bitmap, x + 15, 52, 8, 25, 2); fill_rect(bitmap, x + 25, 52, 18, 8, 2)
    # HIT
    x = offset_x + S_HIT_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 22, 10, 12, 12, 2); fill_rect(bitmap, x + 19, 22, 18, 30, color_index); fill_rect(bitmap, x + 14, 24, 6, 20, 2); fill_rect(bitmap, x + 37, 24, 6, 20, 2); fill_rect(bitmap, x + 19, 52, 8, 25, 2); fill_rect(bitmap, x + 29, 52, 8, 25, 2)
    # JUMP
    x = offset_x + S_JUMP_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 10, 24, 6, 20, 2); fill_rect(bitmap, x + 33, 24, 6, 20, 2); fill_rect(bitmap, x + 15, 52, 8, 15, 2); fill_rect(bitmap, x + 25, 52, 8, 15, 2)
    # CROUCH
    x = offset_x + S_CROUCH_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 30, 12, 12, 2); fill_rect(bitmap, x + 15, 42, 18, 20, color_index); fill_rect(bitmap, x + 10, 44, 6, 15, 2); fill_rect(bitmap, x + 33, 44, 6, 15, 2); fill_rect(bitmap, x + 15, 62, 8, 15, 2); fill_rect(bitmap, x + 25, 62, 8, 15, 2)
    # BLOCK
    x = offset_x + S_BLOCK_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 25, 28, 15, 6, 2); fill_rect(bitmap, x + 25, 42, 15, 6, 2); fill_rect(bitmap, x + 15, 52, 8, 25, 2); fill_rect(bitmap, x + 25, 52, 8, 25, 2)
    # JUMP KICK
    x = offset_x + S_JUMP_KICK_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 10, 24, 6, 20, 2); fill_rect(bitmap, x + 25, 52, 18, 8, 2); fill_rect(bitmap, x + 15, 52, 8, 15, 2)
    # FIREBALL
    x = offset_x + S_FIREBALL_R * SPRITE_WIDTH
    fill_rect(bitmap, x + 18, 10, 12, 12, 2); fill_rect(bitmap, x + 15, 22, 18, 30, color_index); fill_rect(bitmap, x + 20, 30, 18, 6, 2); fill_rect(bitmap, x + 30, 28, 6, 10, 2); fill_rect(bitmap, x + 15, 52, 8, 25, 2); fill_rect(bitmap, x + 25, 52, 8, 25, 2)

    for i in range(NUM_BASE_SPRITES):
        src_x, dst_x = i * SPRITE_WIDTH, (i + NUM_BASE_SPRITES) * SPRITE_WIDTH
        for y in range(SPRITE_HEIGHT):
            for x_s in range(SPRITE_WIDTH):
                bitmap[dst_x + x_s, y] = bitmap[src_x + (SPRITE_WIDTH - 1 - x_s), y]

draw_fighter(fighter_spritesheet, 0, 3)

# --- Haupt-Display-Gruppen ---
main_group = displayio.Group()
try:
    main_group.append(displayio.TileGrid(displayio.OnDiskBitmap("/background.bmp"), pixel_shader=displayio.OnDiskBitmap.pixel_shader))
except (OSError, TypeError):
    bg_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1); bg_bitmap.fill(0)
    bg_palette = displayio.Palette(1); bg_palette[0] = 0x101030 # Dunkelblauer Hintergrund
    main_group.append(displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette))
projectiles_group = displayio.Group()
main_group.append(projectiles_group)
ui_group = displayio.Group()

# --- UI Elemente ---
health_bar_sheet = displayio.Bitmap(1, BAR_HEIGHT * 3, 3); hp_palette = displayio.Palette(3)
hp_palette[0] = 0x555555; hp_palette[1] = 0xFF0000; hp_palette[2] = 0x0000FF
for i in range(3): fill_rect(health_bar_sheet, 0, i * BAR_HEIGHT, 1, BAR_HEIGHT, i)
p1_health_bar = displayio.TileGrid(health_bar_sheet, pixel_shader=hp_palette, width=MAX_HEALTH, height=1, tile_width=1, tile_height=BAR_HEIGHT, default_tile=1, x=12, y=12)
p2_health_bar = displayio.TileGrid(health_bar_sheet, pixel_shader=hp_palette, width=MAX_HEALTH, height=1, tile_width=1, tile_height=BAR_HEIGHT, default_tile=2, x=SCREEN_WIDTH - MAX_HEALTH - 12, y=12)
round_text = label.Label(terminalio.FONT, text="", scale=4, color=0xFFFF00)
round_text.anchor_point = (0.5, 0.5); round_text.anchored_position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
ui_group.append(p1_health_bar); ui_group.append(p2_health_bar); ui_group.append(round_text)

# --- Projektil Klasse ---
class Projectile:
    def __init__(self, x, y, facing_left):
        self.w, self.h = 16, 16
        bitmap = displayio.Bitmap(self.w, self.h, 16)
        fill_rect(bitmap, 4, 4, 8, 8, 5)
        self.sprite = displayio.TileGrid(bitmap, pixel_shader=fighter_palette, x=int(x), y=int(y))
        self.vx = -150 if facing_left else 150
    def update(self, dt): self.sprite.x += int(self.vx * dt)

# --- Fighter Klasse ---
class Fighter:
    def __init__(self, x, y, is_player2=False):
        self.x, self.y, self.is_player2 = x, y, is_player2
        self.vy = 0; self.health = MAX_HEALTH; self.facing_left = False
        self.state, self.state_timer = "idle", 0
        self.punch_cd, self.kick_cd, self.fireball_cd = 0, 0, 0
        self.ai_next_move_time = 0
        self.input_history = []
        self.palette = displayio.Palette(len(fighter_palette))
        for i, c in enumerate(fighter_palette): self.palette[i] = c
        self.palette.make_transparent(0)
        self.palette[3] = fighter_palette[4 if is_player2 else 3]
        self.sprite = displayio.TileGrid(fighter_spritesheet, pixel_shader=self.palette, width=1, height=1, tile_width=SPRITE_WIDTH, tile_height=SPRITE_HEIGHT)
        self.update_sprite_pos()

    def update_sprite_pos(self): self.sprite.x, self.sprite.y = int(self.x), int(self.y)
    def can_act(self): return self.state in ("idle", "crouch", "block") and self.y >= GROUND_Y - SPRITE_HEIGHT
    def move(self, dx): self.x = max(0, min(SCREEN_WIDTH - SPRITE_WIDTH, self.x + dx))
    def punch(self):
        if self.can_act() and self.punch_cd <= 0: self.state, self.state_timer, self.punch_cd = "punch", 0.3, PUNCH_COOLDOWN
    def kick(self):
        if self.can_act() and self.kick_cd <= 0: self.state, self.state_timer, self.kick_cd = "kick", 0.5, KICK_COOLDOWN
    def jump_kick(self):
        if self.state == "jump" and self.kick_cd <= 0: self.state, self.state_timer, self.kick_cd = "jump_kick", 0.6, KICK_COOLDOWN
    def jump(self):
        if self.can_act(): self.vy = JUMP_STRENGTH; self.state = "jump"
    def crouch(self, crouching):
        if crouching:
            if self.can_act(): self.state = "crouch"
        elif self.state == "crouch": self.state = "idle"
    def block(self, blocking):
        if blocking:
            if self.can_act(): self.state = "block"
        elif self.state == "block": self.state = "idle"
    def fireball(self):
        if self.can_act() and self.fireball_cd <= 0:
            self.state, self.state_timer, self.fireball_cd = "fireball", 0.4, FIREBALL_COOLDOWN
            proj_x = self.x if self.facing_left else self.x + SPRITE_WIDTH
            return Projectile(proj_x, self.y + 30, self.facing_left)
        return None
    def get_hit(self, damage):
        if self.state != "hit":
            if self.state == "block": damage *= BLOCK_DAMAGE_REDUCTION
            self.health = max(0, self.health - damage); self.state, self.state_timer = "hit", 0.4
    def face_opponent(self, opponent): self.facing_left = self.x > opponent.x

    def update(self, dt):
        # Cooldowns aktualisieren
        for cd in ['punch_cd', 'kick_cd', 'fireball_cd']: setattr(self, cd, max(0, getattr(self, cd) - dt))

        # Zustands-Timer und Übergänge bei Ablauf aktualisieren
        if self.state_timer > 0:
            self.state_timer -= dt
            if self.state_timer <= 0:
                # Wenn eine zeitgesteuerte Aktion (Angriff, Treffer) endet...
                if self.state in ('punch', 'kick', 'fireball', 'hit', 'jump_kick'):
                    # Prüfen, ob wir in der Luft sind. Wenn ja, in einen neutralen Sprungzustand zurückkehren.
                    if self.y < GROUND_Y - SPRITE_HEIGHT:
                        self.state = 'jump'
                    else: # Ansonsten in den Ruhezustand wechseln.
                        self.state = 'idle'

        # Physik (Schwerkraft) anwenden, wenn in der Luft. Dies ist jetzt unabhängig vom "hit"-Zustand.
        if self.y < GROUND_Y - SPRITE_HEIGHT or self.vy != 0:
            self.y -= self.vy * dt
            self.vy -= GRAVITY * dt
            # Auf Landung prüfen
            if self.y >= GROUND_Y - SPRITE_HEIGHT:
                self.y = GROUND_Y - SPRITE_HEIGHT
                self.vy = 0
                # Wenn wir aus einem neutralen Sprung/Kick gelandet sind, in den Ruhezustand wechseln.
                # Wenn wir landen, während wir getroffen werden, bleiben wir im "hit"-Zustand,
                # bis der Timer abläuft (wird oben behandelt).
                if self.state in ('jump', 'jump_kick'):
                     self.state = 'idle'

        # Sprite basierend auf dem finalen Zustand aktualisieren
        base_sprite_map = {"punch": S_PUNCH_R, "kick": S_KICK_R, "hit": S_HIT_R, "jump": S_JUMP_R,
                           "crouch": S_CROUCH_R, "block": S_BLOCK_R, "jump_kick": S_JUMP_KICK_R,
                           "fireball": S_FIREBALL_R}
        base_sprite = base_sprite_map.get(self.state, S_IDLE_R)
        self.sprite[0, 0] = base_sprite if not self.facing_left else base_sprite + NUM_BASE_SPRITES
        self.update_sprite_pos()

    def get_body_box(self):
        if self.state == "crouch": return (self.x + 10, self.y + 30, SPRITE_WIDTH - 20, SPRITE_HEIGHT - 30)
        return (self.x + 10, self.y, SPRITE_WIDTH - 20, SPRITE_HEIGHT)
    def get_hit_box(self):
        if self.state not in ("punch", "kick", "jump_kick"): return None
        x_off, w = (35, 20) if not self.facing_left else (-10, 20)
        if self.state == "punch": return (self.x + x_off, self.y + 25, w, 15)
        if self.state == "kick": return (self.x + x_off, self.y + 50, w, 20)
        if self.state == "jump_kick": return (self.x + x_off, self.y + 50, w, 20)

    def run_ai(self, opponent, projectiles):
        if time.monotonic() < self.ai_next_move_time: return
        self.ai_next_move_time = time.monotonic() + random.uniform(0.1, 0.4)
        dist = abs(self.x - opponent.x)
        if self.state == "block": self.block(False)
        for p in projectiles:
            if (p.vx > 0 and self.x > p.sprite.x) or (p.vx < 0 and self.x < p.sprite.x):
                if abs(self.x - p.sprite.x) < 100: self.jump(); return
        if opponent.state in ("punch", "kick", "jump_kick") and dist < 60:
            if random.random() < 0.8: self.block(True); return
        if dist > 120 and self.fireball_cd <= 0:
            if random.random() < 0.4: return self.fireball()
        elif dist > 80: self.move(PLAYER_SPEED if not self.facing_left else -PLAYER_SPEED)
        elif dist < 40:
            if random.random() < 0.5: self.punch()
            else: self.kick()
        else:
            action = random.choice([self.punch, self.kick, self.jump])
            action()
        return None

# --- Spiel-Setup & Funktionen ---
game_state = STATE_START_SCREEN
player1 = Fighter(50, GROUND_Y - SPRITE_HEIGHT)
player2 = Fighter(SCREEN_WIDTH - 50 - SPRITE_WIDTH, GROUND_Y - SPRITE_HEIGHT, is_player2=True)
main_group.append(player1.sprite); main_group.append(player2.sprite)
main_group.append(ui_group)
active_projectiles = []

def check_hit(attacker, defender):
    hit_box = attacker.get_hit_box()
    if not hit_box: return False
    body_box = defender.get_body_box()
    hx, hy, hw, hh = hit_box
    bx, by, bw, bh = body_box
    if hx < bx + bw and hx + hw > bx and hy < by + bh and hy + hh > by:
        damage = 0
        if attacker.state == "kick": damage = KICK_DAMAGE
        elif attacker.state == "punch": damage = PUNCH_DAMAGE
        elif attacker.state == "jump_kick": damage = KICK_DAMAGE + 5
        defender.get_hit(damage); return True
    return False

def check_fireball_input(fighter):
    history = fighter.input_history; now = time.monotonic()
    if len(history) < 3: return False
    t_punch, act_punch = history[-1]; t_fwd, act_fwd = history[-2]; t_down, act_down = history[-3]
    dir = 'right' if not fighter.facing_left else 'left'
    if (now - t_punch < 0.2 and act_punch == 'b1' and
        t_punch - t_fwd < 0.2 and act_fwd == dir and
        t_fwd - t_down < 0.2 and act_down == 'down'):
        fighter.input_history.clear(); return True
    return False

def reset_round():
    global active_projectiles, last_p1_health, last_p2_health
    for p in active_projectiles: projectiles_group.remove(p.sprite)
    active_projectiles.clear()
    for p, x_pos in [(player1, 50), (player2, SCREEN_WIDTH - 50 - SPRITE_WIDTH)]:
        p.x, p.health = x_pos, MAX_HEALTH
        p.y, p.vy = GROUND_Y - SPRITE_HEIGHT, 0
        p.state, p.state_timer = "idle", 0
        p.punch_cd, p.kick_cd, p.fireball_cd = 0, 0, 0
        p.input_history.clear()
    last_p1_health, last_p2_health = -1, -1

# --- Hauptschleife ---
last_time = time.monotonic()
last_p1_health, last_p2_health = -1, -1

while True:
    now = time.monotonic(); dt = now - last_time; last_time = now
    button_pressed = {}
    for name, pin in buttons.items():
        current_state = pin.value
        pressed = button_prev_states[name] and not current_state
        button_pressed[name] = pressed
        button_prev_states[name] = current_state
        if pressed and name in ('b1', 'b2', 'up', 'down', 'left', 'right'):
            player1.input_history.append((now, name))
            if len(player1.input_history) > 10: player1.input_history.pop(0)

    if game_state == STATE_START_SCREEN:
        round_text.text = "MORTAL PYTHON"; player1.sprite.hidden = True; player2.sprite.hidden = True
        if button_pressed['b1']:
            game_state = STATE_FIGHT; reset_round()
            round_text.text = "FIGHT!"; player1.sprite.hidden = False; player2.sprite.hidden = False
            display.refresh(); time.sleep(1.0); round_text.text = ""

    elif game_state == STATE_FIGHT:
        player1.block(not buttons['b3'].value)
        player1.crouch(not buttons['down'].value)
        if player1.state == 'idle':
            if not buttons['left'].value: player1.move(-PLAYER_SPEED)
            if not buttons['right'].value: player1.move(PLAYER_SPEED)
        if button_pressed['up']: player1.jump()
        if button_pressed['b2']:
            if player1.state == 'jump': player1.jump_kick()
            else: player1.kick()
        if button_pressed['b1']:
            if check_fireball_input(player1):
                new_proj = player1.fireball()
                if new_proj: active_projectiles.append(new_proj); projectiles_group.append(new_proj.sprite)
            else:
                player1.punch()

        new_proj_ai = player2.run_ai(player1, active_projectiles)
        if new_proj_ai: active_projectiles.append(new_proj_ai); projectiles_group.append(new_proj_ai.sprite)
        player1.face_opponent(player2); player2.face_opponent(player1)
        player1.update(dt); player2.update(dt)

        p1_box = player1.get_body_box(); p2_box = player2.get_body_box()
        if p1_box and p2_box and p1_box[0] < p2_box[0] + p2_box[2] and p1_box[0] + p1_box[2] > p2_box[0]:
            overlap = (p1_box[0] + p1_box[2]) - p2_box[0]
            if overlap > 0:
                pushback = overlap / 2; player1.x -= pushback; player2.x += pushback
        check_hit(player1, player2); check_hit(player2, player1)

        for p in active_projectiles[:]:
            p.update(dt)
            hit = False
            for fighter in [player1, player2]:
                body = fighter.get_body_box()
                if (p.sprite.x < body[0] + body[2] and p.sprite.x + p.w > body[0] and
                        p.sprite.y < body[1] + body[3] and p.sprite.y + p.h > body[1]):
                    fighter.get_hit(FIREBALL_DAMAGE); hit = True; break
            if hit or p.sprite.x < -p.w or p.sprite.x > SCREEN_WIDTH:
                active_projectiles.remove(p); projectiles_group.remove(p.sprite)

        if int(player1.health) != last_p1_health:
            last_p1_health = int(player1.health)
            for i in range(MAX_HEALTH): p1_health_bar[i, 0] = 1 if i < last_p1_health else 0
        if int(player2.health) != last_p2_health:
            last_p2_health = int(player2.health)
            for i in range(MAX_HEALTH): p2_health_bar[i, 0] = 2 if i < last_p2_health else 0

        if player1.health <= 0: game_state = STATE_ROUND_OVER; round_text.text = "PLAYER 2 WINS"
        elif player2.health <= 0: game_state = STATE_ROUND_OVER; round_text.text = "PLAYER 1 WINS"

        try:
            p1_idx = main_group.index(player1.sprite)
            p2_idx = main_group.index(player2.sprite)
            if (player1.y > player2.y and p1_idx < p2_idx) or (player1.y <= player2.y and p1_idx > p2_idx):
                main_group.pop(p1_idx)
                main_group.insert(p2_idx, player1.sprite)
        except ValueError:
            pass

    elif game_state == STATE_ROUND_OVER:
        if button_pressed['b1']: game_state = STATE_START_SCREEN

    display.root_group = main_group
    display.refresh()
