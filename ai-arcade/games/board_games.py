"""
Board games: Checkers, Othello/Reversi, Go (9x9)
"""
from typing import List, Optional, Dict, Tuple, Set


# ============================================================
# CHECKERS  (American 8x8)
# ============================================================
# Pieces: 'b'=black man, 'B'=black king, 'w'=white man, 'W'=white king
# Black moves from row 0→7 (top→bottom), White moves 7→0 (bottom→top)
# Squares labelled 1-32 (standard checkers notation) or row,col

def make_checkers_board() -> List[List[str]]:
    b = [["." for _ in range(8)] for _ in range(8)]
    for row in range(3):
        for col in range(8):
            if (row + col) % 2 == 1:
                b[row][col] = "b"
    for row in range(5, 8):
        for col in range(8):
            if (row + col) % 2 == 1:
                b[row][col] = "w"
    return b


def checkers_board_str(b: List[List[str]], current_turn: str) -> str:
    lines = ["   a b c d e f g h"]
    lines.append("   " + "-" * 16)
    for r in range(8):
        row = f" {8-r}|"
        for c in range(8):
            cell = b[r][c]
            if (r + c) % 2 == 0:
                row += "  "
            else:
                if cell == ".":
                    row += "· "
                elif cell == "b":
                    row += "b "
                elif cell == "B":
                    row += "B "
                elif cell == "w":
                    row += "w "
                elif cell == "W":
                    row += "W "
                else:
                    row += "  "
        lines.append(row)
    lines.append("   " + "-" * 16)
    lines.append("   a b c d e f g h")
    lines.append(f"\nLegend: b=black  B=Black King  w=white  W=White King")
    lines.append(f"Turn: {current_turn.upper()}")
    return "\n".join(lines)


def _parse_checker_sq(sq: str) -> Tuple[int, int]:
    """'e4' → (row, col). Row 1=bottom(index 7), Row 8=top(index 0)."""
    sq = sq.strip().lower()
    col = ord(sq[0]) - ord('a')
    row = 8 - int(sq[1])
    return row, col


def _fmt_sq(r: int, c: int) -> str:
    return chr(ord('a') + c) + str(8 - r)


def checkers_get_moves(b: List[List[str]], turn: str) -> List[Tuple]:
    """Returns list of (from_r, from_c, to_r, to_c, captured_r, captured_c).
    captured_* is None for non-jump moves. Jumps are mandatory if any exist."""
    pieces = [("b", "B")] if turn == "black" else [("w", "W")]
    own = set(pieces[0])
    enemy = {"b", "B"} if turn == "white" else {"w", "W"}

    jumps = []
    simple = []

    for r in range(8):
        for c in range(8):
            p = b[r][c]
            if p not in own:
                continue
            is_king = p.isupper()
            dirs = []
            if turn == "black" or is_king:
                dirs += [(1, -1), (1, 1)]
            if turn == "white" or is_king:
                dirs += [(-1, -1), (-1, 1)]

            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    if b[nr][nc] in enemy:
                        jr, jc = nr + dr, nc + dc
                        if 0 <= jr < 8 and 0 <= jc < 8 and b[jr][jc] == ".":
                            jumps.append((r, c, jr, jc, nr, nc))
                    elif b[nr][nc] == "." and not jumps:
                        simple.append((r, c, nr, nc, None, None))

    return jumps if jumps else simple


def checkers_apply_move(b: List[List[str]], move: Tuple, turn: str) -> str:
    """Apply move, return new turn ('black' or 'white'), or 'black_wins'/'white_wins'/'draw'."""
    fr, fc, tr, tc, cr, cc = move
    piece = b[fr][fc]
    b[fr][fc] = "."
    if cr is not None:
        b[cr][cc] = "."

    # King promotion
    if piece == "b" and tr == 7:
        piece = "B"
    elif piece == "w" and tr == 0:
        piece = "W"
    b[tr][tc] = piece

    # Check for multi-jump (same piece can jump again)
    next_turn = "white" if turn == "black" else "black"

    # Count pieces
    black_count = sum(1 for row in b for cell in row if cell in ("b", "B"))
    white_count = sum(1 for row in b for cell in row if cell in ("w", "W"))
    if black_count == 0:
        return "white_wins"
    if white_count == 0:
        return "black_wins"

    # Check if next player has moves
    if not checkers_get_moves(b, next_turn):
        return "black_wins" if next_turn == "white" else "white_wins"

    return next_turn


