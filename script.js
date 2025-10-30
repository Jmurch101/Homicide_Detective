/*
  Minimal text adventure engine with a simple scene graph.
  Type responses and press Enter. Commands are matched by keywords.
*/

const outputEl = document.getElementById('output');
const formEl = document.getElementById('input-form');
const inputEl = document.getElementById('command');

function appendLine(text, type = 'game') {
  const div = document.createElement('div');
  div.className = `line line--${type}`;
  div.textContent = text;
  outputEl.appendChild(div);
  outputEl.scrollTop = outputEl.scrollHeight;
}

function normalize(text) {
  return String(text).trim().toLowerCase();
}

// Rooms and items for hunt mode
const ROOMS = {
  kitchen: ['oven', 'under sink', 'pantry', 'stove'],
  bedroom: ['closet', 'under bed', 'behind curtains', 'behind door'],
  garage: ['under car', 'trunk', 'backseat', 'tool cabinet'],
  bathroom: ['tub', 'under sink', 'behind door', 'toilet'],
  livingroom: ['sofa', 'under rug', 'tv cabinet', 'bookshelf'],
  basement: ['workbench', 'fuse box', 'storage shelf', 'laundry basket'],
  attic: ['old trunk', 'rafters', 'dusty boxes', 'behind insulation'],
  office: ['desk drawer', 'filing cabinet', 'behind monitor', 'under chair'],
  laundry: ['washer', 'dryer', 'detergent shelf', 'laundry hamper'],
  study: ['globe', 'secret panel', 'under carpet', 'curio cabinet']
};

function randomChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomSample(array, k) {
  const arr = array.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, Math.max(0, Math.min(k, arr.length)));
}

const DIFFICULTY = {
  easy: { requiredClues: 3, extraRooms: 0, killers: 1, lives: 0 },
  medium: { requiredClues: 5, extraRooms: 1, killers: 1, lives: 0 },
  hard: { requiredClues: 8, extraRooms: 2, killers: 2, lives: 1 }
};

const huntState = {
  active: false,
  killerRooms: [],
  activeRooms: [],
  requiredClues: 0,
  cluePairs: new Set(), // of 'room|item'
  foundPairs: new Set(),
  mode: 'choose-difficulty', // 'choose-room' or 'choose-item'
  currentRoom: null,
  difficulty: null,
  lives: 0
};

function initHuntState(difficulty) {
  huntState.active = true;
  huntState.difficulty = difficulty;
  const baseRooms = ['kitchen', 'bedroom', 'garage', 'bathroom'];
  const extrasPool = ['livingroom', 'basement', 'attic', 'office', 'laundry', 'study'];
  const extraRooms = randomSample(extrasPool, DIFFICULTY[difficulty].extraRooms);
  huntState.activeRooms = baseRooms.concat(extraRooms);
  huntState.requiredClues = DIFFICULTY[difficulty].requiredClues;
  const killersCount = DIFFICULTY[difficulty].killers;
  huntState.killerRooms = randomSample(huntState.activeRooms, killersCount);
  huntState.lives = DIFFICULTY[difficulty].lives;
  // Build all (room,item) pairs excluding killer room initially
  const allPairs = [];
  huntState.activeRooms.forEach(room => {
    ROOMS[room].forEach(item => allPairs.push(`${room}|${item}`));
  });
  const candidatePairs = allPairs.filter(p => !huntState.killerRooms.some(kr => p.startsWith(kr + '|')));
  const chosen = randomSample(candidatePairs, huntState.requiredClues);
  huntState.cluePairs = new Set(chosen);
  huntState.foundPairs = new Set();
  huntState.mode = 'choose-room';
  huntState.currentRoom = null;
}

function describeRooms() {
  return `Rooms: ${huntState.activeRooms.join(', ')}`;
}

