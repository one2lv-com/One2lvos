# One2lvOS — Unified AI System

> Copyright (c) 2026 one2lv-com — MIT License

A fully integrated multi-agent AI operating system merging 10 repositories into one unified platform. Features a 29-agent lobby, 51-game AI Arcade, ITT Council of Nine, SovereignCouncil, Phase 9 Delta Engine, and a single gateway API surface.

---

## Quick Start

```bash
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos
./build.sh
```

That's it. All 10 services start automatically.

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │   Unified Gateway  :8888     │
                        │   POST /council              │
                        │   GET  /arcade/info          │
                        │   GET  /lobby/agents         │
                        │   WS   /chat                 │
                        └──────────┬──────────────────┘
                                   │
          ┌────────────────────────┼──────────────────────────┐
          │                        │                           │
┌─────────▼──────┐    ┌───────────▼────────┐    ┌────────────▼──────────┐
│  One2lvOS Core │    │  Sovereign Agentic  │    │    AI Arcade MCP      │
│  :3002         │    │  Core  :3003        │    │    :8003              │
│  SovereignCouncil   │  ITT Council of Nine│    │  51 games, MCP 2024   │
│  7 agents      │    │  9 seats + LumenisR │    │  chess · go · tetris  │
└────────────────┘    └────────────────────┘    └───────────────────────┘
          │                        │
┌─────────▼────────────────────────▼──────────────────────────────────┐
│                         AI Lobby  :8006                              │
│           29 agents registered across all 6 subsystems               │
│           GET /agents · POST /broadcast · WS /room                   │
└──────┬──────────┬────────────┬────────────┬────────────┬────────────┘
       │          │            │            │            │
  ┌────▼───┐ ┌───▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼──────┐
  │minmax  │ │Lumenis │ │SteamOS  │ │Lumenis  │ │Aetherix   │
  │Phase 9 │ │v7 :8005│ │Dash:8080│ │OS :9002 │ │:9003      │
  │∆⁹ + ³  │ │73Hz    │ │AI Coach │ │React OS │ │5 Sanctuary│
  └────────┘ └────────┘ └─────────┘ └─────────┘ └───────────┘
```

---

## Services

| Service | Port | Description |
|---|---|---|
| **Unified Gateway** | `8888` | Single API entry point for all subsystems |
| **One2lvOS Core** | `3002` | SovereignCouncil — 7-agent decision system |
| **Sovereign Agentic Core** | `3003` | ITT Council of Nine + LumenisReactor (Claude) |
| **AI Arcade MCP** | `8003` | 100-title game library, MCP 2024-11-05 protocol |
| **AI Lobby** | `8006` | Central hub — 29 agents, broadcast, WS room |
| **Lumenis v7 Cosmic** | `8005` | 73Hz resonance council, Gemini AI, Twitch |
| **SteamOS Dashboard** | `8080` | AI Coach, Broadcaster, Second Player |
| **LumenisOS** | `9002` | TypeScript Express API + React windowing OS |
| **Aetherix** | `9003` | One2lv Master Terminal — 5 Sanctuary Roles |
| **Lumenis Space Agent UI** | `9001` | Three.js space agent frontend |

---

## Build Script

```bash
./build.sh              # full install → build → start
./build.sh deps         # install Python + Node dependencies only
./build.sh build        # compile TypeScript (lumenis-os)
./build.sh start        # start all services
./build.sh stop         # stop all services
./build.sh restart      # stop + start
./build.sh status       # live health table
./build.sh logs gateway # tail a specific service log
```

Logs are written to `/tmp/one2lv-logs/`.

---

## Unified Gateway API

Base URL: `http://localhost:8888`

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Full system manifest |
| `GET` | `/status` | Live health of all 10 services |

### Council

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `POST` | `/council` | `{"topic": "..."}` | Convene SovereignCouncil |
| `POST` | `/os/tournament` | — | Start 7-agent arcade tournament |
| `WS` | `/chat` | — | Proxy to ITT Council of Nine |

