"""
> Machen sie ein Kampfspiel in dem es verschiedene kampfgruppen gibt mit verschiedenen fahigkeiten. Kampfgruppe eins besteht aus den Maedchen Vivien die makeup wirft, Ioana die karate kicks macht und Allegra die schneidende pickelpflaster wirft. ihre gruppe heisst Die Slayenden Divas zweite Gruppe besteht aus Mario der Geneticzerstoerende zahlen wirft, Lewin der andere Sterne aufs kampffeld wirft der die Gegner schmilzt und Yan der Physikalische Stroeme macht die die Luft durch winden und alles zerstoeren. diese Gruppe heisst Physists. Der Hintergrund ist eine Theaterbuehne auf der die Gruppen kaempfen.
> mache jetzt auch noch mit beweg baren characters und geilen attack effects und fuege die Gruppe Cobras hinzu sie besteht aus Liam der ein Round house macht, aus Joschi der stachelige Yoshi eier schiesst und Luis, der den betaeubenden Sigma schrei schiesst der fast alle umbracht
mach das spiel mit echten irgenwie laufenden figuren die knoepfe sind nur fuer die attacken die figuren laufen automatisch und man sieht sie von der seite und nicht von oben und die attacken haben auch effekte oder explosionen etc.
"""
import time
import board
import displayio
import digitalio
import random
from adafruit_display_text import label
import terminalio
import vectorio
import gc

# --- Display-Initialisierung ---
display = board.DISPLAY
SCREEN_WIDTH = display.width
SCREEN_HEIGHT = display.height
main_group = displayio.Group()
display.root_group = main_group

# --- Farbdefinitionen ---
C_WHITE = 0xFFFFFF
C_BLACK = 0x000000
C_RED = 0xFF0000
C_GREEN = 0x00FF00
C_BLUE = 0x0000FF
C_YELLOW = 0xFFFF00
C_PURPLE = 0x800080
C_BROWN = 0x8B4513
C_PINK = 0xFFC0CB
C_TEAL = 0x008080
C_SKIN = 0xFFCC99
C_JEAN = 0x336699
C_HAIR = 0x3d2314

# --- Knopf-Konstanten ---
BUTTON_1 = board.BUTTON_1
BUTTON_2 = board.BUTTON_2
BUTTON_3 = board.BUTTON_3

buttons = {}
for name, pin in [("B1", BUTTON_1), ("B2", BUTTON_2), ("B3", BUTTON_3)]:
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.INPUT
    io.pull = digitalio.Pull.UP
    buttons[name] = io

last_press_times = {"B1": 0, "B2": 0, "B3": 0}
DEBOUNCE_DELAY = 0.5

# --- Spielwelt-Setup ---
PLAYER_TEAM = "divas"
GROUND_Y = SCREEN_HEIGHT - 30

# --- Sprite-Erstellung ---
def create_sprite_sheet():
    sheet = displayio.Bitmap(8 * 3, 12, 6)
    palette = displayio.Palette(6)
    palette[0] = 0x000000
    palette[1] = C_SKIN
    palette[2] = C_JEAN
    palette[3] = C_HAIR
    palette[4] = C_WHITE
    palette[5] = C_RED
    palette.make_transparent(0)

    pixel_map = {'T': 0, ' ': 0, 'S': 1, 'J': 2, 'H': 3, 'W': 4, 'R': 5}
    sprite_map_art = [
      "T HHH T ", "T HHH T ", "T SSS T ", " WWWWW  ", "RRRRRRR ",
      " RRRRR  ", "  JJJ   ", "  JJJ   ", "  JJJ   ", " S S S  ",
      " S  SS  ", " SS  S  "
    ]
    for y, row_str in enumerate(sprite_map_art):
        if y < 9:
            for x, char in enumerate(row_str):
                color_index = pixel_map[char]
                for frame in range(3):
                    sheet[x + frame * 8, y] = color_index
        else:
            for x in range(8):
                sheet[x, y] = pixel_map[sprite_map_art[9][x]]
                sheet[x + 8, y] = pixel_map[sprite_map_art[10][x]]
                sheet[x + 16, y] = pixel_map[sprite_map_art[11][x]]
    return sheet, palette

sprite_sheet, sprite_palette = create_sprite_sheet()

expl_sheet = displayio.Bitmap(16*4, 16, 4)
expl_palette = displayio.Palette(4)
expl_palette[0] = 0; expl_palette[1] = C_YELLOW; expl_palette[2] = C_RED; expl_palette[3] = C_WHITE
expl_palette.make_transparent(0)
for i in range(4):
    radius = (i + 1) * 2
    for y in range(16):
        for x in range(16):
            dist = int(((x-8)**2 + (y-8)**2)**0.5)
            if dist == radius: expl_sheet[x + i*16, y] = 1
            if dist == radius - 1: expl_sheet[x + i*16, y] = 2

