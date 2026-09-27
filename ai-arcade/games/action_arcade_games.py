"""
Simplified Action/Arcade Games: Platformers, Shooters, Rhythm
"""
from typing import List, Optional, Dict, Tuple
import random


# ============================================================
# SUPER MARIO STYLE - Simple platformer
# ============================================================

def make_platformer() -> Dict:
    """Create simple platformer level"""
    # Simple level: . = empty, # = platform, E = enemy, C = coin, G = goal
    level = [
        "                    G",
        "                   ##",
        "      C            ",
        "    ####     C     ",
        "         E  ####   ",
        "####################",
    ]

    return {
        'level': level,
        'player_x': 2,
        'player_y': 4,
        'score': 0,
        'lives': 3,
        'velocity_y': 0,
        'on_ground': True
    }


def platformer_str(state: Dict) -> str:
    """Display platformer game"""
    lines = ['   PLATFORMER GAME']
    lines.append('   ' + '=' * 40)

    # Draw level with player
    for y, row in enumerate(state['level']):
        line = '   '
        for x, cell in enumerate(row):
            if x == state['player_x'] and y == state['player_y']:
                line += 'P'  # Player
            else:
                line += cell if cell != ' ' else '·'
        lines.append(line)

    lines.append(f'\n   Score: {state["score"]}  Lives: {state["lives"]}')
    lines.append('\n   COMMANDS: left, right, jump')
    lines.append('   Goal: Reach G while collecting coins (C) and avoiding enemies (E)')

    return '\n'.join(lines)


def platformer_move(state: Dict, action: str) -> str:
    """Process platformer action"""
    px, py = state['player_x'], state['player_y']
    level = state['level']

    if action == 'left' and px > 0:
        # Check collision
        if level[py][px - 1] not in ['#', 'E']:
            state['player_x'] -= 1
            if level[py][px - 1] == 'C':
                state['score'] += 10
                # Remove coin
                level[py] = level[py][:px-1] + ' ' + level[py][px:]
    elif action == 'right' and px < len(level[0]) - 1:
        if level[py][px + 1] not in ['#', 'E']:
            state['player_x'] += 1
            if level[py][px + 1] == 'C':
                state['score'] += 10
                level[py] = level[py][:px+1] + ' ' + level[py][px+2:]
            elif level[py][px + 1] == 'G':
                return "LEVEL COMPLETE!"
    elif action == 'jump' and state['on_ground']:
        state['velocity_y'] = -2
        state['on_ground'] = False

    # Apply gravity
    if not state['on_ground']:
        state['velocity_y'] += 1
        new_y = py + (1 if state['velocity_y'] > 0 else -1)
        if 0 <= new_y < len(level) and level[new_y][px] != '#':
            state['player_y'] = new_y
        else:
            state['on_ground'] = True
            state['velocity_y'] = 0

    # Check enemy collision
    if level[state['player_y']][state['player_x']] == 'E':
        state['lives'] -= 1
        state['player_x'] = 2
        state['player_y'] = 4
        return f"Hit enemy! Lives remaining: {state['lives']}"

    return "Moved"


# ============================================================
# GEOMETRY WARS STYLE - Arena shooter
# ============================================================

def make_arena_shooter() -> Dict:
    """Create arena shooter"""
    return {
        'player_x': 5,
        'player_y': 5,
        'enemies': [(random.randint(0, 9), random.randint(0, 9)) for _ in range(3)],
        'bullets': [],
        'score': 0,
        'health': 100,
        'wave': 1
    }


def arena_shooter_str(state: Dict) -> str:
    """Display arena shooter"""
    lines = ['   ARENA SHOOTER']
    lines.append('   ' + '=' * 40)

    # Draw 10x10 arena
    for y in range(10):
        line = '   '
        for x in range(10):
            if (x, y) == (state['player_x'], state['player_y']):
                line += 'P '
            elif (x, y) in state['enemies']:
                line += 'E '
            elif (x, y) in state['bullets']:
                line += '• '
            else:
                line += '· '
        lines.append(line)

    lines.append(f'\n   Score: {state["score"]}  Health: {state["health"]}  Wave: {state["wave"]}')
    lines.append(f'   Enemies: {len(state["enemies"])}')
    lines.append('\n   COMMANDS: move <direction>, shoot <direction>')
    lines.append('   Directions: up, down, left, right, ul, ur, dl, dr')

    return '\n'.join(lines)


