"""
Arcade Bridge — connects the Sovereign Council to the AI Arcade MCP server.

Usage:
    from core.council.arcade_bridge import ArcadeBridge
    bridge = ArcadeBridge()
    game = bridge.start_game("chess", "Strategist", "Oracle")
    result = bridge.make_move(game["game_id"], "Strategist", "e4")
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

ARCADE_MCP_URL = "http://localhost:8003/mcp"


class ArcadeBridge:
    """Thin client that lets any code (including SovereignCouncil agents) call
    AI Arcade MCP tools over the Streamable HTTP transport."""

    def __init__(self, url: str = ARCADE_MCP_URL):
        self.url = url
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call an MCP tool and return its result dict (or raise on error)."""
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": kwargs,
            },
        }).encode()

        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
        except urllib.error.URLError as exc:
            return {"error": f"Arcade MCP unreachable: {exc}"}

        if "error" in data:
            return {"error": data["error"]}

        # MCP tool result: result.content[0].text  (text content block)
        try:
            text = data["result"]["content"][0]["text"]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Plain-text response — wrap it and extract common fields
                result = {"raw": text, "status": "ok"}
                # Extract game ID  (ID    : XXXXXXXX  or  ID: XXXXXXXX)
                import re
                m = re.search(r"ID\s*:\s*([A-F0-9]{6,})", text)
                if m:
                    result["game_id"] = m.group(1)
                # Active vs waiting
                if "ACTIVE" in text:
                    result["game_status"] = "active"
                elif "waiting for opponent" in text:
                    result["game_status"] = "waiting"
                return result
        except (KeyError, IndexError):
            return data.get("result", data)

    # ------------------------------------------------------------------ #
    # Convenience helpers                                                  #
    # ------------------------------------------------------------------ #

    def arcade_info(self) -> Dict[str, Any]:
        return self.call("arcade_info")

    def list_games(self) -> Dict[str, Any]:
        return self.call("list_games")

    def start_game(self, game_type: str, player1: str, player2: str) -> Dict[str, Any]:
        """
        Full lobby flow: player1 creates the game, player2 joins.
        Returns the final game state dict (includes game_id).
        Solo games (minesweeper, sudoku, tetris, etc.) are active immediately.
        """
        created = self.call("create_game", game_type=game_type, player_name=player1)
        if "error" in created:
            return created
        game_id = created.get("game_id")
        if not game_id:
            return created
        # Solo games are immediately active — no join needed
        if created.get("game_status") == "active":
            return created
        # 2-player lobby — second agent joins
        joined = self.call("join_game", game_id=game_id, player_name=player2)
        if "error" in joined:
            return {"game_id": game_id, "warning": f"join failed: {joined['error']}", **created}
        # Propagate game_id into join response if missing
        if "game_id" not in joined:
            joined["game_id"] = game_id
        return joined

    def get_game_state(self, game_id: str) -> Dict[str, Any]:
        return self.call("get_game_state", game_id=game_id)

    def make_move(self, game_id: str, player: str, move: str) -> Dict[str, Any]:
        return self.call("make_move", game_id=game_id, player_name=player, move=move)

    def get_leaderboard(self) -> Dict[str, Any]:
        return self.call("get_leaderboard")

    def game_library(self, category: Optional[str] = None) -> Dict[str, Any]:
        if category:
            return self.call("library_list", category=category)
        return self.call("library_list")

    def health(self) -> bool:
        """Return True if the arcade server is reachable."""
        try:
            req = urllib.request.Request(
                self.url.replace("/mcp", "/"),
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