function promptRoomChoice() {
  // Status
  const clues = `${huntState.foundPairs.size}/${huntState.requiredClues}`;
  const lives = huntState.lives;
  const diff = huntState.difficulty ? ` • Difficulty: ${huntState.difficulty}` : '';
  appendLine(`Status — Clues: ${clues}${lives ? ` • Lives: ${lives}` : ''}${diff}`, 'system');
  appendLine(describeRooms());
  appendLine('Choose a room to search. Type the room name.');
}

function promptItemChoice(room) {
  const items = ROOMS[room];
  appendLine(`You're in the ${room}. Look where? (${items.join(' / ')})`);
}

// Simple scene graph
const scenes = {
  start: {
    text: [
      'There is a killer on the loose. Should we try to stop them? (yes/no)'
    ],
    parse(input) {
      const t = normalize(input);
      if (['y', 'yes', 'yeah', 'yep', 'ok', 'okay', 'sure'].includes(t)) return 'investigate';
      if (['n', 'no', 'nope', 'nah'].includes(t)) return 'avoid';
      return {
        feedback: 'Please answer with "yes" or "no".',
        stay: true
      };
    }
  },

  investigate: {
    text: [
      'You choose to intervene. We need clues before the killer finds us.',
      'Choose a difficulty: easy (3 clues), medium (5 clues, +1 room), hard (8 clues, +2 rooms).'
    ],
    parse() {
      huntState.active = true;
      huntState.mode = 'choose-difficulty';
      appendLine('Type: easy, medium, or hard.', 'system');
      return 'hunt';
    }
  },

  hunt: {
    text: [],
    parse(input) {
      const t = normalize(input);
      if (!huntState.active) {
        huntState.active = true;
        huntState.mode = 'choose-difficulty';
        appendLine('Type: easy, medium, or hard.', 'system');
        return { stay: true };
      }
      if (huntState.mode === 'choose-difficulty') {
        if (!['easy', 'medium', 'hard'].includes(t)) {
          return { feedback: 'Type: easy, medium, or hard.', stay: true };
        }
        initHuntState(t);
        appendLine(`Find ${huntState.requiredClues} clues without entering the killer's room.`, 'system');
        promptRoomChoice();
        return { stay: true };
      }
      if (huntState.mode === 'choose-room') {
        // choose room
        const room = huntState.activeRooms.find(r => t === r);
        if (!room) {
          return { feedback: `Type a room: ${huntState.activeRooms.join(', ')}.`, stay: true };
        }
        if (huntState.killerRooms.includes(room)) {
          if (huntState.lives > 0) {
            huntState.lives -= 1;
            appendLine('The killer attacks! You barely escape this time. Be careful.', 'danger');
            appendLine(`You can survive ${huntState.lives} more encounter(s).`, 'system');
            promptRoomChoice();
            return { stay: true };
          }
          return 'ending_caught_by_killer';
        }
        huntState.currentRoom = room;
        huntState.mode = 'choose-item';
        promptItemChoice(room);
        return { stay: true };
      }
      if (huntState.mode === 'choose-item') {
        const room = huntState.currentRoom;
        const itemMatch = ROOMS[room].find(i => t === i || t.includes(i));
        if (!itemMatch) {
          return { feedback: `In the ${room}, type one of: ${ROOMS[room].join(' / ')}`, stay: true };
        }
        const key = `${room}|${itemMatch}`;
        if (huntState.cluePairs.has(key) && !huntState.foundPairs.has(key)) {
          huntState.foundPairs.add(key);
          appendLine(`You found a clue in the ${room} (${itemMatch}). (${huntState.foundPairs.size}/${huntState.requiredClues})`, 'system');
        } else if (!huntState.cluePairs.has(key)) {
          appendLine('Nothing here. Keep looking.', 'system');
        } else {
          appendLine('You already found this clue.', 'system');
        }
        if (huntState.foundPairs.size >= huntState.requiredClues) {
          return 'ending_all_clues';
        }
        huntState.mode = 'choose-room';
        huntState.currentRoom = null;
        promptRoomChoice();
        return { stay: true };
      }
      return { stay: true };
    }
  },

  avoid: {
    text: [
      'You decide to stay out of it and lock your doors.',
      'Hours pass. Sirens wail in the distance. Guilt gnaws at you.',
      'Do you change your mind and get involved? (yes/no)'
    ],
    parse(input) {
      const t = normalize(input);
      if (['y', 'yes'].includes(t)) return 'investigate';
      if (['n', 'no'].includes(t)) return 'ending_avoid';
      return { feedback: 'Answer "yes" or "no".', stay: true };
    }
  },

  callPolice: {
    text: [
      'You call the police and report the last known location.',
      'They advise you to keep your distance. Do you wait or head to the warehouse anyway? (wait/go)'
    ],
    parse(input) {
      const t = normalize(input);
      if (t.includes('wait')) return 'ending_police_wait';
      if (['go', 'warehouse', 'head', 'move'].some(k => t.includes(k))) return 'warehouse';
      return { feedback: 'Type "wait" or "go".', stay: true };
    }
  },

  warehouse: {
    text: [
      'The warehouse is dark. You hear footsteps above. There is a loose pipe nearby.',
      'Do you arm yourself with the pipe or quietly call out? (pipe/call)'
    ],
    parse(input) {
      const t = normalize(input);
      if (t.includes('pipe')) return 'ending_confront';
      if (t.includes('call')) return 'ending_betrayed';
      return { feedback: 'Type "pipe" or "call".', stay: true };
    }
  },

  // Endings
  ending_caught_by_killer: {
    text: [
      'You step into the room and the door slams behind you.',
      'Breath at your neck. Wrong room. THE END.'
    ],
    danger: true
  },
  ending_all_clues: {
    text: [
      'Piece by piece, the truth emerges from the clues you gathered.',
      'You alert the authorities with precise details. The killer is caught without another victim. THE END.'
    ]
  },
  ending_avoid: {
    text: [
      'Days later, the news reports an arrest made after another close call.',
      'You are safe, but the what-ifs linger. THE END.'
    ]
  },
  ending_police_wait: {
    text: [
      'You wait. Police storm the warehouse and apprehend the suspect.',
      'Your caution may have saved you—and someone else. THE END.'
    ]
  },
  ending_confront: {
    text: [
      'With the pipe in hand, you creak up the stairs. A shadow lunges.',
      'You parry, shouting for help. Sirens swell outside—backup arrives just in time. THE END.'
    ]
  },
  ending_betrayed: {
    text: [
      '"Hello?" you whisper. The footsteps stop. A voice behind you: "Found you."',
      'Trust can be deadly in the dark. THE END.'
    ],
    danger: true
  }
};

