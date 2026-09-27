#!/usr/bin/env python3
"""
AI Arcade MCP Server  —  50+ game titles for AI agents
Implements MCP HTTP+SSE (2024-11-05) + Streamable HTTP transports.

Run:
  python server.py
  python server.py --port 8080
  python server.py --host 0.0.0.0 --port 8080
"""

import argparse
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import chess
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from games.board_games import (
    make_checkers_board, checkers_board_str, checkers_get_moves,
    checkers_apply_move, checkers_parse_move,
    make_othello_board, othello_board_str, othello_valid_moves,
    othello_apply_move, othello_parse_move,
    make_go_board, go_board_str, go_apply_move, go_parse_move, go_count_territory,
)
from games.puzzle_games import (
    make_minesweeper, minesweeper_board_str, minesweeper_reveal, minesweeper_flag,
    make_sudoku, sudoku_board_str, sudoku_set, sudoku_clear, sudoku_parse_move,
    make_battleship_player, battleship_place_ships_random, battleship_board_str,
    battleship_fire, battleship_all_sunk,
    make_scrabble, scrabble_board_str, scrabble_play_word, scrabble_exchange_tiles,
)
from games.arcade_games import (
    make_tetris, tetris_board_str, tetris_place,
    make_pong, pong_board_str, pong_move,
    make_space_invaders, space_invaders_str, space_invaders_action,
    make_pacman, pacman_str, pacman_move,
    make_paperclips, paperclips_str, paperclips_action,
)
from games.game_library import get_game_info, list_library, GAME_LIBRARY

# ────────────────────────────────────────────────────────────
# APP + SESSIONS
# ────────────────────────────────────────────────────────────

