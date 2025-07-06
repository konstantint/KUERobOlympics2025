import os
import board
import displayio
import terminalio
from adafruit_display_text import label
import digitalio
import time
import supervisor

# --- Configuration ---
GAMES_DIR = "games"
DEBOUNCE_DELAY = 0.2  # Time in seconds to wait between button presses

# --- Display Initialization ---
display = board.DISPLAY
main_group = displayio.Group()
display.root_group = main_group

# --- Button Initialization ---
# Helper function to create a button object
def create_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    return button

# Create all button objects
button_up = create_button(board.SWITCH_UP)
button_down = create_button(board.SWITCH_DOWN)
button_press = create_button(board.SWITCH_PRESS)
button_1 = create_button(board.BUTTON_1)
button_2 = create_button(board.BUTTON_2)
button_3 = create_button(board.BUTTON_3)

# List of buttons that trigger execution
exec_buttons = [button_press, button_1, button_2, button_3]

# --- UI Creation (Static Elements) ---
# Centered Title
title_label = label.Label(
    terminalio.FONT,
    text="KUE RobOlympics 26.06.25",
    color=0xFFFFFF,
    scale=2,
    x=display.width // 2,
    y=20,  # Y position with a bit of margin from the top
    anchor_point=(0.5, 0.0)  # Anchor to top-center for horizontal centering
)
title_label.anchored_position = (display.width // 2, 10)
main_group.append(title_label)

# Left-aligned Hint
hint_text = "Up/Down to select, Press to run, Reset to return."
hint_label = label.Label(
    terminalio.FONT,
    text=hint_text,
    color=0xAAAAAA,
    x=5,  # 5 pixels from the left edge
    y=display.height - 15,
    anchor_point=(0.5, 0.5)  # Anchor to its left-middle point
)
hint_label.anchored_position = (display.width // 2, display.height - 15)
main_group.append(hint_label)

# --- File Discovery ---
game_files = []
try:
    game_files = sorted([
        f for f in os.listdir(f"/{GAMES_DIR}/") if f.endswith(".py")
    ])
except OSError:
    # Handle case where 'games' directory doesn't exist
    error_text = f"Directory '{GAMES_DIR}/'\nnot found."
    error_label = label.Label(
        terminalio.FONT,
        text=error_text,
        color=0xFF0000,
        x=display.width // 2,
        y=display.height // 2,
        anchor_point=(0.5, 0.5),
        line_spacing=1.25,
        scale=2
    )
    main_group.append(error_label)
    # Halt execution
    while True:
        pass

# --- Scrolling Menu UI & Logic ---
Y_START = 65
Y_SPACING = 20
MENU_BOTTOM_MARGIN = 30
MAX_VISIBLE_ITEMS = (display.height - Y_START - MENU_BOTTOM_MARGIN) // Y_SPACING

menu_item_labels = []
for i in range(MAX_VISIBLE_ITEMS):
    item_label = label.Label(
        terminalio.FONT,
        text="",  # Initially empty
        color=0xFFFFFF,
        x=20,
        y=Y_START + i * Y_SPACING
    )
    menu_item_labels.append(item_label)
    main_group.append(item_label)

selector_label = label.Label(
    terminalio.FONT, text=">", color=0x00FF00, x=5, y=Y_START
)
main_group.append(selector_label)

if not game_files:
    selector_label.hidden = True
    info_label = label.Label(
        terminalio.FONT,
        text="No .py files found.",
        color=0x808080,
        x=display.width // 2,
        y=Y_START + 20,
        anchor_point=(0.5, 0.0)
    )
    main_group.append(info_label)

selected_index = 0
scroll_offset = 0

def redraw_menu():
    """Redraws the list of games based on the current scroll offset and selection."""
    if not game_files:
        return

    for i in range(MAX_VISIBLE_ITEMS):
        item_label = menu_item_labels[i]
        file_index = scroll_offset + i

        if file_index < len(game_files):
            # Show the game name, truncate if too long
            filename = game_files[file_index]
            if len(filename) > 28:
                filename = filename[:27] + "..."
            item_label.text = filename
        else:
            # This label is not needed for a list item, clear it
            item_label.text = ""

    # Update the position of the selector relative to the visible list
    selector_label.y = Y_START + (selected_index - scroll_offset) * Y_SPACING

# --- Main Application Logic ---
last_button_time = 0

# Initial draw of the menu
redraw_menu()

while True:
    now = time.monotonic()

    # Simple time-based debouncing
    if now - last_button_time > DEBOUNCE_DELAY:
        action_taken = False

        # --- Handle Navigation ---
        if not button_down.value and game_files:
            selected_index = (selected_index + 1) % len(game_files)
            # Scroll down if selection moves past the visible window
            if selected_index > 0 and selected_index >= scroll_offset + MAX_VISIBLE_ITEMS:
                scroll_offset = selected_index - MAX_VISIBLE_ITEMS + 1
            # Handle wrap-around from last to first item
            if selected_index == 0:
                scroll_offset = 0
            redraw_menu()
            action_taken = True

        elif not button_up.value and game_files:
            selected_index = (selected_index - 1 + len(game_files)) % len(game_files)
            # Scroll up if selection moves before the visible window
            if selected_index < scroll_offset:
                scroll_offset = selected_index
            # Handle wrap-around from first to last item
            if selected_index == len(game_files) - 1:
                if len(game_files) > MAX_VISIBLE_ITEMS:
                    scroll_offset = len(game_files) - MAX_VISIBLE_ITEMS
            redraw_menu()
            action_taken = True

        # --- Handle Execution ---
        elif game_files and any(not btn.value for btn in exec_buttons):
            selected_file = game_files[selected_index]
            full_path = f"/{GAMES_DIR}/{selected_file}"
            print(f"Executing: {full_path}")

            display.root_group = displayio.Group()
            for btn in [button_up, button_down] + exec_buttons:
                btn.deinit()

            supervisor.set_next_code_file(full_path)
            supervisor.reload()

        if action_taken:
            last_button_time = now

    time.sleep(0.01)
