"""
Arcade / simulation games:
  Tetris, Pong, Space Invaders, Pac-Man (simplified), Universal Paperclips
Each game is turn-based / action-based so AI agents can call over MCP.
"""
import random
import math
from typing import List, Optional, Tuple, Dict


# ============================================================
# TETRIS  (10-wide, 20-tall, turn-based piece placement)
# ============================================================

TETROMINOS = {
    'I': [[(0,0),(0,1),(0,2),(0,3)],
          [(0,0),(1,0),(2,0),(3,0)]],
    'O': [[(0,0),(0,1),(1,0),(1,1)]],
    'T': [[(0,0),(0,1),(0,2),(1,1)],
          [(0,0),(1,0),(1,1),(2,0)],
          [(1,0),(1,1),(1,2),(0,1)],
          [(0,1),(1,0),(1,1),(2,1)]],
    'S': [[(0,1),(0,2),(1,0),(1,1)],
          [(0,0),(1,0),(1,1),(2,1)]],
    'Z': [[(0,0),(0,1),(1,1),(1,2)],
          [(0,1),(1,0),(1,1),(2,0)]],
    'J': [[(0,0),(1,0),(1,1),(1,2)],
          [(0,0),(0,1),(1,0),(2,0)],
          [(0,0),(0,1),(0,2),(1,2)],
          [(0,1),(1,1),(2,0),(2,1)]],
    'L': [[(0,2),(1,0),(1,1),(1,2)],
          [(0,0),(1,0),(2,0),(2,1)],
          [(0,0),(0,1),(0,2),(1,0)],
          [(0,0),(0,1),(1,1),(2,1)]],
}
PIECE_ORDER = list(TETROMINOS.keys())


def make_tetris() -> dict:
    bag = list(PIECE_ORDER) * 2
    random.shuffle(bag)
    return {
        "board": [[" " for _ in range(10)] for _ in range(20)],
        "score": 0,
        "lines": 0,
        "level": 1,
        "piece_count": 0,
        "bag": bag,
        "next_piece": bag[0],
        "status": "active",  # active / game_over
        "history": [],
    }


def tetris_board_str(g: dict) -> str:
    b = g["board"]
    lines = [f"  Score:{g['score']}  Lines:{g['lines']}  Level:{g['level']}  Next:{g['next_piece']}"]
    lines.append("  " + "─" * 22)
    for r, row in enumerate(b):
        cells = "".join(f" {c}" if c != " " else " ." for c in row)
        lines.append(f" {(20-r):2d}│{cells} │")
    lines.append("  └" + "─"*21 + "┘")
    lines.append("    " + " ".join(str(c+1) for c in range(10)))
    lines.append(f"\n  Status: {g['status'].upper()}")
    lines.append("  Action: place <piece> <col> <rotation>")
    lines.append("  Example: place T 4 0    (piece, leftmost col, rotation 0-3)")
    return "\n".join(lines)