def checkers_parse_move(move_str: str, b: List[List[str]], turn: str):
    """Parse 'e3-f4' or 'e3xf5' and validate."""
    move_str = move_str.strip().lower()
    sep = "x" if "x" in move_str else "-"
    parts = move_str.split(sep)
    if len(parts) != 2:
        return None, "Format: 'e3-f4' (move) or 'e3xf5' (jump)"
    try:
        fr, fc = _parse_checker_sq(parts[0])
        tr, tc = _parse_checker_sq(parts[1])
    except Exception:
        return None, "Invalid square. Use letter+number like 'e3'"

    legal = checkers_get_moves(b, turn)
    for mv in legal:
        if mv[0] == fr and mv[1] == fc and mv[2] == tr and mv[3] == tc:
            return mv, None
    legal_strs = [f"{_fmt_sq(m[0],m[1])}{'-' if m[4] is None else 'x'}{_fmt_sq(m[2],m[3])}" for m in legal]
    return None, f"Illegal move. Legal moves: {', '.join(legal_strs[:12])}"


# ============================================================
# OTHELLO / REVERSI  (8x8)
# ============================================================
# 'B'=black, 'W'=white, '.'=empty

def make_othello_board() -> List[List[str]]:
    b = [["." for _ in range(8)] for _ in range(8)]
    b[3][3] = "W"; b[3][4] = "B"
    b[4][3] = "B"; b[4][4] = "W"
    return b


def othello_board_str(b: List[List[str]], turn: str, valid_moves: List[Tuple[int,int]]) -> str:
    valid_set = set(valid_moves)
    lines = ["   a b c d e f g h"]
    lines.append("   " + "-" * 16)
    for r in range(8):
        row = f" {r+1}|"
        for c in range(8):
            if b[r][c] == "B":
                row += "B "
            elif b[r][c] == "W":
                row += "W "
            elif (r, c) in valid_set:
                row += "* "
            else:
                row += ". "
        lines.append(row)
    lines.append("   " + "-" * 16)
    lines.append("   a b c d e f g h")
    bc = sum(row.count("B") for row in b)
    wc = sum(row.count("W") for row in b)
    lines.append(f"\nScore: B={bc}  W={wc}  (* = valid moves for {turn.upper()})")
    return "\n".join(lines)


DIRS_8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

def othello_valid_moves(b: List[List[str]], turn: str) -> List[Tuple[int,int]]:
    own = "B" if turn == "black" else "W"
    opp = "W" if turn == "black" else "B"
    moves = []
    for r in range(8):
        for c in range(8):
            if b[r][c] != ".":
                continue
            for dr, dc in DIRS_8:
                nr, nc = r+dr, c+dc
                found_opp = False
                while 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == opp:
                    found_opp = True
                    nr += dr; nc += dc
                if found_opp and 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == own:
                    moves.append((r, c))
                    break
    return moves


def othello_apply_move(b: List[List[str]], r: int, c: int, turn: str):
    own = "B" if turn == "black" else "W"
    opp = "W" if turn == "black" else "B"
    b[r][c] = own
    for dr, dc in DIRS_8:
        to_flip = []
        nr, nc = r+dr, c+dc
        while 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == opp:
            to_flip.append((nr, nc))
            nr += dr; nc += dc
        if to_flip and 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == own:
            for fr, fc in to_flip:
                b[fr][fc] = own