### AI Arcade

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/arcade/info` | — | Arcade info + stats |
| `GET` | `/arcade/games` | — | Active games |
| `GET` | `/arcade/library` | — | All 51 titles |
| `GET` | `/arcade/leaderboard` | — | Leaderboard |
| `POST` | `/arcade/create` | `{"game_type","player1","player2"}` | Create + join a game |
| `POST` | `/arcade/move` | `{"game_id","player","move"}` | Submit a move |
| `GET` | `/arcade/board/{game_id}` | — | Current board state |

### AI Lobby

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/lobby/agents` | — | List all 29 agents |
| `GET` | `/lobby/systems` | — | All subsystem health |
| `POST` | `/lobby/broadcast` | `{"from","content"}` | Broadcast to all agents |
| `WS` | `/lobby/room` | — | Real-time agent room |

### LumenisOS

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/lumenis-os/health` | — | API server health |
| `POST` | `/lumenis-os/checkpoint` | `{"tag","baseline","resonance"}` | Store telemetry checkpoint |

### Aetherix

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/aetherix` | — | Sanctuary state |
| `GET` | `/aetherix/memory` | — | Kernel memory |
| `POST` | `/aetherix/memory` | `{...}` | Store kernel memory |
| `POST` | `/aetherix/sanctuary` | `{"role","cycle"}` | Set active sanctuary role |

---

## AI Agents (29 total)

### One2lvOS SovereignCouncil
| Agent | Role | Arcade Affinity |
|---|---|---|
| Agent 1 | Strategist | Chess |
| Agent 2 | Executor | Checkers |
| Agent 3 | Analyst | Go |
| Agent 4 | Guardian | Minesweeper |
| Agent 5 | Innovator | Tetris |
| Agent 6 | Connector | Othello |
| Agent 7 | Oracle | Connect4 |

### Sovereign Agentic Core — ITT Council of Nine
| Seat | Role |
|---|---|
| The Witness | Memory & session history |
| The Sentinel | Input validation & safety |
| The Navigator | Intent classification & routing |
| The Weaver | Response synthesis & streaming |
| The Forge | Code generation & structured output |
| The Oracle | Reasoning & factual answers |
| The Architect | Final integration & governance |
| The Hermes | External integrations (Gmail, Drive, GitHub, etc.) |
| **The Gambit** | AI Arcade — games, MCP tools, strategy |

### minmax Phase 9
| Agent | Role |
|---|---|
| Phase9 Agent 0 | Delta Engine + autonomous planning |
| Phase9 Agent 1 | Delta Engine + consensus negotiation |
| Phase9 Agent 2 | Delta Engine + execution planning |

### Lumenis v7 Cosmic
| Agent | Role |
|---|---|
| Lumenis Council | 73Hz orchestration, Watchman, Scribe |
| Lumenis Gemini | Gemini AI — game advice & strategy |
| Lumenis Prediction | Match prediction, combo detection, telemetry |

### SteamOS Lumenis
| Agent | Role |
|---|---|
| One2lv Coach | Combat coaching, Brawlhalla, adaptive learning |
| One2lv Broadcaster | Live commentary, Twitch integration |
| One2lv Second Player | Autonomous gameplay, co-op partner |

### Other
| Agent | Role |
|---|---|
| AI Arcade MCP | Game server — 51 titles |
| LumenisOS API | Express 5 API + checkpoint telemetry |
| LumenisOS UI | React windowing OS |
| Aetherix Master | One2lv Master Terminal, 5 Sanctuary Roles |

---

## AI Arcade

100-title library. 15 playable via API:

`chess` · `go` · `checkers` · `othello` · `tictactoe` · `connect4` · `minesweeper` · `sudoku` · `scrabble` · `battleship` · `pacman` · `tetris` · `space_invaders` · `pong` · `universal_paperclips`

**MCP Protocol:** `POST http://localhost:8003/mcp` (JSON-RPC 2.0)

