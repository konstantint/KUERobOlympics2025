# CircuitPython 9.x
# Wio Terminal Einhorn im Weltall - Jump & Run Spiel
# FINALE VERSION mit Spieler-Bewegung

import time
import random
import board
import displayio
import digitalio
import terminalio
from adafruit_display_text import label

# --- Konstanten und Spiel-Setup ---
BREITE = 320
HOEHE = 240
BODEN_HOEHE = 210  # Y-Koordinate des Bodens

# Physik-Konstanten
SCHWERKRAFT = -0.8
SPRUNG_KRAFT = 13
SPIELER_LAUF_GESCHWINDIGKEIT = 3 # NEU

# Spiel-Konstanten
START_LEBEN = 3
ALIEN_GESCHWINDIGKEIT = 0.25
GEWINN_ZEIT = 60  # 60 Sekunden zum Gewinnen

# --- Display initialisieren ---
display = board.DISPLAY
haupt_gruppe = displayio.Group()
display.root_group = haupt_gruppe

# --- Steuerung initialisieren ---
# Die drei oberen Tasten zum Springen
button_1 = digitalio.DigitalInOut(board.BUTTON_1)
button_1.direction = digitalio.Direction.INPUT
button_1.pull = digitalio.Pull.UP

button_2 = digitalio.DigitalInOut(board.BUTTON_2)
button_2.direction = digitalio.Direction.INPUT
button_2.pull = digitalio.Pull.UP

button_3 = digitalio.DigitalInOut(board.BUTTON_3)
button_3.direction = digitalio.Direction.INPUT
button_3.pull = digitalio.Pull.UP

# D-Pad zum Neustarten nach Spielende und Laufen
dpad_press = digitalio.DigitalInOut(board.SWITCH_PRESS)
dpad_press.direction = digitalio.Direction.INPUT
dpad_press.pull = digitalio.Pull.UP

switch_left = digitalio.DigitalInOut(board.SWITCH_LEFT) # NEU
switch_left.direction = digitalio.Direction.INPUT
switch_left.pull = digitalio.Pull.UP

switch_right = digitalio.DigitalInOut(board.SWITCH_RIGHT) # NEU
switch_right.direction = digitalio.Direction.INPUT
switch_right.pull = digitalio.Pull.UP


# --- Grafik-Setup (Bitmaps und Paletten direkt im Code) ---

# Hintergrund (Sterne)
star_palette = displayio.Palette(2)
star_palette[0] = 0x000010 # Hintergrund
star_palette[1] = 0xFFFFFF # Sterne
star_bitmap = displayio.Bitmap(BREITE, HOEHE, 2)
star_palette.make_transparent(0) # Hintergrundfarbe ist der erste Index
for _ in range(80):
    star_bitmap[random.randint(0, BREITE-1), random.randint(0, HOEHE-1)] = 1
star_tilegrid = displayio.TileGrid(star_bitmap, pixel_shader=star_palette)

# Eine separate Gruppe für den Hintergrund, damit er immer hinten ist
hintergrund_gruppe = displayio.Group()
hintergrund_gruppe.append(star_tilegrid)
haupt_gruppe.append(hintergrund_gruppe)

# Spiel-Gruppe für alle beweglichen Objekte
spiel_gruppe = displayio.Group()
haupt_gruppe.append(spiel_gruppe)


# Farbpalette für die Sprites
# 0: Transparent, 1: Weiß, 2: Schwarz, 3: Grau, 4: Grün,
# 5: Pink, 6: Gelb, 7: Blau, 8: Rot
sprite_palette = displayio.Palette(9)
sprite_palette.make_transparent(0)
sprite_palette[1] = 0xFFFFFF  # Weiß
sprite_palette[2] = 0x000000  # Schwarz
sprite_palette[3] = 0x808080  # Grau
sprite_palette[4] = 0x00FF00  # Grün
sprite_palette[5] = 0xFF00FF  # Pink
sprite_palette[6] = 0xFFFF00  # Gelb
sprite_palette[7] = 0x0000FF  # Blau
sprite_palette[8] = 0xFF0000  # Rot

# Einhorn-Sprite (32x32)
einhorn_bitmap = displayio.Bitmap(32, 32, 9)
# Körper
for y in range(15, 28):
    for x in range(5, 28):
        einhorn_bitmap[x, y] = 1
