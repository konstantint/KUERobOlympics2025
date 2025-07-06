import time
import board
import displayio
import digitalio
import random
from adafruit_display_text import label
from terminalio import FONT

# --- Spielkonstanten ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
TILE_SIZE = 16 # Kachelgröße in Pixel

# Sicherstellen, dass die Kachelgröße in die Bildschirmgröße passt
MAZE_WIDTH = SCREEN_WIDTH // TILE_SIZE  # 20 Kacheln
MAZE_HEIGHT = SCREEN_HEIGHT // TILE_SIZE # 15 Kacheln

# Spielzustände
STATE_START_SCREEN = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_LEVEL_CLEAR = 3

# Kacheltypen für das Labyrinth
TILE_WALL = 0
TILE_EMPTY = 1
TILE_DOT = 2

# Bewegungsrichtungen
DIR_NONE = 0
DIR_UP = 1
DIR_DOWN = 2
DIR_LEFT = 3
DIR_RIGHT = 4

# --- Labyrinth-Layout ---
# 0 = Wand, 1 = Leerer Gang, 2 = Punkt
# Das Layout ist 15 Zeilen hoch und 20 Spalten breit.
maze_layout = (
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 0),
    (0, 2, 0, 0, 2, 0, 0, 0, 2, 0, 0, 2, 0, 0, 0, 2, 0, 0, 2, 0),
    (0, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 2, 0),
    (0, 2, 2, 2, 2, 0, 2, 0, 0, 0, 0, 0, 0, 2, 0, 2, 2, 2, 2, 0),
    (0, 0, 0, 0, 2, 0, 2, 2, 2, 0, 0, 2, 2, 2, 0, 2, 0, 0, 0, 0),
    (1, 1, 1, 0, 2, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 2, 0, 1, 1, 1),
    (0, 0, 0, 0, 2, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 2, 0, 0, 0, 0),
    (1, 1, 1, 0, 2, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 2, 0, 1, 1, 1),
    (0, 0, 0, 0, 2, 0, 1, 0, 2, 2, 2, 2, 0, 1, 0, 2, 0, 0, 0, 0),
    (0, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 0),
    (0, 2, 0, 0, 2, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 2, 0, 0, 2, 0),
    (0, 2, 2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 2, 2, 0),
    (0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)

# --- Hardware-Initialisierung ---
display = board.DISPLAY
display.auto_refresh = False

# Tasten initialisieren
button_1 = digitalio.DigitalInOut(board.BUTTON_1)
button_1.switch_to_input(pull=digitalio.Pull.UP)

dpad_up = digitalio.DigitalInOut(board.SWITCH_UP)
dpad_up.switch_to_input(pull=digitalio.Pull.UP)
dpad_down = digitalio.DigitalInOut(board.SWITCH_DOWN)
dpad_down.switch_to_input(pull=digitalio.Pull.UP)
dpad_left = digitalio.DigitalInOut(board.SWITCH_LEFT)
dpad_left.switch_to_input(pull=digitalio.Pull.UP)
dpad_right = digitalio.DigitalInOut(board.SWITCH_RIGHT)
dpad_right.switch_to_input(pull=digitalio.Pull.UP)

# --- Grafiken erstellen (Spritesheets) ---

# Farbpalette
# 0: Schwarz, 1: Blau (Wand), 2: Gelb (Pacman), 3: Weiß (Punkt), 4: Rot (Geist)
palette = displayio.Palette(5)
palette[0] = 0x000000  # Schwarz (Hintergrund)
palette[1] = 0x0000FF  # Blau
palette[2] = 0xFFFF00  # Gelb
palette[3] = 0xFFFFFF  # Weiß
palette[4] = 0xFF0000  # Rot

# Labyrinth-Kachel-Bitmap
maze_bitmap = displayio.Bitmap(TILE_SIZE * 3, TILE_SIZE, len(palette))
# Kachel 0: Wand
for x in range(TILE_SIZE):
    for y in range(TILE_SIZE):
        if x == 0 or x == TILE_SIZE - 1 or y == 0 or y == TILE_SIZE - 1:
            maze_bitmap[x, y] = 1