def arena_shooter_update(state: Dict, action: str, direction: str) -> str:
    """Process arena shooter action"""
    dirs = {
        'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0),
        'ul': (-1, -1), 'ur': (1, -1), 'dl': (-1, 1), 'dr': (1, 1)
    }

    if direction not in dirs:
        return "Invalid direction"

    dx, dy = dirs[direction]

    if action == 'move':
        new_x = max(0, min(9, state['player_x'] + dx))
        new_y = max(0, min(9, state['player_y'] + dy))
        state['player_x'] = new_x
        state['player_y'] = new_y
    elif action == 'shoot':
        bullet_x = state['player_x'] + dx
        bullet_y = state['player_y'] + dy
        if 0 <= bullet_x <= 9 and 0 <= bullet_y <= 9:
            state['bullets'].append((bullet_x, bullet_y))

            # Check hit
            if (bullet_x, bullet_y) in state['enemies']:
                state['enemies'].remove((bullet_x, bullet_y))
                state['score'] += 100
                state['bullets'].remove((bullet_x, bullet_y))
                return "Enemy destroyed! +100"

    # Move enemies toward player
    new_enemies = []
    for ex, ey in state['enemies']:
        if abs(ex - state['player_x']) > 0:
            ex += 1 if state['player_x'] > ex else -1
        if abs(ey - state['player_y']) > 0:
            ey += 1 if state['player_y'] > ey else -1
        new_enemies.append((ex, ey))

        # Check collision with player
        if (ex, ey) == (state['player_x'], state['player_y']):
            state['health'] -= 20
            return f"Hit by enemy! Health: {state['health']}"

    state['enemies'] = new_enemies

    # Spawn new wave
    if len(state['enemies']) == 0:
        state['wave'] += 1
        state['enemies'] = [(random.randint(0, 9), random.randint(0, 9))
                           for _ in range(3 + state['wave'])]
        return f"Wave {state['wave']} incoming!"

    return "Updated"


# ============================================================
# RHYTHM GAME - Timing-based
# ============================================================

def make_rhythm_game() -> Dict:
    """Create rhythm game"""
    # Simple beat pattern
    pattern = [
        {'time': 1, 'lane': 1},
        {'time': 2, 'lane': 2},
        {'time': 3, 'lane': 3},
        {'time': 4, 'lane': 2},
        {'time': 5, 'lane': 1},
        {'time': 6, 'lane': 3},
        {'time': 7, 'lane': 2},
        {'time': 8, 'lane': 1},
    ]

    return {
        'pattern': pattern,
        'current_time': 0,
        'score': 0,
        'combo': 0,
        'max_combo': 0,
        'hits': 0,
        'misses': 0
    }


def rhythm_game_str(state: Dict) -> str:
    """Display rhythm game"""
    lines = ['   RHYTHM GAME']
    lines.append('   ' + '=' * 40)

    # Show upcoming notes in 3 lanes
    current = state['current_time']
    for t in range(current, min(current + 8, max(n['time'] for n in state['pattern']) + 1)):
        line = f'   {t:2d} |'
        for lane in [1, 2, 3]:
            # Check if note exists at this time and lane
            has_note = any(n['time'] == t and n['lane'] == lane for n in state['pattern'])
            line += ' ◉ |' if has_note else '   |'
        lines.append(line)

    lines.append('   ' + '-' * 40)
    lines.append('      | 1 | 2 | 3 |  <- Hit lanes')

    lines.append(f'\n   Score: {state["score"]}  Combo: {state["combo"]} (Max: {state["max_combo"]})')
    lines.append(f'   Hits: {state["hits"]}  Misses: {state["misses"]}')
    lines.append('\n   COMMANDS: hit <lane> (1, 2, or 3)')
    lines.append('   Hit the note when it reaches the bottom line!')

    return '\n'.join(lines)