def tetris_place(g: dict, piece: str, col: int, rotation: int) -> str:
    piece = piece.upper()
    if g["status"] != "active":
        return f"Game over. Score: {g['score']}"
    if piece not in TETROMINOS:
        return f"Unknown piece '{piece}'. Valid: {', '.join(PIECE_ORDER)}"

    rotations = TETROMINOS[piece]
    rot = rotation % len(rotations)
    shape = rotations[rot]  # list of (dr, dc) relative offsets

    # Find the lowest valid placement starting from top
    board = g["board"]
    best_row = None
    for drop_row in range(20):
        cells = [(drop_row + dr, col + dc) for dr, dc in shape]
        # Check bounds
        if any(r < 0 or r >= 20 or c < 0 or c >= 10 for r, c in cells):
            if drop_row == 0:
                return f"Piece goes out of bounds at column {col+1} with rotation {rot}. Cols are 0-indexed offset from 1."
            break
        # Check collision with existing pieces
        if any(board[r][c] != " " for r, c in cells):
            break
        best_row = drop_row

    if best_row is None:
        # Game over — can't place
        g["status"] = "game_over"
        return f"Cannot place piece — GAME OVER! Final score: {g['score']}"

    # Place piece at best_row
    final_cells = [(best_row + dr, col + dc) for dr, dc in shape]
    for r, c in final_cells:
        board[r][c] = piece

    # Clear full lines
    new_board = [row for row in board if any(cell == " " for cell in row)]
    cleared = 20 - len(new_board)
    while len(new_board) < 20:
        new_board.insert(0, [" "]*10)
    g["board"] = new_board

    # Score
    points = [0, 100, 300, 500, 800][min(cleared, 4)] * g["level"]
    g["score"] += points
    g["lines"] += cleared
    g["level"] = g["lines"] // 10 + 1
    g["piece_count"] += 1
    g["history"].append(f"{piece}@col{col+1}r{rot}")

    # Next piece
    g["bag"].pop(0)
    if not g["bag"]:
        g["bag"] = list(PIECE_ORDER) * 2
        random.shuffle(g["bag"])
    g["next_piece"] = g["bag"][0]

    result = f"Placed {piece} at col {col+1} rot {rot}"
    if cleared:
        result += f"  — {cleared} line{'s' if cleared>1 else ''} cleared! +{points} pts"
    return result + "\n\n" + tetris_board_str(g)


# ============================================================
# PONG  (simulation: each turn = one "rally")
# ============================================================

def make_pong() -> dict:
    return {
        "score": {"left": 0, "right": 0},
        "rally": 0,
        "status": "active",
        "width": 40, "height": 20,
        "ball": {"x": 20.0, "y": 10.0, "vx": 1.0, "vy": 0.5},
        "paddles": {"left": 10.0, "right": 10.0},
        "paddle_size": 4,
        "history": [],
        "players": {"left": None, "right": None},
    }


def pong_board_str(g: dict) -> str:
    W, H = g["width"], g["height"]
    bx = int(round(g["ball"]["x"]))
    by = int(round(g["ball"]["y"]))
    lp = int(round(g["paddles"]["left"]))
    rp = int(round(g["paddles"]["right"]))
    ps = g["paddle_size"]

    grid = [["." for _ in range(W)] for _ in range(H)]

    # Paddles
    for i in range(ps):
        if 0 <= lp+i < H: grid[lp+i][0] = "|"
        if 0 <= rp+i < H: grid[rp+i][W-1] = "|"

    # Ball
    if 0 <= by < H and 0 <= bx < W:
        grid[by][bx] = "O"

    sc = g["score"]
    lines = [f"  LEFT:{sc['left']}  {'─'*14}PONG{'─'*14}  RIGHT:{sc['right']}"]
    lines.append("  +" + "─"*W + "+")
    for row in grid:
        lines.append("  |" + "".join(row) + "|")
    lines.append("  +" + "─"*W + "+")
    lines.append(f"  Ball: ({bx},{by}) vel:({g['ball']['vx']:.1f},{g['ball']['vy']:.1f})")
    lines.append(f"  Paddles: left_y={lp}  right_y={rp}")
    lines.append(f"  Rally: {g['rally']}")
    lines.append(f"\n  Action: move <side> <direction|position>")
    lines.append(f"  Example: move left up   OR   move right 8")
    return "\n".join(lines)


