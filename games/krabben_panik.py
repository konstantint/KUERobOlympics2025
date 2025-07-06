# SPDX-FileCopyrightText: 2024 (Ihre Initialen)
# SPDX-License-Identifier: MIT

import time
import board
import displayio
import digitalio
import terminalio
from adafruit_display_text import label

# --- Eigene Debouncer-Klasse als Ersatz für adafruit_debouncer ---
# Diese Klasse benötigt keine externe Bibliothek.
class SimpleDebouncer:
    """Eine einfache Klasse zur Tasten-Entprellung."""
    def __init__(self, pin, interval=0.02):
        # Initialisiert den Button-Pin
        self.button = digitalio.DigitalInOut(pin)
        self.button.switch_to_input(pull=digitalio.Pull.UP)

        self._interval = interval
        self._last_time = 0
        # Wir speichern den letzten Zustand, um eine Änderung zu erkennen.
        # True = losgelassen, False = gedrückt (wegen Pull.UP)
        self._last_state = self.button.value
        self.fell = False # Flag für das Drücken der Taste

    def update(self):
        """Muss in jeder Schleife aufgerufen werden, um den Zustand zu prüfen."""
        # Das 'fell'-Flag am Anfang jedes Updates zurücksetzen
        self.fell = False

        current_state = self.button.value
        current_time = time.monotonic()

        # Prüfen, ob eine Zustandsänderung von losgelassen (True) zu gedrückt (False) stattgefunden hat
        # und ob genug Zeit seit dem letzten Drücken vergangen ist.
        if not current_state and self._last_state and (current_time - self._last_time) > self._interval:
            self.fell = True
            # Zeit des bestätigten Tastendrucks speichern, um schnelle Wiederholungen zu vermeiden
            self._last_time = current_time

        self._last_state = current_state

    @property
    def value(self):
        """Gibt den aktuellen Zustand des Buttons zurück (gedrückt/losgelassen)."""
        return self.button.value

# --- Spielkonstanten ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
CRAB_SPEED = 4
SEAGULL_SPEED = 2
ZOMBIE_SPEED = 1

# --- Spielzustände (States) ---
STATE_START_SCREEN = 0
STATE_PLAYING = 1
STATE_GAME_OVER_EXPLOSION = 2
STATE_GAME_OVER_ZOMBIES = 3
STATE_WIN = 4

# --- Farbenpalette ---
SAND = 0xDEB887 # Sandfarbe
RED = 0xFF0000  # Rot für die Krabbe und Blut
WHITE = 0xFFFFFF # Weiß für die Möwe
BLACK = 0x000000 # Schwarz für die Höhle
GREEN = 0x008000 # Grün für die Zombies

# --- Display einrichten ---
display = board.DISPLAY
display.auto_refresh = False

# Die Haupt-Gruppe, die alle sichtbaren Elemente enthält
main_group = displayio.Group()
display.root_group = main_group

# --- Knöpfe/Tasten einrichten (mit unserer SimpleDebouncer-Klasse) ---
button_up = SimpleDebouncer(board.SWITCH_UP)
button_down = SimpleDebouncer(board.SWITCH_DOWN)
button_left = SimpleDebouncer(board.SWITCH_LEFT)
button_right = SimpleDebouncer(board.SWITCH_RIGHT)
button_1 = SimpleDebouncer(board.BUTTON_1) # Oberer linker Knopf

# --- Grafiken erstellen (ohne externe BMPs) ---
# 1. Hintergrund (Sand)
bg_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = SAND
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
main_group.append(background)

# 2. Krabbe (Spieler)
crab_bitmap = displayio.Bitmap(16, 12, 1)
crab_palette = displayio.Palette(1)
crab_palette[0] = RED
crab = displayio.TileGrid(crab_bitmap, pixel_shader=crab_palette, tile_width=16, tile_height=12)
main_group.append(crab)

# 3. Möwe (Gegner)
seagull_bitmap = displayio.Bitmap(20, 15, 1)
seagull_palette = displayio.Palette(1)
seagull_palette[0] = WHITE
seagull = displayio.TileGrid(seagull_bitmap, pixel_shader=seagull_palette, tile_width=20, tile_height=15)
main_group.append(seagull)

# 4. Höhle (Ziel)
cave_bitmap = displayio.Bitmap(30, 60, 1)
cave_palette = displayio.Palette(1)
cave_palette[0] = BLACK
cave = displayio.TileGrid(cave_bitmap, pixel_shader=cave_palette, tile_width=30, tile_height=60)
main_group.append(cave)

# 5. Zombies (zuerst versteckt und außerhalb der Gruppe)
zombie_palette = displayio.Palette(1)
zombie_palette[0] = GREEN
zombie1 = displayio.TileGrid(displayio.Bitmap(16, 24, 1), pixel_shader=zombie_palette, tile_width=16, tile_height=24)
zombie2 = displayio.TileGrid(displayio.Bitmap(16, 24, 1), pixel_shader=zombie_palette, tile_width=16, tile_height=24)

