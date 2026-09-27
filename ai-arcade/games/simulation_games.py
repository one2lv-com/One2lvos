"""
Simplified Simulation Games: Factory builders, City management, Space games
"""
from typing import List, Optional, Dict, Tuple
import random


# ============================================================
# FACTORIO-STYLE - Resource automation
# ============================================================

def make_factorio() -> Dict:
    """Create simplified Factorio game"""
    return {
        'resources': {
            'iron_ore': 100,
            'copper_ore': 100,
            'coal': 50,
            'iron_plate': 0,
            'copper_plate': 0,
            'circuits': 0,
            'power': 10
        },
        'buildings': {
            'furnaces': 0,
            'assemblers': 0,
            'miners': 2
        },
        'production_rate': 1.0,
        'tick': 0,
        'goal_circuits': 100
    }


def factorio_str(state: Dict) -> str:
    """Display factory state"""
    r = state['resources']
    b = state['buildings']

    lines = ['   FACTORY AUTOMATION']
    lines.append('   ' + '=' * 40)
    lines.append('\n   RESOURCES:')
    lines.append(f"   Iron Ore: {r['iron_ore']:<6} Copper Ore: {r['copper_ore']:<6} Coal: {r['coal']}")
    lines.append(f"   Iron Plate: {r['iron_plate']:<4} Copper Plate: {r['copper_plate']:<4}")
    lines.append(f"   Circuits: {r['circuits']:<4}  Power: {r['power']}")

    lines.append('\n   BUILDINGS:')
    lines.append(f"   Miners: {b['miners']}  Furnaces: {b['furnaces']}  Assemblers: {b['assemblers']}")

    lines.append('\n   COMMANDS:')
    lines.append('   mine - Extract raw resources')
    lines.append('   build furnace - Smelt ore into plates (cost: 10 iron ore)')
    lines.append('   build assembler - Craft circuits (cost: 10 iron plate)')
    lines.append('   produce - Run production cycle')

    goal = state['goal_circuits']
    lines.append(f'\n   GOAL: Produce {goal} circuits | Current: {r["circuits"]}/{goal}')

    return '\n'.join(lines)


# ============================================================
# CITY BUILDER - Population & Resources
# ============================================================

def make_city_builder() -> Dict:
    """Create simplified city builder"""
    return {
        'population': 100,
        'happiness': 50,
        'food': 100,
        'water': 100,
        'power': 50,
        'buildings': {
            'houses': 2,
            'farms': 1,
            'wells': 1,
            'power_plants': 1
        },
        'money': 1000,
        'turn': 0
    }


def city_builder_str(state: Dict) -> str:
    """Display city state"""
    lines = ['   CITY MANAGEMENT SIMULATOR']
    lines.append('   ' + '=' * 40)
    lines.append(f'\n   Population: {state["population"]}  Happiness: {state["happiness"]}%')
    lines.append(f'   Money: ${state["money"]}')

    lines.append('\n   RESOURCES:')
    lines.append(f'   Food: {state["food"]}  Water: {state["water"]}  Power: {state["power"]}')

    lines.append('\n   BUILDINGS:')
    b = state['buildings']
    lines.append(f'   Houses: {b["houses"]}  Farms: {b["farms"]}  Wells: {b["wells"]}  Power Plants: {b["power_plants"]}')

    lines.append('\n   COMMANDS:')
    lines.append('   build house ($500) - Increase pop capacity')
    lines.append('   build farm ($300) - Produce +50 food/turn')
    lines.append('   build well ($200) - Produce +50 water/turn')
    lines.append('   build power ($800) - Produce +100 power/turn')
    lines.append('   next - Advance to next turn')

    lines.append(f'\n   Turn: {state["turn"]}')
    return '\n'.join(lines)


def city_builder_turn(state: Dict) -> str:
    """Process city turn"""
    # Production
    state['food'] += state['buildings']['farms'] * 50
    state['water'] += state['buildings']['wells'] * 50
    state['power'] += state['buildings']['power_plants'] * 100

    # Consumption
    pop = state['population']
    state['food'] -= pop * 1
    state['water'] -= pop * 1
    state['power'] -= pop * 0.5

    # Check shortages
    if state['food'] < 0:
        state['happiness'] -= 20
        state['food'] = 0
    if state['water'] < 0:
        state['happiness'] -= 20
        state['water'] = 0
    if state['power'] < 0:
        state['happiness'] -= 10
        state['power'] = 0

    # Population growth
    if state['happiness'] > 60 and state['food'] > 50 and state['water'] > 50:
        state['population'] += int(state['population'] * 0.05)

    # Income
    state['money'] += state['population'] * 2

    state['turn'] += 1

    return f"Turn {state['turn']} complete. Pop: {state['population']}, Happiness: {state['happiness']}%"


# ============================================================
# SPACE MINING - Resource gathering in space
# ============================================================

def make_space_mining() -> Dict:
    """Create space mining game"""
    return {
        'ship_position': 0,
        'fuel': 100,
        'cargo': {
            'iron': 0,
            'gold': 0,
            'platinum': 0,
            'tritium': 0
        },
        'cargo_capacity': 100,
        'credits': 500,
        'asteroids': [
            {'pos': 5, 'resources': {'iron': 50}},
            {'pos': 12, 'resources': {'gold': 20}},
            {'pos': 20, 'resources': {'platinum': 10}},
            {'pos': 30, 'resources': {'tritium': 5}}
        ]
    }