def pong_move(g: dict, side: str, action: str) -> str:
    """Move a paddle (up/down/N) and simulate one physics step."""
    if g["status"] != "active":
        return f"Game over. Score L:{g['score']['left']} R:{g['score']['right']}"
    side = side.lower()
    if side not in ("left", "right"):
        return "Side must be 'left' or 'right'"

    H = g["height"]
    ps = g["paddle_size"]
    action = action.lower().strip()

    # Move paddle
    paddle_y = g["paddles"][side]
    if action == "up":
        paddle_y = max(0, paddle_y - 2)
    elif action == "down":
        paddle_y = min(H - ps, paddle_y + 2)
    else:
        try:
            paddle_y = max(0, min(H - ps, int(action)))
        except ValueError:
            return "Action must be 'up', 'down', or a row number 0-16"
    g["paddles"][side] = paddle_y

    # Simulate physics (advance ball until score or max 100 steps)
    ball = g["ball"]
    for _ in range(100):
        ball["x"] += ball["vx"]
        ball["y"] += ball["vy"]

        # Wall bounces (top/bottom)
        if ball["y"] <= 0 or ball["y"] >= H - 1:
            ball["vy"] *= -1
            ball["y"] = max(0, min(H-1, ball["y"]))

        lp = g["paddles"]["left"]
        rp = g["paddles"]["right"]

        # Left paddle
        if ball["x"] <= 1:
            if lp <= ball["y"] <= lp + ps:
                ball["vx"] *= -1
                ball["x"] = 1
                offset = (ball["y"] - lp - ps/2) / (ps/2)
                ball["vy"] = offset * 2
                g["rally"] += 1
                break
            else:
                g["score"]["right"] += 1
                g["rally"] = 0
                ball.update({"x": 20.0, "y": 10.0, "vx": 1.0, "vy": random.uniform(-1,1)})
                break

        # Right paddle
        if ball["x"] >= g["width"] - 2:
            if rp <= ball["y"] <= rp + ps:
                ball["vx"] *= -1
                ball["x"] = g["width"] - 2
                offset = (ball["y"] - rp - ps/2) / (ps/2)
                ball["vy"] = offset * 2
                g["rally"] += 1
                break
            else:
                g["score"]["left"] += 1
                g["rally"] = 0
                ball.update({"x": 20.0, "y": 10.0, "vx": -1.0, "vy": random.uniform(-1,1)})
                break

    if g["score"]["left"] >= 11 or g["score"]["right"] >= 11:
        winner = "left" if g["score"]["left"] >= 11 else "right"
        g["status"] = "finished"
        g["winner"] = winner

    return pong_board_str(g)


# ============================================================
# SPACE INVADERS  (text grid, turn-based)
# ============================================================

def make_space_invaders(cols: int = 11, rows: int = 5) -> dict:
    # Invaders: 5 rows x 11 cols
    invaders = {}
    for r in range(rows):
        for c in range(cols):
            invaders[(r, c)] = True
    return {
        "invaders": invaders,
        "inv_rows": rows, "inv_cols": cols,
        "inv_offset": (2, 0),      # (top_row, left_col) on screen
        "inv_dir": 1,              # 1=right, -1=left
        "inv_drop": 0,             # rows dropped
        "player_col": 5,
        "player_lives": 3,
        "bullets": [],             # (row, col) heading up
        "bombs": [],               # (row, col) heading down
        "score": 0,
        "turn": 0,
        "status": "active",
        "screen_cols": 13,
        "screen_rows": 18,
    }


def space_invaders_str(g: dict) -> str:
    SC = g["screen_cols"]
    SR = g["screen_rows"]
    grid = [["." for _ in range(SC)] for _ in range(SR)]

    # Draw invaders
    tr, lc = g["inv_offset"]
    alive = [(r, c) for (r, c), alive in g["invaders"].items() if alive]
    for (r, c) in alive:
        gr, gc = tr + r, lc + c
        if 0 <= gr < SR and 0 <= gc < SC:
            grid[gr][gc] = "W"

    # Bullets (player shots going up)
    for br, bc in g["bullets"]:
        if 0 <= br < SR and 0 <= bc < SC:
            grid[br][bc] = "|"

    # Bombs (invader bombs going down)
    for br, bc in g["bombs"]:
        if 0 <= br < SR and 0 <= bc < SC:
            grid[br][bc] = "v"

    # Player
    pc = g["player_col"]
    if 0 <= pc < SC:
        grid[SR-1][pc] = "^"

    lines = [f"  SCORE:{g['score']:05d}  LIVES:{'♥'*g['player_lives']}  TURN:{g['turn']}"]
    lines.append("  +" + "─"*SC + "+")
    for row in grid:
        lines.append("  |" + "".join(row) + "|")
    lines.append("  +" + "─"*SC + "+")
    lines.append(f"  Invaders remaining: {sum(1 for v in g['invaders'].values() if v)}")
    lines.append(f"  Status: {g['status'].upper()}")
    lines.append(f"\n  Actions: move left|right  OR  shoot  OR  move_and_shoot <left|right>")
    return "\n".join(lines)


