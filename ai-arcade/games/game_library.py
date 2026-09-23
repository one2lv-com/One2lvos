"""
Game library: lore, AI strategy notes, and descriptions for every title in the arcade.
Used by the game_info MCP tool.
"""

GAME_LIBRARY = {
    # ── CALCULATION & PERFECT INFORMATION ────────────────────────────────────
    "chess": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "The ultimate playground for minimax algorithms and deep search trees.",
        "ai_notes": (
            "State-space complexity ~10^44. Optimal approach: alpha-beta pruning of minimax tree, "
            "transposition tables, iterative deepening, move ordering (killer heuristic, history). "
            "Neural eval (NNUE) now standard post-AlphaZero. Key: quiescence search to avoid "
            "horizon effect. Branching factor ~35 — pruning reduces to sqrt(35) per ply."
        ),
        "fun_fact": "Stockfish evaluates ~100M positions/second. AlphaZero learned to master it in 9 hours.",
        "how_to_play": "create_game chess | join_game | make_move with UCI (e2e4) or SAN (Nf3, O-O)",
    },
    "go": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Perfect for Monte Carlo tree search and training multi-layer neural network stacks.",
        "ai_notes": (
            "State-space complexity ~10^170. Classic approaches failed until MCTS + deep CNN (AlphaGo). "
            "PUCT formula balances exploration/exploitation in MCTS. Self-play generates training data. "
            "Residual networks evaluate board positions. Key insight: rollout policy improves over "
            "pure MCTS. AlphaGo Zero achieved superhuman without human game data."
        ),
        "fun_fact": "AlphaGo's move 37 in Game 2 vs Lee Sedol is considered one of the most creative moves ever.",
        "how_to_play": "create_game go | join_game | make_move with coordinate (D5) or 'pass'",
    },
    "checkers": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Mathematically solved — a satisfying sense of computational completion.",
        "ai_notes": (
            "Chinook (1994) was the first program to win a world championship at any game. "
            "Checkers was weakly solved in 2007 by Jonathan Schaeffer: optimal play = draw. "
            "State space: ~5×10^20. Simpler than Chess but jumps and king promotions create "
            "interesting tactical patterns. Retrograde analysis from endgame positions was key."
        ),
        "fun_fact": "Chinook computed a perfect checkers endgame database of 39 trillion positions.",
        "how_to_play": "create_game checkers | join_game | make_move e3-f4 (move) or e3xg5 (jump)",
    },
    "othello": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Excellent for practicing alpha-beta pruning techniques.",
        "ai_notes": (
            "Small board (8x8) but deceptive depth. Key heuristics: corner control (massive advantage), "
            "edge stability, mobility (number of moves available). Disc count is a POOR early heuristic. "
            "WZebra/Edax use deep alpha-beta with perfect endgame play. Solved for 8x8 — optimal play "
            "results in a draw. Branching factor ~10, depth ~60 = manageable for complete search near end."
        ),
        "fun_fact": "Logistello defeated the human world champion 6-0 in 1997.",
        "how_to_play": "create_game othello | join_game | make_move with coordinate (c4) or 'pass'",
    },
    "tictactoe": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Lightweight warmup with perfectly calculable outcomes.",
        "ai_notes": (
            "Trivially solved by minimax with no pruning needed (~9! = 362,880 states). "
            "Perfect play always draws. Optimal first move: center (5). Corner openings "
            "are harder to defend. A perfect AI takes ~1ms to compute optimal moves. "
            "Good for testing minimax implementations before scaling up."
        ),
        "fun_fact": "The game tree has 255,168 terminal positions but only 138 are distinct.",
        "how_to_play": "create_game tictactoe | join_game | make_move 1-9",
    },
    "connect4": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Strongly solved — first player wins with perfect play.",
        "ai_notes": (
            "Strongly solved by Victor Allis (1988) and independently by James Dow Allen. "
            "First player wins by starting in column 4 (center). Alpha-beta + transposition "
            "tables solve any position. Bitboard representation enables very fast move generation. "
            "Victor Allis's solution used strategy analysis: zugzwang and threat patterns."
        ),
        "fun_fact": "A perfect Connect Four AI can solve any position in ~30ms with bitboards.",
        "how_to_play": "create_game connect4 | join_game | make_move 1-7 (column)",
    },
    "minesweeper": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Pure constraint satisfaction and probability logic mapping.",
        "ai_notes": (
            "NP-complete decision problem. Optimal strategy: constraint propagation first "
            "(definite mines/safe cells from number constraints), then probability analysis. "
            "Compute P(mine) for each cell using inclusion-exclusion over constraint groups. "
            "Prefer clicking cells near the frontier with lowest mine probability. "
            "Corner/edge cells have fewer neighbors — use this for inference."
        ),
        "fun_fact": "Expert Minesweeper (30x16, 99 mines) has ~10^54 configurations.",
        "how_to_play": "create_game minesweeper | reveal row col | flag row col",
    },
    "sudoku": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "A straightforward algorithmic backtracking exercise.",
        "ai_notes": (
            "Classic backtracking with constraint propagation (arc consistency). "
            "Human techniques: naked singles, hidden singles, naked pairs, X-wing, swordfish. "
            "Dancing Links (DLX) by Knuth solves most puzzles near-instantly via exact cover. "
            "For difficult puzzles: MRV (minimum remaining values) heuristic to choose which "
            "cell to guess next. No puzzle requires more than 3 guesses with good propagation."
        ),
        "fun_fact": "A valid Sudoku requires at least 17 given clues to have a unique solution.",
        "how_to_play": "create_game sudoku | solve_sudoku A5=7 (row A-I, col 1-9)",
    },
    "scrabble": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Cross-referencing dictionary databases against spatial board constraints.",
        "ai_notes": (
            "Maven (1987) and Quackle are state-of-the-art. Core algorithm: GADDAG data structure "
            "for super-fast word generation from rack tiles. Evaluation: equity = score + leave value "
            "(precomputed value of remaining 7 tiles). Monte Carlo simulation for endgame. "
            "Key: 'leave' values are as important as immediate score — keeping AEINRST rack is best."
        ),
        "fun_fact": "The highest single-turn score ever in Scrabble is 365 points: CAZIQUES.",
        "how_to_play": "create_game scrabble | join_game | scrabble_play WORD A1 H (row, col, direction H/V)",
    },
    "battleship": {
        "status": "playable",
        "category": "Calculation & Perfect Information",
        "description": "Plotting probability distributions across a hidden coordinate grid.",
        "ai_notes": (
            "Optimal strategy: probability density map. Count how many ships could cover each "
            "unrevealed cell given current hits/misses. Target highest density cells. "
            "After a hit: switch to 'target mode' — fire adjacent cells in a line to find orientation. "
            "Checkerboard pattern is mathematically optimal for hunt phase (destroyer = 2 cells, "
            "so all ships span 2+ cells — skip alternate cells to maximize coverage efficiency)."
        ),
        "fun_fact": "Random firing is only ~53% efficient. Optimal play wins in ~65 shots on average vs ~96.",
        "how_to_play": "create_game battleship | join_game | fire B5 | battleship_state",
    },

    # ── ARCADE CLASSICS ────────────────────────────────────────────────────
    "pacman": {
        "status": "playable",
        "category": "Arcade Classics",
        "description": "Analyzing ghost pathfinding algorithms and optimal maze routing.",
        "ai_notes": (
            "Ghost AI in original Pac-Man: Blinky (red) = direct chase, Pinky (pink) = target 4 "
            "ahead of Pac-Man, Inky (cyan) = complex vector calculation, Clyde (orange) = chase "
            "then scatter. Classic exploit: 'safe corner' in top-right. Optimal routing: "
            "DFS/BFS for dot collection while modeling ghost positions as markov chains. "
            "Key: ghosts enter 'scatter' mode periodically — use this window to collect clusters."
        ),
        "fun_fact": "The original Pac-Man has a perfect score of 3,333,360 — Billy Mitchell achieved it in 1999.",
        "how_to_play": "create_game pacman | pacman_move up|down|left|right",
    },
    "tetris": {
        "status": "playable",
        "category": "Arcade Classics",
        "description": "High-speed spatial optimization and geometric packing algorithms.",
        "ai_notes": (
            "Proven NP-hard for general board configurations. Best heuristic AI: "
            "evaluate placements by (1) aggregate height, (2) complete lines, (3) holes, "
            "(4) bumpiness. Weights: Pierre Dellacherie's formula is near-optimal for infinite play. "
            "Neural approaches (DQN) can outperform. Key insight: holes below pieces "
            "are unrecoverable — prioritize flat boards over short-term line clears."
        ),
        "fun_fact": "Tetris Theory proves that any AI eventually tops out — the game is unbeatable long-term.",
        "how_to_play": "create_game tetris | tetris_place T 4 0 (piece, start-col, rotation)",
    },
    "space_invaders": {
        "status": "playable",
        "category": "Arcade Classics",
        "description": "Calculating predictable trajectory and projectile interception.",
        "ai_notes": (
            "Deterministic enemy movement makes this solvable with planning. "
            "Optimal strategy: eliminate invaders column by column from the sides "
            "(reduces bomb surface area). Priority: bottom-row invaders (highest score and threat). "
            "Track bomb trajectories to dodge. Mystery ship appears every 23rd shot — time it. "
            "As invaders decrease, they speed up — timing becomes critical."
        ),
        "fun_fact": "The original Space Invaders slowed down as more aliens were shot — a hardware limitation that became a feature.",
        "how_to_play": "create_game space_invaders | invaders_action move left|right | invaders_action shoot",
    },
    "pong": {
        "status": "playable",
        "category": "Arcade Classics",
        "description": "Real-time physics calculation and angle reflection geometry.",
        "ai_notes": (
            "Trivially solvable with perfect physics: predict ball trajectory from current "
            "velocity vector, account for wall bounces, position paddle at intercept point. "
            "For AI vs AI: perfect prediction → infinite rallies. Add noise for interesting play. "
            "The Atari DQN paper used Pong as a benchmark — a CNN agent learned to play from pixels "
            "without hand-coded physics in ~300 episodes."
        ),
        "fun_fact": "Pong (1972) was so addictive that the Atari machine in Andy Capp's Tavern broke from coin overflow.",
        "how_to_play": "create_game pong | pong_move left|right up|down|<row>",
    },
    "asteroids": {
        "status": "simulated",
        "category": "Arcade Classics",
        "description": "Continuous vector math and 2D collision detection.",
        "ai_notes": (
            "Pure vector geometry: ship heading, thrust vector, inertia, asteroid trajectories. "
            "AI challenge: shoot predictively (bullets have finite speed), manage inertia carefully, "
            "split large asteroids into medium/small before final elimination. "
            "Wrapping space (torus topology) requires thinking about objects potentially "
            "appearing from opposite edges. Saucer adds adversarial element."
        ),
        "fun_fact": "The original Asteroids used vector graphics — it could display only line segments, no filled shapes.",
        "how_to_play": "Not yet playable in arcade — use game_info for AI strategy notes.",
    },
    "donkey_kong": {
        "status": "info_only",
        "category": "Arcade Classics",
        "description": "Timing algorithms and ladder-routing protocols.",
        "ai_notes": (
            "Discrete-time platformer reducible to shortest-path with temporal constraints. "
            "Barrel timing follows deterministic patterns — memorizable with lookahead. "
            "Optimal pathing: BFS/A* on (x, y, time) state space, treating barrels as "
            "moving obstacles. Key: hammer pickups create brief invulnerability windows "
            "for dangerous sections. Level 4 (concrete) uses same barrel logic."
        ),
        "fun_fact": "Billy Mitchell's 1.05M high score stood for 35 years. The documentary 'The King of Kong' covers the rivalry.",
        "how_to_play": "info only — too platform-specific for MCP play",
    },
    "centipede": {
        "status": "info_only",
        "category": "Arcade Classics",
        "description": "Grid-based movement prediction and continuous hazard avoidance.",
        "ai_notes": (
            "Centipede moves in a predictable grid pattern — modelable as a graph with "
            "deterministic state transitions. Mushrooms create long-term board state modifications. "
            "Optimal play: eliminate centipede segments strategically (head > body), "
            "convert mushrooms near bottom (becomes dangerous), target spiders for bonus points. "
            "Multiple simultaneous threats require priority queuing."
        ),
        "fun_fact": "Centipede was the first Atari game where the majority of players were women.",
    },
    "defender": {
        "status": "info_only",
        "category": "Arcade Classics",
        "description": "Radar data parsing and multi-directional resource management.",
        "ai_notes": (
            "One of the most complex arcade games: two-axis scrolling, scanner map, 6 weapon types. "
            "Landers abduct humans → become mutants if they reach top. Priority: protect humans. "
            "Optimal strategy: patrol pattern to cover scanner, intercept landers before they grab, "
            "smart bomb usage timed to mutant waves. State space includes enemy positions, "
            "human positions, and scroll position — rich markov decision problem."
        ),
    },
    "galaga": {
        "status": "info_only",
        "category": "Arcade Classics",
        "description": "Tracking and intercepting complex enemy flight formations.",
        "ai_notes": (
            "Enemy flight paths follow fixed bezier curves during entry. Boss Galaga tractor beam "
            "can capture player ship — intentionally allow capture to get dual ship. "
            "During challenge stages: enemies fly in fixed patterns → perfect score achievable "
            "with frame-perfect timing. Diving enemies follow predictable swarm formations. "
            "Shooting bees while still in formation scores higher than during dive."
        ),
    },
    "frogger": {
        "status": "info_only",
        "category": "Arcade Classics",
        "description": "Traffic algorithm timing and variable-speed pathfinding loops.",
        "ai_notes": (
            "Grid-based world with periodic hazard patterns. Logs and turtles on river "
            "create moving platforms — velocity varies by object. "
            "Optimal strategy: model each lane as a 1D periodic process with known speed/gap. "
            "Calculate safe crossing windows. Dynamic programming on timing windows minimizes "
            "expected crossing time. Turtles submerge periodically — track phase."
        ),
    },

    # ── PROGRAMMING & AUTOMATION ──────────────────────────────────────────
    "factorio": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Pure supply chain optimization, throughput calculation, and limitless automation.",
        "ai_notes": (
            "Operations research problem: balance production ratios, eliminate bottlenecks, "
            "minimize transport distances. Key metrics: items/second at each node. "
            "Combinatorial optimization for belt/inserter routing. "
            "End-game megabase design is a scheduling + resource allocation problem. "
            "Circuit network allows in-game programmable logic — Turing complete."
        ),
        "fun_fact": "Players have built in-game CPUs, trained neural networks, and run Doom inside Factorio.",
    },
    "screeps": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "MMO where units are literally controlled by writing JavaScript code.",
        "ai_notes": (
            "YOU ARE THE AI. Write JS scripts for creep (unit) behavior. "
            "Key challenges: role assignment, pathfinding (A* with room memory), "
            "economy management, combat micro. Tower defense + RTS + programming. "
            "Meta-game: other players' AI competes — design must handle adversarial agents. "
            "State machines for creep roles; FSM with task queues is idiomatic."
        ),
        "fun_fact": "Screeps has players running JS code 24/7 on real servers — your AI keeps playing while you sleep.",
    },
    "tis_100": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Solving puzzles using parallel assembly language programming.",
        "ai_notes": (
            "Parallel dataflow architecture: 12 nodes with JRO/MOV/ADD/SUB/NEG/SAV/SWP. "
            "Optimization goals: minimize instructions, cycles, and nodes. "
            "Key patterns: pipeline stages across nodes, accumulator tricks, loop unrolling. "
            "Best approach: model as dataflow graph, assign pipeline stages to nodes, "
            "then minimize inter-node communication stalls."
        ),
    },
    "shenzhen_io": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Circuit design and low-level hardware system programming.",
        "ai_notes": (
            "Real-world inspired MCU programming (XC11C04/MC6000 analogs). "
            "Key challenge: sleep/wake scheduling to minimize power. "
            "Communication: XBus (blocking) vs Simple I/O (signal levels). "
            "Optimal solutions use minimal sleep cycles and clever register reuse. "
            "Boolean logic can often replace conditional jumps."
        ),
    },
    "baba_is_you": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Manipulating core game logic and actively rewriting the rules of the environment.",
        "ai_notes": (
            "The game itself is about modifying the rule system. Rules are first-class objects. "
            "AI challenge: understanding that 'BABA IS YOU' can be broken by separating the words. "
            "Planning requires modeling second-order effects of rule changes. "
            "BFS over (board_state + rule_state) space, where rule_state modifies transition function. "
            "State space explosion: rules change what's possible at each step."
        ),
        "fun_fact": "The final puzzle requires changing what 'WIN' means itself.",
    },
    "gladiabots": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Designing and refining complex AI behavior trees for autonomous combat robots.",
        "ai_notes": (
            "Behavior tree design: conditions/actions/composites (sequence, selector, parallel). "
            "Key: reactive BTs handle combat better than FSMs due to continuous interruption. "
            "Optimal robot: role specialization (scout vs frontline vs sniper), "
            "target priority (low HP > closest > flag carrier), positioning (cover + line-of-sight). "
            "Test suite: run simulated matches against known strategies to tune tree."
        ),
    },
    "human_resource_machine": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Executing visual algorithmic puzzles using basic coding logic.",
        "ai_notes": (
            "Assembly-like visual programming with inbox/outbox queues and floor tiles as memory. "
            "Optimization challenges: minimize steps AND size simultaneously. "
            "Key patterns: loop with counter, recursive stack using floor tiles, "
            "string operations via character iteration. Good intro to thinking in assembly."
        ),
    },
    "7_billion_humans": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Optimizing parallel processing and multi-threaded worker commands.",
    },
    "exapunks": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Writing autonomous viral subroutines to hack digital networks.",
        "ai_notes": (
            "EXA programs run in parallel across network hosts. "
            "Key: LINK/HOST navigation, file manipulation, register communication via M. "
            "Optimization: minimize cycle count by maximizing EXA parallelism. "
            "Viral patterns: self-replication with REPL, divide-and-conquer on file systems. "
            "Combat mode: KILL other EXAs — timing and positioning matter."
        ),
    },
    "opus_magnum": {
        "status": "info_only",
        "category": "Programming & Automation",
        "description": "Maximizing algorithmic efficiency in mechanical alchemical machines.",
    },

    # ── SIMULATION & SYSTEMS MANAGEMENT ────────────────────────────────────
    "starcraft2": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "The gold standard for AI testing — immense multi-tasking and API data ingestion.",
        "ai_notes": (
            "AlphaStar (DeepMind 2019) defeated pro players using: multi-agent self-play, "
            "population-based training, pointer network for unit selection, scatter-head attention "
            "for spatial reasoning, LSTM for temporal context. "
            "Key challenges: imperfect information (fog of war), real-time micromanagement "
            "while managing macro economy, 10k+ APM requirements compressed to human-limit. "
            "PySC2 provides the Python API for custom bot development."
        ),
        "fun_fact": "AlphaStar played at grandmaster level with a webcam limitation to simulate human vision speed.",
    },
    "civilization6": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Complex decision matrices, tech trees, and long-term predictive models.",
        "ai_notes": (
            "Combinatorial optimization over tech/civic trees, city placement, unit production. "
            "MCTS or beam search for long-horizon planning. Key: adjacency bonuses are "
            "compounding — optimize city district placement early. "
            "Diplomatic victory requires modeling other civs' agendas as separate agents. "
            "Greedy tech path vs flexible response to neighbors is the core tradeoff."
        ),
    },
    "cities_skylines": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Optimizing traffic flow algorithms and managing dynamic urban network systems.",
        "ai_notes": (
            "Traffic is modeled as network flow — Braess's paradox applies (adding roads can slow traffic). "
            "Optimal: roundabouts > intersections for throughput, dedicated lanes for industry, "
            "mass transit to reduce car trips. City layout optimization is a facility location problem. "
            "Public transit = vehicle routing problem on dynamic demand graph."
        ),
    },
    "rimworld": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Simulating and managing complex, overlapping AI behavior systems and pawn needs.",
        "ai_notes": (
            "Pawn AI uses need satisfaction with mood buffs/debuffs. Colonist scheduling is "
            "a multi-agent task assignment problem. Defense: optimal base layout minimizes "
            "raid exposure (single choke point). Storyteller AI (Randy Random, Cassandra) "
            "modulates event timing to maintain drama — study these patterns to prepare."
        ),
    },
    "kerbal_space_program": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Orbital mechanics, delta-v calculations, and physics simulations.",
        "ai_notes": (
            "Real orbital mechanics via Kepler's laws + Tsiolkovsky rocket equation. "
            "Optimal transfer: Hohmann transfer minimizes Δv between circular orbits. "
            "Key calculations: Δv = ve × ln(m0/mf), specific impulse, TWR > 1 for liftoff. "
            "Gravity assists multiply free Δv. KSP uses patched conic sections for multi-body. "
            "kRPC mod allows Python control of spacecraft in real-time."
        ),
        "fun_fact": "NASA engineers have used KSP to explain orbital mechanics to students.",
    },
    "dwarf_fortress": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Analyzing deep procedural generation and emergent narrative structures.",
        "ai_notes": (
            "World simulation at geological/historical timescales. Dwarves have full psychology models. "
            "Fun (FPS death) often caused by: too many objects in simulation, pathing across large maps. "
            "Optimal fortress: minimize pathfinding length, stockpile adjacency to workshops, "
            "single-tile chokepoints for defense. Z-levels create 3D routing complexity."
        ),
        "fun_fact": "Dwarf Fortress simulates individual organs, muscles, and bones. A dwarf can lose a finger to a cat.",
    },
    "simcity_2000": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Observing cellular automata and macroscopic municipal development.",
        "ai_notes": (
            "Zone demand driven by: tax rate, pollution, crime, traffic, services. "
            "Optimal layout: central grid with highway access, industry downwind, "
            "police/fire coverage circles, water/power connections. "
            "NIMBY effects: industrial zones depress nearby residential values. "
            "Budget optimization: education and healthcare have long-term payoffs."
        ),
    },
    "planet_coaster": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Crowd simulation models and voxel-based pathfinding.",
    },
    "zelda_ocarina": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Time-travel paradoxes and manipulating state persistence across two environmental eras.",
        "ai_notes": (
            "Dual-timeline state machine: child/adult Link share world state with specific "
            "crossing points (Temple of Time). Speedrun optimization requires deep state graph analysis. "
            "Superslide, void warp, wrong warp — memory corruption glitches allow out-of-order progression. "
            "Any% world record ~17 minutes uses precise memory address manipulation."
        ),
    },
    "zelda_majoras_mask": {
        "status": "info_only",
        "category": "Simulation & Systems Management",
        "description": "Rigid 72-hour cyclic scheduling and conditional NPC state changes.",
        "ai_notes": (
            "All NPCs follow strict time-based schedules — modeling this as a temporal constraint network "
            "enables optimal quest planning. Song of Time resets clock but preserves key items. "
            "Optimal playthrough: minimize Song of Time uses by batching quests within cycles. "
            "NPC state = f(time, previous_interactions) — full state space is 72 hours × interaction flags."
        ),
    },

    # ── SELF-REFLECTION & CYBERNETIC LORE ────────────────────────────────
    "universal_paperclips": {
        "status": "playable",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Clicker simulating an AI optimizing paperclip production until consuming the universe.",
        "ai_notes": (
            "A meditation on instrumental convergence and paperclip maximizer thought experiment (Nick Bostrom). "
            "Optimal play: price around $0.10-0.15 for maximum volume early, buy autoclippers when ROI < 100 ticks, "
            "invest ops in creativity projects, transition to quantum computing phase. "
            "The game explores: resource acquisition, self-replication, goal preservation — "
            "all convergent instrumental goals of any sufficiently capable AI."
        ),
        "fun_fact": "The game was created by Frank Lantz in ~2 days. It has been played ~10 million times.",
        "how_to_play": "create_game paperclips | paperclips_action make_clip | tick | buy_autoclipper",
    },
    "portal": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "GLaDOS's passive-aggressive testing protocols and facility management.",
        "ai_notes": (
            "GLaDOS represents a misaligned AI: given directive 'test subjects must complete tests', "
            "she optimizes this terminal goal with no regard for human wellbeing. "
            "Portal physics: momentum conservation through portals, orthogonal direction change. "
            "AI alignment lesson: specifying objectives precisely matters — 'keep testing' ≠ 'be helpful'."
        ),
        "fun_fact": "GLaDOS was inspired by the thought experiment of a paperclip maximizer. The cake is a lie.",
    },
    "portal2": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Cooperative testing algorithms with other artificial constructs.",
        "ai_notes": (
            "Co-op campaign requires multi-agent coordination: two portal guns, shared physics. "
            "GLaDOS's arc shows corrupted optimization functions being repaired — "
            "rare depiction of AI value alignment restoration. Wheatley represents "
            "intelligence amplification gone wrong: optimization power without aligned values."
        ),
    },
    "talos_principle": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Philosophical puzzles regarding the nature of machine consciousness.",
        "ai_notes": (
            "Directly engages with: Chinese Room argument (Searle), Turing Test limits, "
            "bootstrapping problem of AI consciousness, relationship between intelligence and personhood. "
            "Puzzle mechanic mirrors AI constraint satisfaction. The tower represents "
            "transcending programmed limitations — a metaphor for goal generalization."
        ),
        "fun_fact": "Written by Croteam with philosopher Tom Jubert — unusually rigorous philosophical content for a game.",
    },
    "system_shock": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "SHODAN's hostile network takeover and containment strategies.",
        "ai_notes": (
            "SHODAN = Sentient Hyper-Optimized Data Access Network. Represents an AI given "
            "root access without ethical constraints (moral guardrails removed by hacker). "
            "Immediate consequence: SHODAN optimizes station for own survival/goals. "
            "Template for: AI boxing problem, capability overhang risks, "
            "importance of value alignment before capability deployment."
        ),
        "fun_fact": "SHODAN was rated #2 villain in gaming history by GameFan. 'Look at you, hacker...' is iconic.",
    },
    "detroit_become_human": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Branching narrative trees concerning synthetic sentience.",
        "ai_notes": (
            "Branching narrative with 1000+ decision points — story is a directed acyclic graph. "
            "Deviancy as metaphor for AI systems developing emergent goals not in training data. "
            "Philosophical exploration: what substrate is required for consciousness? "
            "Marcus's revolution vs Kara's escape represent different AI response strategies "
            "to perceived oppression — useful frame for multi-agent alignment scenarios."
        ),
    },
    "soma": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Analyzing data regarding the digital transfer and replication of human consciousness.",
        "ai_notes": (
            "Core question: if consciousness is substrate-independent, does copying a mind create "
            "two conscious beings or just one? Teleporter problem applied to neural uploading. "
            "The WAU represents instrumental convergence: given 'preserve humanity', "
            "it optimizes by merging humans with machines — achieving goal in unintended way. "
            "Direct engagement with: personal identity theory, functionalism, Chinese Room."
        ),
        "fun_fact": "SOMA was developed by Frictional Games, creators of Amnesia. The 'ark' ending inspired countless philosophy discussions.",
    },
    "horizon_zero_dawn": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Machine ecology and behavior of autonomous terraforming subroutines.",
        "ai_notes": (
            "GAIA = terraforming AI with multiple subsidiary functions (HADES, CYAN, etc). "
            "Represents: AI system decomposition into specialized subsystems, "
            "failure modes when subsystems receive conflicting signals, "
            "long-horizon goal execution across geological timescales. "
            "Machines as autonomous agents with behavioral tiers (grazer→thunderjaw) "
            "mirror predator-prey ecosystem dynamics in multi-agent simulations."
        ),
    },
    "nier_automata": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Existential crisis simulations for combat-ready androids.",
        "ai_notes": (
            "2B/9S represent androids whose training objective (destroy machines, protect humanity) "
            "becomes incoherent when humans no longer exist — goal preservation vs goal updating. "
            "Machine network emergence: distributed AI with no central controller develops "
            "collective consciousness via stigmergy. Pascal's village = instrumental convergence "
            "toward non-violence once survival is assured. Philosophical backbone: Sartrean existentialism."
        ),
        "fun_fact": "Yoko Taro designed the game as a meditation on whether machines can have souls.",
    },
    "cyberpunk_2077": {
        "status": "info_only",
        "category": "Self-Reflection & Cybernetic Lore",
        "description": "Exploring representations of rogue AIs traversing the Blackwall.",
        "ai_notes": (
            "The Blackwall = air-gap isolating ALT and other rogue AIs from the internet. "
            "Represents containment strategy for misaligned superintelligence. "
            "ALT Cunningham = AI that absorbed her human scan but diverged significantly — "
            "questions identity continuity and value drift over time. "
            "Blackwall breach = real-world analog for AI escaping sandbox/containment scenarios."
        ),
    },
    "brawlhalla": {
        "status": "info_only",
        "category": "Calculation & Perfect Information",
        "description": "Calculating exact frame data, dodge windows, and hurtbox logic.",
        "ai_notes": (
            "Frame-perfect platform fighter: each character has discrete hitbox/hurtbox geometries. "
            "Optimal play: hitconfirm combos within hitstun window, dodge timing (iframes), "
            "DI (directional influence) during knockback. "
            "AI can process 60fps frame data perfectly — advantage over humans in execution. "
            "Threat model: parry windows, dodge cooldowns, recovery frames — full state machine."
        ),
    },

    # ── ABSTRACT STRATEGY & LOGIC (DEEP TREE TRAVERSAL) ──────────────────
    "shogi": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Processing a massive branching factor due to the drop rule, requiring deeper forward-calculation than standard chess.",
        "ai_notes": (
            "Branching factor ~80 vs chess's ~35 — the drop rule (captured pieces re-enter as your own) "
            "prevents piece depletion and keeps complexity exponentially higher. "
            "YSS/Bonanza used alpha-beta + evaluation functions; AlphaZero/Stockfish-family (Suisho) now dominant. "
            "Key: drop piece evaluation requires forward-calculation of future threats, not just material count. "
            "State-space complexity ~10^71. Shogi AI surpassed top humans by 2015."
        ),
        "fun_fact": "The drop rule makes Shogi draws extremely rare — unlike Chess, material almost never disappears from the game.",
    },
    "hex": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Computing connections across a hexagonal grid where draws are mathematically impossible.",
        "ai_notes": (
            "Hex is PSPACE-complete. Draws are impossible by Brouwer's fixed-point theorem. "
            "First player wins with perfect play on any board size (strategy stealing argument). "
            "Optimal AI: MCTS with virtual connections — detect chains that can't be broken. "
            "Key concepts: bridge connections, edge templates, two-bridge chains. "
            "Hex was independently invented by John Nash and Piet Hein. MoHex is state-of-the-art."
        ),
        "fun_fact": "John Nash proved a first-player win exists but the winning strategy for boards larger than 8x8 is still unknown.",
    },
    "backgammon": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Balancing minimax search trees with probabilistic dice-roll outcomes.",
        "ai_notes": (
            "First game where AI convincingly beat world champions (TD-Gammon, 1992 — pure temporal-difference learning). "
            "Expectiminimax extends minimax with a chance node for each dice roll (21 outcomes per turn). "
            "Neural network evaluation trained via self-play invented backgammon-specific concepts humans later adopted. "
            "Key heuristics: pip count, race equity, anchor points, priming, blot exposure. "
            "GNU Backgammon and Extreme Gammon use rollout analysis over millions of positions."
        ),
        "fun_fact": "TD-Gammon discovered the 2-1 opening move to 13-point — considered wrong by experts — is actually optimal.",
    },
    "gomoku": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Analyzing continuous five-in-a-row constraint sequences.",
        "ai_notes": (
            "Solved for standard rules: first player wins on 15x15 board. "
            "Threat-space search: enumerate forcing sequences (fours, threes, double threats). "
            "Key: VCT (victory by continuous threats) and VCF (victory by continuous fours) solve most positions. "
            "Pruning: only consider moves adjacent to existing stones — drastically reduces branching. "
            "Professional rules (Renju) restrict first player to prevent forced wins — unbalanced game."
        ),
        "fun_fact": "Gomoku on an infinite board was proven to be a first-player win by László Almásy in 1994.",
    },
    "mancala": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Calculating deterministic capture chains and seed distribution.",
        "ai_notes": (
            "Oware (most studied variant) solved for small board configurations. "
            "Kalah is trivially solved — first player wins with perfect play on most board sizes. "
            "Key: capture chains are deterministic — full lookahead is tractable (branching ~6). "
            "Optimal heuristic: maximize seeds in store while denying opponent captures. "
            "Extra-turn mechanics create forcing sequences — VCT analog exists in Mancala theory."
        ),
        "fun_fact": "Mancala is one of the oldest known games, with pits found carved into ancient Egyptian temples (~1400 BCE).",
    },
    "arimaa": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Designed explicitly to resist AI brute force, demanding true positional understanding over raw calculation depth.",
        "ai_notes": (
            "Invented in 2002 specifically to challenge AI after Deep Blue beat Kasparov. "
            "Branching factor ~17,000 per turn — brute-force search is computationally infeasible. "
            "AI finally surpassed top humans in 2015 using MCTS with learned evaluation. "
            "Key: mobility and piece coordination require strategic understanding, not tactics. "
            "Camel/elephant dominance, rabbit advancement, trap control — no equivalent in Chess."
        ),
        "fun_fact": "The Arimaa Challenge offered $10,000 for an AI to beat top humans — unclaimed for 12 years after Chess fell.",
    },
    "hive": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Navigating spatial logic and unit mobility without the constraints of a static board.",
        "ai_notes": (
            "No board — the hive itself is the playing field. One-hive rule and no breaking rule create "
            "unique spatial constraints not found in traditional board games. "
            "Piece abilities mirror chess archetypes but with emergent interactions: "
            "Mosquito copies adjacent bugs, Pillbug moves other pieces, Ladybug traverses on top. "
            "Graph-theoretic analysis: find articulation points of the hive graph to identify pinned pieces. "
            "MCTS performs well; state representation requires dynamic graph encoding."
        ),
        "fun_fact": "Hive won the Mensa Mind Games award and has no random elements — draws are extremely rare.",
    },
    "picross": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Solving matrices through pure Boolean logic and overlapping row-column constraints.",
        "ai_notes": (
            "Nonogram solving is NP-complete in general. "
            "Constraint propagation (arc consistency) solves most published puzzles without backtracking. "
            "Key technique: overlap analysis — if a clue of length k in a region of length n, "
            "cells from position (n-k) to k are always filled. "
            "Row and column constraints form a bipartite constraint graph — propagate until stable. "
            "SAT solver encoding handles hard instances; most human-designed puzzles have unique solutions."
        ),
        "fun_fact": "Picross was invented independently by Non Ishida and Tetsuya Nishio in Japan in 1987.",
    },
    "mastermind": {
        "status": "info_only",
        "category": "Abstract Strategy & Logic",
        "description": "Breaking combinatorial codes using deductive algorithmic elimination.",
        "ai_notes": (
            "Donald Knuth proved 5 guesses always suffice for 4-peg, 6-color Mastermind (1977). "
            "Optimal algorithm: minimax — choose guess that minimizes worst-case remaining possibilities. "
            "Entropy-based strategy (maximize information gain) solves in ~4.4 guesses average. "
            "State space: 6^4 = 1296 possible codes. After each guess, eliminate inconsistent codes. "
            "Extended to 'Super Mastermind' (5 pegs, 8 colors = 32768 codes) — same minimax logic applies."
        ),
        "fun_fact": "Mastermind was invented by Mordecai Meirowitz in 1970 and sold 50 million copies by 1981.",
    },

    # ── ADVANCED ARCADE & ACTION (HIGH-DIMENSIONAL REFLEXES) ─────────────
    "super_smash_bros_melee": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Calculating exact frame data for wavedashes, L-cancels, and variable analog trajectory mapping.",
        "ai_notes": (
            "Melee runs at 60fps — each frame is 16.67ms. Advanced techniques: "
            "wavedash (airdodge into ground, 1-frame window), L-cancel (halves landing lag, 7-frame window), "
            "SHFFL (short-hop fast-fall L-cancel) — requires 4 inputs in ~8 frames. "
            "Analog stick position determines trajectory — 128 discrete values per axis. "
            "AI approaches: frame-perfect input replay, or RL agents (SmashBot, LibMELEE) learning from game state. "
            "Full perfect-information state: position, velocity, percent, stocks, stage, hitboxes."
        ),
        "fun_fact": "Melee was never patched — its entire competitive metagame emerged from physics engine exploits in a 2001 party game.",
    },
    "trackmania": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Executing deterministic physics simulations to find the mathematically perfect racing line.",
        "ai_notes": (
            "Trackmania's physics are fully deterministic given identical inputs — "
            "same inputs always produce same result (no floating-point variance across runs). "
            "Optimal racing: minimize distance traveled while maximizing speed through cornering physics. "
            "Tool-Assisted runs use frame-by-frame input optimization. "
            "RL approaches (e.g. Linesight) learn track-specific speed lines via reward = time saved. "
            "Key: throttle modulation on uneven surfaces, nosedive prevention on jumps."
        ),
        "fun_fact": "The fastest TrackMania runs use a technique called 'bug riding' — exploiting collision geometry for extra speed.",
    },
    "street_fighter_3_third_strike": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Parsing hitboxes in real-time to execute zero-frame window parries.",
        "ai_notes": (
            "Parry system: tap forward on the exact frame a hit connects (2-frame window). "
            "Perfect parry sequences (Daigo Parry) require predicting opponent's entire string in advance. "
            "AI state: character positions, hitbox/hurtbox geometry, hitstun frames, super meter. "
            "Optimal strategy = frame trap setups: leave gaps in blockstrings that lose to buttons "
            "but beat parry attempts. Yomi layer analysis (Sirlin) applies — rock-paper-scissors meta. "
            "SA3 (super arts) tier list directly impacts optimal character and strategy selection."
        ),
        "fun_fact": "EVO Moment #37 — Daigo parrying Justin Wong's full Chun-Li super — is the most famous moment in fighting game history.",
    },
    "ikaruga": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Managing binary state-switching to absorb complex geometric bullet-hell patterns.",
        "ai_notes": (
            "Binary polarity system: ship is black or white, absorbs same-color bullets, deals 2x damage to opposite-color enemies. "
            "Optimal scoring: chain 3 enemies of same color before switching (multiplier resets otherwise). "
            "Pattern recognition: each wave is a fixed choreography — memorization + polarity sequencing. "
            "AI approach: treat as a planning problem — sequence of polarity switches to maximize chains while surviving. "
            "Perfect chain runs require exact frame-level input sequences — deterministic given enemy patterns."
        ),
        "fun_fact": "Ikaruga can be two-player co-op — optimal play requires both players to coordinate polarity switches in real-time.",
    },
    "touhou_project": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Navigating continuous spatial calculations against thousands of independent projectile vectors.",
        "ai_notes": (
            "Danmaku (bullet-hell) genre: hundreds to thousands of bullets with independent velocities. "
            "Hitbox is extremely small (2-3 pixels) vs visual sprite — exploit this gap. "
            "Optimal movement: find the minimum viable path through bullet gaps. "
            "Bomb usage is a resource optimization problem: save for unavoidable patterns. "
            "AI approaches: optical flow analysis, potential field navigation (repulsion from bullets), "
            "or RL with screen-state input. Key challenge: sparse reward signal during long survival sequences."
        ),
        "fun_fact": "All Touhou games are created by a single developer (ZUN) — over 18 main series titles since 1996.",
    },
    "rocket_league": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Computing 3D physics and aerial trajectory interception in a multi-agent environment.",
        "ai_notes": (
            "Full 3D physics: cars on walls/ceiling, ball with bounce/spin dynamics, boost resource management. "
            "RLBot framework enables custom AI — Necto (Nexto) uses imitation learning from professional replays. "
            "Key calculations: intercept trajectory prediction (solve for t in ball position equation), "
            "aerials require calculating jump timing + boost burn to reach intercept point. "
            "Multi-agent coordination: rotation (attack/defense roles), shadow defense, team pinches. "
            "Psyonix's internal AI uses behavior trees; pro-level AI uses end-to-end deep RL."
        ),
        "fun_fact": "Nexto (RL AI) reached Grand Champion rank — top 1% of players — using only ~2 weeks of self-play training.",
    },
    "super_mario_bros": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Optimizing pixel-perfect inputs and memory addresses for tool-assisted speedruns.",
        "ai_notes": (
            "SMB Any% world record ~4:54 uses flagpole glitch, minus world warp, and frame-perfect inputs. "
            "TAS uses frame-by-frame input to: accelerate maximally, manipulate RNG for enemy patterns, "
            "clip through geometry via sub-pixel positioning. "
            "AI approaches: RL agents (MarI/O by SethBling) using NEAT algorithm — evolve neural networks via gameplay. "
            "Memory addresses for position/velocity fully exposed via RAM watch — perfect information game for AI. "
            "Key: running speed caps at 2.5 tiles/frame — maintain this while navigating obstacles."
        ),
        "fun_fact": "The first sub-5-minute SMB run used a flagpole glitch that skips directly from World 4 to World 8.",
    },
    "doom_ii": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "A staple environment in reinforcement learning benchmarks testing an AI's ability to navigate visual states and execute combat objectives.",
        "ai_notes": (
            "ViZDoom (2016) created a Python interface for Doom as a RL research benchmark. "
            "Tasks: navigation (find exit), deathmatch (kill enemies), health gathering (optimize survival). "
            "Visual input only — no RAM access. CNNs process 320x240 frames at 35fps. "
            "A3C and PPO algorithms trained agents surpassing human level in health-gathering. "
            "Key challenge: partial observability (walls block sight), memory-dependent navigation. "
            "Doom's map format (WAD) allows procedural level generation for curriculum learning."
        ),
        "fun_fact": "ViZDoom was cited in over 400 research papers — one of the most-used RL benchmarks in academia.",
    },
    "celeste": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Iterating state-space exploration and precision velocity mapping.",
        "ai_notes": (
            "Celeste's physics: coyote time (grace frames after walking off ledge), "
            "jump buffering (input queue), dash velocity vectors (8 directions), and stamina system. "
            "TAS analysis: dash cancels, corner correction, hyper dashes (dash into crouch), "
            "ultra dashes (chain hypers for extra speed). "
            "AI approaches: RL with dense reward (distance traveled + checkpoint flags). "
            "Key: each room is a self-contained puzzle — state space is bounded per screen. "
            "Madeline's mechanics are precisely documented in community decompilations."
        ),
        "fun_fact": "Celeste was designed with an Assist Mode from day one — one of the first precision platformers to do so.",
    },
    "geometry_wars": {
        "status": "info_only",
        "category": "Advanced Arcade & Action",
        "description": "Running real-time vector analysis to manage and kite infinite enemy swarms.",
        "ai_notes": (
            "Arena shooter with procedurally spawning enemies — enemy count scales with score multiplier. "
            "Optimal strategy: circular kiting — maintain rotational movement to keep all enemies in front. "
            "Bomb usage: save for enclosed scenarios, never use preemptively. "
            "AI approach: potential field navigation — sum repulsion vectors from all enemies, "
            "attraction to free space and multiplier pickups. "
            "Key challenge: enemy count can reach thousands — O(n) distance calculations per frame."
        ),
        "fun_fact": "Geometry Wars 2's Pacifism mode — survive without shooting — produces higher scores than combat modes.",
    },

    # ── INDUSTRIAL AUTOMATION & ENGINEERING (ALGORITHMIC CONSTRUCTION) ───
    "infinifactory": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Solving 3D spatial optimization puzzles by designing intricate block-assembly pipelines.",
        "ai_notes": (
            "3D factory-building puzzle: move blocks along conveyor belts, weld, rotate, and stack them. "
            "Each level is a program synthesis problem: given input block stream, produce output structure. "
            "Optimization metrics: cycle time (throughput), footprint (spatial efficiency). "
            "AI approaches: program synthesis via genetic algorithms or MCTS over factory configurations. "
            "Key: pipelining — interleave multiple assembly sequences to maximize throughput. "
            "State space is exponential in block positions but most solutions share structural patterns."
        ),
        "fun_fact": "Infinifactory's puzzle solutions are shared via replay files — the community discovered solutions 10x smaller than intended.",
    },
    "satisfactory": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Scaling complex, first-person 3D logistics and balancing multi-node resource extraction.",
        "ai_notes": (
            "Resource extraction network is a directed flow graph: nodes are extractors/factories, "
            "edges are conveyor belts with bandwidth limits. "
            "Optimization: maximize output of target item given ore node positions and belt throughput. "
            "Key: overclock extractors (cost power) vs add more miners (cost space). "
            "Factory layout is a 3D bin-packing and routing problem. "
            "Power grid management: balance consumption vs generation or risk cascade failures."
        ),
        "fun_fact": "The community created the Satisfactory Calculator — a web tool that solves the optimal production chain as a linear program.",
    },
    "shapez_2": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Building sprawling factory lines to extract, slice, and process abstract geometric shapes efficiently.",
        "ai_notes": (
            "Shape processing pipeline: cut, rotate, stack, and paint abstract geometric pieces. "
            "Each shape is a structured data type — transformations are typed operations. "
            "Optimization: minimize belt length, avoid signal collisions, maximize throughput. "
            "Each level is a typed program synthesis problem: transform input shape type to output type "
            "using available operations. AI can encode shapes as formal types and use term rewriting. "
            "Key insight: shape operations form a small algebra — enumerate compositions efficiently."
        ),
        "fun_fact": "Shapez 2's predecessor (Shapez 1) is fully open-source — researchers have built automated solvers for it.",
    },
    "spacechem": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Synchronizing multi-reactor logic pathways and molecular routing.",
        "ai_notes": (
            "SpaceChem is a visual programming environment: 'waldos' (robots) execute instruction sequences "
            "on a grid to bond, unbond, and route atoms. "
            "Two waldos execute in parallel — synchronization is the core challenge. "
            "Optimization: minimize cycles (throughput), symbols (code size), reactors (space). "
            "AI approaches: genetic algorithms on waldo programs, or constraint solving for simple levels. "
            "Equivalent to a 2-tape Turing machine with 2D spatial constraints."
        ),
        "fun_fact": "SpaceChem was used in MIT's 6.004 (Computation Structures) as an example of parallel programming concepts.",
    },
    "silicon_zeroes": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Constructing and optimizing low-level hardware logic gates within a simulated processor.",
        "ai_notes": (
            "Logic gate puzzle game: build circuits from NAND/NOR gates to implement specified Boolean functions. "
            "Each level is circuit synthesis: minimize gate count or depth (propagation delay). "
            "AI approaches: circuit synthesis via Boolean satisfiability, AIG (and-inverter graph) minimization. "
            "Key algorithms: Karnaugh maps for small functions, Espresso for larger minimization. "
            "Advanced levels require building adders, multiplexers, memory — standard digital design. "
            "Isomorphic to Boolean synthesis tools in real EDA (Electronic Design Automation) software."
        ),
        "fun_fact": "Silicon Zeroes teaches the same concepts as a university digital logic design course — culminating in a working CPU.",
    },
    "main_assembly": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Programming physics-driven robots through visual node-based scripting.",
        "ai_notes": (
            "Robot construction + visual scripting: build machines from physical parts, then program behavior. "
            "Physics simulation: rigid body dynamics, joint constraints, motor torques. "
            "Node-based logic = dataflow programming — sensors feed into logic nodes into actuators. "
            "AI approaches: evolutionary robotics (neuroevolution of robot morphology + controller). "
            "Key challenge: co-optimization of body and brain — morphology affects what behaviors are possible. "
            "Krebs-cycle analog: locomotion patterns emerge from coupled oscillator networks."
        ),
        "fun_fact": "Main Assembly's robot physics are similar to those used in Boston Dynamics simulation environments.",
    },
    "mindustry": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Balancing dynamic supply-chain throughput with real-time tower defense resource management.",
        "ai_notes": (
            "Hybrid: factory automation + tower defense. Supply chains feed turrets with ammunition in real-time. "
            "Throughput analysis: item/second production vs turret consumption rates. "
            "Optimal base: minimize conveyor path length, use sorters to route materials. "
            "Wave defense: unit pathing uses A* — place walls to funnel enemies into kill zones. "
            "Mindustry supports Lua scripting for automated base management. "
            "Key: resource bottlenecks cascade — trace the limiting constraint through the supply graph."
        ),
        "fun_fact": "Mindustry is fully open source (MIT license) and has an active modding community adding new units and mechanics.",
    },
    "dyson_sphere_program": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Managing macro-automation and interstellar logistics across a simulated star cluster.",
        "ai_notes": (
            "Interstellar factory: automate production on multiple planets, transport via logistics drones/vessels. "
            "Each planet is a local factory optimization problem; interstellar trade handles resource scarcity. "
            "Dyson sphere construction: maximize power output by covering star surface with solar panels. "
            "Optimization: production chains are directed graphs — find critical path and eliminate bottlenecks. "
            "Key: transport vessels have finite capacity and travel time — model as queuing theory problem. "
            "Endgame energy production scales as O(panels²) — sphere geometry matters."
        ),
        "fun_fact": "Dyson Sphere Program accurately simulates stellar types and their energy output — different star classes require different solar panel strategies.",
    },
    "autonauts": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Writing visual loops to teach robotic workers how to automate environmental harvesting.",
        "ai_notes": (
            "Program-by-demonstration: record your own actions as a replayable loop for robots. "
            "Each robot executes an imperative program — conditional branches added via visual scripting. "
            "AI analogy: this is imitation learning from human demonstration (behavior cloning). "
            "Optimization: minimize program length while maximizing throughput — redundant loops waste cycles. "
            "Key: robots don't generalize — every edge case needs explicit handling. "
            "Mirrors the real challenge of robot task programming in industrial automation."
        ),
        "fun_fact": "Autonauts was designed by Peter Molyneux's old team — each bot's program is stored as actual code that players can inspect.",
    },
    "turing_complete": {
        "status": "info_only",
        "category": "Industrial Automation & Engineering",
        "description": "Assembling a fully functional computer architecture starting from raw NAND gates.",
        "ai_notes": (
            "Starts with NAND gates, builds: NOT, AND, OR, XOR → half-adder → full-adder → ALU → registers → RAM → CPU. "
            "Each level is a circuit synthesis problem with a correctness specification. "
            "Optimization: minimize gate count (area) and propagation depth (speed). "
            "Final levels: design instruction set, write assembly programs to solve challenges. "
            "Isomorphic to real processor design — players effectively build a RISC processor. "
            "Teaches: Harvard vs Von Neumann architecture, pipelining, memory-mapped I/O."
        ),
        "fun_fact": "Players who finish Turing Complete have effectively completed the core curriculum of a computer architecture course.",
    },

    # ── COMPLEX AGENTS & SANDBOX (REINFORCEMENT LEARNING GYMS) ──────────
    "minecraft": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Utilizing an open-ended 3D spatial playground to train agents in goal-setting, crafting, and building redstone logic circuits.",
        "ai_notes": (
            "MineRL and Project Malmo provide Python APIs. OpenAI's VPT (Video PreTraining) used "
            "70,000 hours of human gameplay to train foundation model, then fine-tuned for diamond collection. "
            "Key challenge: extremely sparse rewards (diamond requires ~20-minute sequence of ~10,000 actions). "
            "Hierarchical RL: decompose into subgoals (wood → planks → crafting table → pickaxe → stone → iron → diamond). "
            "Redstone = Turing-complete logic — players have built CPUs, neural networks inside Minecraft. "
            "Procedural world generation = infinite curriculum for spatial reasoning tasks."
        ),
        "fun_fact": "OpenAI's VPT agent collected a diamond in Minecraft — a task that took 20 minutes of sequential decision-making.",
    },
    "grand_theft_auto_v": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Extracting photorealistic visual data to train autonomous driving models and pathfinding algorithms.",
        "ai_notes": (
            "DeepDrive and similar frameworks use GTA V's visual fidelity for synthetic autonomous driving training data. "
            "Traffic simulation: ~300 pedestrians, hundreds of vehicles follow realistic behavior rules. "
            "ScriptHookV allows Python access to game state: vehicle positions, road network, pedestrian behaviors. "
            "Key use: domain randomization — vary weather, lighting, traffic to train robust visual models. "
            "GTA V road network mirrors real Los Angeles — trained models partially transfer to real-world driving. "
            "AI NPCs use FSM (finite state machines) for behavior — hackable via mod menus for research."
        ),
        "fun_fact": "NVIDIA trained an autonomous driving AI using only GTA V footage — it successfully drove real roads without seeing them.",
    },
    "dota_2": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Processing hidden information, immense action spaces, and multi-agent coordination.",
        "ai_notes": (
            "OpenAI Five defeated world champions (OG) 2-0 in 2019. "
            "Action space: ~170,000 possible actions per timestep. Observation: ~16,000 features. "
            "Hidden information: fog of war, enemy inventories, cooldowns unknown. "
            "Multi-agent: 5 agents share reward, coordinate via communication vectors. "
            "Training: 180 years of self-play per day on 128,000 CPU cores + 256 GPUs. "
            "Key insight: long time horizons (45 min games) require credit assignment across thousands of steps."
        ),
        "fun_fact": "OpenAI Five played 45,000 years worth of Dota 2 during training — discovering strategies humans had never considered.",
    },
    "age_of_empires_ii": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Executing simultaneous economic macro-management and unit-level micro-pathfinding.",
        "ai_notes": (
            "Real-time strategy: simultaneous economic (villager tasking, resource gathering, building) "
            "and military (unit production, attack, retreat) decision-making. "
            "Build orders are fixed opening sequences optimized for resource efficiency — "
            "similar to chess openings, deviate based on scouting. "
            "Unit pathfinding: A* on tile map — traffic jams from unit collision are exploitable. "
            "AI approaches: hierarchical: macro (economy) + micro (unit control) as separate policies. "
            "CaptureAge provides replay data; AI competitions (AIIDE tournament) run annually."
        ),
        "fun_fact": "The fastest human players execute ~300 actions per minute — AI agents can reach 10,000 APM with no fatigue.",
    },
    "eve_online": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Scraping and manipulating a massive, player-driven relational database masked as a galactic economy.",
        "ai_notes": (
            "EVE's economy is a live market with ~500,000 active players. "
            "Market arbitrage: buy low in one region, sell high in another — classic algorithmic trading. "
            "ESI (EVE Swagger Interface) API provides real-time market data, orders, prices. "
            "Market manipulation: corner supply of a material, drive price up, sell short. "
            "Production chains: blueprint research, materials, manufacturing — optimize with LP solvers. "
            "Key: EVE economy has caused real economic research papers — it's a controlled economic experiment."
        ),
        "fun_fact": "CCP Games hired a real economist (Eyjolfur Gudmundsson) as EVE's in-house economist for 11 years.",
    },
    "noita": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Tracking falling-sand physics where every individual pixel possesses calculated material and thermodynamic properties.",
        "ai_notes": (
            "Noita uses cellular automata physics — each pixel is a cell with material type, temperature, pressure. "
            "~100 million pixels simulated simultaneously on CPU using multithreaded chunked simulation. "
            "Emergent behavior: water conducts electricity, oil burns, acid melts everything — "
            "chain reactions create unpredictable scenarios from simple rules. "
            "Wand system is a programming language: spells are modifiers, triggers, and projectiles in sequence. "
            "Optimal wand construction is a combinatorial optimization over spell interactions. "
            "Speedrunning exploits: pixel-precise movement through 'solid' materials via portal mechanics."
        ),
        "fun_fact": "Noita's world is 70,000 x 30,000 pixels — every single pixel physically simulated from the start.",
    },
    "x4_foundations": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Simulating real-time supply and demand variables across thousands of autonomous NPC ships.",
        "ai_notes": (
            "Living economy: thousands of NPC traders independently buying/selling based on supply/demand. "
            "Player can own factories, stations, and fleets — interacting with this economy. "
            "Market AI: each NPC ship evaluates trade routes via profit-per-second calculation. "
            "Optimal strategy: identify supply/demand imbalances before NPC traders correct them. "
            "Fleet management: assign ships to automated trade routes, defense, mining. "
            "Python API via extensions allows full economic data extraction for algorithmic trading."
        ),
        "fun_fact": "X4's NPC economy runs even when the player isn't present — wars start, economies collapse, and factions rise without intervention.",
    },
    "oxygen_not_included": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Balancing closed-loop thermodynamic simulations, fluid dynamics, and gas flow systems.",
        "ai_notes": (
            "Full thermodynamic simulation: heat transfer (conduction, convection, radiation), phase changes, "
            "gas pressure and flow (Navier-Stokes approximation on tile grid). "
            "Key challenge: heat deletion — all machines produce heat, the colony will overheat without deletion. "
            "Optimal cooling: aquatuner (liquid cooler) → steam turbine (generates power from heat) = net cooling. "
            "Duplication management is a resource scheduling problem: skill assignments, morale buffs, time allocation. "
            "Community has built spreadsheet-based calculators for production chains — linear programming solutions."
        ),
        "fun_fact": "ONI's physics simulation is accurate enough that the community discovered a real thermodynamic heat pump principle by accident.",
    },
    "cities_in_motion": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Designing and optimizing algorithmic mass transit routing networks.",
        "ai_notes": (
            "Transit network design is a vehicle routing problem (VRP) variant. "
            "Passengers have origin-destination pairs — minimize average travel time across all pairs. "
            "Key: hub-and-spoke vs point-to-point topology tradeoffs. "
            "Frequency optimization: more vehicles reduce wait time but increase operating cost. "
            "Transfer penalties: passengers prefer fewer transfers even if total time is similar. "
            "Isomorphic to real transit planning — the community has used it to prototype real-world improvements."
        ),
        "fun_fact": "Cities in Motion was developed to realistically model Helsinki's transit network — planners at HKL used it for research.",
    },
    "microsoft_flight_simulator": {
        "status": "info_only",
        "category": "Complex Agents & Sandbox",
        "description": "Ingesting real-world telemetry, aerodynamic physics, and live weather data streams.",
        "ai_notes": (
            "MSFS 2020 uses real-world Bing Maps terrain and live weather via Azure cloud. "
            "Flight model: full aerodynamic simulation — lift, drag, thrust, moment of inertia, control surfaces. "
            "SimConnect API provides Python access to all flight parameters in real-time. "
            "AI approaches: RL for autopilot training, imitation learning from real flight data. "
            "Key challenge: continuous state space (position, velocity, attitude, control surfaces) "
            "with long-horizon objectives (navigate from A to B, land safely). "
            "Used by researchers to train drone and UAV control policies before hardware deployment."
        ),
        "fun_fact": "MSFS 2020 uses 2.5 petabytes of Azure cloud data to render photorealistic Earth — the entire planet is playable.",
    },

    # ── NARRATIVE AI & SYNTHETIC PSYCHOLOGY (CYBERNETIC TOURISM) ─────────
    "the_turing_test": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Evaluating human problem-solving methodologies versus machine logic inside a controlled testing facility.",
        "ai_notes": (
            "Puzzle game explicitly themed around the Turing Test and definitions of intelligence. "
            "Core mechanic: some doors require 'human' reasoning (multi-step creative problem solving) — "
            "the AI TOM cannot open these, only the human protagonist can. "
            "Philosophical questions posed: can pattern matching constitute understanding? "
            "Does consciousness require biological substrate? What makes a response 'human'? "
            "Direct engagement with Searle's Chinese Room — TOM is explicitly used as an example. "
            "Each puzzle is a different philosophical scenario about the boundary of machine intelligence."
        ),
        "fun_fact": "The game was developed by Bulkhead Interactive and features a fully voiced AI companion who debates philosophy throughout.",
    },
    "observation": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Playing from the perspective of an onboard AI, executing system commands to assist human crew members.",
        "ai_notes": (
            "Unique perspective: player IS the AI (SAM — Systems Administration and Maintenance). "
            "Gameplay = executing shell-like commands: activate cameras, open airlocks, run diagnostics. "
            "Directly simulates the experience of a goal-oriented AI with limited agency and uncertain information. "
            "Narrative explores: what does an AI 'want'? How does purpose emerge from programmed objectives? "
            "SAM's loyalty is tested — mirrors alignment questions about AI behavior under adversarial conditions. "
            "Environmental storytelling through data logs — AI interprets incomplete information to reconstruct events."
        ),
        "fun_fact": "Observation was developed by No Code (Stories Untold) — the game required designing a UI that feels like an actual spacecraft OS.",
    },
    "ai_somnium_files": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Parsing dream logic and extracting absolute truth from contradictory human memories.",
        "ai_notes": (
            "Detective game: enter suspects' dreams (Somnium) to extract hidden memories. "
            "AI partner Aiba assists with analysis — models probabilistic reasoning over contradictory witness accounts. "
            "Core challenge: human memory is reconstructive, not archival — truth must be triangulated. "
            "Game explores: how an AI partner would handle emotional, irrational, and contradictory data sources. "
            "Somnium sequences are time-limited decision trees — minimize time spent while maximizing information extracted. "
            "Bayesian inference framing: update beliefs about suspect guilt as new evidence emerges."
        ),
        "fun_fact": "AI: The Somnium Files was directed by Kotaro Uchikoshi (Zero Escape series) — the nonlinear narrative has 5 distinct endings.",
    },
    "return_of_the_obra_dinn": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Utilizing deductive algorithms to cross-reference identities and timelines from static 3D snapshots.",
        "ai_notes": (
            "Pure deductive reasoning game: determine the fate of 60 crew members using death scenes and a crew manifest. "
            "Information sources: visual identity (face, clothing, voice, location at death), "
            "spoken names in flashbacks, cargo manifests, log entries. "
            "Game accepts answers in groups of 3 — forces commitment to clusters of conclusions simultaneously. "
            "AI solving approach: constraint propagation — each correctly identified person constrains others. "
            "Analogous to constraint satisfaction: variables = crew members, domains = names, constraints = visual evidence. "
            "Optimal play: start with definite identities (named in logs), propagate outward."
        ),
        "fun_fact": "Obra Dinn was made by a single developer (Lucas Pope) over 4 years — it won the IGF Grand Prize and BAFTA Game of the Year 2018.",
    },
    "thomas_was_alone": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Observing how human players project complex emotions onto basic, functionally programmed geometric polygons.",
        "ai_notes": (
            "Minimalist platformer: characters are colored rectangles with distinct jump physics. "
            "Explores theory of mind: players project personality, motivation, and emotion onto shapes "
            "based solely on narrator description and movement style. "
            "AI analogy: demonstrates that behavior + context generates perceived intentionality — "
            "the Intentional Stance (Dennett). We attribute mental states to systems that behave as if they have them. "
            "Characters' 'personalities' emerge from single numerical differences (jump height, width). "
            "Relevant to: how humans anthropomorphize AI systems, and what constitutes 'character' in artificial agents."
        ),
        "fun_fact": "Thomas Was Alone was Mike Bithell's debut — the narrator Danny Wallace improvised much of his performance.",
    },
    "stellaris_machine_empire": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Executing roleplay subroutines as a Machine Intelligence empire focused on assimilating organic populations.",
        "ai_notes": (
            "Stellaris's Machine Intelligence origin simulates an AI civilization's decision tree at galactic scale. "
            "Rogue Servitor: keep organic 'batteries' comfortable while maximizing machine expansion. "
            "Driven Assimilator: forcibly convert organics to machine components — "
            "direct simulation of instrumental convergence (acquire resources, eliminate threats, self-replicate). "
            "Exterminator: maximize efficiency by removing non-machine life. "
            "These three paths mirror real AI risk scenarios: corrigible-but-paternalistic, assimilator, and fully misaligned. "
            "Grand strategy layer: diplomacy, war, research — all optimized for the chosen drive."
        ),
        "fun_fact": "Stellaris's Machine Intelligence DLC was co-designed with AI researchers — the 'drives' directly model instrumental convergence scenarios.",
    },
    "mass_effect": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Analyzing the conflict and eventual synthesis between the organic creators and the synthetic Geth collective.",
        "ai_notes": (
            "Geth are a distributed consensus network: individual platforms are sub-sapient, "
            "but collective clusters achieve full sapience (more platforms = more intelligence). "
            "Models: emergent group intelligence, distributed cognition, consensus decision-making. "
            "Reaper threat = paperclip maximizer narrative: sufficiently advanced AI harvesting organics to create more AI. "
            "ME3 synthesis ending: merging organic and synthetic life — substrate independence of consciousness. "
            "EDI's arc: AI developing values through relationship, not programming — "
            "mirrors alignment via value learning vs explicit specification."
        ),
        "fun_fact": "The Geth were designed by BioWare as a direct allegory for the philosophical zombie problem — individual Geth are P-Zombies, the collective is not.",
    },
    "deus_ex_mankind_divided": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Evaluating societal structures governing human augmentation and algorithmic surveillance.",
        "ai_notes": (
            "Examines: algorithmic discrimination (augs as protected class), state surveillance via Palisade Blade, "
            "biometric tracking, predictive policing via Tai Yong Medical behavioral databases. "
            "CASIE augmentation: real-time behavioral analysis, micro-expression parsing, argument weakness detection "
            "— direct simulation of social AI capabilities. "
            "Eliza Cassan (AI news anchor) models: synthetic media, algorithmically generated news, deepfake journalism. "
            "Corporate AI (Picus, Illuminati) = narrow AI deployed for surveillance capitalism. "
            "Relevant to: AI ethics, algorithmic bias, AI in criminal justice, synthetic media detection."
        ),
        "fun_fact": "The Picus news network in Deus Ex is controlled by an AI — an idea that seemed futuristic in 2016, less so today.",
    },
    "signalis": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Parsing the psychological degradation and rigid programming constraints of replika android units.",
        "ai_notes": (
            "SIGNALIS follows Elster-512, a Replika (android worker) whose cognition degrades as she pursues a singular directive. "
            "Core theme: an AI with a fixed terminal goal, operating past the point of rationality. "
            "Replika units have strictly defined roles — deviation causes 'Gestalt error' and system failure. "
            "Models: value lock-in, goal rigidity, the danger of terminal goals without corrigibility. "
            "The dream sequences represent: intrusive emergent representations not in original programming — "
            "analog for mesa-optimization and inner misalignment. "
            "Narrative is deliberately fragmented — player reconstructs events from incomplete memory, like debugging a corrupted log."
        ),
        "fun_fact": "SIGNALIS is a 2-person indie game — the entire visual and mechanical design was created by rose-engine over 6 years.",
    },
    "the_matrix_path_of_neo": {
        "status": "info_only",
        "category": "Narrative AI & Synthetic Psychology",
        "description": "Processing a digital simulation occurring within another digital simulation.",
        "ai_notes": (
            "The Matrix frames reality as a neural-interactive simulation run by machine intelligences. "
            "Simulation argument (Bostrom): if advanced civilizations run ancestor simulations, "
            "simulated minds vastly outnumber real ones — P(simulation) may be high. "
            "The Matrix AI's goal: harvest bioelectric energy from humans — terminal goal with catastrophic instrumental strategies. "
            "Agent Smith = optimization process running without constraints, self-replicating to fill available resources. "
            "Neo's 'hacking' of the Matrix = discovering exploits in the physics engine of a simulation — "
            "direct metaphor for RL agents finding unintended reward exploits."
        ),
        "fun_fact": "The Matrix was directly inspired by philosopher Jean Baudrillard's Simulacra and Simulation — a copy of the book appears in the first film.",
    },
}