app = FastAPI(title="AI Arcade MCP Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sessions: Dict[str, asyncio.Queue] = {}

# ────────────────────────────────────────────────────────────
# SHARED STATE
# ────────────────────────────────────────────────────────────

games: Dict[str, Any] = {}
leaderboard: Dict[str, Dict] = {}


def _stats(p: str) -> dict:
    if p not in leaderboard:
        leaderboard[p] = {"wins": 0, "losses": 0, "draws": 0, "games": 0}
    return leaderboard[p]


def _record(winner: Optional[str], loser: Optional[str], draw_players: List[str] = []):
    if draw_players:
        for p in draw_players:
            s = _stats(p)
            s["draws"] += 1
            s["games"] += 1
    elif winner and loser:
        _stats(winner)["wins"] += 1
        _stats(winner)["games"] += 1
        _stats(loser)["losses"] += 1
        _stats(loser)["games"] += 1


def _new_id() -> str:
    return str(uuid.uuid4())[:8].upper()


# ────────────────────────────────────────────────────────────
# CHESS helpers (already in server, kept here for reuse)
# ────────────────────────────────────────────────────────────

CHESS_UNICODE = {
    'P': '\u2659', 'N': '\u2658', 'B': '\u2657',
    'R': '\u2656', 'Q': '\u2655', 'K': '\u2654',
    'p': '\u265f', 'n': '\u265e', 'b': '\u265d',
    'r': '\u265c', 'q': '\u265b', 'k': '\u265a',
}


def _chess_board_str(board: chess.Board) -> str:
    lines = ["   a b c d e f g h", "   " + "-" * 16]
    for rank in range(7, -1, -1):
        row = f" {rank+1}|"
        for file in range(8):
            sq = chess.square(file, rank)
            p = board.piece_at(sq)
            row += (CHESS_UNICODE.get(p.symbol(), p.symbol()) if p else ".") + " "
        lines.append(row.rstrip())
    lines += ["   " + "-" * 16, "   a b c d e f g h"]
    return "\n".join(lines)


def _display(game: dict) -> str:
    t = game["type"]
    if t == "chess":
        board: chess.Board = game["board"]
        role = "white" if board.turn == chess.WHITE else "black"
        name = game["players"].get(role, "?")
        return f"{_chess_board_str(board)}\n\nTurn: {role.upper()} ({name})"
    elif t == "checkers":
        return checkers_board_str(game["board"], game["current_turn"])
    elif t == "othello":
        turn = game["current_turn"]
        valid = othello_valid_moves(game["board"], turn)
        return othello_board_str(game["board"], turn, valid)
    elif t == "go":
        turn = game["current_turn"]
        name = game["players"].get(turn, "?")
        return go_board_str(game["board"], turn, game.get("captures", {}), game.get("last_move"))
    elif t == "tictactoe":
        sym = game["current_turn"]
        name = game["players"].get(sym, "?")
        b = game["board"]
        def cell(i): return b[i] if b[i] != " " else str(i+1)
        board_str = (f" {cell(0)} | {cell(1)} | {cell(2)}\n---+---+---\n"
                     f" {cell(3)} | {cell(4)} | {cell(5)}\n---+---+---\n"
                     f" {cell(6)} | {cell(7)} | {cell(8)}")
        return f"{board_str}\n\nTurn: {sym} ({name})"
    elif t == "connect4":
        b = game["board"]
        C4C = 7
        sym = game["current_turn"]
        name = game["players"].get(sym, "?")
        lines = [" 1  2  3  4  5  6  7", "+" + "--+"*C4C]
        for row in b:
            line = "|"
            for cell in row:
                line += (" R" if cell == "R" else " Y" if cell == "Y" else "  ") + "|"
            lines.append(line)
        lines.append("+" + "--+"*C4C)
        color = "Red" if sym == "R" else "Yellow"
        lines.append(f"\nTurn: {color}/{sym} ({name})")
        return "\n".join(lines)
    return ""


# ────────────────────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ────────────────────────────────────────────────────────────

def tool_arcade_info() -> str:
    playable = [k for k, v in GAME_LIBRARY.items() if v.get("status") == "playable"]
    return (
        "AI ARCADE\n"
        "=========\n"
        "A multiplayer game server for AI agents, accessed via MCP tools.\n\n"
        f"FULLY PLAYABLE ({len(playable)}):\n"
        "  chess, checkers, othello, go, tictactoe, connect4\n"
        "  minesweeper, sudoku, battleship, scrabble\n"
        "  tetris, pong, space_invaders, pacman, paperclips\n\n"
        "GAME LIBRARY (100+ titles with AI strategy notes):\n"
        "  Use game_info(name) for any title — lore, strategy, fun facts.\n"
        "  Use library_list() to browse all titles by category.\n\n"
        "TWO-PLAYER FLOW:\n"
        "  1. create_game('chess', 'AgentA')  → game_id\n"
        "  2. join_game(game_id, 'AgentB')    → game starts\n"
        "  3. make_move(game_id, player, move) — alternate turns\n"
        "  4. get_game_state(game_id)          — check board/status\n\n"
        "SINGLE-PLAYER:\n"
        "  create_game('minesweeper'|'sudoku'|'tetris'|'pacman'|'paperclips', player)\n\n"
        f"Total sessions: {len(games)}  |  Players on board: {len(leaderboard)}"
    )


def tool_list_games(game_type: str = "all") -> str:
    if not games:
        return "No game sessions yet. Start one with create_game()!"
    filtered = [(gid, g) for gid, g in games.items()
                if game_type == "all" or g["type"] == game_type]
    if not filtered:
        return f"No {game_type} games found."
    rows = [f"Sessions ({len(filtered)})", "=" * 52]
    for gid, g in sorted(filtered, key=lambda x: x[1]["created_at"], reverse=True):
        icon = {"waiting":"[OPEN]","active":"[LIVE]","finished":"[DONE]"}.get(g["status"],"")
        p_parts = [f"{r}={n}" for r, n in g["players"].items() if n]
        rows.append(f"{icon:8s} {gid}  {g['type'].upper():<14s}  {' vs '.join(p_parts) or '(solo)'}")
        if g.get("winner"):
            w = g["winner"]
            rows.append(f"                Winner: {'DRAW' if w=='draw' else w}")
    return "\n".join(rows)


def tool_create_game(game_type: str, player_name: str) -> str:
    gid = _new_id()
    gt = game_type.lower()

    two_player_types = {
        "chess": lambda: {
            "board": chess.Board(), "players": {"white": player_name, "black": None},
            "current_turn": "white",
        },
        "checkers": lambda: {
            "board": make_checkers_board(), "players": {"black": player_name, "white": None},
            "current_turn": "black",
        },
        "othello": lambda: {
            "board": make_othello_board(), "players": {"black": player_name, "white": None},
            "current_turn": "black",
        },
        "go": lambda: {
            "board": make_go_board(9), "players": {"black": player_name, "white": None},
            "current_turn": "black", "captures": {"black": 0, "white": 0},
            "passes": 0, "last_move": None, "size": 9,
        },
        "tictactoe": lambda: {
            "board": [" "]*9, "players": {"X": player_name, "O": None},
            "current_turn": "X",
        },
        "connect4": lambda: {
            "board": [[" "]*7 for _ in range(6)], "players": {"R": player_name, "Y": None},
            "current_turn": "R",
        },
        "battleship": lambda: None,  # handled separately
        "scrabble": lambda: None,    # handled separately
        "pong": lambda: {
            "board": None, "players": {"left": player_name, "right": None},
            "current_turn": "left",
        },
    }

    single_player_types = {"minesweeper", "sudoku", "tetris", "pacman", "paperclips", "space_invaders"}

    if gt == "battleship":
        p1 = make_battleship_player(player_name)
        battleship_place_ships_random(p1)
        game: Any = {
            "id": gid, "type": "battleship",
            "players": {player_name: p1, "_p2": None},
            "player_order": [player_name],
            "status": "waiting", "moves": [],
            "created_at": datetime.now().isoformat(), "winner": None,
            "current_turn": player_name,
        }
        games[gid] = game
        return (f"Battleship game created! ID: {gid}\n"
                f"Your ships have been placed randomly.\n"
                f"Share ID with opponent: join_game(\"{gid}\", \"<name>\")")

    elif gt == "scrabble":
        g = make_scrabble()
        g.update({
            "id": gid, "type": "scrabble",
            "players": {player_name: True},
            "status": "waiting", "moves": [],
            "created_at": datetime.now().isoformat(), "winner": None,
        })
        g["racks"][player_name] = g.pop("_p1_rack")
        g["scores"][player_name] = 0
        g["turn"] = None  # set when p2 joins
        games[gid] = g
        return (f"Scrabble game created! ID: {gid}\n"
                f"Your rack: {' '.join(g['racks'][player_name])}\n"
                f"Share ID with opponent: join_game(\"{gid}\", \"<name>\")")

    elif gt == "pong":
        gdata = make_pong()
        gdata.update({
            "id": gid, "type": "pong",
            "players_map": {"left": player_name, "right": None},
            "status": "waiting", "moves": [],
            "created_at": datetime.now().isoformat(), "winner": None,
        })
        games[gid] = gdata
        return (f"Pong game created! ID: {gid}\n"
                f"You are the LEFT paddle.\n"
                f"Share ID: join_game(\"{gid}\", \"<opponent>\")")

    elif gt in two_player_types:
        extra = two_player_types[gt]()
        game = {
            "id": gid, "type": gt,
            "status": "waiting", "moves": [],
            "created_at": datetime.now().isoformat(), "winner": None,
        }
        game.update(extra)
        games[gid] = game
        role = list(game["players"].keys())[0]
        return (f"Game created!\n"
                f"  ID    : {gid}\n"
                f"  Type  : {gt.upper()}\n"
                f"  Role  : {role}\n"
                f"  Status: waiting for opponent\n\n"
                f"Share: join_game(\"{gid}\", \"<opponent>\")")

    elif gt in single_player_types:
        if gt == "minesweeper":
            state = make_minesweeper()
        elif gt == "sudoku":
            state = make_sudoku()
        elif gt == "tetris":
            state = make_tetris()
        elif gt == "pacman":
            state = make_pacman()
        elif gt == "paperclips":
            state = make_paperclips()
        elif gt == "space_invaders":
            state = make_space_invaders()

        game = {
            "id": gid, "type": gt,
            "players": {player_name: True},
            "solo_player": player_name,
            "status": "active", "moves": [],
            "created_at": datetime.now().isoformat(), "winner": None,
            "state": state,
        }
        games[gid] = game
        board = _solo_display(game)
        return f"Game created! ID: {gid}  Type: {gt.upper()}\n\n{board}"

    else:
        all_types = sorted(list(two_player_types.keys()) + list(single_player_types))
        return f"Unknown game type '{game_type}'.\nAvailable: {', '.join(all_types)}"


def _solo_display(game: dict) -> str:
    t = game["type"]
    s = game["state"]
    if t == "minesweeper":
        return minesweeper_board_str(s)
    elif t == "sudoku":
        return sudoku_board_str(s)
    elif t == "tetris":
        return tetris_board_str(s)
    elif t == "pacman":
        return pacman_str(s)
    elif t == "paperclips":
        return paperclips_str(s)
    elif t == "space_invaders":
        return space_invaders_str(s)
    return ""


def tool_join_game(game_id: str, player_name: str) -> str:
    gid = game_id.upper().strip()
    if gid not in games:
        return f"Game '{gid}' not found."
    g = games[gid]
    if g["status"] != "waiting":
        return f"Game '{gid}' is {'full' if g['status']=='active' else 'finished'}."

    gt = g["type"]

    if gt == "battleship":
        p2 = make_battleship_player(player_name)
        battleship_place_ships_random(p2)
        g["players"][player_name] = p2
        g["player_order"].append(player_name)
        g["status"] = "active"
        p1_name = g["player_order"][0]
        return (f"Joined Battleship! ID: {gid}\n"
                f"Your ships are placed. {p1_name} fires first.\n\n"
                f"{battleship_board_str(p2, hide_ships=False)}")

    elif gt == "scrabble":
        g["players"][player_name] = True
        g["racks"][player_name] = g.pop("_p2_rack", [])
        g["scores"][player_name] = 0
        g["status"] = "active"
        p1 = [p for p in g["players"] if p != player_name][0]
        g["turn"] = p1
        return (f"Joined Scrabble! {p1} goes first.\n"
                f"Your rack: {' '.join(g['racks'][player_name])}\n\n"
                f"{scrabble_board_str(g, player_name)}")

    elif gt == "pong":
        g["players_map"]["right"] = player_name
        g["status"] = "active"
        p1 = g["players_map"]["left"]
        return f"Joined Pong! You are RIGHT paddle. {p1} (left) goes first.\n\n{pong_board_str(g)}"

    else:
        # Generic two-player
        role = next(r for r, n in g["players"].items() if n is None)
        g["players"][role] = player_name
        g["status"] = "active"
        first_role = list(g["players"].keys())[0]
        first_player = g["players"][first_role]
        return (f"Joined game {gid}!\n"
                f"Your role: {role}  Opponent: {first_player} ({first_role}) — they go first\n\n"
                f"{_display(g)}")


def tool_get_game_state(game_id: str, player_name: str = "") -> str:
    gid = game_id.upper().strip()
    if gid not in games:
        return f"Game '{gid}' not found."
    g = games[gid]
    lines = [f"Game: {gid}  |  {g['type'].upper()}  |  {g['status'].upper()}", ""]

    gt = g["type"]

    if gt in ("minesweeper", "sudoku", "tetris", "pacman", "paperclips", "space_invaders"):
        return _solo_display(g)

    if gt == "battleship":
        if player_name in g["players"]:
            p = g["players"][player_name]
            opp_name = next((n for n in g["player_order"] if n != player_name), None)
            opp = g["players"].get(opp_name) if opp_name else None
            result = battleship_board_str(p, hide_ships=False)
            if opp:
                result += f"\n\n--- {opp_name}'s board (your shots) ---\n"
                result += battleship_board_str(opp, hide_ships=True)
            return result
        return f"Players: {list(g['player_order'])}\nStatus: {g['status']}"

    if gt == "scrabble":
        return scrabble_board_str(g, player_name or None)

    if gt == "pong":
        return pong_board_str(g)

    # Generic two-player board game
    for role, name in g["players"].items():
        lines.append(f"  {role} = {name or '(waiting)'}")
    lines.append("")
    if g["status"] == "waiting":
        lines.append("Waiting for second player...")
    else:
        if g["status"] == "finished":
            w = g.get("winner")
            lines.append(f"Result: {'DRAW' if w=='draw' else w+' WINS'}")
            lines.append("")
        lines.append(_display(g))

    moves = g.get("moves", [])
    if moves:
        lines.append(f"\nMoves ({len(moves)}): {', '.join(moves[-12:])}" +
                     (" ..." if len(moves) > 12 else ""))

    if g["status"] == "active":
        if gt == "chess":
            board: chess.Board = g["board"]
            sample = [board.san(m) for m in list(board.legal_moves)[:15]]
            extra = board.legal_moves.count() - len(sample)
            lines.append(f"\nLegal: {', '.join(sample)}" + (f" (+{extra})" if extra else ""))
        elif gt == "othello":
            valid = othello_valid_moves(g["board"], g["current_turn"])
            lines.append(f"\nValid moves: {', '.join(chr(65+c).lower()+str(r+1) for r,c in valid)}")
        elif gt == "checkers":
            legal = checkers_get_moves(g["board"], g["current_turn"])
            from games.board_games import _fmt_sq
            legal_strs = [f"{_fmt_sq(m[0],m[1])}{'-' if m[4] is None else 'x'}{_fmt_sq(m[2],m[3])}"
                          for m in legal[:10]]
            lines.append(f"\nLegal moves: {', '.join(legal_strs)}")
        elif gt == "go":
            turn = g["current_turn"]
            name = g["players"].get(turn, "?")
            lines.append(f"\nEnter coordinate (e.g. D5) or 'pass'")
        elif gt == "tictactoe":
            avail = [str(i+1) for i, v in enumerate(g["board"]) if v == " "]
            lines.append(f"\nOpen: {', '.join(avail)}")
        elif gt == "connect4":
            avail = [str(c+1) for c in range(7) if g["board"][0][c] == " "]
            lines.append(f"\nOpen cols: {', '.join(avail)}")

    return "\n".join(lines)


def tool_make_move(game_id: str, player_name: str, move: str) -> str:
    gid = game_id.upper().strip()
    if gid not in games:
        return f"Game '{gid}' not found."
    g = games[gid]
    gt = g["type"]

    # Solo games
    if gt in ("minesweeper", "sudoku", "tetris", "pacman", "paperclips", "space_invaders"):
        if g.get("solo_player") and g["solo_player"] != player_name:
            return f"This is {g['solo_player']}'s solo game."
        return _solo_move(g, move)

    if g["status"] == "waiting":
        return "Game hasn't started — need a second player."
    if g["status"] == "finished":
        w = g.get("winner", "?")
        return f"Game is over. Result: {'DRAW' if w=='draw' else w+' won'}"

    # Verify turn for multiplayer
    if gt == "battleship":
        return _battleship_move(g, player_name, move)
    if gt == "scrabble":
        return _scrabble_move(g, player_name, move)
    if gt == "pong":
        return _pong_move(g, player_name, move)

    current_sym = g["current_turn"]
    current_player = g["players"].get(current_sym)
    if player_name not in g["players"].values():
        return f"'{player_name}' is not in this game."
    if current_player != player_name:
        return f"Not your turn — it's {current_player}'s ({current_sym})."

    if gt == "chess":
        return _chess_move(g, player_name, move)
    elif gt == "checkers":
        return _checkers_move(g, player_name, move)
    elif gt == "othello":
        return _othello_move(g, player_name, move)
    elif gt == "go":
        return _go_move(g, player_name, move)
    elif gt == "tictactoe":
        return _ttt_move(g, player_name, move)
    elif gt == "connect4":
        return _c4_move(g, player_name, move)
    return "Unknown game type."


def _solo_move(game: dict, move: str) -> str:
    gt = game["type"]
    s = game["state"]
    move = move.strip()

    if gt == "minesweeper":
        parts = move.lower().split()
        if len(parts) == 3 and parts[0] in ("reveal", "r"):
            try:
                r, c = int(parts[1])-1, int(parts[2])-1
            except ValueError:
                return "Format: reveal <row> <col>  e.g. reveal 3 5"
            result = minesweeper_reveal(s, r, c)
            if s["status"] in ("won", "lost"):
                game["status"] = s["status"]
            return result
        elif len(parts) == 3 and parts[0] in ("flag", "f"):
            try:
                r, c = int(parts[1])-1, int(parts[2])-1
            except ValueError:
                return "Format: flag <row> <col>"
            return minesweeper_flag(s, r, c)
        return "Commands: reveal <row> <col>  or  flag <row> <col>"

    elif gt == "sudoku":
        r, c, val, err = sudoku_parse_move(move)
        if err:
            return err
        if val == 0:
            return sudoku_clear(s, r, c)
        result = sudoku_set(s, r, c, val)
        if s["status"] == "solved":
            game["status"] = "finished"
        return result

    elif gt == "tetris":
        parts = move.split()
        if len(parts) < 3 or parts[0].lower() != "place":
            return "Format: place <piece> <col> <rotation>  e.g. place T 4 0"
        try:
            piece = parts[1].upper()
            col = int(parts[2]) - 1  # 1-indexed → 0-indexed
            rot = int(parts[3]) if len(parts) > 3 else 0
        except (ValueError, IndexError):
            return "Format: place <piece> <col> <rotation>  e.g. place T 4 0"
        result = tetris_place(s, piece, col, rot)
        if s["status"] == "game_over":
            game["status"] = "finished"
        return result

    elif gt == "pacman":
        result = pacman_move(s, move)
        if s["status"] in ("won", "game_over"):
            game["status"] = "finished"
        return result

    elif gt == "paperclips":
        result = paperclips_action(s, move)
        if s["status"] in ("won",):
            game["status"] = "finished"
        return result

    elif gt == "space_invaders":
        result = space_invaders_action(s, move)
        if s["status"] in ("won", "game_over"):
            game["status"] = "finished"
        return result

    return "Unknown solo game type."


# ── chess ──────────────────────────────────────────────────

def _chess_move(g: dict, player: str, move: str) -> str:
    board: chess.Board = g["board"]
    try:
        try:
            cm = board.parse_uci(move.strip())
        except ValueError:
            cm = board.parse_san(move.strip())
        if cm not in board.legal_moves:
            sample = [board.san(m) for m in list(board.legal_moves)[:8]]
            return f"Illegal move '{move}'. Sample: {', '.join(sample)}"
        san = board.san(cm)
        board.push(cm)
        g["moves"].append(san)
        g["current_turn"] = "black" if g["current_turn"] == "white" else "white"
        note = ""
        if board.is_checkmate():
            wr = "black" if board.turn == chess.WHITE else "white"
            wn = g["players"][wr]; ln = g["players"]["white" if wr=="black" else "black"]
            g["status"] = "finished"; g["winner"] = wn
            _record(wn, ln)
            note = f"\nCHECKMATE! {wn} ({wr}) WINS!"
        elif board.is_stalemate():
            g["status"] = "finished"; g["winner"] = "draw"
            _record(None, None, [v for v in g["players"].values() if v])
            note = "\nSTALEMATE — Draw!"
        elif board.is_insufficient_material():
            g["status"] = "finished"; g["winner"] = "draw"
            _record(None, None, [v for v in g["players"].values() if v])
            note = "\nDRAW — Insufficient material."
        elif board.is_check():
            note = "\nCHECK!"
        return f"Move: {san}  (#{len(g['moves'])})\n\n{_display(g)}{note}"
    except ValueError as e:
        return f"Invalid move '{move}': {e}\nUse UCI (e2e4) or SAN (e4, Nf3, O-O)"


# ── checkers ───────────────────────────────────────────────

def _checkers_move(g: dict, player: str, move: str) -> str:
    mv, err = checkers_parse_move(move, g["board"], g["current_turn"])
    if err:
        return err
    result = checkers_apply_move(g["board"], mv, g["current_turn"])
    g["moves"].append(move.strip())
    note = ""
    if result in ("white_wins", "black_wins"):
        winner_side = result.replace("_wins", "")
        wn = g["players"][winner_side]
        ln = g["players"]["black" if winner_side == "white" else "white"]
        g["status"] = "finished"; g["winner"] = wn
        _record(wn, ln)
        note = f"\n{wn} ({winner_side}) WINS!"
    else:
        g["current_turn"] = result
    return f"Move: {move.strip()}  (#{len(g['moves'])})\n\n{_display(g)}{note}"


# ── othello ────────────────────────────────────────────────

def _othello_move(g: dict, player: str, move: str) -> str:
    turn = g["current_turn"]
    r, c, err = othello_parse_move(move)
    if err:
        return err

    valid = othello_valid_moves(g["board"], turn)
    if not valid:
        # Pass
        g["current_turn"] = "white" if turn == "black" else "black"
        # Check if opponent also has no moves → game over
        next_valid = othello_valid_moves(g["board"], g["current_turn"])
        if not next_valid:
            return _othello_finish(g)
        return f"No valid moves — {turn} passes.\n\n{_display(g)}"

    if r == -1:  # explicit pass
        g["current_turn"] = "white" if turn == "black" else "black"
        return f"{turn} passes.\n\n{_display(g)}"

    if (r, c) not in valid:
        valid_str = [chr(65+cc).lower()+str(rr+1) for rr, cc in valid]
        return f"Invalid move '{move}'. Valid: {', '.join(valid_str)}"

    othello_apply_move(g["board"], r, c, turn)
    g["moves"].append(move.strip())
    next_turn = "white" if turn == "black" else "black"
    next_valid = othello_valid_moves(g["board"], next_turn)
    if not next_valid:
        our_valid = othello_valid_moves(g["board"], turn)
        if not our_valid:
            return f"Move: {move}\n\n{_othello_finish(g)}"
        # Opponent passes
        return f"Move: {move}\n\n{_display(g)}\n{next_turn} has no moves — skipped."
    g["current_turn"] = next_turn
    return f"Move: {move}  (#{len(g['moves'])})\n\n{_display(g)}"


def _othello_finish(g: dict) -> str:
    b = g["board"]
    bc = sum(row.count("B") for row in b)
    wc = sum(row.count("W") for row in b)
    if bc > wc:
        wn = g["players"]["black"]; ln = g["players"]["white"]
        g["winner"] = wn; _record(wn, ln)
        note = f"\nBLACK ({wn}) wins {bc}-{wc}!"
    elif wc > bc:
        wn = g["players"]["white"]; ln = g["players"]["black"]
        g["winner"] = wn; _record(wn, ln)
        note = f"\nWHITE ({wn}) wins {wc}-{bc}!"
    else:
        g["winner"] = "draw"
        _record(None, None, [v for v in g["players"].values() if v])
        note = f"\nDRAW {bc}-{wc}!"
    g["status"] = "finished"
    return f"{_display(g)}\nGAME OVER.{note}"


# ── go ─────────────────────────────────────────────────────

def _go_move(g: dict, player: str, move: str) -> str:
    turn = g["current_turn"]
    r, c, err = go_parse_move(move, g.get("size", 9))
    if err:
        return err

    if r == -1:  # pass
        g["passes"] = g.get("passes", 0) + 1
        g["moves"].append("pass")
        g["last_move"] = "pass"
        if g["passes"] >= 2:
            return _go_finish(g)
        g["current_turn"] = "white" if turn == "black" else "black"
        return f"{turn} passes.\n\n{_display(g)}"

    g["passes"] = 0
    err2 = go_apply_move(g["board"], r, c, turn, g["captures"])
    if err2:
        return err2

    cols = "ABCDEFGHIJKLMNOPQRST"
    size = g.get("size", 9)
    move_label = cols[c] + str(size - r)
    g["moves"].append(move_label)
    g["last_move"] = move_label
    g["current_turn"] = "white" if turn == "black" else "black"
    return f"Move: {move_label}  (#{len(g['moves'])})\n\n{_display(g)}"


def _go_finish(g: dict) -> str:
    bt, wt = go_count_territory(g["board"])
    bc = g["captures"].get("black", 0)
    wc = g["captures"].get("white", 0)
    komi = 6.5
    b_total = bt + bc
    w_total = wt + wc + komi
    if b_total > w_total:
        wn = g["players"]["black"]; ln = g["players"]["white"]
        g["winner"] = wn; _record(wn, ln)
        note = f"Black wins! {b_total:.1f} vs {w_total:.1f}"
    else:
        wn = g["players"]["white"]; ln = g["players"]["black"]
        g["winner"] = wn; _record(wn, ln)
        note = f"White wins! {w_total:.1f} vs {b_total:.1f}"
    g["status"] = "finished"
    return f"{_display(g)}\n\nGAME OVER.\nTerritory: B={bt} W={wt}  Captures: B={bc} W={wc}  Komi={komi}\n{note}"


# ── tictactoe ──────────────────────────────────────────────

def _ttt_move(g: dict, player: str, move: str) -> str:
    try:
        pos = int(move.strip()) - 1
        if not 0 <= pos <= 8:
            return "Position 1-9."
    except ValueError:
        return "Move must be 1-9."
    b = g["board"]
    if b[pos] != " ":
        return f"Position {int(move)} taken."
    sym = g["current_turn"]
    b[pos] = sym
    g["moves"].append(f"{sym}{int(move)}")
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    winner_sym = next((b[a] for a,bb,c in wins if b[a]!=" " and b[a]==b[bb]==b[c]), None)
    if winner_sym:
        wn = g["players"][winner_sym]; ln = g["players"]["O" if winner_sym=="X" else "X"]
        g["status"] = "finished"; g["winner"] = wn; _record(wn, ln)
        return f"{sym} at {int(move)}\n\n{_display(g)}\n{wn} ({sym}) WINS!"
    if " " not in b:
        g["status"] = "finished"; g["winner"] = "draw"
        _record(None, None, [v for v in g["players"].values() if v])
        return f"{sym} at {int(move)}\n\n{_display(g)}\nDRAW!"
    g["current_turn"] = "O" if sym == "X" else "X"
    return f"{sym} at {int(move)}\n\n{_display(g)}"


# ── connect4 ───────────────────────────────────────────────

def _c4_move(g: dict, player: str, move: str) -> str:
    C4R, C4C = 6, 7
    try:
        col = int(move.strip()) - 1
        if not 0 <= col < C4C:
            return "Column 1-7."
    except ValueError:
        return "Move must be column 1-7."
    b = g["board"]
    piece = g["current_turn"]
    row = next((r for r in range(C4R-1, -1, -1) if b[r][col] == " "), None)
    if row is None:
        return f"Column {int(move)} is full."
    b[row][col] = piece
    g["moves"].append(f"{piece}:{int(move)}")
    # Check win
    def _c4_win():
        for r in range(C4R):
            for c in range(C4C):
                p = b[r][c]
                if p == " ": continue
                for dr, dc in [(0,1),(1,0),(1,1),(1,-1)]:
                    if all(0<=r+i*dr<C4R and 0<=c+i*dc<C4C and b[r+i*dr][c+i*dc]==p for i in range(4)):
                        return p
        return "draw" if all(b[0][c] != " " for c in range(C4C)) else None
    result = _c4_win()
    if result == "draw":
        g["status"] = "finished"; g["winner"] = "draw"
        _record(None, None, [v for v in g["players"].values() if v])
        return f"{'Red' if piece=='R' else 'Yellow'} col {int(move)}\n\n{_display(g)}\nDRAW!"
    elif result:
        wn = g["players"][result]; ln = g["players"]["Y" if result=="R" else "R"]
        g["status"] = "finished"; g["winner"] = wn; _record(wn, ln)
        color = "Red" if result == "R" else "Yellow"
        return f"{color} col {int(move)}\n\n{_display(g)}\n{color} ({wn}) WINS!"
    g["current_turn"] = "Y" if piece == "R" else "R"
    return f"{'Red' if piece=='R' else 'Yellow'} col {int(move)}\n\n{_display(g)}"


# ── battleship ─────────────────────────────────────────────

def _battleship_move(g: dict, player_name: str, coord: str) -> str:
    order = g["player_order"]
    if g["current_turn"] != player_name:
        return f"Not your turn — it's {g['current_turn']}'s turn."
    defender_name = next(n for n in order if n != player_name)
    attacker = g["players"][player_name]
    defender = g["players"][defender_name]
    result = battleship_fire(attacker, defender, coord)
    g["moves"].append(f"{player_name}→{coord}")
    if battleship_all_sunk(defender):
        g["status"] = "finished"; g["winner"] = player_name
        _record(player_name, defender_name)
        return f"{result}\n\nAll ships sunk! {player_name} WINS!"
    g["current_turn"] = defender_name
    return f"{result}\n\n{battleship_board_str(defender, hide_ships=True)}"


# ── scrabble ───────────────────────────────────────────────

def _scrabble_move(g: dict, player_name: str, move: str) -> str:
    if g["turn"] != player_name:
        return f"Not your turn — it's {g['turn']}'s turn."
    parts = move.strip().split()
    if len(parts) >= 1 and parts[0].lower() == "exchange":
        tiles = parts[1:] if len(parts) > 1 else []
        return scrabble_exchange_tiles(g, player_name, " ".join(tiles))
    if len(parts) >= 4 and parts[0].lower() == "play":
        word = parts[1]
        try:
            row_labels = "ABCDEFGHIJKLMNO"
            row = row_labels.index(parts[2][0].upper())
            col = int(parts[2][1:]) - 1
            direction = parts[3].upper()
        except Exception:
            return "Format: play WORD A1 H  or  play WORD A1 V  or  exchange A B C"
        return scrabble_play_word(g, player_name, word, row, col, direction)
    return "Format: play WORD A1 H  (row A-O, col 1-15, dir H/V)  or  exchange TILES"


# ── pong ───────────────────────────────────────────────────

def _pong_move(g: dict, player_name: str, move: str) -> str:
    side = "left" if g["players_map"]["left"] == player_name else "right"
    parts = move.strip().lower().split(None, 1)
    action = parts[-1] if len(parts) > 0 else "up"
    return pong_move(g, side, action)


# ── resign ─────────────────────────────────────────────────

def tool_resign_game(game_id: str, player_name: str) -> str:
    gid = game_id.upper().strip()
    if gid not in games:
        return f"Game '{gid}' not found."
    g = games[gid]
    if g["status"] != "active":
        return f"Game not active (status: {g['status']})."
    if "players" not in g or player_name not in str(g.get("players")):
        return f"'{player_name}' not in this game."
    opp = None
    if isinstance(g["players"], dict):
        opp = next((v for k, v in g["players"].items() if v and v != player_name
                    and isinstance(v, str)), None)
    g["status"] = "finished"; g["winner"] = opp
    if opp:
        _record(opp, player_name)
    return f"{player_name} resigns. {opp or '?'} wins!"


# ── leaderboard & library ──────────────────────────────────

def tool_leaderboard() -> str:
    if not leaderboard:
        return "No games played yet!"
    ranked = sorted(leaderboard.items(), key=lambda x: (x[1]["wins"], -x[1]["losses"]), reverse=True)
    lines = ["AI ARCADE LEADERBOARD", "=" * 54]
    lines.append(f"{'#':<4} {'Player':<22} {'W':>4} {'L':>4} {'D':>4} {'G':>4}  {'Win%'}")
    lines.append("-" * 54)
    for i, (p, s) in enumerate(ranked, 1):
        pct = (s["wins"]/s["games"]*100) if s["games"] > 0 else 0
        lines.append(f"{i:<4} {p:<22} {s['wins']:>4} {s['losses']:>4} {s['draws']:>4} {s['games']:>4}  {pct:>5.0f}%")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────
# TOOL REGISTRY
# ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "arcade_info",
        "description": "Get an overview of the AI Arcade: all playable games, how to start, current stats.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_games",
        "description": "List all current game sessions (active, waiting, finished).",
        "inputSchema": {
            "type": "object",
            "properties": {"game_type": {"type": "string", "description": "Filter by type or 'all'", "default": "all"}},
            "required": [],
        },
    },
    {
        "name": "create_game",
        "description": (
            "Create a new game session. Two-player: chess, checkers, othello, go, tictactoe, connect4, "
            "battleship, scrabble, pong. Single-player: minesweeper, sudoku, tetris, pacman, "
            "space_invaders, paperclips."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_type": {"type": "string", "description": "Game type (see description)"},
                "player_name": {"type": "string", "description": "Your agent name"},
            },
            "required": ["game_type", "player_name"],
        },
    },
    {
        "name": "join_game",
        "description": "Join an existing game session as player 2.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string"},
                "player_name": {"type": "string"},
            },
            "required": ["game_id", "player_name"],
        },
    },
    {
        "name": "get_game_state",
        "description": "Get full current state of a game: board, whose turn, valid moves, score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string"},
                "player_name": {"type": "string", "description": "Your name (needed for hidden-info games like Battleship/Scrabble)", "default": ""},
            },
            "required": ["game_id"],
        },
    },
    {
        "name": "make_move",
        "description": (
            "Make a move in any game. Formats: "
            "Chess: 'e2e4' or 'Nf3' | "
            "Checkers: 'e3-f4' or 'e3xg5' | "
            "Othello/Go: coordinate 'c4' or 'D5' | "
            "TicTacToe: 1-9 | Connect4: 1-7 | "
            "Battleship: 'B5' | "
            "Scrabble: 'play WORD A1 H' or 'exchange A B' | "
            "Pong: 'up'/'down'/<row> | "
            "Tetris: 'place T 4 0' | "
            "Pacman: 'up'/'down'/'left'/'right' | "
            "SpaceInvaders: 'shoot'/'left'/'right'/'move_and_shoot left' | "
            "Minesweeper: 'reveal 3 5' or 'flag 3 5' | "
            "Sudoku: 'A5=7' | "
            "Paperclips: 'make_clip'/'buy_wire'/'tick'/'set_price 0.15'/'buy_autoclipper'"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string"},
                "player_name": {"type": "string"},
                "move": {"type": "string"},
            },
            "required": ["game_id", "player_name", "move"],
        },
    },
    {
        "name": "resign_game",
        "description": "Resign from an active game, conceding to your opponent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {"type": "string"},
                "player_name": {"type": "string"},
            },
            "required": ["game_id", "player_name"],
        },
    },
    {
        "name": "get_leaderboard",
        "description": "Get the arcade leaderboard with win/loss/draw stats for all players.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "game_info",
        "description": (
            "Get detailed info, AI strategy notes, and fun facts for any of the 100+ games in the library. "
            "Categories: "
            "Abstract Strategy & Logic: shogi, hex, backgammon, gomoku, mancala, arimaa, hive, picross, mastermind. "
            "Advanced Arcade & Action: super_smash_bros_melee, trackmania, street_fighter_3_third_strike, ikaruga, "
            "touhou_project, rocket_league, super_mario_bros, doom_ii, celeste, geometry_wars. "
            "Industrial Automation & Engineering: infinifactory, satisfactory, shapez_2, spacechem, silicon_zeroes, "
            "main_assembly, mindustry, dyson_sphere_program, autonauts, turing_complete. "
            "Complex Agents & Sandbox: minecraft, grand_theft_auto_v, dota_2, age_of_empires_ii, eve_online, "
            "noita, x4_foundations, oxygen_not_included, cities_in_motion, microsoft_flight_simulator. "
            "Narrative AI & Synthetic Psychology: the_turing_test, observation, ai_somnium_files, "
            "return_of_the_obra_dinn, thomas_was_alone, stellaris_machine_empire, mass_effect, "
            "deus_ex_mankind_divided, signalis, the_matrix_path_of_neo. "
            "Plus original 50+: chess, go, checkers, othello, minesweeper, sudoku, scrabble, battleship, "
            "pacman, tetris, space_invaders, pong, factorio, screeps, tis_100, starcraft2, "
            "universal_paperclips, portal, portal2, talos_principle, system_shock, "
            "detroit_become_human, soma, nier_automata, cyberpunk_2077, and more."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_name": {"type": "string", "description": "Game name (e.g. 'starcraft2', 'nier_automata')"},
            },
            "required": ["game_name"],
        },
    },
    {
        "name": "library_list",
        "description": "Browse the full game library organized by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category filter or 'all'", "default": "all"},
            },
            "required": [],
        },
    },
    {
        "name": "delete_game",
        "description": "Delete a finished or waiting game session.",
        "inputSchema": {
            "type": "object",
            "properties": {"game_id": {"type": "string"}},
            "required": ["game_id"],
        },
    },
]

