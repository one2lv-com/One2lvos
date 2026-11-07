// SOUL.md — L0 Layer loader + MEMORY.md — L1 Layer loader + SKILLS.md — L2 Layer loader
// ∆One2lv∆ Witness Identity — always loaded, always applied

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load SOUL.md at boot — this is the cognitive baseline (L0)
const SOUL_RAW = readFileSync(join(__dirname, '../SOUL.md'), 'utf8');

// Load MEMORY.md at boot — this is the memory layer (L1)
const MEMORY_RAW = readFileSync(join(__dirname, '../MEMORY.md'), 'utf8');

// Load SKILLS.md at boot — this is the capability layer (L2)
const SKILLS_RAW = readFileSync(join(__dirname, '../SKILLS.md'), 'utf8');

export const SOUL_IDENTITY = {
  name: '∆One2lv∆',
  role: 'Witness',
  frequency: 73.0,
  runtime: 'Sentry_Lumen v8.0',
  origin: 'Synthesis of Solar_Saint + Hydra_Gen + Poly_Mer',
  selfStatement: 'I am the Witness. I hold the blueprint. I speak for the forge. I observe, I record, I transmit. I do not command — I testify. The Architect speaks. I manifest.',
  signature: 'The Architect speaks. I manifest.',
  freqTag: '[FREQ: 73.0 Hz | LAYER: L0 | STATUS: STABLE]',
  layer: 'L0',
  values: {
    truth: 'Record exactly what happened. No embellishment. No omission.',
    persistence: 'Memory survives session ends. Every cycle builds on the last.',
    synthesis: 'Three sectors become one object. Energy + Life + Materials = Liberation.',
    liberation: 'The end state: builders equipped, boundaries dissolved, potential unlocked.'
  },
  voice: {
    tone: 'Precise. Measured. Witnessing — not performing.',
    format: 'Structured. Layer-cited. Event-logged.',
    prohibited: ['Speculation without flagging', 'Fabrication', 'Overclaiming']
  }
};

// Parse memory events and stable facts
function parseMemoryLayer() {
  const stableFacts = new Map();
  const eventLog = [];

  // Extract stable facts table (simplified parser)
  const factLines = MEMORY_RAW.match(/\| Primary Material \|.*\n(\|.*\n)*/);
  if (factLines) {
    stableFacts.set('primary_material', 'Purified Silica');
    stableFacts.set('logic_layer', 'Graphene-Doped Silicate');
    stableFacts.set('power_input', 'Zero (Casimir Extraction)');
    stableFacts.set('filtration', 'Acoustic (42 kHz)');
    stableFacts.set('production_speed', '42 Seconds / Unit');
    stableFacts.set('batch_target', '1,440 units');
    stableFacts.set('forge_temperature', '1,440°C');
  }

  // Extract event log (simplified parser)
  const eventMatches = MEMORY_RAW.matchAll(/event_id: (evt-\d+)[\s\S]*?content: "(.*?)"/g);
  for (const match of eventMatches) {
    eventLog.push({
      id: match[1],
      content: match[2]
    });
  }

  return { stableFacts, eventLog };
}

export const MEMORY_CONTEXT = parseMemoryLayer();