# --- Textelemente ---
font = terminalio.FONT
win_text = label.Label(font, text="GEWONNEN!", color=WHITE, scale=3)
lose_text = label.Label(font, text="GAME OVER", color=RED, scale=4)
blood_text = label.Label(font, text="!!! BLUT !!!", color=RED, scale=3)
start_text = label.Label(font, text="Krabben-Panik\n\n- D-Pad: Bewegen\n- Ziel: Die Hoehle\n- Knopf 1: Start", color=BLACK, scale=2, line_spacing=1.2)
start_text.anchor_point = (0.5, 0.5)
start_text.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

# --- Hilfsfunktionen ---
def check_collision(obj1, obj2):
    """Prüft, ob sich zwei TileGrid-Objekte überschneiden."""
    return (obj1.x < obj2.x + obj2.tile_width and
            obj1.x + obj1.tile_width > obj2.x and
            obj1.y < obj2.y + obj2.tile_height and
            obj1.y + obj1.tile_height > obj2.y)

def reset_game():
    """Setzt das Spiel auf den Anfangszustand zurück."""
    crab.x = 40
    crab.y = SCREEN_HEIGHT // 2
    seagull.x = SCREEN_WIDTH - 60
    seagull.y = SCREEN_HEIGHT // 2
    cave.x = SCREEN_WIDTH - cave.tile_width
    cave.y = SCREEN_HEIGHT // 2 - cave.tile_height // 2

    crab.hidden = False
    seagull.hidden = False
    cave.hidden = False

    temp_elements = [win_text, lose_text, blood_text, zombie1, zombie2, start_text]
    for element in temp_elements:
        try:
            main_group.remove(element)
        except ValueError:
            pass

    return STATE_PLAYING

# --- Initiales Spiel-Setup ---
game_state = STATE_START_SCREEN
main_group.append(start_text)
crab.hidden = True
seagull.hidden = True
cave.hidden = True
cutscene_timer = 0

# --- Haupt-Spielschleife ---
while True:
    # Alle Knöpfe auf einmal aktualisieren
    for b in [button_up, button_down, button_left, button_right, button_1]:
        b.update()

    # ### Zustandsmaschine (State Machine) ###

    if game_state == STATE_START_SCREEN:
        if button_1.fell:
            game_state = reset_game()

    elif game_state == STATE_PLAYING:
        # Krabben-Steuerung mit dem D-Pad ('.value' gibt True zurück, wenn losgelassen)
        if not button_left.value and crab.x > 0:
            crab.x -= CRAB_SPEED
        if not button_right.value and crab.x < SCREEN_WIDTH - crab.tile_width:
            crab.x += CRAB_SPEED
        if not button_up.value and crab.y > 0:
            crab.y -= CRAB_SPEED
        if not button_down.value and crab.y < SCREEN_HEIGHT - crab.tile_height:
            crab.y += CRAB_SPEED

        # Möwen-KI
        if seagull.x < crab.x: seagull.x += SEAGULL_SPEED
        elif seagull.x > crab.x: seagull.x -= SEAGULL_SPEED
        if seagull.y < crab.y: seagull.y += SEAGULL_SPEED
        elif seagull.y > crab.y: seagull.y -= SEAGULL_SPEED

        # Kollisionsprüfung
        if check_collision(crab, seagull):
            game_state = STATE_GAME_OVER_EXPLOSION
            crab.hidden = True
            blood_text.x = crab.x - 20
            blood_text.y = crab.y
            main_group.append(blood_text)
            cutscene_timer = time.monotonic()

        if check_collision(crab, cave):
            game_state = STATE_WIN
            win_text.x = (SCREEN_WIDTH - win_text.width) // 2
            win_text.y = SCREEN_HEIGHT // 2
            main_group.append(win_text)

    elif game_state == STATE_GAME_OVER_EXPLOSION:
        if time.monotonic() - cutscene_timer > 2.0:
            game_state = STATE_GAME_OVER_ZOMBIES
            main_group.remove(blood_text)

            zombie1.x = 0; zombie1.y = 0
            zombie2.x = 0; zombie2.y = SCREEN_HEIGHT - zombie2.tile_height
            main_group.append(zombie1)
            main_group.append(zombie2)

    elif game_state == STATE_GAME_OVER_ZOMBIES:
        if not seagull.hidden:
            zombies_reached_target = True
            if zombie1.x < seagull.x: zombie1.x += ZOMBIE_SPEED; zombies_reached_target = False
            if zombie1.y < seagull.y: zombie1.y += ZOMBIE_SPEED; zombies_reached_target = False
            if zombie2.x < seagull.x: zombie2.x += ZOMBIE_SPEED; zombies_reached_target = False
            if zombie2.y > seagull.y: zombie2.y -= ZOMBIE_SPEED; zombies_reached_target = False

            if zombies_reached_target:
                seagull.hidden = True
                lose_text.anchor_point = (0.5, 0.5)
                lose_text.anchored_position = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                main_group.append(lose_text)

        if button_1.fell:
            game_state = reset_game()

    elif game_state == STATE_WIN:
        if button_1.fell:
            game_state = reset_game()

    display.refresh()
    time.sleep(0.02)# Write your code here :-)
