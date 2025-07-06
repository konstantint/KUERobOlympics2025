# -*- coding: utf-8 -*-

import time
import board
import displayio
import keypad
import terminalio
from adafruit_display_text import label

# --- Spielkonstanten ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
PLAYER_SPEED = 3
JOSCHUA_SPEED = 1
# Die Reichweite, in der Joschua zuschlägt (quadriert für schnellere Berechnung)
ATTACK_RANGE_SQ = 25 * 25
# Abklingzeit zwischen Joschuas Angriffen in Sekunden
ATTACK_COOLDOWN = 1.5
# Dauer der Angriff-Animation in Sekunden
ATTACK_ANIM_DURATION = 0.4

# --- Display-Initialisierung ---
display = board.DISPLAY
main_group = displayio.Group()
display.root_group = main_group

# --- Farbpaletten ---
# Palette für Herzen: 0:Transparent, 1:Pink/Gold, 2:Schwarz (Schatten)
sprite_palette = displayio.Palette(3)
sprite_palette.make_transparent(0)
sprite_palette[1] = 0xFF0099  # Pink für Spieler
sprite_palette[2] = 0x222222  # Dunkler Schatten

# Palette für Joschua: 0:Transparent, 1:Haut, 2:Braun(Keule), 3:Schwarz(Augen)
joschua_palette = displayio.Palette(4)
joschua_palette.make_transparent(0)
joschua_palette[1] = 0xFFCC99  # Hautfarbe
joschua_palette[2] = 0x8B4513  # Braun für Keule/Haare
joschua_palette[3] = 0x000000  # Schwarz für Augen

# --- Hilfsfunktion zum Erstellen von Bitmaps aus Text ---
def fill_bitmap_from_string(bitmap, palette_map, pixel_string_array):
    """Füllt eine Bitmap basierend auf einem Array von Zeichenketten."""
    # Diese Funktion kombiniert mehrere Zeilen in eine, wenn das Array verschachtelt ist
    # und füllt die Bitmap.
    if isinstance(pixel_string_array[0], list):
         # Flache die Liste der Listen von Strings zu einer einzigen Liste von Strings ab
        pixel_string_array = [item for sublist in pixel_string_array for item in sublist]

    for y, row in enumerate(pixel_string_array):
        for x, pixel_char in enumerate(row):
            if y < bitmap.height and x < bitmap.width:
                try:
                    bitmap[x, y] = palette_map[pixel_char]
                except KeyError:
                    # Ignoriere Zeichen, die nicht in der Map sind (z.B. bei unregelmäßigen Zeilen)
                    pass


# --- Sprite-Erstellung ---

# 1. Spieler-Herz (Normal & Zerbrochen)
heart_bmp = displayio.Bitmap(16, 14, 3)
broken_heart_bmp = displayio.Bitmap(16, 14, 3)

heart_map = {" ": 0, "P": 1, "S": 2}
heart_pixels = [
    "  PP    PP  ",
    " PSSP  PSSP ",
    "PSSSSP PSSSP",
    "PSSSSS PSSSP",
    "PSSSSSSSSSP",
    " PSSSSSSSP ",
    "  PSSSSSP  ",
    "   PSSSP   ",
    "    PSP    ",
    "     P     ",
]
fill_bitmap_from_string(heart_bmp, heart_map, heart_pixels)
fill_bitmap_from_string(broken_heart_bmp, heart_map, heart_pixels)

# Riss im zerbrochenen Herz hinzufügen (mit Schattenfarbe)
for i in range(5):
    broken_heart_bmp[7 - i, 3 + i] = 2
    broken_heart_bmp[8 + i, 5 + i] = 2

player_heart = displayio.TileGrid(heart_bmp, pixel_shader=sprite_palette)

# 2. Ziel-Herz (gleiche Form, andere Farbe)
goal_palette = displayio.Palette(3)
goal_palette.make_transparent(0)
goal_palette[1] = 0xFFD700  # Gold
goal_palette[2] = 0x222222
goal_heart = displayio.TileGrid(heart_bmp, pixel_shader=goal_palette)