let currentScene = 'start';

function renderScene(sceneKey) {
  const scene = scenes[sceneKey];
  if (!scene) return;
  scene.text.forEach(line => appendLine(line, scene.danger ? 'danger' : 'game'));
  currentScene = sceneKey;
}

function handleInput(value) {
  if (!value) return;
  appendLine(`> ${value}`, 'player');

  const scene = scenes[currentScene];
  if (!scene || typeof scene.parse !== 'function') {
    appendLine('The story has ended. Type "restart" to begin again.', 'system');
    return;
  }

  const result = scene.parse(value);
  if (typeof result === 'string') {
    renderScene(result);
    return;
  }
  if (result && result.stay) {
    if (result.feedback) appendLine(result.feedback, 'system');
    return;
  }
}

function restart() {
  outputEl.innerHTML = '';
  currentScene = 'start';
  renderScene(currentScene);
}

formEl.addEventListener('submit', (e) => {
  e.preventDefault();
  const value = inputEl.value.trim();
  inputEl.value = '';
  if (normalize(value) === 'restart') {
    restart();
    return;
  }
  handleInput(value);
});

// Prologue then initial prompt
appendLine('You are a homicide detective, called to a chilling case.', 'system');
appendLine("They call the suspect the 'House Hunter'—a predator who stalks homes after dark.", 'system');
appendLine('Find the clues, avoid the killer, and end the spree.', 'system');
renderScene(currentScene);