# Kopf
for y in range(8, 20):
    for x in range(20, 30):
        einhorn_bitmap[x, y] = 1
# Beine
for x in range(8, 12): einhorn_bitmap[x, 28] = einhorn_bitmap[x, 29] = 1
for x in range(18, 22): einhorn_bitmap[x, 28] = einhorn_bitmap[x, 29] = 1
# Auge
einhorn_bitmap[26, 12] = 2
# Horn (Regenbogen)
einhorn_bitmap[28, 5] = einhorn_bitmap[29, 6] = 8 # Rot
einhorn_bitmap[27, 6] = einhorn_bitmap[28, 7] = 6 # Gelb
einhorn_bitmap[26, 7] = einhorn_bitmap[27, 8] = 4 # Grün
einhorn_bitmap[25, 8] = einhorn_bitmap[26, 9] = 7 # Blau
einhorn_bitmap[24, 9] = einhorn_bitmap[25,10] = 5 # Pink


# UFO-Sprite (40x20)
ufo_bitmap = displayio.Bitmap(40, 20, 9)
# Kuppel
for y in range(0, 8):
    for x in range(12, 28):
        if (x-20)**2 + (y-8)**2 * 2.5 < 64:
            ufo_bitmap[x, y] = 4 # Grün
# Untertasse
for y in range(8, 15):
    for x in range(0, 40):
        if (x-20)**2 + (y-11)**2 * 8 < 350:
            ufo_bitmap[x, y] = 3 # Grau

# Alien-Sprite (24x24)
alien_bitmap = displayio.Bitmap(24, 24, 9)
# Körper
for y in range(4, 24):
    for x in range(0, 24):
       if (x-12)**2 + (y-14)**2 < 120:
            alien_bitmap[x, y] = 4 # Grün
# Auge
for y in range(8, 16):
    for x in range(8, 16):
        alien_bitmap[x, y] = 1 # Weiß
alien_bitmap[12, 12] = 2 # Pupille

# Herz-Sprite (16x16)
herz_bitmap = displayio.Bitmap(16, 16, 9)
herz_pixels = [
    "0011000000110000", "0111100001111000", "1111110011111100", "1111111111111110",
    "0111111111111100", "0011111111111000", "0001111111110000", "0000111111100000",
    "0000011111100000", "0000001111000000", "0000000110000000", "0000000000000000"
]
for y, row in enumerate(herz_pixels):
    for x, p in enumerate(row):
        if p == '1':
            herz_bitmap[x, y] = 8 # Rot

# Glitzer-Sprite (8x8)
glitzer_bitmap = displayio.Bitmap(8, 8, 9)
glitzer_bitmap[3, 0] = glitzer_bitmap[4, 0] = 6
glitzer_bitmap[3, 7] = glitzer_bitmap[4, 7] = 6
glitzer_bitmap[0, 3] = glitzer_bitmap[0, 4] = 6
glitzer_bitmap[7, 3] = glitzer_bitmap[7, 4] = 6
glitzer_bitmap[2, 2] = glitzer_bitmap[5, 5] = 1
glitzer_bitmap[2, 5] = glitzer_bitmap[5, 2] = 1

# --- UI-Gruppe, die immer im Vordergrund ist ---
ui_gruppe = displayio.Group()
haupt_gruppe.append(ui_gruppe)

# Leben-Anzeige
leben_gruppe = displayio.Group()
for i in range(START_LEBEN):
    herz = displayio.TileGrid(herz_bitmap, pixel_shader=sprite_palette, x=BREITE - (i + 1) * 20, y=5)
    leben_gruppe.append(herz)
ui_gruppe.append(leben_gruppe)

# Timer-Anzeige
timer_text = label.Label(terminalio.FONT, text="Zeit: 0s", color=0xFFFFFF, x=5, y=12)
ui_gruppe.append(timer_text)