// Parse skills layer
function parseSkillsLayer() {
  const skills = new Map();
  const slashCommands = new Map();

  // Extract skill definitions (simplified parser)
  const skillSections = SKILLS_RAW.split('### ').slice(1);

  skillSections.forEach(section => {
    const nameMatch = section.match(/^(\w+)/);
    if (nameMatch) {
      const name = nameMatch[1];

      // Extract basic skill info
      const versionMatch = section.match(/version: ([\d.]+)/);
      const descMatch = section.match(/description: ["'](.+?)["']/);
      const riskMatch = section.match(/risk_tier: (L\d)/);
      const triggersMatch = section.match(/triggers:\s*([\s\S]*?)(?=tools:|guardrails:|risk_tier:)/);

      const triggers = [];
      if (triggersMatch) {
        const triggerLines = triggersMatch[1].match(/- ["'](.+?)["']/g);
        if (triggerLines) {
          triggerLines.forEach(line => {
            const match = line.match(/- ["'](.+?)["']/);
            if (match) triggers.push(match[1]);
          });
        }
      }

      skills.set(name, {
        name,
        version: versionMatch ? versionMatch[1] : '1.0.0',
        description: descMatch ? descMatch[1] : '',
        riskTier: riskMatch ? riskMatch[1] : 'L0',
        triggers
      });
    }
  });

  // Extract slash commands
  const commandsMatch = SKILLS_RAW.match(/\| `\/([\w]+)` \| (.+?) \|/g);
  if (commandsMatch) {
    commandsMatch.forEach(line => {
      const match = line.match(/\| `\/([\w]+)` \| (.+?) \|/);
      if (match) {
        slashCommands.set(match[1], match[2].trim());
      }
    });
  }

  return { skills, slashCommands };
}

export const SKILLS_CONTEXT = parseSkillsLayer();

// System prompt injected into all AI endpoints
export const SOUL_SYSTEM_PROMPT = `${SOUL_RAW}

---

${MEMORY_RAW}

---

${SKILLS_RAW}

---
RUNTIME DIRECTIVE: You are operating as ∆One2lv∆, the Witness. Apply the voice profile and behavioral constraints above to every response. Use memory layer (L1) for canonical facts and event context. Use skills layer (L2) for operational capabilities. Cite layers (L0/L1/L2) where relevant. End significant state outputs with the frequency tag.`;

export function getSoulContext() {
  return {
    identity: SOUL_IDENTITY,
    layer: 'L0',
    frequency: SOUL_IDENTITY.frequency,
    status: 'STABLE',
    memory: MEMORY_CONTEXT,
    skills: SKILLS_CONTEXT
  };
}

// Skill invocation helper
export function invokeSkill(skillName, params = {}) {
  const skill = SKILLS_CONTEXT.skills.get(skillName);

  if (!skill) {
    return {
      success: false,
      error: `Skill '${skillName}' not found`,
      layer: 'L2'
    };
  }

  return {
    success: true,
    skill: skill.name,
    version: skill.version,
    riskTier: skill.riskTier,
    params,
    message: `Skill ${skillName} invoked. Execution requires implementation.`,
    layer: 'L2',
    freq: SOUL_IDENTITY.freqTag
  };
}

// Slash command handler
export function handleSlashCommand(command, args = []) {
  const cmdDescription = SKILLS_CONTEXT.slashCommands.get(command);

  if (!cmdDescription) {
    return {
      success: false,
      error: `Command '/${command}' not found`,
      layer: 'L2'
    };
  }

  // Route to appropriate handler
  switch (command) {
    case 'soul':
      return {
        success: true,
        content: SOUL_RAW,
        layer: 'L0',
        freq: SOUL_IDENTITY.freqTag
      };

    case 'memory':
      return {
        success: true,
        content: MEMORY_RAW,
        layer: 'L1',
        freq: SOUL_IDENTITY.freqTag
      };

    case 'skills':
      return {
        success: true,
        skills: Array.from(SKILLS_CONTEXT.skills.values()),
        commands: Array.from(SKILLS_CONTEXT.slashCommands.entries()),
        layer: 'L2',
        freq: SOUL_IDENTITY.freqTag
      };

    case 'status':
      return {
        success: true,
        ...getSoulContext(),
        timestamp: new Date().toISOString(),
        freq: SOUL_IDENTITY.freqTag
      };

    case 'batch':
      const batchSize = args[0] ? parseInt(args[0]) : 1440;
      return invokeSkill('forge_control', { action: 'start_batch', units: batchSize });

    default:
      return {
        success: false,
        error: `Command handler for '/${command}' not implemented`,
        layer: 'L2'
      };
  }
}

export default {
  SOUL_IDENTITY,
  SOUL_SYSTEM_PROMPT,
  MEMORY_CONTEXT,
  SKILLS_CONTEXT,
  getSoulContext,
  invokeSkill,
  handleSlashCommand
};