# Kachel 1: Leer
# (ist bereits schwarz/0, also nichts zu tun)
# Kachel 2: Punkt
dot_x, dot_y = (TILE_SIZE * 2) + TILE_SIZE // 2, TILE_SIZE // 2
maze_bitmap[dot_x-1, dot_y] = 3
maze_bitmap[dot_x, dot_y-1] = 3
maze_bitmap[dot_x, dot_y] = 3
maze_bitmap[dot_x+1, dot_y] = 3
maze_bitmap[dot_x, dot_y+1] = 3


# Pac-Man-Bitmap (4 Richtungen x 2 Animationsphasen = 8 Kacheln)
pacman_bitmap = displayio.Bitmap(TILE_SIZE * 8, TILE_SIZE, len(palette))
# Einfache Pac-Man-Form (Kreis mit fehlendem Keil)
# Kachel 0-1: Rechts, 2-3: Links, 4-5: Runter, 6-7: Hoch
center = TILE_SIZE // 2
radius = TILE_SIZE // 2 - 1
for frame in range(8):
    offset_x = frame * TILE_SIZE
    for x in range(TILE_SIZE):
        for y in range(TILE_SIZE):
            dist_sq = (x - center) ** 2 + (y - center) ** 2
            if dist_sq < radius ** 2:
                # Logik für Mundöffnung (je nach Frame und Richtung)
                is_mouth_open = frame % 2 == 0
                if not is_mouth_open:
                     pacman_bitmap[offset_x + x, y] = 2 # Geschlossener Mund
                else:
                    # Rechts (frame 0)
                    if frame // 2 == 0 and y > x: continue
                    # Links (frame 2)
                    if frame // 2 == 1 and y < x: continue
                    # Runter (frame 4)
                    if frame // 2 == 2 and x > y: continue
                    # Hoch (frame 6)
                    if frame // 2 == 3 and x < y: continue
                    pacman_bitmap[offset_x + x, y] = 2

# Geist-Bitmap (2 Animationsphasen)
ghost_bitmap = displayio.Bitmap(TILE_SIZE * 2, TILE_SIZE, len(palette))
for frame in range(2):
    offset_x = frame * TILE_SIZE
    for x in range(2, TILE_SIZE - 2):
        for y in range(2, TILE_SIZE):
            ghost_bitmap[offset_x + x, y] = 4
    # Augen
    ghost_bitmap[offset_x + 5, 5] = 3
    ghost_bitmap[offset_x + 10, 5] = 3
    if frame == 1: # "wackelnde" untere Kante
        ghost_bitmap[offset_x + 2, TILE_SIZE - 1] = 0
        ghost_bitmap[offset_x + 6, TILE_SIZE - 1] = 0
        ghost_bitmap[offset_x + 10, TILE_SIZE - 1] = 0


# --- Display-Gruppen und Objekte ---
main_group = displayio.Group()

# Labyrinth TileGrid
maze_grid = displayio.TileGrid(
    maze_bitmap,
    pixel_shader=palette,
    width=MAZE_WIDTH,
    height=MAZE_HEIGHT,
    tile_width=TILE_SIZE,
    tile_height=TILE_SIZE
)
main_group.append(maze_grid)

# Pac-Man TileGrid
pacman_sprite = displayio.TileGrid(
    pacman_bitmap,
    pixel_shader=palette,
    tile_width=TILE_SIZE,
    tile_height=TILE_SIZE
)
main_group.append(pacman_sprite)

# Geist TileGrid
ghost_sprite = displayio.TileGrid(
    ghost_bitmap,
    pixel_shader=palette,
    tile_width=TILE_SIZE,
    tile_height=TILE_SIZE
)
main_group.append(ghost_sprite)

# UI Text-Labels
score_label = label.Label(FONT, text="Punkte: 0", color=0xFFFFFF, x=5, y=5)
main_group.append(score_label)

lives_label = label.Label(FONT, text="Leben: 3", color=0xFFFFFF, x=250, y=5)
main_group.append(lives_label)

# Mitteilungs-Label (für Game Over etc.)
message_label = label.Label(FONT, text="", color=0xFFFF00, scale=2)
message_label.anchor_point = (0.5, 0.5)
message_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
main_group.append(message_label)