# --- Klassen Definition ---
class GameObject:
    def __init__(self, group, x, y, width, height, sheet, palette, frame=0):
        self.x, self.y = x, y
        self.vx, self.vy = 0, 0
        self.width, self.height = width, height
        self.tile_grid = displayio.TileGrid(sheet, pixel_shader=palette, width=1, height=1, tile_width=width, tile_height=height)
        self.tile_grid.x, self.tile_grid.y = int(x), int(y)
        self.tile_grid[0] = frame
        self.group = group
        group.append(self.tile_grid)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.tile_grid.x, self.tile_grid.y = int(self.x), int(self.y)

    def destroy(self):
        try: self.group.remove(self.tile_grid)
        except (ValueError, IndexError): pass

class Character(GameObject):
    def __init__(self, group, x, y, data):
        super().__init__(group, x, y, 8, 12, sprite_sheet, sprite_palette)
        self.data = data
        self.direction = 1 if x < SCREEN_WIDTH / 2 else -1
        self.vx = self.direction * random.uniform(0.5, 1.2)
        self.tile_grid.flip_x = self.direction == -1
        self.frame = 0
        self.anim_timer = time.monotonic()
        self.attack_cooldown = random.uniform(2.0, 5.0)
        self.last_attack_time = time.monotonic()

        # KORREKTUR: Paletten für Lebensbalken separat erstellen
        hp_bg_palette = displayio.Palette(1)
        hp_bg_palette[0] = C_RED
        self.hp_bar_bg = vectorio.Rectangle(pixel_shader=hp_bg_palette, width=14, height=3, x=0, y=0)

        hp_fg_palette = displayio.Palette(1)
        hp_fg_palette[0] = C_GREEN
        self.hp_bar_fg = vectorio.Rectangle(pixel_shader=hp_fg_palette, width=14, height=3, x=0, y=0)

        self.hp_group = displayio.Group()
        self.hp_group.append(self.hp_bar_bg)
        self.hp_group.append(self.hp_bar_fg)
        group.append(self.hp_group)
        self.update_hp_bar()

    def update(self):
        super().update()
        if self.x < 0 or self.x > SCREEN_WIDTH - self.width:
            self.direction *= -1
            self.vx *= -1
            self.tile_grid.flip_x = self.direction == -1
        if time.monotonic() - self.anim_timer > 0.2:
            self.frame = (self.frame % 2) + 1
            self.tile_grid[0] = self.frame
            self.anim_timer = time.monotonic()
        self.update_hp_bar()

    def update_hp_bar(self):
        self.hp_group.x, self.hp_group.y = self.tile_grid.x - 3, self.tile_grid.y - 5
        self.hp_bar_fg.width = int(14 * (self.data['hp'] / self.data['max_hp']))
        if not self.data['alive']: self.hp_group.hidden = True

    def take_damage(self, amount):
        if self.data['alive']:
            self.data['hp'] = max(0, self.data['hp'] - amount)
            if self.data['hp'] == 0:
                self.data['alive'] = False
                self.destroy()

    def destroy(self):
        super().destroy()
        try: self.group.remove(self.hp_group)
        except (ValueError, IndexError): pass

class Projectile(GameObject):
    def __init__(self, group, x, y, vx, color, owner_team, damage):
        p_sheet = displayio.Bitmap(5, 5, 2)
        p_palette = displayio.Palette(2)
        p_palette.make_transparent(0)
        p_palette[1] = color
        p_sheet.fill(1)

        super().__init__(group, x, y, 5, 5, p_sheet, p_palette)

        self.vx = vx
        self.vy = 0
        self.owner_team = owner_team
        self.damage = damage

    def update(self):
        super().update()
        return self.x < -10 or self.x > SCREEN_WIDTH + 10

class Explosion(GameObject):
    def __init__(self, group, x, y):
        super().__init__(group, x, y, 16, 16, expl_sheet, expl_palette)
        self.frame = 0
        self.anim_timer = time.monotonic()

    def update(self):
        if time.monotonic() - self.anim_timer > 0.05:
            self.frame += 1
            if self.frame >= 4:
                return True
            self.tile_grid[0] = self.frame
            self.anim_timer = time.monotonic()
        return False

# --- Spiel-Setup ---
bg_palette = displayio.Palette(2)
bg_palette[0] = C_BROWN
bg_palette[1] = 0x400030
bg_bitmap = displayio.Bitmap(SCREEN_WIDTH, SCREEN_HEIGHT, 2)
for y in range(SCREEN_HEIGHT):
    for x in range(SCREEN_WIDTH): bg_bitmap[x, y] = 0 if y >= GROUND_Y else 1
main_group.append(displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette))

