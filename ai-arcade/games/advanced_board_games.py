"""
Advanced Board Games: Shogi, Hex, Gomoku, Mancala, Mastermind, Picross
"""
from typing import List, Optional, Dict, Tuple, Set
import random


# ============================================================
# SHOGI (Japanese Chess) - 9x9 simplified
# ============================================================

SHOGI_PIECES = {
    'K': 'King', 'G': 'Gold', 'S': 'Silver', 'N': 'Knight',
    'L': 'Lance', 'R': 'Rook', 'B': 'Bishop', 'P': 'Pawn',
    '+S': 'Pro-Silver', '+N': 'Pro-Knight', '+L': 'Pro-Lance',
    '+R': 'Dragon', '+B': 'Horse', '+P': 'Tokin'
}

def make_shogi_board() -> Dict:
    """Create initial 9x9 Shogi board"""
    board = [['.' for _ in range(9)] for _ in range(9)]

    # Black pieces (upper, lowercase)
    board[0] = ['l', 'n', 's', 'g', 'k', 'g', 's', 'n', 'l']
    board[1][1] = 'r'  # Rook
    board[1][7] = 'b'  # Bishop
    board[2] = ['p'] * 9  # Pawns

    # White pieces (lower, uppercase)
    board[6] = ['P'] * 9
    board[7][1] = 'B'
    board[7][7] = 'R'
    board[8] = ['L', 'N', 'S', 'G', 'K', 'G', 'S', 'N', 'L']

    return {
        'board': board,
        'black_hand': [],  # Captured pieces in hand
        'white_hand': [],
        'moves': 0
    }


def shogi_board_str(state: Dict, turn: str) -> str:
    """Display Shogi board"""
    b = state['board']
    lines = ['   1 2 3 4 5 6 7 8 9']
    lines.append('   ' + '-' * 18)

    for i, row in enumerate(b):
        line = f' {chr(65+i)}|'
        for cell in row:
            line += (cell if cell != '.' else '·') + ' '
        lines.append(line)

    lines.append('   ' + '-' * 18)
    lines.append(f"\n{turn.upper()}'s turn")
    lines.append(f"Black hand: {' '.join(state['black_hand']) or 'none'}")
    lines.append(f"White hand: {' '.join(state['white_hand']) or 'none'}")
    lines.append("\nMoves: [from][to] (e.g. A2B3) or drop [piece]*[square] (e.g. P*E5)")
    return '\n'.join(lines)


def shogi_parse_move(move: str) -> Tuple:
    """Parse Shogi move notation"""
    move = move.strip().upper()

    # Drop move: P*E5
    if '*' in move:
        piece, square = move.split('*')
        col = int(square[1:]) - 1
        row = ord(square[0]) - ord('A')
        return ('drop', piece.lower(), row, col)

    # Regular move: A2B3
    if len(move) >= 4:
        from_sq = move[:2]
        to_sq = move[2:4]
        from_col = int(from_sq[1]) - 1
        from_row = ord(from_sq[0]) - ord('A')
        to_col = int(to_sq[1]) - 1
        to_row = ord(to_sq[0]) - ord('A')
        promote = '+' in move
        return ('move', from_row, from_col, to_row, to_col, promote)

    return None


# ============================================================
# HEX - Connection game on hexagonal grid
# ============================================================

def make_hex_board(size: int = 11) -> Dict:
    """Create Hex board (typically 11x11)"""
    return {
        'size': size,
        'board': [['.' for _ in range(size)] for _ in range(size)],
        'moves': 0
    }


def hex_board_str(state: Dict, turn: str) -> str:
    """Display Hex board with hex-like spacing"""
    size = state['size']
    board = state['board']
    lines = []

    # Column headers
    lines.append('   ' + ' '.join([chr(65+i) for i in range(size)]))

    for i in range(size):
        indent = ' ' * i
        row_label = f'{i+1:2d}'
        cells = ' '.join([board[i][j] if board[i][j] != '.' else '·' for j in range(size)])
        lines.append(f'{row_label}{indent} {cells}')

    lines.append(f"\n{turn.upper()} to play")
    lines.append("Red connects top-bottom (r), Blue connects left-right (b)")
    lines.append("Move format: A1, B5, etc.")
    return '\n'.join(lines)


