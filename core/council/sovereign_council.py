"""
Sovereign Council - Multi-Agent Decision System
================================================

7-agent council for autonomous decision-making, with AI Arcade integration.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass

from core.council.arcade_bridge import ArcadeBridge


@dataclass
class Agent:
    """Council Agent"""
    name: str
    role: str
    status: str = "online"


# Map each agent to the game they favour during arcade sessions
AGENT_GAME_AFFINITY = {
    "Agent 1": "chess",          # Strategist  — long-term planning
    "Agent 2": "checkers",       # Executor    — decisive captures
    "Agent 3": "go",             # Analyst     — territory / pattern reading
    "Agent 4": "minesweeper",    # Guardian    — risk detection
    "Agent 5": "tetris",         # Innovator   — creative placement
    "Agent 6": "othello",        # Connector   — flipping alliances
    "Agent 7": "connect4",       # Oracle      — sees lines ahead
}


class SovereignCouncil:
    """
    7-Agent Council System with AI Arcade integration.
    Agents can challenge each other to games via the arcade MCP bridge.
    """

    def __init__(self):
        self.agents = [
            Agent("Agent 1", "Strategist - Long-term planning"),
            Agent("Agent 2", "Executor - Action implementation"),
            Agent("Agent 3", "Analyst - Data processing"),
            Agent("Agent 4", "Guardian - Security & safety"),
            Agent("Agent 5", "Innovator - Creative solutions"),
            Agent("Agent 6", "Connector - Integration & communication"),
            Agent("Agent 7", "Oracle - Prediction & foresight"),
        ]

        self.session_count = 0
        self.decisions = []
        self.arcade = ArcadeBridge()

    # ------------------------------------------------------------------ #
    # Core council methods                                                 #
    # ------------------------------------------------------------------ #

    def convene(self, topic: str) -> Dict:
        """Convene council for decision"""
        self.session_count += 1

        print(f"\n[COUNCIL] Session #{self.session_count}: {topic}")
        print("[COUNCIL] Agents convening...")

        time.sleep(0.2)  # Simulate deliberation

        # Each agent provides input
        inputs = []
        for agent in self.agents:
            print(f"[COUNCIL]   • {agent.name} ({agent.role}): Analyzing...")
            inputs.append({
                "agent": agent.name,
                "role": agent.role,
                "recommendation": f"Recommendation from {agent.name}"
            })

        # Synthesize decision
        decision = {
            "session": self.session_count,
            "topic": topic,
            "timestamp": time.time(),
            "inputs": inputs,
            "consensus": "Council has reached consensus",
            "action": "Recommended action path",
            "confidence": 0.95
        }

        self.decisions.append(decision)

        print(f"[COUNCIL] ✓ Decision reached (confidence: {decision['confidence']*100}%)")

        return decision

    def get_status(self) -> Dict:
        """Get council status"""
        arcade_online = self.arcade.health()
        status = {
            "agents": len(self.agents),
            "online": sum(1 for a in self.agents if a.status == "online"),
            "sessions": self.session_count,
            "decisions": len(self.decisions),
            "arcade": {
                "online": arcade_online,
                "url": self.arcade.url,
            },
        }
        return status

    # ------------------------------------------------------------------ #
    # Arcade integration                                                   #
    # ------------------------------------------------------------------ #

    def arcade_challenge(self, agent1_name: str, agent2_name: str,
                          game_type: Optional[str] = None) -> Dict:
        """
        Have two council agents challenge each other to an arcade game.
        If game_type is omitted, agent1's affinity game is used.
        Returns the created game info.
        """
        if game_type is None:
            game_type = AGENT_GAME_AFFINITY.get(agent1_name, "chess")

        print(f"\n[ARCADE] {agent1_name} challenges {agent2_name} to {game_type}!")
        result = self.arcade.start_game(
            game_type=game_type,
            player1=agent1_name,
            player2=agent2_name,
        )
        if "game_id" in result:
            status = result.get("game_status", result.get("status", "ready"))
            print(f"[ARCADE] Game {result['game_id']} ready ({game_type}, status={status})")
        else:
            print(f"[ARCADE] Game creation error: {result.get('error', result)}")
        return result

    def arcade_status(self) -> Dict:
        """Return live arcade info + active games."""
        info = self.arcade.arcade_info()
        games = self.arcade.list_games()
        board = self.arcade.get_leaderboard()
        return {
            "arcade": info,
            "active_games": games.get("games", []),
            "leaderboard": board.get("leaderboard", {}),
        }

    def arcade_move(self, game_id: str, agent_name: str, move: str) -> Dict:
        """Let a named council agent submit a move."""
        result = self.arcade.make_move(game_id=game_id, player=agent_name, move=move)

        print(f"[ARCADE] {agent_name} played {move!r} in {game_id}: {result.get('status', result)}")
        return result

    def arcade_tournament(self) -> Dict:
        """
        Kick off a round-robin mini-tournament where agents play their
        affinity games against the next agent in the ring.
        Returns dict of game_id per match.
        """
        print("\n[ARCADE] Starting Council Tournament!")
        matches = {}
        agents = self.agents
        for i, agent in enumerate(agents):
            opponent = agents[(i + 1) % len(agents)]
            game_type = AGENT_GAME_AFFINITY.get(agent.name, "chess")
            result = self.arcade_challenge(agent.name, opponent.name, game_type)
            if "game_id" in result:
                matches[f"{agent.name}_vs_{opponent.name}"] = {
                    "game_id": result["game_id"],
                    "game_type": game_type,
                }
        print(f"[ARCADE] Tournament started: {len(matches)} matches")
        return {"tournament": matches}

    # ------------------------------------------------------------------ #
    # AI Lobby integration                                                 #
    # ------------------------------------------------------------------ #

    LOBBY_URL = "http://localhost:8006"

    def lobby_register(self) -> None:
        """Register all 7 council agents in the AI Lobby."""
        import urllib.request
        for agent in self.agents:
            aff = AGENT_GAME_AFFINITY.get(agent.name, "chess")
            profile = {
                "id": f"sovereign_{agent.role.split(' ')[0].lower()}",
                "name": agent.name,
                "system": "One2lvOS SovereignCouncil",
                "role": agent.role.split(" - ")[0].lower(),
                "url": "http://localhost:3002",
                "protocol": "python-internal",
                "capabilities": [agent.role.split(" - ")[1] if " - " in agent.role else agent.role,
                                  aff, "arcade_challenge", "council_vote"],
                "arcade_affinity": aff,
                "status": agent.status,
            }
            data = __import__("json").dumps(profile).encode()
            req = urllib.request.Request(
                f"{self.LOBBY_URL}/agents/register", data=data,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=3):
                    pass
            except Exception:
                pass

    def lobby_broadcast(self, content: str, meta: dict = None) -> dict:
        """Post a message to the AI Lobby broadcast channel."""
        import urllib.request, json
        body = json.dumps({"from": "SovereignCouncil", "content": content, "meta": meta or {}}).encode()
        req = urllib.request.Request(
            f"{self.LOBBY_URL}/broadcast", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return json.loads(r.read())
        except Exception as e:
            return {"error": str(e)}
