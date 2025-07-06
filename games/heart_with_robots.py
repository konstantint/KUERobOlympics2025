# SPDX-FileCopyrightText: 2024 DEVS GER for adafruit-community
# SPDX-License-Identifier: MIT

import time
import board
import displayio
import random

# --- 1. Display-Setup ---
# Initialisiert das eingebaute Display des Wio Terminals.
display = board.DISPLAY

# --- 2. Grafiken erstellen (Bitmaps) ---

def create_bitmap_from_string(s, w, h):
    """Erstellt eine Bitmap aus einem mehrzeiligen String (sichere Version)."""
    max_val = 0
    for char in s:
        if char.isdigit():
            max_val = max(max_val, int(char))

    bitmap = displayio.Bitmap(w, h, max_val + 1)
    lines = s.strip().split("\n")
    for y, line in enumerate(lines):
        if y >= h: break
        for x, char in enumerate(line):
            if x >= w: break
            if char.isdigit():
                bitmap[x, y] = int(char)
    return bitmap

# Herz-Grafik (ASCII-Art)
HERZ_BREITE = 36
HERZ_ART = """
...11111111........11111111...
.111111111111....111111111111.
11111111111111..11111111111111
111111111111111111111111111111
111111111111111111111111111111
111111111111111111111111111111
111111111111111111111111111111
.1111111111111111111111111111.
..11111111111111111111111111..
...111111111111111111111111...
....1111111111111111111111....
.....11111111111111111111.....
......11111111111111111.......
.......11111111111111.........
........11111111111...........
.........11111111.............
..........111111..............
...........1111...............
............11................
"""
HERZ_ART = HERZ_ART.strip()
HERZ_HOEHE = len(HERZ_ART.split("\n"))

herz_bitmap = create_bitmap_from_string(HERZ_ART, HERZ_BREITE, HERZ_HOEHE)

herz_palette = displayio.Palette(2)
herz_palette[0] = 0x000000  # Transparent
herz_palette[1] = 0xFF0000  # Rot
herz_palette.make_transparent(0)

herz_tilegrid = displayio.TileGrid(herz_bitmap, pixel_shader=herz_palette)
herz_tilegrid.x = display.width // 2 - herz_bitmap.width // 2
herz_tilegrid.y = display.height // 2 - herz_bitmap.height // 2

# Roboter-Grafik (ASCII-Art)
ROBOTER_BREITE = 10
ROBOTER_HOEHE = 10
ROBOTER_ART = """
..111111..
.11222211.
.11111111.
.13333331.
.13111131.
..111111..
..1....1..
.11....11.
111....111
"""
roboter_bitmap = create_bitmap_from_string(ROBOTER_ART, ROBOTER_BREITE, ROBOTER_HOEHE)

roboter_palette = displayio.Palette(4)
roboter_palette[0] = 0x000000  # Transparent
roboter_palette.make_transparent(0)
roboter_palette[1] = 0x888888  # Grau
roboter_palette[2] = 0x00FFFF  # Cyan (Auge)
roboter_palette[3] = 0x555555  # Dunkelgrau

# --- 3. Roboter-Management ---
class Roboter:
    def __init__(self, bitmap, palette):
        self.tilegrid = displayio.TileGrid(bitmap, pixel_shader=palette)
        self.x = 0.0
        self.y = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.active = False

MAX_ROBOTER = 40
roboter_liste = []
for _ in range(MAX_ROBOTER):
    roboter_liste.append(Roboter(roboter_bitmap, roboter_palette))

SPAWN_X = display.width // 2
SPAWN_Y = display.height // 2

# --- 4. Anzeige-Gruppe und Hauptschleife ---
haupt_gruppe = displayio.Group()
haupt_gruppe.append(herz_tilegrid)

display.root_group = haupt_gruppe

spawn_timer = 0
herz_puls_richtung = 1
herz_puls_faktor = 1.0

while True:
    # --- Herz-Puls-Animation ---
    # KORRIGIERT: Die Logik wurde angepasst, um den `ValueError` zu verhindern.
    # Der `herz_puls_faktor` wird jetzt innerhalb der gültigen Grenzen [0.5, 1.0] gehalten,
    # bevor die Farbe berechnet wird.
    herz_puls_faktor += 0.02 * herz_puls_richtung

    # Prüfen und korrigieren, wenn die Grenzen überschritten werden
    if herz_puls_faktor > 1.0:
        herz_puls_faktor = 1.0  # Auf Maximum begrenzen
        herz_puls_richtung = -1 # Richtung umkehren
    elif herz_puls_faktor < 0.5:
        herz_puls_faktor = 0.5   # Auf Minimum begrenzen
        herz_puls_richtung = 1  # Richtung umkehren

    rot_anteil = int(255 * herz_puls_faktor)
    # Diese Zeile ist jetzt sicher, da rot_anteil immer zwischen 127 und 255 liegt.
    herz_palette[1] = (rot_anteil, 0, 0)

    # --- Roboter erzeugen (spawnen) ---
    spawn_timer += 1
    if spawn_timer > 3:
        spawn_timer = 0
        for r in roboter_liste:
            if not r.active:
                r.active = True
                r.x = float(SPAWN_X - ROBOTER_BREITE // 2)
                r.y = float(SPAWN_Y - ROBOTER_HOEHE // 2)
                r.dx = random.uniform(-2.5, 2.5)
                r.dy = random.uniform(-2.5, 2.5)
                haupt_gruppe.append(r.tilegrid)
                break

    # --- Alle aktiven Roboter aktualisieren ---
    for r in roboter_liste:
        if r.active:
            r.x += r.dx
            r.y += r.dy
            r.tilegrid.x = int(r.x)
            r.tilegrid.y = int(r.y)

            if (r.tilegrid.x < -ROBOTER_BREITE or
                r.tilegrid.x > display.width or
                r.tilegrid.y < -ROBOTER_HOEHE or
                r.tilegrid.y > display.height):
                r.active = False
                haupt_gruppe.remove(r.tilegrid)

    time.sleep(0.01)# Write your code here :-)