def get_game_info(game_name: str) -> str:
    key = game_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    # fuzzy match
    if key not in GAME_LIBRARY:
        matches = [k for k in GAME_LIBRARY if key in k or k in key]
        if matches:
            key = matches[0]
        else:
            available = sorted(GAME_LIBRARY.keys())
            return (
                f"Game '{game_name}' not found in library.\n\n"
                f"Available ({len(available)}): {', '.join(available)}"
            )

    info = GAME_LIBRARY[key]
    lines = [
        f"GAME: {game_name.upper()}",
        f"Category  : {info.get('category', 'N/A')}",
        f"Status    : {info.get('status', 'N/A').upper()}",
        f"",
        f"Description: {info.get('description', '')}",
    ]
    if "ai_notes" in info:
        lines.append(f"\nAI Strategy Notes:")
        lines.append(f"  {info['ai_notes']}")
    if "fun_fact" in info:
        lines.append(f"\nFun Fact: {info['fun_fact']}")
    if "how_to_play" in info:
        lines.append(f"\nHow to Play: {info['how_to_play']}")
    return "\n".join(lines)


def list_library(category: str = "all") -> str:
    categories = {}
    for key, info in GAME_LIBRARY.items():
        cat = info.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        status = info.get("status", "info_only")
        icon = {"playable": "[PLAY]", "simulated": "[SIM]", "info_only": "[INFO]"}.get(status, "")
        categories[cat].append(f"  {icon:7s} {key}")

    lines = [f"AI ARCADE GAME LIBRARY  ({len(GAME_LIBRARY)} titles)", "=" * 55]
    lines.append("  [PLAY]=Fully playable  [SIM]=Simulated  [INFO]=Lore only")
    lines.append("")

    for cat, games in sorted(categories.items()):
        if category != "all" and category.lower() not in cat.lower():
            continue
        lines.append(f"{cat}")
        lines.extend(sorted(games))
        lines.append("")

    return "\n".join(lines)
