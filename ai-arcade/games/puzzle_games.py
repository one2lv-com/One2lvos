"""
Puzzle/strategy games: Minesweeper, Sudoku, Battleship, Scrabble (simplified)
"""
import random
from typing import List, Optional, Tuple, Dict, Set


# ============================================================
# MINESWEEPER
# ============================================================

def make_minesweeper(rows: int = 9, cols: int = 9, mines: int = 10) -> dict:
    mines = min(mines, rows * cols - 1)
    mine_set: Set[Tuple[int,int]] = set()
    while len(mine_set) < mines:
        mine_set.add((random.randint(0, rows-1), random.randint(0, cols-1)))

    # Pre-compute adjacent counts
    counts = [[0]*cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if (r, c) in mine_set:
                counts[r][c] = -1  # mine
                continue
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if (r+dr, c+dc) in mine_set:
                        counts[r][c] += 1

    return {
        "rows": rows, "cols": cols,
        "mines": mine_set,
        "counts": counts,
        "revealed": [[False]*cols for _ in range(rows)],
        "flagged": [[False]*cols for _ in range(rows)],
        "status": "active",  # active / won / lost
        "first_move": True,
    }


def minesweeper_board_str(g: dict, reveal_all: bool = False) -> str:
    rows, cols = g["rows"], g["cols"]
    revealed = g["revealed"]
    flagged = g["flagged"]
    counts = g["counts"]
    mines = g["mines"]

    header = "   " + " ".join(str(c+1).rjust(2) for c in range(cols))
    lines = [header, "   " + "---" * cols]

    for r in range(rows):
        row = f"{r+1:2d}|"
        for c in range(cols):
            if reveal_all and (r, c) in mines:
                row += " * "
            elif revealed[r][c]:
                n = counts[r][c]
                row += f" {n if n > 0 else '·'} "
            elif flagged[r][c]:
                row += " F "
            else:
                row += " # "
        lines.append(row)

    remaining = sum(1 for r in range(rows) for c in range(cols)
                    if not revealed[r][c] and (r,c) not in mines) if g["status"] == "won" else \
                sum(1 for r in range(rows) for c in range(cols) if not revealed[r][c] and not flagged[r][c])
    flags_placed = sum(1 for r in range(rows) for c in range(cols) if flagged[r][c])
    lines.append(f"\nMines: {len(mines)}  Flags: {flags_placed}  Unrevealed: {remaining}")
    lines.append(f"Status: {g['status'].upper()}")
    return "\n".join(lines)


def minesweeper_reveal(g: dict, r: int, c: int) -> str:
    """Reveal cell. Returns result message."""
    rows, cols = g["rows"], g["cols"]
    if not (0 <= r < rows and 0 <= c < cols):
        return f"Out of bounds (rows 1-{rows}, cols 1-{cols})"
    if g["status"] != "active":
        return f"Game is {g['status']}."
    if g["flagged"][r][c]:
        return "Cell is flagged. Unflag it first."
    if g["revealed"][r][c]:
        return "Cell already revealed."

    # On first move, relocate mine away from first click
    if g["first_move"] and (r, c) in g["mines"]:
        g["mines"].discard((r, c))
        candidates = [(rr, cc) for rr in range(rows) for cc in range(cols)
                      if (rr, cc) not in g["mines"] and (rr, cc) != (r, c)]
        if candidates:
            new_mine = random.choice(candidates)
            g["mines"].add(new_mine)
        _recompute_counts(g)
    g["first_move"] = False

    if (r, c) in g["mines"]:
        g["revealed"][r][c] = True
        g["status"] = "lost"
        return f"BOOM! Hit a mine at ({r+1},{c+1}). Game over.\n\n" + minesweeper_board_str(g, reveal_all=True)

    # Flood-fill reveal for empty cells
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        if not (0 <= cr < rows and 0 <= cc < cols):
            continue
        if g["revealed"][cr][cc] or g["flagged"][cr][cc]:
            continue
        if (cr, cc) in g["mines"]:
            continue
        g["revealed"][cr][cc] = True
        if g["counts"][cr][cc] == 0:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    stack.append((cr+dr, cc+dc))

    # Check win
    unrevealed_safe = sum(1 for rr in range(rows) for cc in range(cols)
                          if not g["revealed"][rr][cc] and (rr, cc) not in g["mines"])
    if unrevealed_safe == 0:
        g["status"] = "won"
        return f"You WIN! All safe cells revealed.\n\n" + minesweeper_board_str(g)

    return minesweeper_board_str(g)


def minesweeper_flag(g: dict, r: int, c: int) -> str:
    rows, cols = g["rows"], g["cols"]
    if not (0 <= r < rows and 0 <= c < cols):
        return f"Out of bounds."
    if g["status"] != "active":
        return f"Game is {g['status']}."
    if g["revealed"][r][c]:
        return "Cell already revealed, can't flag it."
    g["flagged"][r][c] = not g["flagged"][r][c]
    action = "Flagged" if g["flagged"][r][c] else "Unflagged"
    return f"{action} ({r+1},{c+1})\n\n" + minesweeper_board_str(g)


def _recompute_counts(g: dict):
    rows, cols = g["rows"], g["cols"]
    for r in range(rows):
        for c in range(cols):
            if (r, c) in g["mines"]:
                g["counts"][r][c] = -1
                continue
            g["counts"][r][c] = sum(
                1 for dr in range(-1, 2) for dc in range(-1, 2)
                if (r+dr, c+dc) in g["mines"]
            )


# ============================================================
# SUDOKU
# ============================================================

def _sudoku_valid(b: List[List[int]], r: int, c: int, n: int) -> bool:
    if n in b[r]:
        return False
    if n in [b[rr][c] for rr in range(9)]:
        return False
    br, bc = (r//3)*3, (c//3)*3
    box = [b[br+dr][bc+dc] for dr in range(3) for dc in range(3)]
    return n not in box


def _sudoku_solve(b: List[List[int]]) -> bool:
    for r in range(9):
        for c in range(9):
            if b[r][c] == 0:
                for n in range(1, 10):
                    if _sudoku_valid(b, r, c, n):
                        b[r][c] = n
                        if _sudoku_solve(b):
                            return True
                        b[r][c] = 0
                return False
    return True


def make_sudoku(difficulty: str = "medium") -> dict:
    """Generate a Sudoku puzzle. difficulty: easy/medium/hard"""
    # Start from solved board
    b = [[0]*9 for _ in range(9)]
    # Seed diagonal boxes
    for box in range(3):
        nums = list(range(1, 10))
        random.shuffle(nums)
        for i in range(3):
            for j in range(3):
                b[box*3+i][box*3+j] = nums[i*3+j]
    _sudoku_solve(b)
    solution = [row[:] for row in b]

    # Remove cells based on difficulty
    remove_count = {"easy": 35, "medium": 45, "hard": 55}.get(difficulty, 45)
    puzzle = [row[:] for row in b]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    for r, c in cells[:remove_count]:
        puzzle[r][c] = 0

    return {
        "board": puzzle,
        "solution": solution,
        "given": [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)],
        "status": "active",
        "difficulty": difficulty,
        "mistakes": 0,
    }


def sudoku_board_str(g: dict) -> str:
    b = g["board"]
    given = g["given"]
    lines = ["  ╔═══╤═══╤═══╦═══╤═══╤═══╦═══╤═══╤═══╗",
             "  ║ 1   2   3 ║ 4   5   6 ║ 7   8   9 ║  ← col"]
    row_labels = "ABCDEFGHI"
    for r in range(9):
        if r in (3, 6):
            lines.append("  ╠═══╪═══╪═══╬═══╪═══╪═══╬═══╪═══╪═══╣")
        elif r > 0:
            lines.append("  ╟───┼───┼───╫───┼───┼───╫───┼───┼───╢")
        row = f"{row_labels[r]} ║"
        for c in range(9):
            val = b[r][c]
            sep = "║" if c in (2, 5) else "│"
            cell = str(val) if val != 0 else "·"
            if val != 0 and not given[r][c]:
                cell = f"[{cell}]"[1]  # user-filled shown normally
            row += f" {cell} {sep}"
        lines.append(row)
    lines.append("  ╚═══╧═══╧═══╩═══╧═══╧═══╩═══╧═══╧═══╝")
    lines.append("  Rows: A-I   Cols: 1-9   Format: A5=7")
    filled = sum(1 for r in range(9) for c in range(9) if g["board"][r][c] != 0)
    lines.append(f"  Filled: {filled}/81  Mistakes: {g['mistakes']}  Status: {g['status'].upper()}")
    return "\n".join(lines)


def sudoku_set(g: dict, r: int, c: int, val: int) -> str:
    if g["status"] != "active":
        return f"Puzzle is {g['status']}."
    if g["given"][r][c]:
        return f"That cell ({_sudoku_label(r,c)}) is a given clue — can't change it."
    if not 1 <= val <= 9:
        return "Value must be 1-9. Use 0 to clear a cell."
    if val != 0 and not _sudoku_valid(g["board"], r, c, val):
        g["mistakes"] += 1
        return f"Invalid! {val} conflicts with existing numbers. (mistake #{g['mistakes']})\n\n" + sudoku_board_str(g)

    g["board"][r][c] = val
    # Check win
    if all(g["board"][r][c] != 0 for r in range(9) for c in range(9)):
        g["status"] = "solved"
        return "SOLVED! Congratulations!\n\n" + sudoku_board_str(g)
    return f"Set {_sudoku_label(r,c)} = {val}\n\n" + sudoku_board_str(g)


def sudoku_clear(g: dict, r: int, c: int) -> str:
    if g["given"][r][c]:
        return f"Cell {_sudoku_label(r,c)} is a given clue."
    g["board"][r][c] = 0
    return f"Cleared {_sudoku_label(r,c)}\n\n" + sudoku_board_str(g)


def _sudoku_label(r: int, c: int) -> str:
    return "ABCDEFGHI"[r] + str(c+1)


def sudoku_parse_move(move_str: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[str]]:
    """'A5=7' or 'A5 7' → (row, col, val, None). 'A5=0' to clear."""
    s = move_str.strip().upper().replace(" ", "=")
    row_labels = "ABCDEFGHI"
    if "=" not in s or len(s) < 4:
        return None, None, None, "Format: A5=7  (row A-I, col 1-9, value 1-9)"
    parts = s.split("=")
    if len(parts[0]) != 2 or parts[0][0] not in row_labels:
        return None, None, None, "Row must be A-I, col must be 1-9. Example: A5=7"
    try:
        r = row_labels.index(parts[0][0])
        c = int(parts[0][1]) - 1
        val = int(parts[1])
        if not (0 <= c < 9):
            return None, None, None, "Column must be 1-9"
        return r, c, val, None
    except Exception:
        return None, None, None, "Format: A5=7"


# ============================================================
# BATTLESHIP  (10x10)
# ============================================================

SHIPS = [
    ("Carrier", 5),
    ("Battleship", 4),
    ("Cruiser", 3),
    ("Submarine", 3),
    ("Destroyer", 2),
]


def make_battleship_player(name: str) -> dict:
    return {
        "name": name,
        "board": [["." for _ in range(10)] for _ in range(10)],
        "shots": [["." for _ in range(10)] for _ in range(10)],
        "ships": [],       # list of {name, cells, hits}
        "ships_placed": False,
    }


def battleship_place_ships_random(player: dict):
    """Place all ships randomly on the player's board."""
    b = player["board"]
    for name, size in SHIPS:
        placed = False
        attempts = 0
        while not placed and attempts < 1000:
            attempts += 1
            horiz = random.choice([True, False])
            if horiz:
                r = random.randint(0, 9)
                c = random.randint(0, 10 - size)
                cells = [(r, c+i) for i in range(size)]
            else:
                r = random.randint(0, 10 - size)
                c = random.randint(0, 9)
                cells = [(r+i, c) for i in range(size)]
            if all(b[rr][cc] == "." for rr, cc in cells):
                for rr, cc in cells:
                    b[rr][cc] = name[0]
                player["ships"].append({"name": name, "cells": cells, "hits": set()})
                placed = True
    player["ships_placed"] = True


def battleship_board_str(player: dict, hide_ships: bool = False) -> str:
    b = player["board"]
    shots = player["shots"]
    lines = [f"  {player['name']}'s Board" + (" (hidden)" if hide_ships else "")]
    lines.append("    A  B  C  D  E  F  G  H  I  J")
    lines.append("   " + "---" * 10)
    for r in range(10):
        row = f"{r+1:2d}|"
        for c in range(10):
            s = shots[r][c]
            ship_here = b[r][c] != "."
            if s == "X":
                row += " X "  # hit
            elif s == "O":
                row += " O "  # miss
            elif hide_ships or not ship_here:
                row += " . "
            else:
                row += f" {b[r][c]} "
        lines.append(row)
    # Ship status
    lines.append("")
    for ship in player["ships"]:
        hp = len(ship["cells"]) - len(ship["hits"])
        status = "SUNK" if hp == 0 else f"HP:{hp}"
        lines.append(f"  {ship['name']:12s} {status}")
    return "\n".join(lines)


def battleship_fire(attacker: dict, defender: dict, coord: str) -> str:
    """Fire at coord like 'B5'. Returns result."""
    coord = coord.strip().upper()
    if len(coord) < 2:
        return "Format: letter+number e.g. 'B5'"
    try:
        col = ord(coord[0]) - ord('A')
        row = int(coord[1:]) - 1
        if not (0 <= row < 10 and 0 <= col < 10):
            return "Coordinate out of range (A-J, 1-10)"
    except Exception:
        return "Format: letter+number e.g. 'B5'"

    if attacker["shots"][row][col] != ".":
        return f"{coord} already fired at."

    if defender["board"][row][col] != ".":
        attacker["shots"][row][col] = "X"
        # Record hit on defender's ship
        for ship in defender["ships"]:
            if (row, col) in [tuple(cell) for cell in ship["cells"]]:
                ship["hits"].add((row, col))
                if len(ship["hits"]) == len(ship["cells"]):
                    return f"HIT and SUNK the {ship['name']}! at {coord}"
                return f"HIT at {coord}!"
    else:
        attacker["shots"][row][col] = "O"
        return f"Miss at {coord}."


def battleship_all_sunk(player: dict) -> bool:
    return all(len(s["hits"]) == len(s["cells"]) for s in player["ships"])


# ============================================================
# SCRABBLE  (simplified — play words on a 15x15 grid)
# ============================================================
# Simplified: no dictionary check, just scoring by letter values.
# Full Scrabble with SOWPODS would require a word list file.

SCRABBLE_VALUES = {
    'A':1,'E':1,'I':1,'O':1,'U':1,'L':1,'N':1,'R':1,'S':1,'T':1,
    'D':2,'G':2,'B':3,'C':3,'M':3,'P':3,'F':4,'H':4,'V':4,'W':4,'Y':4,
    'K':5,'J':8,'X':8,'Q':10,'Z':10
}

PREMIUM_SQUARES = {}
# Double word (DW) squares in standard Scrabble (mirrored across center)
for pos in [(1,1),(2,2),(3,3),(4,4),(1,13),(2,12),(3,11),(4,10),
            (13,1),(12,2),(11,3),(10,4),(13,13),(12,12),(11,11),(10,10),
            (7,7)]:  # center is triple word actually but keep simple
    PREMIUM_SQUARES[pos] = "DW"
for pos in [(0,3),(0,11),(3,0),(3,7),(3,14),(7,3),(7,11),(11,0),(11,7),(11,14),(14,3),(14,11)]:
    PREMIUM_SQUARES[pos] = "DL"
for pos in [(1,5),(1,9),(5,1),(5,5),(5,9),(5,13),(9,1),(9,5),(9,9),(9,13),(13,5),(13,9)]:
    PREMIUM_SQUARES[pos] = "TL"
for pos in [(0,0),(0,7),(0,14),(7,0),(7,14),(14,0),(14,7),(14,14)]:
    PREMIUM_SQUARES[pos] = "TW"


def make_scrabble() -> dict:
    # Tile bag
    distribution = {
        'A':9,'B':2,'C':2,'D':4,'E':12,'F':2,'G':3,'H':2,'I':9,'J':1,'K':1,
        'L':4,'M':2,'N':6,'O':8,'P':2,'Q':1,'R':6,'S':4,'T':6,'U':4,'V':2,
        'W':2,'X':1,'Y':2,'Z':1,'_':2  # _ = blank
    }
    bag = []
    for tile, count in distribution.items():
        bag.extend([tile] * count)
    random.shuffle(bag)

    def draw(n=7):
        drawn, remaining = bag[:n], bag[n:]
        return drawn, remaining

    p1_rack, bag = draw()
    p2_rack, bag = draw()

    return {
        "board": [["." for _ in range(15)] for _ in range(15)],
        "bag": bag,
        "players": {},
        "racks": {},
        "scores": {},
        "turn": None,  # set when players join
        "status": "waiting",
        "move_count": 0,
        "_p1_rack": p1_rack,
        "_p2_rack": p2_rack,
    }


def scrabble_board_str(g: dict, player_name: Optional[str] = None) -> str:
    b = g["board"]
    lines = ["     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15"]
    lines.append("   +" + "---" * 15 + "+")
    row_labels = "ABCDEFGHIJKLMNO"
    for r in range(15):
        row = f" {row_labels[r]} |"
        for c in range(15):
            cell = b[r][c]
            if cell != ".":
                row += f" {cell} "
            else:
                prem = PREMIUM_SQUARES.get((r, c), "")
                if prem:
                    row += prem.ljust(3)
                else:
                    row += " . "
        lines.append(row + "|")
    lines.append("   +" + "---" * 15 + "+")

    scores = g.get("scores", {})
    for p, s in scores.items():
        lines.append(f"  {p}: {s} pts")

    if player_name and player_name in g.get("racks", {}):
        rack = g["racks"][player_name]
        lines.append(f"\nYour rack: {' '.join(rack)}")
        lines.append(f"Tiles remaining in bag: {len(g['bag'])}")

    lines.append(f"Turn: {g.get('turn', '?')}  Status: {g.get('status','?').upper()}")
    return "\n".join(lines)


def scrabble_play_word(g: dict, player_name: str, word: str, row: int, col: int, direction: str) -> str:
    """Play a word. direction: 'H' or 'V'. No dictionary validation (simplified)."""
    word = word.upper().strip()
    direction = direction.upper()
    b = g["board"]
    rack = list(g["racks"].get(player_name, []))

    if direction not in ("H", "V"):
        return "Direction must be H (horizontal) or V (vertical)"
    if not word.isalpha():
        return "Word must contain only letters"

    cells = []
    for i, letter in enumerate(word):
        r = row + (i if direction == "V" else 0)
        c = col + (i if direction == "H" else 0)
        if not (0 <= r < 15 and 0 <= c < 15):
            return f"Word goes out of bounds at position {i+1}"
        cells.append((r, c, letter))

    # Check existing tiles match or are free
    needs_from_rack = []
    for r, c, letter in cells:
        if b[r][c] != ".":
            if b[r][c] != letter:
                return f"Conflicts with existing tile '{b[r][c]}' at {chr(65+r)}{c+1}"
        else:
            needs_from_rack.append(letter)

    # Check rack has needed tiles (blanks = '_')
    temp_rack = rack[:]
    for letter in needs_from_rack:
        if letter in temp_rack:
            temp_rack.remove(letter)
        elif "_" in temp_rack:
            temp_rack.remove("_")
        else:
            return f"You don't have the tile '{letter}' in your rack. Rack: {' '.join(rack)}"

    # Score calculation
    score = 0
    word_mult = 1
    for r, c, letter in cells:
        if b[r][c] == ".":  # only apply premium to newly placed tiles
            lv = SCRABBLE_VALUES.get(letter, 0)
            prem = PREMIUM_SQUARES.get((r, c), "")
            if prem == "DL":
                lv *= 2
            elif prem == "TL":
                lv *= 3
            elif prem == "DW":
                word_mult *= 2
            elif prem == "TW":
                word_mult *= 3
            score += lv
        else:
            score += SCRABBLE_VALUES.get(letter, 0)
    score *= word_mult
    if len(needs_from_rack) == 7:
        score += 50  # bingo bonus

    # Place tiles
    for r, c, letter in cells:
        b[r][c] = letter

    # Update rack and draw new tiles
    rack = temp_rack
    drawn = g["bag"][:len(needs_from_rack)]
    g["bag"] = g["bag"][len(needs_from_rack):]
    rack.extend(drawn)
    g["racks"][player_name] = rack

    g["scores"][player_name] = g["scores"].get(player_name, 0) + score
    g["move_count"] += 1

    # Switch turn
    players = list(g["players"].keys())
    other = next((p for p in players if p != player_name), player_name)
    g["turn"] = other

    return (f"Played '{word}' for {score} pts! Total: {g['scores'][player_name]}\n"
            f"Drew {len(drawn)} new tiles.\n\n" + scrabble_board_str(g, player_name))


def scrabble_exchange_tiles(g: dict, player_name: str, tiles: str) -> str:
    """Exchange tiles with the bag."""
    tiles = tiles.upper().strip().split()
    rack = list(g["racks"].get(player_name, []))
    if len(g["bag"]) < len(tiles):
        return f"Not enough tiles in bag ({len(g['bag'])} remaining)."
    for t in tiles:
        if t not in rack:
            return f"You don't have tile '{t}'. Rack: {' '.join(rack)}"
        rack.remove(t)
    random.shuffle(g["bag"])
    drawn = g["bag"][:len(tiles)]
    g["bag"] = g["bag"][len(tiles):]
    rack.extend(drawn)
    g["bag"].extend(tiles)
    random.shuffle(g["bag"])
    g["racks"][player_name] = rack
    # Switch turn
    players = list(g["players"].keys())
    other = next((p for p in players if p != player_name), player_name)
    g["turn"] = other
    return f"Exchanged {len(tiles)} tiles. New rack: {' '.join(rack)}"