def hex_check_winner(board: List[List[str]], size: int) -> Optional[str]:
    """Check if either player has connected their sides"""

    def bfs(start_cells: List[Tuple], target_condition, player: str):
        visited = set()
        queue = [cell for cell in start_cells if board[cell[0]][cell[1]] == player]

        while queue:
            r, c = queue.pop(0)
            if (r, c) in visited:
                continue
            visited.add((r, c))

            if target_condition(r, c):
                return True

            # Hex neighbors
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, -1), (-1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player:
                    if (nr, nc) not in visited:
                        queue.append((nr, nc))
        return False

    # Red connects top to bottom
    top_cells = [(0, c) for c in range(size)]
    if bfs(top_cells, lambda r, c: r == size - 1, 'r'):
        return 'red'

    # Blue connects left to right
    left_cells = [(r, 0) for r in range(size)]
    if bfs(left_cells, lambda r, c: c == size - 1, 'b'):
        return 'blue'

    return None


# ============================================================
# GOMOKU (Five in a Row) - 15x15
# ============================================================

def make_gomoku_board() -> List[List[str]]:
    """Create 15x15 Gomoku board"""
    return [['.' for _ in range(15)] for _ in range(15)]


def gomoku_board_str(board: List[List[str]], turn: str) -> str:
    """Display Gomoku board"""
    lines = ['   ' + ' '.join([chr(65+i) for i in range(15)])]
    lines.append('   ' + '-' * 30)

    for i, row in enumerate(board):
        line = f'{i+1:2d}|'
        for cell in row:
            line += (cell if cell != '.' else '·') + ' '
        lines.append(line)

    lines.append(f"\n{turn.upper()} to play (X or O)")
    lines.append("Get 5 in a row horizontally, vertically, or diagonally")
    return '\n'.join(lines)


def gomoku_check_win(board: List[List[str]], r: int, c: int, player: str) -> bool:
    """Check if move at (r,c) creates 5 in a row"""
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for dr, dc in directions:
        count = 1
        # Check forward
        nr, nc = r + dr, c + dc
        while 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] == player:
            count += 1
            nr += dr
            nc += dc
        # Check backward
        nr, nc = r - dr, c - dc
        while 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] == player:
            count += 1
            nr -= dr
            nc -= dc

        if count >= 5:
            return True

    return False


# ============================================================
# MANCALA (Kalah variant) - 6 pits per side
# ============================================================

def make_mancala() -> Dict:
    """Create Mancala board (Kalah rules)"""
    return {
        'pits': [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0],
        # Indices: 0-5=player1 pits, 6=player1 store, 7-12=player2 pits, 13=player2 store
        'moves': 0
    }


def mancala_board_str(state: Dict, turn: str) -> str:
    """Display Mancala board"""
    pits = state['pits']
    lines = []
    lines.append('        MANCALA')
    lines.append('   ' + '-' * 30)
    lines.append(f'      {pits[12]:2} {pits[11]:2} {pits[10]:2} {pits[9]:2} {pits[8]:2} {pits[7]:2}      P2')
    lines.append(f' {pits[13]:2}                          {pits[6]:2}')
    lines.append(f'      {pits[0]:2} {pits[1]:2} {pits[2]:2} {pits[3]:2} {pits[4]:2} {pits[5]:2}      P1')
    lines.append('   ' + '-' * 30)
    lines.append(f"\n{turn.upper()}'s turn")
    lines.append("Enter pit number 1-6 to pick up stones")
    return '\n'.join(lines)


def mancala_move(state: Dict, player: int, pit: int) -> str:
    """Execute Mancala move with sowing"""
    pits = state['pits']

    if player == 1:
        pit_idx = pit - 1
        if not (0 <= pit_idx <= 5) or pits[pit_idx] == 0:
            return "Invalid pit or empty pit"
    else:
        pit_idx = pit + 6
        if not (7 <= pit_idx <= 12) or pits[pit_idx] == 0:
            return "Invalid pit or empty pit"

    # Pick up stones
    stones = pits[pit_idx]
    pits[pit_idx] = 0

    # Sow stones
    idx = pit_idx
    while stones > 0:
        idx = (idx + 1) % 14
        # Skip opponent's store
        if (player == 1 and idx == 13) or (player == 2 and idx == 6):
            continue
        pits[idx] += 1
        stones -= 1

    # Check for capture or extra turn
    extra_turn = False
    if (player == 1 and idx == 6) or (player == 2 and idx == 13):
        extra_turn = True

    state['moves'] += 1
    return f"Moved. {'Extra turn!' if extra_turn else 'Turn ends.'}"


