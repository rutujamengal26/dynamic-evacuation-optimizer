"""
animate.py
----------
Replays the simulation's tick-by-tick history as a colourised terminal
animation -- occupancy bars per room, live event flashes, and a running
clock. Pure ANSI, no extra window needed.
"""

import time
from colors import clear_screen, bar, occupancy_color, RESET, BOLD, BRIGHT_CYAN, BRIGHT_RED, DIM, GREEN


def play(history, population, log_entries, delay=0.5):
    rooms = sorted(population)
    initial = dict(population)
    log_by_tick = {}
    for t, msg in log_entries:
        log_by_tick.setdefault(t, []).append(msg)

    fired = []
    for (t, wave_id, remaining) in history:
        clear_screen()
        print(f"{BOLD}{BRIGHT_CYAN}EVACUATION IN PROGRESS -- tick {t}   (wave {wave_id}){RESET}\n")

        total_initial = sum(initial.values())
        total_remaining = sum(remaining.values())
        overall_frac = total_remaining / total_initial if total_initial else 0
        print(f"  Building overall: {bar(overall_frac, width=36)} "
              f"{total_remaining:>4d} / {total_initial} still inside\n")

        for r in rooms:
            frac = remaining[r] / initial[r] if initial[r] else 0
            status = f"{GREEN}clear{RESET}" if remaining[r] == 0 else ""
            print(f"  {r:<6s}{bar(frac)}  {remaining[r]:>3d}/{initial[r]:<3d}  {status}")

        if t in log_by_tick:
            for msg in log_by_tick[t]:
                if msg not in fired:
                    fired.append(msg)
        if fired:
            print(f"\n  {BRIGHT_RED}{BOLD}EVENTS SO FAR{RESET}")
            for msg in fired:
                print(f"  {BRIGHT_RED}>> {msg}{RESET}")

        print(f"\n{DIM}(playing at {delay}s/tick -- close/interrupt with Ctrl+C){RESET}")
        time.sleep(delay)

    clear_screen()
    print(f"{BOLD}{GREEN}EVACUATION COMPLETE at tick {history[-1][0] if history else 0}{RESET}\n")