def space_mining_str(state: Dict) -> str:
    """Display space mining state"""
    lines = ['   SPACE MINING OPERATIONS']
    lines.append('   ' + '=' * 50)
    lines.append(f'\n   Ship Position: Sector {state["ship_position"]}')
    lines.append(f'   Fuel: {state["fuel"]}  Credits: {state["credits"]}')

    cargo_used = sum(state['cargo'].values())
    lines.append(f'\n   CARGO ({cargo_used}/{state["cargo_capacity"]}):')
    for resource, amount in state['cargo'].items():
        if amount > 0:
            lines.append(f'   {resource.capitalize()}: {amount}')

    lines.append('\n   NEARBY ASTEROIDS:')
    for ast in state['asteroids']:
        if abs(ast['pos'] - state['ship_position']) <= 5:
            resources = ', '.join([f"{k}:{v}" for k, v in ast['resources'].items()])
            lines.append(f'   Sector {ast["pos"]}: {resources}')

    lines.append('\n   COMMANDS:')
    lines.append('   move <sector> - Travel to sector (costs fuel)')
    lines.append('   mine - Mine asteroid at current position')
    lines.append('   sell - Sell cargo at station (position 0)')
    lines.append('   refuel - Buy fuel (at position 0)')

    return '\n'.join(lines)


# ============================================================
# LOGIC CIRCUIT BUILDER - Build circuits from gates
# ============================================================

def make_circuit_builder() -> Dict:
    """Create logic circuit builder"""
    return {
        'gates': [],
        'inputs': {'A': 0, 'B': 0},
        'target_function': 'XOR',  # Target to build
        'tests_passed': 0
    }


def circuit_builder_str(state: Dict) -> str:
    """Display circuit builder"""
    lines = ['   LOGIC CIRCUIT BUILDER']
    lines.append('   ' + '=' * 40)
    lines.append(f'\n   Target: Build {state["target_function"]} gate')

    lines.append('\n   INPUTS:')
    lines.append(f'   A={state["inputs"]["A"]}  B={state["inputs"]["B"]}')

    lines.append('\n   CIRCUIT:')
    if state['gates']:
        for i, gate in enumerate(state['gates']):
            lines.append(f'   {i+1}. {gate["type"]}({gate["inputs"]})')
    else:
        lines.append('   (empty)')

    lines.append('\n   AVAILABLE GATES:')
    lines.append('   AND, OR, NOT, NAND, NOR, XOR')

    lines.append('\n   COMMANDS:')
    lines.append('   add AND A B - Add AND gate with inputs A and B')
    lines.append('   add NOT A - Add NOT gate')
    lines.append('   set A 1 - Set input A to 1')
    lines.append('   test - Test circuit against all inputs')
    lines.append('   clear - Clear circuit')

    return '\n'.join(lines)


# ============================================================
# TERRAFORM - Planet colonization
# ============================================================

def make_terraform() -> Dict:
    """Create terraform game"""
    return {
        'planet_name': 'Mars-Alpha',
        'atmosphere': {
            'oxygen': 5,
            'temperature': -60,
            'pressure': 0.1
        },
        'terrain': {
            'water': 0,
            'vegetation': 0,
            'cities': 0
        },
        'resources': {
            'energy': 1000,
            'minerals': 500,
            'population': 100
        },
        'turn': 0,
        'goal': {'oxygen': 20, 'temperature': 15, 'pressure': 1.0}
    }


def terraform_str(state: Dict) -> str:
    """Display terraform state"""
    lines = [f'   TERRAFORM: {state["planet_name"]}']
    lines.append('   ' + '=' * 50)

    a = state['atmosphere']
    goal = state['goal']
    lines.append('\n   ATMOSPHERE:')
    lines.append(f'   Oxygen: {a["oxygen"]}% (goal: {goal["oxygen"]}%)')
    lines.append(f'   Temperature: {a["temperature"]}°C (goal: {goal["temperature"]}°C)')
    lines.append(f'   Pressure: {a["pressure"]} atm (goal: {goal["pressure"]} atm)')

    t = state['terrain']
    lines.append('\n   TERRAIN:')
    lines.append(f'   Water Coverage: {t["water"]}%')
    lines.append(f'   Vegetation: {t["vegetation"]}%')
    lines.append(f'   Cities: {t["cities"]}')

    r = state['resources']
    lines.append('\n   RESOURCES:')
    lines.append(f'   Energy: {r["energy"]}')
    lines.append(f'   Minerals: {r["minerals"]}')
    lines.append(f'   Population: {r["population"]}')

    lines.append('\n   ACTIONS:')
    lines.append('   build greenhouse - Increase O2 (cost: 200 energy)')
    lines.append('   build heater - Increase temp (cost: 300 energy)')
    lines.append('   build compressor - Increase pressure (cost: 250 energy)')
    lines.append('   build water pump - Add water (cost: 150 energy, 100 minerals)')
    lines.append('   next - Advance turn')

    lines.append(f'\n   Turn: {state["turn"]}')

    # Check if terraformed
    if (a["oxygen"] >= goal["oxygen"] and
        a["temperature"] >= goal["temperature"] and
        a["pressure"] >= goal["pressure"]):
        lines.append('\n   *** PLANET TERRAFORMED! ***')

    return '\n'.join(lines)