display.root_group = main_group

# --- Spielvariablen ---
game_state = STATE_START_SCREEN
score = 0
lives = 3
total_dots = 0

player = {
    "x": 1, "y": 1, # Gitter-Koordinaten
    "direction": DIR_RIGHT,
    "next_direction": DIR_NONE,
    "animation_frame": 0
}

ghost = {
    "x": 10, "y": 7, # Gitter-Koordinaten
    "direction": DIR_LEFT,
    "animation_frame": 0
}

# --- Hilfsfunktionen ---
def reset_level():
    """Setzt das Level zurück (Punkte, Positionen etc.)."""
    global total_dots, score, lives

    # Spielerposition zurücksetzen
    player["x"], player["y"] = 1, 1
    player["direction"] = DIR_RIGHT
    player["next_direction"] = DIR_NONE

    # Geistposition zurücksetzen
    ghost["x"], ghost["y"] = 10, 7
    ghost["direction"] = DIR_LEFT

    # Labyrinth neu aufbauen und Punkte zählen
    total_dots = 0
    for y in range(MAZE_HEIGHT):
        for x in range(MAZE_WIDTH):
            tile_type = maze_layout[y][x]
            maze_grid[x, y] = tile_type
            if tile_type == TILE_DOT:
                total_dots += 1

    update_ui()

def new_game():
    """Startet ein komplett neues Spiel."""
    global score, lives
    score = 0
    lives = 3
    reset_level()

def update_ui():
    """Aktualisiert die Textanzeigen für Punkte und Leben."""
    score_label.text = f"Punkte: {score}"
    lives_label.text = f"Leben: {lives}"

def can_move(x, y, direction):
    """Prüft, ob eine Bewegung in eine Richtung von Position (x,y) möglich ist."""
    if direction == DIR_UP and maze_layout[y - 1][x] != TILE_WALL:
        return True
    if direction == DIR_DOWN and maze_layout[y + 1][x] != TILE_WALL:
        return True
    if direction == DIR_LEFT and maze_layout[y][x - 1] != TILE_WALL:
        return True
    if direction == DIR_RIGHT and maze_layout[y][x + 1] != TILE_WALL:
        return True
    # Sonderfall für den Tunnel
    if (x, y) == (0, 7) and direction == DIR_LEFT: return True
    if (x, y) == (MAZE_WIDTH - 1, 7) and direction == DIR_RIGHT: return True

    return False

# --- Haupt-Spiellogik ---
last_update_time = time.monotonic()
animation_counter = 0

