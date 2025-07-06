import time
import board
import displayio
import random
import digitalio
import keypad
from adafruit_display_text import label
from terminalio import FONT
from adafruit_display_shapes.circle import Circle

# --- Konstanten und Spiel-Setup ---
BREITE = board.DISPLAY.width
HOEHE = board.DISPLAY.height
SPIELDAUER = 30  # Sekunden
BALL_RADIUS = 10
ZIEL_RADIUS = 8
BALL_GESCHWINDIGKEIT = 2     # Reduzierte Startgeschwindigkeit für bessere Kontrolle
BALL_BESCHLEUNIGUNG = 0.015  # Geringe Beschleunigung für sanfte Geschwindigkeitszunahme

# --- Display initialisieren ---
display = board.DISPLAY
# Haupt-Anzeigegruppe erstellen
haupt_gruppe = displayio.Group()
display.root_group = haupt_gruppe

# --- Spielobjekte erstellen ---

# Hintergrund
hintergrund_bitmap = displayio.Bitmap(BREITE, HOEHE, 1)
hintergrund_palette = displayio.Palette(1)
hintergrund_palette[0] = 0x000000  # Schwarz
hintergrund_tg = displayio.TileGrid(hintergrund_bitmap, pixel_shader=hintergrund_palette)
haupt_gruppe.append(hintergrund_tg)

# Ball erstellen
ball = Circle(0, 0, BALL_RADIUS, fill=0xFF0000) # Rot
haupt_gruppe.append(ball)

# Ziel erstellen
ziel = Circle(0, 0, ZIEL_RADIUS, fill=0x00FF00) # Grün
haupt_gruppe.append(ziel)


# --- Text-Labels erstellen ---
# Label für Punktestand und Zeit
info_text = f"Punkte: 0  Zeit: {SPIELDAUER}"
info_label = label.Label(FONT, text=info_text, color=0xFFFFFF, x=5, y=10)
haupt_gruppe.append(info_label)

# Label für "Spiel Ende"
spiel_ende_text = "Spiel Ende!\nPunkte: 0\n\nTaste 1 für Neustart"
spiel_ende_label = label.Label(
    FONT,
    text=spiel_ende_text,
    color=0xFFFFFF,
    scale=2,
    line_spacing=1.2,
    anchored_position=(BREITE // 2, HOEHE // 2),
    anchor_point=(0.5, 0.5)
)


# --- Tasten initialisieren ---
TASTEN_PINS = (
    board.BUTTON_1,
    board.SWITCH_UP,
    board.SWITCH_DOWN,
    board.SWITCH_LEFT,
    board.SWITCH_RIGHT,
)
tasten = keypad.Keys(TASTEN_PINS, value_when_pressed=False, pull=True)

# KORREKTUR: Zustandsspeicher für gedrückte Tasten
gedrueckte_tasten = [False] * len(TASTEN_PINS)
# Tasten-Indizes für bessere Lesbarkeit
KEY_BUTTON_1 = 0
KEY_UP = 1
KEY_DOWN = 2
KEY_LEFT = 3
KEY_RIGHT = 4


# --- Hilfsfunktionen ---
def ziel_neu_platzieren():
    """Platziert das Ziel an einer neuen zufälligen Position."""
    ziel.x = random.randint(ZIEL_RADIUS, BREITE - ZIEL_RADIUS)
    ziel.y = random.randint(20 + ZIEL_RADIUS, HOEHE - ZIEL_RADIUS)

def kollision_pruefen(circle1, r1, circle2, r2):
    """Prüft auf eine Kollision zwischen zwei Circle-Objekten."""
    dist_sq = (circle1.x - circle2.x)**2 + (circle1.y - circle2.y)**2
    return dist_sq < (r1 + r2)**2

def spiel_zuruecksetzen():
    """Setzt das Spiel in den Anfangszustand zurück."""
    global punkte, start_zeit
    punkte = 0
    start_zeit = time.monotonic()

    # KORREKTUR: Tastenstatus und Ereignis-Warteschlange zurücksetzen
    tasten.events.clear()
    for i in range(len(gedrueckte_tasten)):
        gedrueckte_tasten[i] = False

    ball.x = BREITE // 2
    ball.y = HOEHE // 2

    ziel_neu_platzieren()

    if ball not in haupt_gruppe:
        haupt_gruppe.append(ball)
    if ziel not in haupt_gruppe:
        haupt_gruppe.append(ziel)
    if info_label not in haupt_gruppe:
        haupt_gruppe.append(info_label)

    if spiel_ende_label in haupt_gruppe:
        haupt_gruppe.remove(spiel_ende_label)

# --- Haupt-Schleife ---
while True:
    spiel_zuruecksetzen()
    aktuelle_geschwindigkeit = float(BALL_GESCHWINDIGKEIT)

    # Spiel-Schleife (läuft, solange die Zeit nicht abgelaufen ist)
    while True:
        vergangene_zeit = time.monotonic() - start_zeit
        verbleibende_zeit = SPIELDAUER - vergangene_zeit

        if verbleibende_zeit <= 0:
            break

        aktuelle_geschwindigkeit += BALL_BESCHLEUNIGUNG
        info_label.text = f"Punkte: {punkte}  Zeit: {int(verbleibende_zeit)}"

        # KORREKTUR: Ereignisse verarbeiten und Tastenstatus aktualisieren
        while event := tasten.events.get():
            if event.pressed:
                gedrueckte_tasten[event.key_number] = True
            elif event.released:
                gedrueckte_tasten[event.key_number] = False

        # KORREKTUR: Bewegung basierend auf dem Zustand der Tasten steuern
        bewegungs_schritt = int(aktuelle_geschwindigkeit)

        if gedrueckte_tasten[KEY_UP]:
            ball.y -= bewegungs_schritt
        if gedrueckte_tasten[KEY_DOWN]:
            ball.y += bewegungs_schritt
        if gedrueckte_tasten[KEY_LEFT]:
            ball.x -= bewegungs_schritt
        if gedrueckte_tasten[KEY_RIGHT]:
            ball.x += bewegungs_schritt

        # Ball innerhalb der Bildschirmgrenzen halten
        ball.x = max(BALL_RADIUS, min(ball.x, BREITE - BALL_RADIUS))
        ball.y = max(20 + BALL_RADIUS, min(ball.y, HOEHE - BALL_RADIUS))

        # Kollision mit dem Ziel prüfen
        if kollision_pruefen(ball, BALL_RADIUS, ziel, ZIEL_RADIUS):
            punkte += 1
            ziel_neu_platzieren()

        time.sleep(0.01)

    # --- Spiel Ende ---
    # Spiel-Elemente ausblenden
    haupt_gruppe.remove(ball)
    haupt_gruppe.remove(ziel)
    haupt_gruppe.remove(info_label)

    # "Spiel Ende"-Label anzeigen
    spiel_ende_label.text = f"Spiel Ende!\nPunkte: {punkte}\n\nTaste 1 für Neustart"
    haupt_gruppe.append(spiel_ende_label)

    # Auf Tastendruck für Neustart warten
    while True:
        event = tasten.events.get()
        if event and event.pressed and event.key_number == KEY_BUTTON_1:
            break
        time.sleep(0.05)