# Spielende-Nachrichten
game_over_text = label.Label(terminalio.FONT, text="GAME OVER", scale=4, color=0xFF0000)
game_over_text.anchor_point = (0.5, 0.5)
game_over_text.anchored_position = (BREITE // 2, HOEHE // 2 - 20)

win_text = label.Label(terminalio.FONT, text="GEWONNEN!", scale=4, color=0xFFFF00)
win_text.anchor_point = (0.5, 0.5)
win_text.anchored_position = (BREITE // 2, HOEHE // 2 - 20)

restart_text = label.Label(terminalio.FONT, text="Taste druecken zum Neustart", scale=2, color=0xFFFFFF)
restart_text.anchor_point = (0.5, 0.5)
restart_text.anchored_position = (BREITE // 2, HOEHE // 2 + 30)

# --- Spielobjekte ---
spieler = displayio.TileGrid(einhorn_bitmap, pixel_shader=sprite_palette)
alien = displayio.TileGrid(alien_bitmap, pixel_shader=sprite_palette)

# Listen für dynamische Objekte
ufos = []
glitzer_partikel = []

# --- Spielvariablen ---
spiel_zustand = "START" # "PLAYING", "GAME_OVER", "WIN"
leben = START_LEBEN
spieler_y_v = 0.0 # Vertikale Geschwindigkeit
spiel_geschwindigkeit = 3.0
start_zeit = 0.0
alien_x_float = 0.0

def reset_spiel():
    """Setzt das Spiel in den Anfangszustand zurück."""
    global leben, spieler_y_v, spiel_geschwindigkeit, start_zeit, spiel_zustand, alien_x_float

    # Alte Objekte aus der Spiel-Gruppe entfernen
    while ufos:
        ufo_obj = ufos.pop()
        if ufo_obj in spiel_gruppe: spiel_gruppe.remove(ufo_obj)
    while glitzer_partikel:
        p = glitzer_partikel.pop()
        if p['tile'] in spiel_gruppe: spiel_gruppe.remove(p['tile'])

    # UI zurücksetzen (aus der UI-Gruppe entfernen)
    if game_over_text in ui_gruppe: ui_gruppe.remove(game_over_text)
    if win_text in ui_gruppe: ui_gruppe.remove(win_text)
    if restart_text in ui_gruppe: ui_gruppe.remove(restart_text)

    # Variablen zurücksetzen
    leben = START_LEBEN
    spieler_y_v = 0.0
    spiel_geschwindigkeit = 3.0
    start_zeit = time.monotonic()

    # Objekte neu positionieren und zur Spiel-Gruppe hinzufügen
    spieler.x = 20 # Startposition
    spieler.y = BODEN_HOEHE - 32

    alien_x_float = -30.0
    alien.x = int(alien_x_float)
    alien.y = BODEN_HOEHE - 24

    if spieler not in spiel_gruppe: spiel_gruppe.append(spieler)
    if alien not in spiel_gruppe: spiel_gruppe.append(alien)

    # Leben-Anzeige aktualisieren
    while len(leben_gruppe) > 0: leben_gruppe.pop()
    for i in range(START_LEBEN):
        herz = displayio.TileGrid(herz_bitmap, pixel_shader=sprite_palette, x=BREITE - (i + 1) * 20, y=5)
        leben_gruppe.append(herz)

    if leben_gruppe not in ui_gruppe: ui_gruppe.append(leben_gruppe)
    if timer_text not in ui_gruppe: ui_gruppe.append(timer_text)

    spiel_zustand = "PLAYING"

def aabb_collision(obj1, obj2):
    """Prüft auf eine Kollision zweier TileGrids (Axis-Aligned Bounding Box)."""
    return not (obj1.x + obj1.bitmap.width <= obj2.x or
                obj1.x >= obj2.x + obj2.bitmap.width or
                obj1.y + obj1.bitmap.height <= obj2.y or
                obj1.y >= obj2.y + obj2.bitmap.height)

# --- Haupt-Schleife ---
reset_spiel() # Spiel beim Start initialisieren

while True:
    jetzt = time.monotonic()

    # --- Eingabe ---
    sprung_taste_gedrueckt = not button_1.value or not button_2.value or not button_3.value
    neustart_taste_gedrueckt = sprung_taste_gedrueckt or not dpad_press.value

    # --- Logik je nach Spielzustand ---

    if spiel_zustand == "PLAYING":
        # Zeit aktualisieren
        vergangene_zeit = int(jetzt - start_zeit)
        timer_text.text = f"Zeit: {vergangene_zeit}s"

        # Gewinnbedingung
        if vergangene_zeit >= GEWINN_ZEIT:
            spiel_zustand = "WIN"
            continue

        # Spielereingabe (Springen)
        if sprung_taste_gedrueckt and spieler.y >= BODEN_HOEHE - 32:
            spieler_y_v = SPRUNG_KRAFT

        # NEU: Horizontale Bewegung des Spielers
        if not switch_right.value:
            spieler.x += SPIELER_LAUF_GESCHWINDIGKEIT
        if not switch_left.value:
            spieler.x -= SPIELER_LAUF_GESCHWINDIGKEIT

        # NEU: Begrenzung des Spielers auf den Bildschirm
        if spieler.x < 0:
            spieler.x = 0
        if spieler.x > BREITE - einhorn_bitmap.width:
            spieler.x = BREITE - einhorn_bitmap.width

        # Spielerphysik (Schwerkraft)
        spieler_y_v += SCHWERKRAFT
        spieler.y -= int(spieler_y_v)

        # Bodenkollision
        if spieler.y >= BODEN_HOEHE - 32:
            spieler.y = BODEN_HOEHE - 32
            spieler_y_v = 0

        # Alien-Bewegung
        alien_x_float += ALIEN_GESCHWINDIGKEIT
        alien.x = int(alien_x_float)

        # UFOs spawnen und bewegen
        spiel_geschwindigkeit = 3.0 + vergangene_zeit / 15.0
        ufo_spawn_chance = 0.02 + vergangene_zeit / 1000.0

        if random.random() < ufo_spawn_chance:
            neues_ufo = displayio.TileGrid(ufo_bitmap, pixel_shader=sprite_palette)
            neues_ufo.x = BREITE
            neues_ufo.y = random.randint(BODEN_HOEHE - 80, BODEN_HOEHE - 20)
            ufos.append(neues_ufo)
            spiel_gruppe.append(neues_ufo)

        for ufo in list(ufos):
            ufo.x -= int(spiel_geschwindigkeit)
            if ufo.x < -40:
                ufos.remove(ufo)
                spiel_gruppe.remove(ufo)

            # Kollision Spieler mit UFO
            if aabb_collision(spieler, ufo):
                ufos.remove(ufo)
                spiel_gruppe.remove(ufo)
                leben -= 1
                if leben >= 0 and len(leben_gruppe) > 0:
                    leben_gruppe.pop()
                if leben <= 0:
                    spiel_zustand = "GAME_OVER"
                    break

        if spiel_zustand == "GAME_OVER": continue

        # Kollision Spieler mit Alien
        if aabb_collision(spieler, alien):
            spiel_zustand = "GAME_OVER"
            continue

    elif spiel_zustand == "GAME_OVER":
        # Aufräumen und Nachricht anzeigen
        if game_over_text not in ui_gruppe:
            while ufos: spiel_gruppe.remove(ufos.pop())
            if spieler in spiel_gruppe: spiel_gruppe.remove(spieler)
            if alien in spiel_gruppe: spiel_gruppe.remove(alien)
            ui_gruppe.append(game_over_text)
            ui_gruppe.append(restart_text)

        if neustart_taste_gedrueckt:
            reset_spiel()

    elif spiel_zustand == "WIN":
        # Aufräumen, Nachricht und Glitzer anzeigen
        if win_text not in ui_gruppe:
            while ufos: spiel_gruppe.remove(ufos.pop())
            if alien in spiel_gruppe: spiel_gruppe.remove(alien)
            ui_gruppe.append(win_text)
            ui_gruppe.append(restart_text)

        # Glitzer-Partikel erzeugen und animieren
        if random.random() < 0.5:
            p = {
                'tile': displayio.TileGrid(glitzer_bitmap, pixel_shader=sprite_palette),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-4, -1),
                'life': 1.0
            }
            p['tile'].x = spieler.x + 26
            p['tile'].y = spieler.y + 8
            glitzer_partikel.append(p)
            spiel_gruppe.append(p['tile'])

        for p in list(glitzer_partikel):
            p['tile'].x += int(p['vx'])
            p['tile'].y += int(p['vy'])
            p['vy'] += 0.1
            p['life'] -= 0.02
            if p['life'] <= 0:
                glitzer_partikel.remove(p)
                if p['tile'] in spiel_gruppe: spiel_gruppe.remove(p['tile'])

        if neustart_taste_gedrueckt:
            reset_spiel()

    # Kurze Pause zur Steuerung der Framerate
    time.sleep(0.02)# Write your code here :-)
