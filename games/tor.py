import time
import board
import displayio
import digitalio
import vectorio
import terminalio
import random
from adafruit_display_text import label

# --- Display-Initialisierung ---
display = board.DISPLAY
# Hauptgruppe, die alles auf dem Bildschirm enthält
main_group = displayio.Group()
display.root_group = main_group

# Bildschirm-Dimensionen
BILDSCHIRM_BREITE = display.width
BILDSCHIRM_HOEHE = display.height

# --- Farbpalette ---
# 0:Feld, 1:Weiss, 2:Blau, 3:Gelb, 4:Rot, 5:Spieler-Grün
palette = displayio.Palette(6)
palette[0] = 0x008000      # Grün (Feld)
palette[1] = 0xFFFFFF      # Weiss
palette[2] = 0x0000FF      # Blau (Spieler Standard)
palette[3] = 0xFFFF00      # Gelb (Nachrichten)
palette[4] = 0xFF0000      # Rot (Spieler Fehlschuss)
palette[5] = 0x00FF00      # Grün (Spieler Tor)

# Farb-Indizes als Konstanten für bessere Lesbarkeit
BLAU_INDEX = 2
ROT_INDEX = 4
GRUEN_SPIELER_INDEX = 5

# --- Konstanten ---
SPIELER_GROESSE = 20
spieler_geschwindigkeit = 4
BALL_RADIUS = 6
TOR_BREITE = 10
TOR_HOEHE = 80
SCHUSS_GESCHWINDIGKEIT = 8
LINIEN_DICKE = 2

# --- Hintergrund-Elemente ---
spielfeld = vectorio.Rectangle(
    pixel_shader=palette, width=BILDSCHIRM_BREITE, height=BILDSCHIRM_HOEHE,
    x=0, y=0, color_index=0
)
main_group.append(spielfeld)