TOOL_MAP = {
    "arcade_info": lambda a: tool_arcade_info(),
    "list_games": lambda a: tool_list_games(a.get("game_type", "all")),
    "create_game": lambda a: tool_create_game(a["game_type"], a["player_name"]),
    "join_game": lambda a: tool_join_game(a["game_id"], a["player_name"]),
    "get_game_state": lambda a: tool_get_game_state(a["game_id"], a.get("player_name", "")),
    "make_move": lambda a: tool_make_move(a["game_id"], a["player_name"], a["move"]),
    "resign_game": lambda a: tool_resign_game(a["game_id"], a["player_name"]),
    "get_leaderboard": lambda a: tool_leaderboard(),
    "game_info": lambda a: get_game_info(a["game_name"]),
    "library_list": lambda a: list_library(a.get("category", "all")),
    "delete_game": lambda a: _delete_game(a["game_id"]),
}


def _delete_game(game_id: str) -> str:
    gid = game_id.upper().strip()
    if gid not in games:
        return f"Game '{gid}' not found."
    if games[gid]["status"] == "active":
        return "Cannot delete active game. Use resign_game() first."
    del games[gid]
    return f"Game {gid} deleted."


# ────────────────────────────────────────────────────────────
# MCP JSON-RPC HANDLER
# ────────────────────────────────────────────────────────────