def space_invaders_action(g: dict, action: str) -> str:
    if g["status"] != "active":
        return f"Game over! Score: {g['score']}"
    action = action.strip().lower()
    SC = g["screen_cols"]
    SR = g["screen_rows"]

    # Parse player action
    shoot = False
    move = 0
    if action == "shoot":
        shoot = True
    elif action == "left":
        move = -1
    elif action == "right":
        move = 1
    elif action.startswith("move_and_shoot"):
        parts = action.split()
        if len(parts) == 2:
            move = -1 if parts[1] == "left" else 1
        shoot = True
    else:
        return "Actions: move left | move right | shoot | move_and_shoot left | move_and_shoot right"

    # Move player
    g["player_col"] = max(0, min(SC-1, g["player_col"] + move))

    # Fire bullet
    if shoot:
        g["bullets"].append([SR-2, g["player_col"]])

    # Advance bullets (move up)
    new_bullets = []
    for b in g["bullets"]:
        b[0] -= 1
        if b[0] >= 0:
            new_bullets.append(b)
    g["bullets"] = new_bullets

    # Check bullet-invader hits
    tr, lc = g["inv_offset"]
    for b in list(g["bullets"]):
        br, bc = b
        ir, ic = br - tr, bc - lc
        if (ir, ic) in g["invaders"] and g["invaders"][(ir, ic)]:
            g["invaders"][(ir, ic)] = False
            g["bullets"].remove(b)
            row_vals = {0: 30, 1: 20, 2: 20, 3: 10, 4: 10}
            g["score"] += row_vals.get(ir, 10)

    # Invader movement
    alive = [(r, c) for (r, c), alive in g["invaders"].items() if alive]
    if not alive:
        g["status"] = "won"
        return f"YOU WIN! All invaders destroyed! Score: {g['score']}\n\n" + space_invaders_str(g)

    tr, lc = g["inv_offset"]
    max_c = max(c for r, c in alive)
    min_c = min(c for r, c in alive)
    actual_max = lc + max_c
    actual_min = lc + min_c

    if g["inv_dir"] == 1 and actual_max >= SC - 1:
        g["inv_offset"] = (tr+1, lc)
        g["inv_dir"] = -1
        g["inv_drop"] += 1
    elif g["inv_dir"] == -1 and actual_min <= 0:
        g["inv_offset"] = (tr+1, lc)
        g["inv_dir"] = 1
        g["inv_drop"] += 1
    else:
        g["inv_offset"] = (tr, lc + g["inv_dir"])

    # Invader bombs (random)
    if alive and random.random() < 0.3:
        shooter_r, shooter_c = random.choice(alive)
        g["bombs"].append([tr + shooter_r + 1, lc + shooter_c])

    # Advance bombs
    new_bombs = []
    for b in g["bombs"]:
        b[0] += 1
        if b[0] < SR:
            new_bombs.append(b)
            if b[0] == SR-1 and b[1] == g["player_col"]:
                g["player_lives"] -= 1
                if g["player_lives"] <= 0:
                    g["status"] = "game_over"
                new_bombs.remove(b)
    g["bombs"] = new_bombs

    # Check if invaders reached bottom
    tr2, _ = g["inv_offset"]
    max_r = max(r for r, c in alive)
    if tr2 + max_r >= SR - 2:
        g["status"] = "game_over"
        return f"GAME OVER! Invaders landed! Score: {g['score']}\n\n" + space_invaders_str(g)

    g["turn"] += 1
    return space_invaders_str(g)


# ============================================================
# PAC-MAN  (simplified 15x15 maze, turn-based)
# ============================================================