def rhythm_game_hit(state: Dict, lane: int) -> str:
    """Process rhythm hit"""
    try:
        lane = int(lane)
    except:
        return "Invalid lane"

    if lane not in [1, 2, 3]:
        return "Lane must be 1, 2, or 3"

    current = state['current_time']

    # Check for note within timing window
    hit = False
    for note in state['pattern']:
        if note['lane'] == lane and abs(note['time'] - current) <= 1:
            # Good hit!
            points = 100
            if abs(note['time'] - current) == 0:
                points = 200  # Perfect!
            state['score'] += points * (1 + state['combo'] * 0.1)
            state['combo'] += 1
            state['max_combo'] = max(state['max_combo'], state['combo'])
            state['hits'] += 1
            state['pattern'].remove(note)
            hit = True
            break

    if not hit:
        state['combo'] = 0
        state['misses'] += 1
        return "Miss!"

    state['current_time'] += 1

    if not state['pattern']:
        return "SONG COMPLETE!"

    return f"{'PERFECT!' if points == 200 else 'Good!'} +{int(points)} Combo: {state['combo']}"


# ============================================================
# RACING GAME - Simple track
# ============================================================

def make_racing_game() -> Dict:
    """Create simple racing game"""
    # Track: 0=road, 1=wall, 2=boost
    track = [
        [1, 0, 0, 0, 1],
        [1, 0, 2, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 2, 0, 1],
        [1, 0, 0, 0, 1],
        [0, 0, 0, 0, 0],  # Finish line
    ]

    return {
        'track': track,
        'player_x': 2,
        'player_y': 0,
        'speed': 1,
        'boosts': 3,
        'damage': 0,
        'time': 0
    }


def racing_game_str(state: Dict) -> str:
    """Display racing game"""
    lines = ['   RACING GAME']
    lines.append('   ' + '=' * 40)

    # Show track view
    py = state['player_y']
    for y in range(max(0, py - 2), min(len(state['track']), py + 4)):
        line = '   '
        for x, cell in enumerate(state['track'][y]):
            if x == state['player_x'] and y == state['player_y']:
                line += 'P '
            elif cell == 1:
                line += '█ '
            elif cell == 2:
                line += '+ '
            else:
                line += '· '
        lines.append(line)

    lines.append(f'\n   Speed: {state["speed"]}  Boosts: {state["boosts"]}  Damage: {state["damage"]}%')
    lines.append(f'   Position: {state["player_y"]}/{len(state["track"])}  Time: {state["time"]}s')
    lines.append('\n   COMMANDS: left, right, boost, forward')

    return '\n'.join(lines)


def racing_game_move(state: Dict, action: str) -> str:
    """Process racing action"""
    track = state['track']
    px, py = state['player_x'], state['player_y']

    if action == 'left' and px > 0:
        state['player_x'] -= 1
    elif action == 'right' and px < len(track[0]) - 1:
        state['player_x'] += 1
    elif action == 'boost' and state['boosts'] > 0:
        state['speed'] += 1
        state['boosts'] -= 1
        return "Boost activated!"
    elif action == 'forward':
        state['player_y'] += state['speed']
        state['time'] += 1

    # Check collision
    if state['player_y'] < len(track):
        cell = track[state['player_y']][state['player_x']]
        if cell == 1:  # Wall
            state['damage'] += 20
            state['speed'] = max(1, state['speed'] - 1)
            return f"Crashed! Damage: {state['damage']}%"
        elif cell == 2:  # Boost pickup
            state['boosts'] += 1
            track[state['player_y']][state['player_x']] = 0
            return "Boost pickup! +1"

    # Check finish
    if state['player_y'] >= len(track):
        return f"RACE COMPLETE! Time: {state['time']}s"

    return "Moved"