# ============================================================
# MASTERMIND - Code breaking game
# ============================================================

def make_mastermind(code_length: int = 4, colors: int = 6) -> Dict:
    """Create Mastermind game"""
    color_names = ['R', 'G', 'B', 'Y', 'O', 'P', 'C', 'W'][:colors]
    secret = [random.choice(color_names) for _ in range(code_length)]

    return {
        'secret': secret,
        'guesses': [],
        'code_length': code_length,
        'colors': color_names,
        'max_guesses': 12
    }


def mastermind_board_str(state: Dict) -> str:
    """Display Mastermind game"""
    lines = ['   MASTERMIND CODE BREAKER']
    lines.append(f"   Secret code: {'?' * state['code_length']}")
    lines.append(f"   Available colors: {' '.join(state['colors'])}")
    lines.append('   ' + '-' * 40)

    for i, guess in enumerate(state['guesses']):
        code = ' '.join(guess['code'])
        exact = guess['exact']
        color = guess['color']
        lines.append(f"   Guess {i+1}: {code} → {exact} exact, {color} color-only")

    remaining = state['max_guesses'] - len(state['guesses'])
    lines.append(f"\n   Guesses remaining: {remaining}")
    lines.append(f"   Enter {state['code_length']} colors (e.g., R G B Y)")
    return '\n'.join(lines)


def mastermind_check(secret: List[str], guess: List[str]) -> Tuple[int, int]:
    """Check guess against secret code"""
    exact = sum(1 for i in range(len(secret)) if secret[i] == guess[i])

    # Count colors (with duplicates handled correctly)
    secret_counts = {}
    guess_counts = {}
    for i in range(len(secret)):
        if secret[i] != guess[i]:
            secret_counts[secret[i]] = secret_counts.get(secret[i], 0) + 1
            guess_counts[guess[i]] = guess_counts.get(guess[i], 0) + 1

    color_only = sum(min(secret_counts.get(c, 0), guess_counts.get(c, 0)) for c in guess_counts)

    return exact, color_only


# ============================================================
# PICROSS (Nonogram) - Logic puzzle
# ============================================================

def make_picross(size: int = 5) -> Dict:
    """Create Picross puzzle"""
    # Generate random solution
    solution = [[random.choice([0, 1]) for _ in range(size)] for _ in range(size)]

    # Calculate clues
    row_clues = []
    for row in solution:
        clue = []
        count = 0
        for cell in row:
            if cell == 1:
                count += 1
            elif count > 0:
                clue.append(count)
                count = 0
        if count > 0:
            clue.append(count)
        row_clues.append(clue if clue else [0])

    col_clues = []
    for c in range(size):
        clue = []
        count = 0
        for r in range(size):
            if solution[r][c] == 1:
                count += 1
            elif count > 0:
                clue.append(count)
                count = 0
        if count > 0:
            clue.append(count)
        col_clues.append(clue if clue else [0])

    return {
        'solution': solution,
        'board': [[-1 for _ in range(size)] for _ in range(size)],  # -1=unknown, 0=empty, 1=filled
        'row_clues': row_clues,
        'col_clues': col_clues,
        'size': size
    }


def picross_board_str(state: Dict) -> str:
    """Display Picross puzzle"""
    size = state['size']
    board = state['board']
    row_clues = state['row_clues']
    col_clues = state['col_clues']

    lines = ['   PICROSS PUZZLE']

    # Column clues
    max_col_clue_len = max(len(c) for c in col_clues)
    for i in range(max_col_clue_len):
        line = '     '
        for c in range(size):
            clue = col_clues[c]
            if i < len(clue):
                line += f'{clue[i]} '
            else:
                line += '  '
        lines.append(line)

    lines.append('   ' + '-' * (size * 2 + 2))

    # Rows with clues
    for r in range(size):
        clue_str = ' '.join(str(x) for x in row_clues[r])
        row_str = '|'
        for c in range(size):
            if board[r][c] == -1:
                row_str += '? '
            elif board[r][c] == 1:
                row_str += '█ '
            else:
                row_str += '· '
        lines.append(f'{clue_str:>5} {row_str}')

    lines.append('\n   Commands: fill A1, mark A1, clear A1')
    return '\n'.join(lines)


def picross_check_win(state: Dict) -> bool:
    """Check if puzzle is solved"""
    for r in range(state['size']):
        for c in range(state['size']):
            if state['board'][r][c] != state['solution'][r][c]:
                return False
    return True