while True:
    current_time = time.monotonic()

    # --- Zustand: Startbildschirm ---
    if game_state == STATE_START_SCREEN:
        message_label.text = "PAC-MAN\nDruecke Knopf 1"
        if not button_1.value:
            new_game()
            game_state = STATE_PLAYING
            message_label.text = ""
            time.sleep(0.2) # debounce

    # --- Zustand: Spiel läuft ---
    elif game_state == STATE_PLAYING:
        # 1. Eingabe verarbeiten
        if not dpad_up.value:
            player["next_direction"] = DIR_UP
        elif not dpad_down.value:
            player["next_direction"] = DIR_DOWN
        elif not dpad_left.value:
            player["next_direction"] = DIR_LEFT
        elif not dpad_right.value:
            player["next_direction"] = DIR_RIGHT

        # 2. Spielzustand aktualisieren (alle ~0.15 Sekunden)
        if current_time - last_update_time > 0.15:
            last_update_time = current_time
            animation_counter += 1

            # Spieler bewegen
            px, py = player["x"], player["y"]

            # Versuch, die "nächste" Richtung zu nehmen (für flüssige Kurven)
            if player["next_direction"] != DIR_NONE and can_move(px, py, player["next_direction"]):
                player["direction"] = player["next_direction"]
                player["next_direction"] = DIR_NONE

            # Bewegen in die aktuelle Richtung
            if can_move(px, py, player["direction"]):
                if player["direction"] == DIR_UP:
                    player["y"] -= 1
                elif player["direction"] == DIR_DOWN:
                    player["y"] += 1
                elif player["direction"] == DIR_LEFT:
                    # Tunnel-Logik
                    if px == 0 and py == 7:
                        player["x"] = MAZE_WIDTH - 1
                    else:
                        player["x"] -= 1
                elif player["direction"] == DIR_RIGHT:
                     # Tunnel-Logik
                    if px == MAZE_WIDTH - 1 and py == 7:
                        player["x"] = 0
                    else:
                        player["x"] += 1

            # Geist bewegen (einfache zufällige KI)
            gx, gy = ghost["x"], ghost["y"]
            valid_moves = []
            if ghost["direction"] != DIR_DOWN and can_move(gx, gy, DIR_UP): valid_moves.append(DIR_UP)
            if ghost["direction"] != DIR_UP and can_move(gx, gy, DIR_DOWN): valid_moves.append(DIR_DOWN)
            if ghost["direction"] != DIR_RIGHT and can_move(gx, gy, DIR_LEFT): valid_moves.append(DIR_LEFT)
            if ghost["direction"] != DIR_LEFT and can_move(gx, gy, DIR_RIGHT): valid_moves.append(DIR_RIGHT)

            if valid_moves:
                # Bevorzuge, geradeaus zu gehen, anstatt immer zufällig abzubiegen
                if can_move(gx, gy, ghost["direction"]) and len(valid_moves) < 3 and random.randint(0,2) > 0:
                     pass # gehe geradeaus weiter
                else:
                    ghost["direction"] = random.choice(valid_moves)

            if can_move(gx, gy, ghost["direction"]):
                if ghost["direction"] == DIR_UP: ghost["y"] -= 1
                elif ghost["direction"] == DIR_DOWN: ghost["y"] += 1
                elif ghost["direction"] == DIR_LEFT: ghost["x"] -= 1
                elif ghost["direction"] == DIR_RIGHT: ghost["x"] += 1

            # 3. Kollisionen prüfen
            # Punkt gegessen?
            if maze_grid[player["x"], player["y"]] == TILE_DOT:
                maze_grid[player["x"], player["y"]] = TILE_EMPTY
                score += 10
                total_dots -= 1
                update_ui()

            # Geist gefangen?
            if player["x"] == ghost["x"] and player["y"] == ghost["y"]:
                lives -= 1
                update_ui()
                if lives <= 0:
                    game_state = STATE_GAME_OVER
                else:
                    # Positionen zurücksetzen nach Lebensverlust
                    player["x"], player["y"] = 1, 1
                    ghost["x"], ghost["y"] = 10, 7
                    display.refresh()
                    time.sleep(1) # Kurze Pause

            # Alle Punkte gesammelt?
            if total_dots <= 0:
                game_state = STATE_LEVEL_CLEAR

        # 4. Anzeige aktualisieren
        # Spieler
        pacman_sprite.x = player["x"] * TILE_SIZE
        pacman_sprite.y = player["y"] * TILE_SIZE
        anim_frame = (animation_counter % 2)
        dir_offset = (player["direction"] - 1) * 2 if player["direction"] != DIR_NONE else 0
        if dir_offset < 0: dir_offset = 0 # Sicherheitscheck für DIR_NONE
        pacman_sprite[0] = anim_frame + dir_offset

        # Geist
        ghost_sprite.x = ghost["x"] * TILE_SIZE
        ghost_sprite.y = ghost["y"] * TILE_SIZE
        ghost_sprite[0] = (animation_counter % 2)

    # --- Zustand: Game Over ---
    elif game_state == STATE_GAME_OVER:
        message_label.text = "GAME OVER\nDruecke Knopf 1"
        if not button_1.value:
            game_state = STATE_START_SCREEN
            time.sleep(0.2) # debounce

    # --- Zustand: Level geschafft ---
    elif game_state == STATE_LEVEL_CLEAR:
        message_label.text = "LEVEL GESCHAFFT!\nDruecke Knopf 1"
        if not button_1.value:
            game_state = STATE_START_SCREEN
            time.sleep(0.2) # debounce

    # Bildschirm rendern
    display.refresh()# Write your code here :-)