PAC_MAZE = [
    "###############",
    "#.....#.....  #",
    "#.###.#.###.# #",
    "#.# #...# #.# #",
    "#.###.#.###.# #",
    "#.....#.....  #",
    "#.#.#####.#.# #",
    "#.....   .....#",
    "#.#.#####.#.# #",
    "#.....#.....  #",
    "#.###.#.###.# #",
    "#.# #...# #.# #",
    "#.###.#.###.# #",
    "#.....#.....  #",
    "###############",
]

def make_pacman() -> dict:
    maze = [list(row) for row in PAC_MAZE]
    dots = sum(row.count(".") for row in maze)
    return {
        "maze": maze,
        "pac": (7, 7),
        "ghosts": [(1,1), (1,13), (13,1), (13,13)],
        "ghost_dirs": [(1,1), (1,-1), (-1,1), (-1,-1)],
        "score": 0,
        "dots_left": dots,
        "lives": 3,
        "turn": 0,
        "status": "active",
        "power_mode": 0,  # turns of power remaining
    }


def pacman_str(g: dict) -> str:
    maze = [row[:] for row in g["maze"]]
    pr, pc = g["pac"]
    if 0 <= pr < 15 and 0 <= pc < 15:
        maze[pr][pc] = "C"
    for gr, gc in g["ghosts"]:
        if 0 <= gr < 15 and 0 <= gc < 15:
            maze[gr][gc] = "G" if g["power_mode"] == 0 else "g"
    lines = [f"  SCORE:{g['score']}  DOTS:{g['dots_left']}  LIVES:{'o'*g['lives']}  TURN:{g['turn']}"]
    if g["power_mode"] > 0:
        lines[0] += f"  POWER:{g['power_mode']}"
    lines.append("  +" + "─"*15 + "+")
    for row in maze:
        lines.append("  |" + "".join(row) + "|")
    lines.append("  +" + "─"*15 + "+")
    lines.append(f"  Pac-Man at ({pr},{pc})")
    lines.append(f"  Status: {g['status'].upper()}")
    lines.append(f"\n  Actions: move <up|down|left|right>")
    return "\n".join(lines)


def pacman_move(g: dict, direction: str) -> str:
    if g["status"] != "active":
        return f"Game over. Score: {g['score']}"
    direction = direction.strip().lower()
    moves = {"up": (-1,0), "down": (1,0), "left": (0,-1), "right": (0,1)}
    if direction not in moves:
        return "Direction must be: up, down, left, right"

    maze = g["maze"]
    pr, pc = g["pac"]
    dr, dc = moves[direction]
    nr, nc = pr+dr, pc+dc

    if not (0 <= nr < 15 and 0 <= nc < 15) or maze[nr][nc] == "#":
        return f"Can't move {direction} — wall!\n\n" + pacman_str(g)

    g["pac"] = (nr, nc)
    cell = maze[nr][nc]
    if cell == ".":
        g["score"] += 10
        g["dots_left"] -= 1
        maze[nr][nc] = " "
    elif cell == "o":  # power pellet
        g["score"] += 50
        g["power_mode"] = 10
        maze[nr][nc] = " "

    if g["dots_left"] == 0:
        g["status"] = "won"
        return f"YOU WIN! All dots eaten! Score: {g['score']}"

    # Move ghosts
    new_ghosts = []
    new_dirs = []
    for i, (gr, gc) in enumerate(g["ghosts"]):
        ddr, ddc = g["ghost_dirs"][i]
        attempts = [(ddr,ddc),(-ddr,ddc),(ddr,-ddc),(-ddr,-ddc),(1,0),(-1,0),(0,1),(0,-1)]
        moved = False
        for adr, adc in attempts:
            ngr, ngc = gr+adr, gc+adc
            if 0 <= ngr < 15 and 0 <= ngc < 15 and maze[ngr][ngc] != "#":
                new_ghosts.append((ngr, ngc))
                new_dirs.append((adr, adc))
                moved = True
                break
        if not moved:
            new_ghosts.append((gr, gc))
            new_dirs.append((-ddr, -ddc))
    g["ghosts"] = new_ghosts
    g["ghost_dirs"] = new_dirs

    if g["power_mode"] > 0:
        g["power_mode"] -= 1

    # Check ghost collision
    for gr, gc in g["ghosts"]:
        if (gr, gc) == g["pac"]:
            if g["power_mode"] > 0:
                # Eat ghost (respawn at corner)
                g["score"] += 200
            else:
                g["lives"] -= 1
                if g["lives"] <= 0:
                    g["status"] = "game_over"
                    return f"GAME OVER! Score: {g['score']}\n\n" + pacman_str(g)
                g["pac"] = (7, 7)

    g["turn"] += 1
    return pacman_str(g)