# 3. Joschua (Bitmap mit 2 Frames: Idle & Angriff)
# TileGrid ist 16x24, Bitmap ist 32x24 (2x1)
joschua_bmp = displayio.Bitmap(32, 24, 4)
joschua_map = {" ": 0, "H": 1, "K": 2, "A": 3}
# Frame 1: Idle (x=0 bis 15)
joschua_idle = [
    "      KKKK      ",
    "     KHHHH      ",
    "     H A HA     ",
    "     HHHHHH     ",
    "      HHHH      ",
    "    HHHHKKHHH   ",
    "   H HHHHKKH H  ",
    "  H  HHHHHH  H  ",
    "     HHHHHH     ",
    "     H KKKH     ",
    "     H KKKH     ",
    "     H    H     ",
    "     H    H     ",
    "    HHH  HHH    ",
    "   HH H  H HH   ",
]
# Frame 2: Angriff (x=16 bis 31)
joschua_attack = [
    "      KKKK  KKK ",
    "     KHHHH KKKK ",
    "     H A HA KKH ",
    "     HHHHHH KH  ",
    "      HHHHHHH   ",
    "    HHHHHHHH    ",
    "   H HHHHHH     ",
    "  H  HHHHHH     ",
    "     HHHHHH     ",
    "     H    H     ",
    "     H    H     ",
    "     H    H     ",
    "     H    H     ",
    "    HHH  HHH    ",
    "   HH H  H HH   ",
]
# Kombinierte Pixel-Daten für die Bitmap-Füllfunktion
joschua_pixel_data = [row + att for row, att in zip(joschua_idle, joschua_attack)]
fill_bitmap_from_string(joschua_bmp, joschua_map, joschua_pixel_data)


joschua = displayio.TileGrid(
    joschua_bmp,
    pixel_shader=joschua_palette,
    width=1, height=1,
    tile_width=16, tile_height=24
)

# --- Text-Labels für Spielende ---
win_label = label.Label(terminalio.FONT, text="GEWONNEN!", color=0x00FF00, scale=3)
win_label.anchor_point = (0.5, 0.5)
win_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)

lose_label = label.Label(terminalio.FONT, text="VERLOREN!", color=0xFF0000, scale=3)
lose_label.anchor_point = (0.5, 0.5)
lose_label.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

# --- Tasten-Initialisierung ---
keys = keypad.Keys(
    (board.SWITCH_UP, board.SWITCH_DOWN, board.SWITCH_LEFT, board.SWITCH_RIGHT,
     board.BUTTON_1, board.BUTTON_2, board.BUTTON_3, board.SWITCH_PRESS),
    value_when_pressed=False,
    pull=True
)

# --- Spielzustands-Variablen ---
game_state = "START"
last_attack_time = 0
# NEU: Variablen für kontinuierliche Bewegung
move_up = False
move_down = False
move_left = False
move_right = False

# --- Hilfsfunktionen ---
def reset_game():
    """Setzt das Spiel auf den Anfangszustand zurück."""
    # player_heart wird global deklariert, damit wir es neu erstellen können.
    global game_state, move_up, move_down, move_left, move_right, player_heart

    while len(main_group) > 0:
        main_group.pop()

    # KORREKTUR: Das player_heart-Objekt wird neu erstellt.
    # Dies ist notwendig, da es auf dem Gewinnbildschirm zu einer anderen
    # Gruppe hinzugefügt wird. Ohne Neuerstellung würde der Versuch, es
    # erneut zur main_group hinzuzufügen, einen "Layer already in a group"-Fehler
    # verursachen. Dies stellt sicher, dass wir immer ein "sauberes" Objekt haben.
    player_heart = displayio.TileGrid(heart_bmp, pixel_shader=sprite_palette)

    player_heart.x = 20
    player_heart.y = SCREEN_HEIGHT // 2 - 7
    # Die Zeile 'player_heart.bitmap = heart_bmp' ist nicht mehr nötig,
    # da das Herz mit dem korrekten Bitmap neu erstellt wird.

    goal_heart.x = SCREEN_WIDTH - goal_heart.tile_width - 20
    goal_heart.y = SCREEN_HEIGHT // 2 - 7

    joschua.x = SCREEN_WIDTH // 2
    joschua.y = SCREEN_HEIGHT // 2 - 12
    joschua[0] = 0

    main_group.append(goal_heart)
    main_group.append(joschua)
    main_group.append(player_heart)

    # Bewegungsstatus zurücksetzen
    move_up = move_down = move_left = move_right = False
    game_state = "PLAYING"