# --- Spielfeld-Grafiken ---
mittellinie = vectorio.Rectangle(
    pixel_shader=palette, width=LINIEN_DICKE, height=BILDSCHIRM_HOEHE,
    x=(BILDSCHIRM_BREITE // 2) - (LINIEN_DICKE // 2), y=0, color_index=1
)
main_group.append(mittellinie)

MITTELKREIS_RADIUS = 40
mittelkreis_aussen = vectorio.Circle(
    pixel_shader=palette, radius=MITTELKREIS_RADIUS,
    x=BILDSCHIRM_BREITE // 2, y=BILDSCHIRM_HOEHE // 2, color_index=1
)
main_group.append(mittelkreis_aussen)

mittelkreis_innen = vectorio.Circle(
    pixel_shader=palette, radius=MITTELKREIS_RADIUS - LINIEN_DICKE,
    x=BILDSCHIRM_BREITE // 2, y=BILDSCHIRM_HOEHE // 2, color_index=0
)
main_group.append(mittelkreis_innen)

obere_linie = vectorio.Rectangle(
    pixel_shader=palette, width=BILDSCHIRM_BREITE, height=LINIEN_DICKE,
    x=0, y=0, color_index=1
)
main_group.append(obere_linie)

untere_linie = vectorio.Rectangle(
    pixel_shader=palette, width=BILDSCHIRM_BREITE, height=LINIEN_DICKE,
    x=0, y=BILDSCHIRM_HOEHE - LINIEN_DICKE, color_index=1
)
main_group.append(untere_linie)

# --- Vordergrund-Elemente ---
tor = vectorio.Rectangle(
    pixel_shader=palette, width=TOR_BREITE, height=TOR_HOEHE,
    x=BILDSCHIRM_BREITE - TOR_BREITE, y=(BILDSCHIRM_HOEHE - TOR_HOEHE) // 2,
    color_index=1
)
main_group.append(tor)

spieler = vectorio.Rectangle(
    pixel_shader=palette, width=SPIELER_GROESSE, height=SPIELER_GROESSE,
    x=50, y=BILDSCHIRM_HOEHE // 2 - SPIELER_GROESSE // 2, color_index=BLAU_INDEX
)
main_group.append(spieler)

ball = vectorio.Circle(
    pixel_shader=palette, radius=BALL_RADIUS,
    x=100, y=BILDSCHIRM_HOEHE // 2, color_index=1
)
main_group.append(ball)

# --- Spiel-Anzeigen ---
score = 0
score_label = label.Label(
    terminalio.FONT, text=f"Score: {score}", color=0xFFFFFF,
    x=10, y=15
)
main_group.append(score_label)

leben = 3
herzen_label = label.Label(
    terminalio.FONT, text="<3 " * leben, color=0xFF0000,
    anchor_point=(1.0, 0.0), anchored_position=(BILDSCHIRM_BREITE - 10, 5)
)
main_group.append(herzen_label)

tor_nachricht = label.Label(
    terminalio.FONT, text="TOR!", color=palette[3], scale=5,
    anchor_point=(0.5, 0.5),
    anchored_position=(BILDSCHIRM_BREITE // 2, BILDSCHIRM_HOEHE // 2)
)
tor_nachricht.hidden = True
main_group.append(tor_nachricht)

game_over_label = label.Label(
    terminalio.FONT, text="Game Over", color=palette[3], scale=4,
    anchor_point=(0.5, 0.5),
    anchored_position=(BILDSCHIRM_BREITE // 2, BILDSCHIRM_HOEHE // 2 - 20)
)
game_over_label.hidden = True
main_group.append(game_over_label)

neustart_label = label.Label(
    terminalio.FONT, text="Knopf 1\ndruecken", color=0xFFFFFF, scale=2,
    anchor_point=(0.5, 0.5),
    anchored_position=(BILDSCHIRM_BREITE // 2, BILDSCHIRM_HOEHE // 2 + 30)
)
neustart_label.hidden = True
main_group.append(neustart_label)

# --- Tasten-Initialisierung ---
def setup_button(pin):
    button_io = digitalio.DigitalInOut(pin)
    button_io.direction = digitalio.Direction.INPUT
    button_io.pull = digitalio.Pull.UP
    return button_io

button_up = setup_button(board.SWITCH_UP)
button_down = setup_button(board.SWITCH_DOWN)
button_left = setup_button(board.SWITCH_LEFT)
button_right = setup_button(board.SWITCH_RIGHT)
button_shoot = setup_button(board.BUTTON_1)

# --- Spiel-Zustand ---
hat_ball = False
ball_dx, ball_dy = 0, 0
letzter_schuss_zustand = True
game_over = False

def reset_positionen():
    global hat_ball, ball_dx, ball_dy
    hat_ball = False
    ball_dx, ball_dy = 0, 0
    max_x = (BILDSCHIRM_BREITE // 2) - SPIELER_GROESSE
    spieler.x = random.randint(0, max_x)
    spieler.y = random.randint(LINIEN_DICKE, BILDSCHIRM_HOEHE - SPIELER_GROESSE - LINIEN_DICKE)
    ball.x = spieler.x + SPIELER_GROESSE + BALL_RADIUS + 5
    ball.y = spieler.y + SPIELER_GROESSE // 2
    spieler.color_index = BLAU_INDEX

reset_positionen()

# --- Haupt-Schleife ---
while True:
    if not game_over:
        if not button_up.value: spieler.y -= spieler_geschwindigkeit
        if not button_down.value: spieler.y += spieler_geschwindigkeit
        if not button_left.value: spieler.x -= spieler_geschwindigkeit
        if not button_right.value: spieler.x += spieler_geschwindigkeit

        # KORREKTUR: Spieler kann nicht über die Mittellinie laufen
        spieler.x = max(0, min(spieler.x, mittellinie.x - SPIELER_GROESSE))
        spieler.y = max(LINIEN_DICKE, min(spieler.y, BILDSCHIRM_HOEHE - SPIELER_GROESSE - LINIEN_DICKE))

        aktueller_schuss_zustand = button_shoot.value
        if hat_ball and letzter_schuss_zustand and not aktueller_schuss_zustand:
            hat_ball = False
            ball_dx = SCHUSS_GESCHWINDIGKEIT
        letzter_schuss_zustand = aktueller_schuss_zustand

        if hat_ball:
            ball.x, ball.y = spieler.x + SPIELER_GROESSE, spieler.y + SPIELER_GROESSE // 2
            ball_dx, ball_dy = 0, 0
        else:
            ball.x += ball_dx
            ball.y += ball_dy
            if ball.y - BALL_RADIUS < LINIEN_DICKE or ball.y + BALL_RADIUS > BILDSCHIRM_HOEHE - LINIEN_DICKE:
                ball.y = max(BALL_RADIUS + LINIEN_DICKE, min(ball.y, BILDSCHIRM_HOEHE - BALL_RADIUS - LINIEN_DICKE))
                ball_dy *= -1
            if ball.x - BALL_RADIUS < 0:
                ball.x = BALL_RADIUS
                ball_dx *= -1

        if not hat_ball:
            if (spieler.x < ball.x + BALL_RADIUS and
                spieler.x + SPIELER_GROESSE > ball.x - BALL_RADIUS and
                spieler.y < ball.y + BALL_RADIUS and
                spieler.y + SPIELER_GROESSE > ball.y - BALL_RADIUS):
                hat_ball = True

        if ball.x + BALL_RADIUS > tor.x and tor.y < ball.y < tor.y + tor.height:
            score += 1
            score_label.text = f"Score: {score}"
            spieler.color_index = GRUEN_SPIELER_INDEX
            tor_nachricht.hidden = False
            display.refresh()
            time.sleep(1.5)
            tor_nachricht.hidden = True
            reset_positionen()

        if ball.x - BALL_RADIUS > BILDSCHIRM_BREITE:
            leben -= 1
            herzen_label.text = "<3 " * leben
            spieler.color_index = ROT_INDEX
            display.refresh()
            time.sleep(1.0)

            if leben <= 0:
                game_over = True
                game_over_label.hidden = False
                neustart_label.hidden = False
            else:
                reset_positionen()
    else:
        if not button_shoot.value:
            score, leben = 0, 3
            score_label.text = f"Score: {score}"
            herzen_label.text = "<3 " * leben
            game_over_label.hidden = True
            neustart_label.hidden = True
            game_over = False
            reset_positionen()
            while not button_shoot.value: time.sleep(0.01)

    time.sleep(0.02)# Write your code here :-)