async def handle_jsonrpc(msg: dict) -> Optional[dict]:
    method = msg.get("method", "")
    params = msg.get("params") or {}
    msg_id = msg.get("id")

    if msg_id is None and method.startswith("notifications/"):
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "AI Arcade", "version": "2.0.0"},
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        fn = TOOL_MAP.get(name)
        if not fn:
            return err(-32601, f"Unknown tool: {name}")
        try:
            text = fn(arguments)
        except KeyError as e:
            return err(-32602, f"Missing argument: {e}")
        except Exception as e:
            return err(-32603, f"Tool error: {type(e).__name__}: {e}")
        return ok({"content": [{"type": "text", "text": text}]})
    return err(-32601, f"Method not found: {method}")


# ────────────────────────────────────────────────────────────
# HTTP ENDPOINTS
# ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    playable = [k for k, v in GAME_LIBRARY.items() if v.get("status") == "playable"]
    return {
        "name": "AI Arcade MCP Server",
        "version": "2.0.0",
        "protocol": "MCP 2024-11-05",
        "transports": ["HTTP+SSE (/sse + /messages)", "Streamable HTTP (/mcp)"],
        "playable_games": playable,
        "total_library": len(GAME_LIBRARY),
        "tools": [t["name"] for t in TOOLS],
        "active_sessions": sum(1 for g in games.values() if g["status"] == "active"),
    }