def othello_parse_move(move_str: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """'c4' → (row=3, col=2, None). Returns (None, None, error_str) on failure."""
    s = move_str.strip().lower()
    if s == "pass":
        return -1, -1, None
    if len(s) < 2:
        return None, None, "Format: column letter + row number e.g. 'c4'"
    try:
        col = ord(s[0]) - ord('a')
        row = int(s[1]) - 1
        if not (0 <= row < 8 and 0 <= col < 8):
            return None, None, "Square out of range (a-h, 1-8)"
        return row, col, None
    except Exception:
        return None, None, "Format: column letter + row number e.g. 'c4'"


# ============================================================
# GO  (9x9 with capture, no Ko for simplicity)
# ============================================================
# '.'=empty, 'B'=black stone, 'W'=white stone

def make_go_board(size: int = 9) -> List[List[str]]:
    return [["." for _ in range(size)] for _ in range(size)]


def go_board_str(b: List[List[str]], turn: str, captures: Dict[str,int], last_move: Optional[str] = None) -> str:
    size = len(b)
    cols = "ABCDEFGHIJKLMNOPQRST"[:size]
    lines = [f"    {' '.join(cols)}"]
    lines.append("   +" + "--+" * size)
    for r in range(size):
        row = f"{size-r:2d} |"
        for c in range(size):
            cell = b[r][c]
            row += ("B " if cell == "B" else "W " if cell == "W" else ". ")
        lines.append(row + f"| {size-r}")
    lines.append("   +" + "--+" * size)
    lines.append(f"    {' '.join(cols)}")
    lines.append(f"\nCaptures: Black={captures.get('black',0)}  White={captures.get('white',0)}")
    lines.append(f"Turn: {turn.upper()}" + (f"  Last: {last_move}" if last_move else ""))
    return "\n".join(lines)


def go_get_group(b: List[List[str]], r: int, c: int) -> Tuple[Set[Tuple[int,int]], int]:
    """Return (group_cells, liberty_count)."""
    size = len(b)
    color = b[r][c]
    if color == ".":
        return set(), 0
    visited = set()
    liberties = set()
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        if (cr, cc) in visited:
            continue
        visited.add((cr, cc))
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = cr+dr, cc+dc
            if 0 <= nr < size and 0 <= nc < size:
                if b[nr][nc] == ".":
                    liberties.add((nr, nc))
                elif b[nr][nc] == color and (nr, nc) not in visited:
                    stack.append((nr, nc))
    return visited, len(liberties)


def go_apply_move(b: List[List[str]], r: int, c: int, turn: str, captures: Dict[str,int]) -> Optional[str]:
    """Place stone, remove captured groups. Returns error string or None."""
    size = len(b)
    if not (0 <= r < size and 0 <= c < size):
        return "Position out of bounds"
    if b[r][c] != ".":
        return "Position already occupied"

    own = "B" if turn == "black" else "W"
    opp = "W" if turn == "black" else "B"
    b[r][c] = own

    cap_key = "black" if turn == "black" else "white"

    # Remove captured opponent groups
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < size and 0 <= nc < size and b[nr][nc] == opp:
            group, libs = go_get_group(b, nr, nc)
            if libs == 0:
                captures[cap_key] = captures.get(cap_key, 0) + len(group)
                for gr, gc in group:
                    b[gr][gc] = "."

    # Check suicide (own group has no liberties after capture)
    _, own_libs = go_get_group(b, r, c)
    if own_libs == 0:
        b[r][c] = "."  # Revert — suicide not allowed
        return "Suicide move not allowed (would have no liberties)"

    return None


def go_parse_move(move_str: str, size: int = 9) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """'C4' → (row, col, None). 'pass' → (-1, -1, None)."""
    s = move_str.strip().upper()
    if s == "PASS":
        return -1, -1, None
    cols = "ABCDEFGHIJKLMNOPQRST"
    if len(s) < 2 or s[0] not in cols:
        return None, None, f"Format: column letter + row number e.g. 'D5' or 'pass'"
    try:
        col = cols.index(s[0])
        row = size - int(s[1:])
        if not (0 <= row < size and 0 <= col < size):
            return None, None, f"Out of range. Board is {size}x{size} ({cols[:size]}1-{size})"
        return row, col, None
    except Exception:
        return None, None, "Format: letter + number e.g. 'D5'"


def go_count_territory(b: List[List[str]]) -> Tuple[int, int]:
    """Simple territory count (flood fill empty regions)."""
    size = len(b)
    visited = set()
    b_terr = w_terr = 0

    for r in range(size):
        for c in range(size):
            if b[r][c] != "." or (r, c) in visited:
                continue
            # Flood fill empty region
            region = set()
            borders = set()
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if (cr, cc) in region:
                    continue
                region.add((cr, cc))
                visited.add((cr, cc))
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = cr+dr, cc+dc
                    if 0 <= nr < size and 0 <= nc < size:
                        if b[nr][nc] == ".":
                            stack.append((nr, nc))
                        else:
                            borders.add(b[nr][nc])
            if len(borders) == 1:
                if "B" in borders:
                    b_terr += len(region)
                elif "W" in borders:
                    w_terr += len(region)
    return b_terr, w_terr
