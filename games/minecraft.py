# -*- coding: utf-8 -*-
import board
import displayio
import time
import random
import keypad
import terminalio
from adafruit_display_text import label

# --- Spiel-Konfiguration ---
# Display
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
TILE_SIZE = 16
SCREEN_TILES_X = SCREEN_WIDTH // TILE_SIZE  # 20
SCREEN_TILES_Y = SCREEN_HEIGHT // TILE_SIZE # 15

# Welt
WORLD_WIDTH = 100  # In Kacheln
WORLD_HEIGHT = 60 # In Kacheln

# Physik
GRAVITY = 0.4
JUMP_VELOCITY = -7.0
MAX_FALL_SPEED = 8.0
PLAYER_SPEED = 2.0
FRICTION = 0.85

# --- Asset- und Block-Definitionen ---
# Kachel-Indizes im programmatisch erstellten Sprite-Bitmap
BLOCKS = {
    "SKY":      {"id": 0, "solid": False},
    "GRASS":    {"id": 1, "solid": True},
    "DIRT":     {"id": 2, "solid": True},
    "STONE":    {"id": 3, "solid": True},
    "WOOD":     {"id": 4, "solid": True},
    "LEAVES":   {"id": 5, "solid": False},
}
PLAYER_TILE = 6
CURSOR_TILE = 7

# Umgekehrte Zuordnung für einfacheren Zugriff
BLOCK_ID_TO_NAME = {v["id"]: k for k, v in BLOCKS.items()}


# --- Erzeuge Sprite-Grafiken im Speicher (RAM) ---
# Anstatt eine Datei zu laden, erstellen wir Bitmap und Palette direkt.
sprite_bitmap = displayio.Bitmap(128, 16, 256)
sprite_palette = displayio.Palette(256)
sprite_palette.make_transparent(0) # Index 0 ist normalerweise Himmel, aber hier machen wir ihn transparent für den Fall der Fälle

# Farben definieren
sprite_palette[0] = 0x6495ED # 0: HIMMEL (Cornflower Blue)
sprite_palette[1] = 0x228B22 # 1: GRAS (Forest Green)
sprite_palette[2] = 0x8B4513 # 2: ERDE (Saddle Brown)
sprite_palette[3] = 0x808080 # 3: STEIN (Gray)
sprite_palette[4] = 0x80502A # 4: HOLZ (Dark Wood Brown)
sprite_palette[5] = 0x006400 # 5: BLÄTTER (Dark Green)
sprite_palette[6] = 0xFF4500 # 6: SPIELER (Orangered)
sprite_palette[7] = 0xFFFFFF # 7: CURSOR (Weiß)

# Hilfsfunktionen zum Zeichnen der Kacheln in die Bitmap
def draw_tile(bitmap, tile_x_pos, color_index):
    start_x = tile_x_pos * TILE_SIZE
    for x in range(start_x, start_x + TILE_SIZE):
        for y in range(TILE_SIZE):
            bitmap[x, y] = color_index

def draw_cursor_tile(bitmap, tile_x_pos, color_index):
    start_x = tile_x_pos * TILE_SIZE
    for i in range(TILE_SIZE):
        bitmap[start_x + i, 0] = color_index
        bitmap[start_x + i, TILE_SIZE - 1] = color_index
        bitmap[start_x, i] = color_index
        bitmap[start_x + TILE_SIZE - 1, i] = color_index

# Zeichne alle benötigten Kacheln
draw_tile(sprite_bitmap, 0, 0) # HIMMEL
draw_tile(sprite_bitmap, 1, 1) # GRAS
draw_tile(sprite_bitmap, 2, 2) # ERDE
draw_tile(sprite_bitmap, 3, 3) # STEIN
draw_tile(sprite_bitmap, 4, 4) # HOLZ
draw_tile(sprite_bitmap, 5, 5) # BLÄTTER
draw_tile(sprite_bitmap, 6, 6) # SPIELER
draw_cursor_tile(sprite_bitmap, 7, 7) # CURSOR


# --- Welt-Generierung ---
world_data = [[BLOCKS["SKY"]["id"]] * WORLD_HEIGHT for _ in range(WORLD_WIDTH)]

