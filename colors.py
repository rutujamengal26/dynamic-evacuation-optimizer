"""
colors.py
---------
Tiny ANSI helper. Works natively on Linux/Mac terminals and on modern
Windows Terminal/PowerShell 7. On older Windows consoles it auto-enables
colour via colorama if that package is installed; otherwise it just
degrades to plain, uncoloured text (never crashes).
"""

try:
    import colorama
    colorama.init()
except ImportError:
    pass

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_CYAN = "\033[96m"


def occupancy_color(fraction_remaining):
    """Green = mostly evacuated, yellow = halfway, red = still crowded."""
    if fraction_remaining <= 0.0:
        return BRIGHT_GREEN
    if fraction_remaining <= 0.34:
        return GREEN
    if fraction_remaining <= 0.67:
        return YELLOW
    return BRIGHT_RED


def clear_screen():
    print("\033[H\033[J", end="")


def bar(fraction, width=24, filled_char="#", empty_char="-"):
    filled = round(width * max(0.0, min(1.0, fraction)))
    color = occupancy_color(fraction)
    return f"{color}{filled_char * filled}{DIM}{empty_char * (width - filled)}{RESET}"