CHAR_DATA = {
    "divas": [{"name": "Vivien", "hp": 100, "max_hp": 100, "alive": True, "attack": {"schaden": 15, "color": C_PINK}},
              {"name": "Ioana", "hp": 120, "max_hp": 120, "alive": True, "attack": {"schaden": 20, "color": C_RED}},
              {"name": "Allegra", "hp": 90, "max_hp": 90, "alive": True, "attack": {"schaden": 18, "color": C_YELLOW}}],
    "physists": [{"name": "Mario", "hp": 110, "max_hp": 110, "alive": True, "attack": {"schaden": 17, "color": C_GREEN}},
                 {"name": "Lewin", "hp": 100, "max_hp": 100, "alive": True, "attack": {"schaden": 22, "color": C_PURPLE}},
                 {"name": "Yan", "hp": 95, "max_hp": 95, "alive": True, "attack": {"schaden": 19, "color": C_BLUE}}],
    "cobras": [{"name": "Liam", "hp": 110, "max_hp": 110, "alive": True, "attack": {"schaden": 25, "color": C_TEAL}},
               {"name": "Joschi", "hp": 100, "max_hp": 100, "alive": True, "attack": {"schaden": 20, "color": C_GREEN}},
               {"name": "Luis", "hp": 85, "max_hp": 85, "alive": True, "attack": {"schaden": 35, "color": C_WHITE}}],
}
characters = []
for team, team_data in CHAR_DATA.items():
    for char_data in team_data:
        x = random.randint(10, SCREEN_WIDTH - 20)
        c = Character(main_group, x, GROUND_Y - 12, char_data)
        c.team = team
        characters.append(c)

player_character_objects = [c for c in characters if c.team == PLAYER_TEAM]

projectiles, explosions = [], []
game_over_label = label.Label(terminalio.FONT, text="", scale=3, color=C_YELLOW, anchor_point=(0.5, 0.5), anchored_position=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
main_group.append(game_over_label)
game_over = False

# --- Hauptschleife ---
while not game_over:
    now = time.monotonic()

    button_map = {"B1": 0, "B2": 1, "B3": 2}
    for btn_name, char_idx in button_map.items():
        if not buttons[btn_name].value and now - last_press_times[btn_name] > DEBOUNCE_DELAY:
            if char_idx < len(player_character_objects):
                char = player_character_objects[char_idx]
                if char.data['alive']:
                    attack = char.data['attack']
                    proj = Projectile(main_group, char.x, char.y, 4 * char.direction, attack['color'], PLAYER_TEAM, attack['schaden'])
                    projectiles.append(proj)
                    last_press_times[btn_name] = now

    for char in characters:
        if char.team != PLAYER_TEAM and char.data['alive']:
            if now - char.last_attack_time > char.attack_cooldown:
                targets = [t for t in characters if t.team != char.team and t.data['alive']]
                if targets:
                    target = random.choice(targets)
                    char.direction = 1 if target.x > char.x else -1
                    char.vx = abs(char.vx) * char.direction
                    char.tile_grid.flip_x = char.direction == -1
                    attack = char.data['attack']
                    proj = Projectile(main_group, char.x, char.y, 4 * char.direction, attack['color'], char.team, attack['schaden'])
                    projectiles.append(proj)
                    char.last_attack_time = now
                    char.attack_cooldown = random.uniform(3.0, 6.0)

    for char in characters:
        if char.data['alive']: char.update()

    projectiles_to_remove = []
    for proj in projectiles:
        if proj.update():
            if proj not in projectiles_to_remove: projectiles_to_remove.append(proj)
        else:
            for char in characters:
                if char.data['alive'] and char.team != proj.owner_team:
                    if (proj.x < char.x + char.width and proj.x + proj.width > char.x and
                        proj.y < char.y + char.height and proj.y + proj.height > char.y):
                        char.take_damage(proj.damage)
                        explosions.append(Explosion(main_group, char.x-4, char.y-2))
                        if proj not in projectiles_to_remove: projectiles_to_remove.append(proj)
                        break

    explosions_to_remove = []
    for expl in explosions:
        if expl.update(): explosions_to_remove.append(expl)

    for p in projectiles_to_remove: p.destroy(); projectiles.remove(p)
    for e in explosions_to_remove: e.destroy(); explosions.remove(e)

    teams_alive = set(c.team for c in characters if c.data['alive'])
    if len(teams_alive) <= 1:
        game_over = True
        winner = list(teams_alive)[0] if teams_alive else "Niemand"
        team_names_map = {"divas": "Slayenden Divas", "physists": "Physists", "cobras": "Cobras", "Niemand": "Niemand"}
        display_name = team_names_map.get(winner, "Unbekannt")
        game_over_label.text = f"Team {display_name}\nhat gewonnen!"
        game_over_label.y = SCREEN_HEIGHT // 2

    gc.collect()
    time.sleep(0.02)

while True: pass
