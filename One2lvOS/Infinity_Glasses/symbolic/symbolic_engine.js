// Symbolic Transformation Engine
// ~ | π √ ∆ v =
class SymbolicEngine {
    constructor() {
        this.operators = {
            '~': { name: 'wave', description: 'oscillation / passing motion', precedence: 1 },
            '|': { name: 'axis', description: 'stake / fixed reference / boundary', precedence: 2 },
            'π': { name: 'disc', description: 'rotation / curved plane / orbit', precedence: 3 },
            '√': { name: 'root', description: 'base magnitude / extracted foundation', precedence: 4 },
            '∆': { name: 'delta', description: 'change / transformation / gradient', precedence: 5 },
            'v': { name: 'vector', description: 'velocity vector / directed motion', precedence: 6 },
            '=': { name: 'resolution', description: 'resolved state / outcome', precedence: 7 },
            '•': { name: 'coupling', description: 'interaction node / point contact', precedence: 3 },
            '³': { name: 'cubic', description: '3D amplification / volumetric expansion', precedence: 8 },
            '⁹': { name: 'ninth', description: 'high-order / intensified transformation', precedence: 8 },
            '+': { name: 'add', description: 'amplification / increase', precedence: 4 },
            '-': { name: 'subtract', description: 'attenuation / compression', precedence: 4 }
        };

        this.transformHistory = [];
    }

    parse(expression) {
        const tokens = [];
        let currentToken = '';

        for (const char of expression) {
            if (this.operators[char]) {
                if (currentToken) {
                    tokens.push({ type: 'operand', value: currentToken });
                    currentToken = '';
                }
                tokens.push({ type: 'operator', value: char, ...this.operators[char] });
            } else if (char === ' ') {
                if (currentToken) {
                    tokens.push({ type: 'operand', value: currentToken });
                    currentToken = '';
                }
            } else {
                currentToken += char;
            }
        }

        if (currentToken) {
            tokens.push({ type: 'operand', value: currentToken });
        }

        return tokens;
    }

    transform(expression) {
        const tokens = this.parse(expression);

        const pipeline = [];
        let state = { value: 0, phase: 'init' };

        tokens.forEach((token, index) => {
            if (token.type === 'operator') {
                const step = this.applyOperator(token, state);
                pipeline.push(step);
                state = step.newState;
            }
        });

        const result = {
            expression: expression,
            tokens: tokens,
            pipeline: pipeline,
            finalState: state,
            symbolic: this.generateSymbolicResult(expression),
            timestamp: Date.now()
        };

        this.transformHistory.push(result);

        return result;
    }

    applyOperator(token, currentState) {
        let newState = { ...currentState };

        switch (token.value) {
            case '~':
                // Wave - introduce oscillation
                newState.value = Math.sin(currentState.value || 0);
                newState.phase = 'oscillating';
                break;

            case '|':
                // Axis - fixed reference point
                newState.value = 0;
                newState.phase = 'centered';
                break;

            case 'π':
                // Disc - rotational transform
                newState.value = currentState.value * Math.PI;
                newState.phase = 'rotating';
                break;

            case '√':
                // Root - extract base magnitude
                newState.value = Math.sqrt(Math.abs(currentState.value || 0));
                newState.phase = 'extracted';
                break;

            case '∆':
                // Delta - apply change
                newState.value = currentState.value + (Math.random() - 0.5);
                newState.phase = 'transforming';
                break;

            case 'v':
                // Vector - directional motion
                newState.value = currentState.value * 1.5;
                newState.phase = 'vectorized';
                break;

            case '=':
                // Resolution - finalize
                newState.value = Math.round(currentState.value * 1000) / 1000;
                newState.phase = 'resolved';
                break;

            case '•':
                // Coupling - multiply
                newState.value = currentState.value * 2;
                newState.phase = 'coupled';
                break;

            case '³':
                // Cubic - volumetric expansion
                newState.value = Math.pow(currentState.value || 1, 3);
                newState.phase = 'expanded';
                break;

            case '⁹':
                // Ninth power - high-order transform
                newState.value = Math.pow(currentState.value || 1, 9);
                newState.phase = 'intensified';
                break;

            case '+':
                // Add - amplification
                newState.value = currentState.value + 1;
                newState.phase = 'amplified';
                break;

            case '-':
                // Subtract - attenuation
                newState.value = currentState.value - 1;
                newState.phase = 'attenuated';
                break;
        }

        return {
            operator: token,
            previousState: currentState,
            newState: newState,
            description: `${token.name}: ${token.description}`
        };
    }

    generateSymbolicResult(expression) {
        // Generate a symbolic interpretation
        const hash = this.hashString(expression);
        const value = (hash % 10000) / 1000;

        return {
            numeric: value,
            symbolic: expression,
            interpretation: this.interpretExpression(expression)
        };
    }

    interpretExpression(expression) {
        const interpretations = {
            '~ | π √ =': 'Wave through axis → disc rotation → root extraction → resolution',
            '~ | π √ ∆ v =': 'Full transformation: oscillation → reference → rotation → extraction → change → vector → result',
            '~ | π': 'Oscillating disc rotation',
            '√ ∆ v': 'Root extraction → transformation → vectorization',
            '| π': 'Axial rotation',
            '∆⁹v': 'High-order transformation with velocity'
        };

        return interpretations[expression] || 'Custom symbolic transformation';
    }

    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash);
    }

    getHistory(limit = 10) {
        return this.transformHistory.slice(-limit);
    }

    clearHistory() {
        this.transformHistory = [];
    }

    getOperators() {
        return Object.entries(this.operators).map(([symbol, data]) => ({
            symbol: symbol,
            ...data
        }));
    }

    visualizePipeline(expression) {
        const result = this.transform(expression);
        let visual = 'Transformation Pipeline:\n\n';

        result.pipeline.forEach((step, index) => {
            visual += `Step ${index + 1}: ${step.operator.value} (${step.operator.name})\n`;
            visual += `  ${step.description}\n`;
            visual += `  ${step.previousState.value.toFixed(4)} → ${step.newState.value.toFixed(4)}\n`;
            visual += `  Phase: ${step.previousState.phase} → ${step.newState.phase}\n\n`;
        });

        visual += `Final Result: ${result.finalState.value.toFixed(4)} (${result.finalState.phase})`;

        return visual;
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SymbolicEngine;
}