def generate_world():
    print("Generiere Welt...")
    # Grundlegendes Terrain
    surface_y = [WORLD_HEIGHT // 2] * WORLD_WIDTH
    for i in range(1, WORLD_WIDTH):
        surface_y[i] = max(10, min(WORLD_HEIGHT - 10, surface_y[i-1] + random.randint(-1, 1)))

    for x in range(WORLD_WIDTH):
        for y in range(WORLD_HEIGHT):
            if y > surface_y[x]:
                world_data[x][y] = BLOCKS["STONE"]["id"]
            if y > surface_y[x] and y <= surface_y[x] + 5:
                world_data[x][y] = BLOCKS["DIRT"]["id"]
            if y == surface_y[x]:
                world_data[x][y] = BLOCKS["GRASS"]["id"]

    # Bäume pflanzen
    for x in range(5, WORLD_WIDTH - 5):
        if world_data[x][surface_y[x]] == BLOCKS["GRASS"]["id"] and random.random() < 0.1:
            tree_height = random.randint(4, 7)
            # Stamm
            for i in range(tree_height):
                if surface_y[x] - i -1 > 0:
                    world_data[x][surface_y[x] - i] = BLOCKS["WOOD"]["id"]
            # Blätter
            canopy_y = surface_y[x] - tree_height
            for lx in range(-2, 3):
                for ly in range(-2, 3):
                    if (lx*lx + ly*ly) < 5 and world_data[x+lx][canopy_y+ly] == BLOCKS["SKY"]["id"]:
                        world_data[x+lx][canopy_y+ly] = BLOCKS["LEAVES"]["id"]
    print("Welt-Generierung abgeschlossen.")


# --- Display-Setup ---
display = board.DISPLAY
main_group = displayio.Group()

# Welt-TileGrid (nutzt die im Speicher erstellte Bitmap)
world_tilegrid = displayio.TileGrid(sprite_bitmap, pixel_shader=sprite_palette,
                                    width=SCREEN_TILES_X, height=SCREEN_TILES_Y,
                                    tile_width=TILE_SIZE, tile_height=TILE_SIZE)
main_group.append(world_tilegrid)

# Spieler-Sprite
player_sprite = displayio.TileGrid(sprite_bitmap, pixel_shader=sprite_palette,
                                   width=1, height=1, tile_width=TILE_SIZE, tile_height=TILE_SIZE)
player_sprite[0, 0] = PLAYER_TILE
main_group.append(player_sprite)

# Cursor-Sprite
cursor_sprite = displayio.TileGrid(sprite_bitmap, pixel_shader=sprite_palette,
                                   width=1, height=1, tile_width=TILE_SIZE, tile_height=TILE_SIZE)
cursor_sprite[0, 0] = CURSOR_TILE
main_group.append(cursor_sprite)

# UI-Elemente
ui_label = label.Label(terminalio.FONT, text="Hotbar:", color=0xFFFFFF,
                       background_color=0x000000, padding_top=2, padding_bottom=2,
                       padding_left=2, padding_right=2)
ui_label.anchor_point = (0.0, 0.0)
ui_label.anchored_position = (5, 5)
main_group.append(ui_label)

display.root_group = main_group

# --- Eingabe-Verarbeitung ---
keys = keypad.Keys((board.BUTTON_1, board.BUTTON_2, board.BUTTON_3,
                    board.SWITCH_UP, board.SWITCH_DOWN, board.SWITCH_LEFT, board.SWITCH_RIGHT),
                   value_when_pressed=False, pull=True)

# --- Spiel-Zustand ---
player_x = (WORLD_WIDTH * TILE_SIZE) / 2
player_y = (WORLD_HEIGHT * TILE_SIZE) / 4
player_vx, player_vy = 0, 0
player_facing = 1  # 1 für rechts, -1 für links
on_ground = False
camera_x, camera_y = 0, 0
inventory = {"DIRT": 99, "STONE": 99, "WOOD": 99}
hotbar = ["DIRT", "STONE", "WOOD"]
hotbar_index = 0

# --- Hilfsfunktionen ---
def get_tile_coords(pixel_x, pixel_y):
    return int(pixel_x // TILE_SIZE), int(pixel_y // TILE_SIZE)

def is_solid(world_tile_x, world_tile_y):
    if not (0 <= world_tile_x < WORLD_WIDTH and 0 <= world_tile_y < WORLD_HEIGHT):
        return True # Außerhalb der Welt ist alles fest
    block_id = world_data[world_tile_x][world_tile_y]
    return BLOCKS[BLOCK_ID_TO_NAME[block_id]]["solid"]

def draw_world():
    start_tile_x, start_tile_y = int(camera_x // TILE_SIZE), int(camera_y // TILE_SIZE)
    for i in range(SCREEN_TILES_X):
        for j in range(SCREEN_TILES_Y):
            world_x, world_y = start_tile_x + i, start_tile_y + j
            if 0 <= world_x < WORLD_WIDTH and 0 <= world_y < WORLD_HEIGHT:
                world_tilegrid[i, j] = world_data[world_x][world_y]
            else:
                world_tilegrid[i, j] = BLOCKS["SKY"]["id"]

def update_ui():
    selected_item = hotbar[hotbar_index]
    count = inventory.get(selected_item, 0)
    ui_label.text = f"{selected_item}: {count}"

# --- Initialisierung ---
generate_world()
update_ui()

# --- Haupt-Spielschleife ---
while True:
    event = keys.events.get()

    if event and event.pressed:
        if event.key_number == 5: # LINKS
            player_vx = -PLAYER_SPEED
            player_facing = -1
        elif event.key_number == 6: # RECHTS
            player_vx = PLAYER_SPEED
            player_facing = 1

        if on_ground and event.key_number == 3: # HOCH (Springen)
            player_vy = JUMP_VELOCITY
            on_ground = False

        target_x, target_y = get_tile_coords(player_x + player_facing * TILE_SIZE/2, player_y + TILE_SIZE/2)

        if event.key_number == 0: # BUTTON 1: Block abbauen
            if is_solid(target_x, target_y):
                block_id = world_data[target_x][target_y]
                block_name = BLOCK_ID_TO_NAME.get(block_id)
                if block_name and block_name in inventory:
                    inventory[block_name] += 1
                world_data[target_x][target_y] = BLOCKS["SKY"]["id"]
                update_ui()

        elif event.key_number == 1: # BUTTON 2: Block platzieren
            selected_item = hotbar[hotbar_index]
            if inventory.get(selected_item, 0) > 0 and not is_solid(target_x, target_y):
                player_tile_x, player_tile_y = get_tile_coords(player_x, player_y)
                if (target_x, target_y) != (player_tile_x, player_tile_y):
                    world_data[target_x][target_y] = BLOCKS[selected_item]["id"]
                    inventory[selected_item] -= 1
                    update_ui()

        elif event.key_number == 2: # BUTTON 3: Hotbar wechseln
            hotbar_index = (hotbar_index + 1) % len(hotbar)
            update_ui()

    # --- Physik ---
    player_vy = min(player_vy + GRAVITY, MAX_FALL_SPEED)
    player_vx *= FRICTION
    if abs(player_vx) < 0.1: player_vx = 0

    player_x += player_vx
    left_x, right_x = player_x, player_x + TILE_SIZE - 1
    top_y, bottom_y = player_y, player_y + TILE_SIZE - 1
    for step_y in (top_y, bottom_y):
        if player_vx > 0:
            tx, ty = get_tile_coords(right_x, step_y)
            if is_solid(tx, ty): player_x = tx * TILE_SIZE - TILE_SIZE; player_vx = 0; break
        elif player_vx < 0:
            tx, ty = get_tile_coords(left_x, step_y)
            if is_solid(tx, ty): player_x = (tx + 1) * TILE_SIZE; player_vx = 0; break

    player_y += player_vy
    on_ground = False
    left_x, right_x = player_x, player_x + TILE_SIZE - 1
    top_y, bottom_y = player_y, player_y + TILE_SIZE - 1
    for step_x in (left_x, right_x):
        if player_vy > 0:
            tx, ty = get_tile_coords(step_x, bottom_y)
            if is_solid(tx, ty): player_y = ty * TILE_SIZE - TILE_SIZE; player_vy = 0; on_ground = True; break
        elif player_vy < 0:
            tx, ty = get_tile_coords(step_x, top_y)
            if is_solid(tx, ty): player_y = (ty + 1) * TILE_SIZE; player_vy = 0; break

    # --- Kamera und Zeichnen ---
    camera_x = max(0, min(player_x - SCREEN_WIDTH / 2, WORLD_WIDTH * TILE_SIZE - SCREEN_WIDTH))
    camera_y = max(0, min(player_y - SCREEN_HEIGHT / 2, WORLD_HEIGHT * TILE_SIZE - SCREEN_HEIGHT))

    draw_world()

    player_sprite.x = int(player_x - camera_x)
    player_sprite.y = int(player_y - camera_y)

    target_x, target_y = get_tile_coords(player_x + player_facing * TILE_SIZE/2, player_y + TILE_SIZE/2)
    cursor_sprite.x = int(target_x * TILE_SIZE - camera_x)
    cursor_sprite.y = int(target_y * TILE_SIZE - camera_y)

    time.sleep(0.01)# Write your code here :-)