def check_collision(tg1, tg2):
    """Prüft auf Bounding-Box-Kollision zwischen zwei TileGrids."""
    return not (
        tg1.x + tg1.tile_width <= tg2.x or
        tg1.x >= tg2.x + tg2.tile_width or
        tg1.y + tg1.tile_height <= tg2.y or
        tg1.y >= tg2.y + tg2.tile_height
    )

# --- Haupt-Spielschleife ---
while True:
    now = time.monotonic()
    event = keys.events.get()

    if game_state == "START":
        reset_game()

    elif game_state == "PLAYING":
        # --- NEUE Spielersteuerung für kontinuierliche Bewegung ---
        # 1. Events abfragen und Bewegungsstatus setzen/löschen
        if event:
            key_num = event.key_number
            if key_num == 0:  # HOCH
                move_up = event.pressed
            elif key_num == 1:  # RUNTER
                move_down = event.pressed
            elif key_num == 2:  # LINKS
                move_left = event.pressed
            elif key_num == 3:  # RECHTS
                move_right = event.pressed

        # 2. Spieler basierend auf dem Status bewegen
        if move_up:
            player_heart.y -= PLAYER_SPEED
        if move_down:
            player_heart.y += PLAYER_SPEED
        if move_left:
            player_heart.x -= PLAYER_SPEED
        if move_right:
            player_heart.x += PLAYER_SPEED
        # --- Ende der neuen Spielersteuerung ---

        # Spieler innerhalb der Bildschirmgrenzen halten
        player_heart.x = max(0, min(player_heart.x, SCREEN_WIDTH - player_heart.tile_width))
        player_heart.y = max(0, min(player_heart.y, SCREEN_HEIGHT - player_heart.tile_height))

        # --- Joschua KI ---
        dx = player_heart.x - joschua.x
        dy = player_heart.y - joschua.y
        if dx > 0: joschua.x += JOSCHUA_SPEED
        elif dx < 0: joschua.x -= JOSCHUA_SPEED
        if dy > 0: joschua.y += JOSCHUA_SPEED
        elif dy < 0: joschua.y -= JOSCHUA_SPEED

        dist_sq = dx * dx + dy * dy
        is_attacking = joschua[0] == 1

        if not is_attacking and dist_sq < ATTACK_RANGE_SQ and now - last_attack_time > ATTACK_COOLDOWN:
            joschua[0] = 1
            last_attack_time = now

        if is_attacking and now - last_attack_time > ATTACK_ANIM_DURATION:
            joschua[0] = 0

        # --- Kollisionserkennung ---
        if is_attacking and check_collision(player_heart, joschua):
            game_state = "LOST"

        if check_collision(player_heart, goal_heart):
            game_state = "WON"

    elif game_state == "WON":
        while len(main_group) > 0: main_group.pop()

        scaled_heart_group = displayio.Group(scale=2)
        player_heart.x = 0
        player_heart.y = 0
        scaled_heart_group.append(player_heart)

        scaled_width = player_heart.tile_width * 2
        scaled_height = player_heart.tile_height * 2
        scaled_heart_group.x = SCREEN_WIDTH // 2 - scaled_width // 2
        scaled_heart_group.y = SCREEN_HEIGHT // 2 - scaled_height // 2 - 20

        main_group.append(scaled_heart_group)
        main_group.append(win_label)

        game_state = "END_SCREEN"

    elif game_state == "LOST":
        player_heart.bitmap = broken_heart_bmp
        main_group.append(lose_label)

        game_state = "END_SCREEN"

    elif game_state == "END_SCREEN":
        if event and event.pressed:
            game_state = "START"

    time.sleep(0.016)
