import board
import displayio
import vectorio
import digitalio
import time

# --- Konfiguration ---
BALL_RADIUS = 10                  # Radius des Balls in Pixeln
BALL_COLOR = 0xFF0000             # Farbe des Balls (Rot im RGB565 Format)
INITIAL_X = board.DISPLAY.width // 2   # Startposition X (Mitte des Bildschirms)
INITIAL_Y = board.DISPLAY.height // 2  # Startposition Y (Mitte des Bildschirms)

GRAVITY = 0.2                     # Schwerkraft: Beschleunigung nach unten pro Frame
BOUNCE_FACTOR = 0.85              # Abprall-Faktor (0.0 = kein Abprall, 1.0 = perfekter Abprall)
DAMPING_FACTOR = 0.995            # Dämpfungsfaktor (Luftwiderstand/Reibung)
INPUT_ACCELERATION = 0.5          # Beschleunigung durch Tastendruck

# --- Display-Einrichtung ---
display = board.DISPLAY

# Erstelle eine Haupt-Anzeigegruppe
main_group = displayio.Group()

# Erstelle eine Farbpalette für den Ball
ball_palette = displayio.Palette(1)
ball_palette[0] = BALL_COLOR

# Erstelle den springenden Ball (ein Kreis)
# vectorio.Circle erstellt einen Kreis, der dynamisch neu gezeichnet werden kann
ball = vectorio.Circle(
    pixel_shader=ball_palette,
    radius=BALL_RADIUS,
    x=INITIAL_X,
    y=INITIAL_Y
)
main_group.append(ball) # Füge den Ball zur Anzeigegruppe hinzu

# Setze die Anzeigegruppe als Wurzel des Displays
display.root_group = main_group

# --- Tasten-Einrichtung ---
# Wio Terminal Richtungstasten (SWITCH_LEFT, SWITCH_RIGHT, SWITCH_UP, SWITCH_DOWN)
# Tasten sind intern mit Pull-Up-Widerständen verbunden, daher ist der Wert 'False', wenn gedrückt.
button_up = digitalio.DigitalInOut(board.SWITCH_UP)
button_up.pull = digitalio.Pull.UP

button_down = digitalio.DigitalInOut(board.SWITCH_DOWN)
button_down.pull = digitalio.Pull.UP

button_left = digitalio.DigitalInOut(board.SWITCH_LEFT)
button_left.pull = digitalio.Pull.UP

button_right = digitalio.DigitalInOut(board.SWITCH_RIGHT)
button_right.pull = digitalio.Pull.UP

# --- Physik-Variablen für den Ball ---
ball_dx = 0.0 # Geschwindigkeit in X-Richtung
ball_dy = 0.0 # Geschwindigkeit in Y-Richtung

# --- Haupt-Spiel-Loop ---
while True:
    # --- Eingabe-Verarbeitung ---
    # Wenn eine Taste gedrückt ist (Value ist False), die Geschwindigkeit anpassen
    if not button_left.value:
        ball_dx -= INPUT_ACCELERATION
    if not button_right.value:
        ball_dx += INPUT_ACCELERATION
    if not button_up.value:
        ball_dy -= INPUT_ACCELERATION
    if not button_down.value:
        ball_dy += INPUT_ACCELERATION

    # --- Physik anwenden ---
    ball_dy += GRAVITY # Schwerkraft anwenden (Beschleunigung nach unten)

    # Dämpfung/Reibung anwenden (verlangsamt den Ball über die Zeit)
    ball_dx *= DAMPING_FACTOR
    ball_dy *= DAMPING_FACTOR

    # Position des Balls aktualisieren
    # vectorio.Circle.x und y erwarten Integer-Werte
    ball.x += int(ball_dx)
    ball.y += int(ball_dy)

    # --- Kollisionserkennung und -reaktion (Wände) ---
    # Kollision mit linkem/rechtem Rand
    if ball.x - BALL_RADIUS < 0: # Ball berührt linken Rand
        ball.x = BALL_RADIUS # Position auf den Rand setzen
        ball_dx = -ball_dx * BOUNCE_FACTOR # Geschwindigkeit umkehren und dämpfen
    elif ball.x + BALL_RADIUS > display.width: # Ball berührt rechten Rand
        ball.x = display.width - BALL_RADIUS
        ball_dx = -ball_dx * BOUNCE_FACTOR

    # Kollision mit oberem/unterem Rand
    if ball.y - BALL_RADIUS < 0: # Ball berührt oberen Rand
        ball.y = BALL_RADIUS
        ball_dy = -ball_dy * BOUNCE_FACTOR
    elif ball.y + BALL_RADIUS > display.height: # Ball berührt unteren Rand
        ball.y = display.height - BALL_RADIUS
        ball_dy = -ball_dy * BOUNCE_FACTOR

    # Eine kurze Pause einlegen, um die Bildrate zu steuern
    time.sleep(0.02) # Etwa 50 Bilder pro Sekunde