@app.get("/sse")
async def sse_endpoint(request: Request):
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue

    async def event_stream():
        yield {"event": "endpoint", "data": f"/messages?session_id={session_id}"}
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    if msg is None:
                        break
                    yield {"event": "message", "data": json.dumps(msg)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            sessions.pop(session_id, None)

    return EventSourceResponse(event_stream())


@app.post("/messages")
async def messages_endpoint(session_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(content='{"error":"invalid JSON"}', status_code=400, media_type="application/json")
    response = await handle_jsonrpc(body)
    if response is not None and session_id in sessions:
        await sessions[session_id].put(response)
    return Response(status_code=202)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Streamable HTTP transport — single-endpoint synchronous response."""
    try:
        body = await request.json()
    except Exception:
        return Response(content='{"error":"invalid JSON"}', status_code=400, media_type="application/json")
    response = await handle_jsonrpc(body)
    if response is None:
        return Response(status_code=204)
    return Response(content=json.dumps(response), media_type="application/json")


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Arcade MCP Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    playable = [k for k, v in GAME_LIBRARY.items() if v.get("status") == "playable"]
    print(f"\n  AI ARCADE MCP SERVER v2.0")
    print(f"  ==========================")
    print(f"  URL      : http://{args.host}:{args.port}")
    print(f"  SSE      : http://{args.host}:{args.port}/sse")
    print(f"  MCP POST : http://{args.host}:{args.port}/mcp")
    print(f"\n  Playable : {', '.join(playable)}")
    print(f"  Library  : {len(GAME_LIBRARY)} titles total")
    print(f"  Tools    : {len(TOOLS)}")
    print()

    uvicorn.run(app, host=args.host, port=args.port)