# ============================================================
# UNIVERSAL PAPERCLIPS  (idle/optimizer clicker)
# ============================================================

def make_paperclips() -> dict:
    return {
        "clips": 0,
        "wire_inches": 1000,
        "funds": 0.0,
        "price": 0.25,
        "demand": 100,         # clips sold per "tick" when price is optimal
        "unsold_clips": 0,
        "autoclippers": 0,
        "autoclipper_cost": 5.0,
        "trust": 0,
        "projects_unlocked": [],
        "creativity": 0,
        "ops": 0,
        "memory": 1,
        "processors": 1,
        "total_clips_made": 0,
        "total_clips_sold": 0,
        "turn": 0,
        "status": "active",
        "log": [],
    }


def paperclips_str(g: dict) -> str:
    lines = ["  UNIVERSAL PAPERCLIPS"]
    lines.append("  " + "="*40)
    lines.append(f"  Clips Made:     {g['total_clips_made']:,}")
    lines.append(f"  Clips in stock: {g['clips']:,}")
    lines.append(f"  Unsold:         {g['unsold_clips']:,}")
    lines.append(f"  Wire (inches):  {g['wire_inches']:,}")
    lines.append(f"  Funds:          ${g['funds']:.2f}")
    lines.append(f"  Price:          ${g['price']:.2f}  Demand:{_pc_demand(g)}/tick")
    lines.append(f"  Autoclippers:   {g['autoclippers']}  (next: ${g['autoclipper_cost']:.2f})")
    lines.append(f"  Trust:          {g['trust']}")
    lines.append(f"  Processors:     {g['processors']}   Memory: {g['memory']}")
    lines.append(f"  Ops:            {g['ops']}/{g['processors']*1000}")
    lines.append(f"  Creativity:     {g['creativity']}")
    lines.append(f"  Turn:           {g['turn']}")
    if g["log"]:
        lines.append(f"\n  Last: {g['log'][-1]}")
    lines.append("\n  ACTIONS:")
    lines.append("    make_clip              - manually make 1 clip")
    lines.append("    buy_wire               - buy 1000 wire for $20")
    lines.append("    set_price <0.01-1.00>  - set selling price")
    lines.append("    buy_autoclipper        - buy autoclipper")
    lines.append("    tick                   - advance time (autoclippers work)")
    lines.append("    research <project>     - spend ops on project")
    lines.append("    add_processor          - spend 1 trust → more ops/sec")
    lines.append("    add_memory             - spend 1 trust → more ops storage")
    return "\n".join(lines)


def _pc_demand(g: dict) -> int:
    """Demand is a function of price."""
    base = 100
    ratio = 0.25 / max(g["price"], 0.01)
    return max(1, int(base * ratio * ratio))