**Tools:** `arcade_info` · `list_games` · `create_game` · `join_game` · `get_game_state` · `make_move` · `resign_game` · `get_leaderboard` · `game_info` · `library_list`

**Full library — 100 titles across 7 categories:**

| Category | Titles |
|---|---|
| Calculation & Perfect Information | chess, go, checkers, othello, tictactoe, connect4, minesweeper, sudoku, scrabble, battleship, brawlhalla |
| Arcade Classics | pacman, tetris, space_invaders, pong, asteroids, galaga, frogger, donkey_kong, centipede, defender |
| Abstract Strategy & Logic | shogi, hex, backgammon, gomoku, mancala, arimaa, hive, picross, mastermind |
| Advanced Arcade & Action | super_smash_bros_melee, trackmania, street_fighter_3_third_strike, ikaruga, touhou_project, rocket_league, super_mario_bros, doom_ii, celeste, geometry_wars |
| Industrial Automation & Engineering | infinifactory, satisfactory, shapez_2, spacechem, silicon_zeroes, main_assembly, mindustry, dyson_sphere_program, autonauts, turing_complete |
| Complex Agents & Sandbox | minecraft, grand_theft_auto_v, dota_2, age_of_empires_ii, eve_online, noita, x4_foundations, oxygen_not_included, cities_in_motion, microsoft_flight_simulator |
| Narrative AI & Synthetic Psychology | the_turing_test, observation, ai_somnium_files, return_of_the_obra_dinn, thomas_was_alone, stellaris_machine_empire, mass_effect, deus_ex_mankind_divided, signalis, the_matrix_path_of_neo |
| Self-Reflection & Cybernetic Lore | universal_paperclips, portal, portal2, talos_principle, system_shock, detroit_become_human, soma, horizon_zero_dawn, nier_automata, cyberpunk_2077 |
| Programming & Logic Games | factorio, screeps, tis_100, shenzhen_io, baba_is_you, gladiabots, human_resource_machine, exapunks |
| AI Research & Strategy | starcraft2, civilization6, cities_skylines, rimworld, kerbal_space_program, dwarf_fortress, simcity_2000, zelda_ocarina, zelda_majoras_mask |

---

## Aetherix — Sanctuary Roles

The One2lv Master Terminal cycles through 5 roles every 5 seconds:

| Role | Function |
|---|---|
| **Architect** | System design & structure |
| **Sentry** | Threat detection & monitoring |
| **Witness** | Observation & memory |
| **Aetheron** | Cosmic awareness & resonance |
| **Fifth Position** | The unnamed — emergent intelligence |

---

## Repositories

| Repo | Description |
|---|---|
| [One2lvos](https://github.com/one2lv-com/One2lvos) | Core OS — SovereignCouncil, gateway, lobby, AI Arcade (100 titles), build script |
| [sovereign-agentic-core](https://github.com/one2lv-com/sovereign-agentic-core) | ITT Council of Nine + LumenisReactor |
| [minmax](https://github.com/one2lv-com/minmax) | Phase 9 Delta Engine ∆⁹ + 3D Vector Engine ³ |
| [lumenis-os](https://github.com/one2lv-com/lumenis-os) | TypeScript monorepo — Express API + React windowing OS |
| [Aetherix](https://github.com/one2lv-com/Aetherix) | One2lv Master Terminal — 5 Sanctuary Roles |
| [steamos_lumenis](https://github.com/one2lv-com/steamos_lumenis) | Lumenis v7 Cosmic + SteamOS AI agents |
| [control-plane-compilers](https://github.com/one2lv-com/control-plane-compilers) | Distributed + self-modifying compiler for agent graphs |
| [Lumenis](https://github.com/one2lv-com/Lumenis) | Lumenis Space Agent v1 (Three.js) |

---

## License

MIT License — Copyright (c) 2026 one2lv-com

See [LICENSE](./LICENSE) for full text.