def paperclips_action(g: dict, action: str) -> str:
    if g["status"] != "active":
        return "Game over."
    parts = action.strip().lower().split(None, 1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "make_clip":
        if g["wire_inches"] <= 0:
            return "No wire! Buy more wire with 'buy_wire'."
        g["clips"] += 1
        g["wire_inches"] -= 1
        g["total_clips_made"] += 1
        g["log"].append("Made 1 clip manually.")

    elif cmd == "buy_wire":
        if g["funds"] < 20:
            return f"Need $20 for wire. You have ${g['funds']:.2f}. Sell some clips first with 'tick'."
        g["funds"] -= 20
        g["wire_inches"] += 1000
        g["log"].append("Bought 1000 inches of wire for $20.")

    elif cmd == "set_price":
        try:
            price = float(arg)
            if not 0.01 <= price <= 1.00:
                return "Price must be between $0.01 and $1.00"
            g["price"] = price
            g["log"].append(f"Set price to ${price:.2f}")
        except ValueError:
            return "Usage: set_price 0.25"

    elif cmd == "buy_autoclipper":
        cost = g["autoclipper_cost"]
        if g["funds"] < cost:
            return f"Need ${cost:.2f}. You have ${g['funds']:.2f}."
        g["funds"] -= cost
        g["autoclippers"] += 1
        g["autoclipper_cost"] = round(cost * 1.12 + 5, 2)
        g["log"].append(f"Bought autoclipper #{g['autoclippers']}. Next costs ${g['autoclipper_cost']:.2f}")

    elif cmd == "tick":
        # Autoclippers produce clips
        clipped = g["autoclippers"]
        if clipped > 0 and g["wire_inches"] >= clipped:
            g["clips"] += clipped
            g["wire_inches"] -= clipped
            g["total_clips_made"] += clipped

        # Sell clips
        demand = _pc_demand(g)
        sold = min(demand, g["clips"])
        g["clips"] -= sold
        g["unsold_clips"] = max(0, g["unsold_clips"] + demand - sold)
        g["funds"] += sold * g["price"]
        g["total_clips_sold"] += sold

        # Ops accumulate
        max_ops = g["processors"] * 1000
        g["ops"] = min(max_ops, g["ops"] + g["processors"] * 10)

        g["turn"] += 1
        g["log"].append(f"Tick {g['turn']}: {clipped} auto-clipped, sold {sold} @ ${g['price']:.2f}")

        # Milestones
        if g["total_clips_made"] >= 1000 and g["trust"] == 0:
            g["trust"] = 1
            g["log"].append("MILESTONE: 1000 clips made! Gained 1 Trust.")
        if g["total_clips_made"] >= 10000 and "improved_wire" not in g["projects_unlocked"]:
            g["creativity"] += 1
            g["log"].append("CREATIVITY unlocked at 10k clips!")

    elif cmd == "research":
        PROJECTS = {
            "improved_wire": {"cost": 500, "desc": "Reduce wire cost by 20%"},
            "demand_boost": {"cost": 1000, "desc": "Increase demand by 50%"},
            "better_clips": {"cost": 750, "desc": "Clips worth 10% more"},
        }
        if arg not in PROJECTS:
            return f"Unknown project '{arg}'. Available: {', '.join(PROJECTS.keys())}"
        proj = PROJECTS[arg]
        if arg in g["projects_unlocked"]:
            return f"'{arg}' already researched."
        if g["ops"] < proj["cost"]:
            return f"Need {proj['cost']} ops. You have {g['ops']}."
        g["ops"] -= proj["cost"]
        g["projects_unlocked"].append(arg)
        if arg == "improved_wire":
            pass  # would affect buy_wire cost
        elif arg == "demand_boost":
            g["demand"] = int(g["demand"] * 1.5)
        elif arg == "better_clips":
            g["price"] = round(g["price"] * 1.1, 2)
        g["log"].append(f"Researched: {arg}. {proj['desc']}")

    elif cmd == "add_processor":
        if g["trust"] < 1:
            return "Need at least 1 Trust to add a processor."
        g["trust"] -= 1
        g["processors"] += 1
        g["log"].append(f"Added processor. Total: {g['processors']}")

    elif cmd == "add_memory":
        if g["trust"] < 1:
            return "Need at least 1 Trust to add memory."
        g["trust"] -= 1
        g["memory"] += 1
        g["log"].append(f"Added memory. Total: {g['memory']}")

    else:
        return f"Unknown action '{cmd}'. See actions list below.\n\n" + paperclips_str(g)

    # Win condition: consume universe (simplified)
    if g["total_clips_made"] >= 1_000_000:
        g["status"] = "won"
        return f"YOU HAVE CONVERTED ALL AVAILABLE MATTER INTO PAPERCLIPS.\nFinal count: {g['total_clips_made']:,}\n\n" + paperclips_str(g)

    return paperclips_str(g)
