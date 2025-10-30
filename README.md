# Text Adventure (Web)

A minimal browser-based text adventure with a simple GUI input box.

## Run

- Open `index.html` in any modern browser (double-click it on macOS Finder).
- Type responses and press Enter.
- Type `restart` at any time to restart the story.

### Run the PyQt desktop app

1. Create a virtual environment (recommended):
   - macOS/Linux:
     ```bash
     python3 -m venv .venv && source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     py -3 -m venv .venv; .venv\\Scripts\\Activate.ps1
     ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python pyqt_main.py
   ```

## Extend the Story

- Edit `script.js` and modify the `scenes` object.
- Each scene has:
  - `text`: array of lines to display
  - `parse(input)`: function that returns the next scene key string, or `{ feedback, stay: true }` to remain in the same scene with a hint.
  - Optional `danger: true` to style the scene text as dangerous.

Example addition:

```js
scenes.searchBasement = {
  text: [
    'You creep into the basement. It smells like damp concrete.',
    'Do you turn on the light or use your phone? (light/phone)'
  ],
  parse(input) {
    const t = input.trim().toLowerCase();
    if (t.includes('light')) return 'breakerPops';
    if (t.includes('phone')) return 'footsteps';
    return { feedback: 'Type "light" or "phone".', stay: true };
  }
};
```

Hook it from an existing scene by returning 'searchBasement' in its `parse` function.

## Hunt Mode (rooms/items)

After answering "yes" to the initial prompt, the game enters Hunt Mode:

- A random killer room is chosen: kitchen, bedroom, garage, or bathroom.
- Each room has a clue hidden at one random location among four items:
  - kitchen: oven, under sink, pantry, stove
  - bedroom: closet, under bed, behind curtains, behind door
  - garage: under car, trunk, backseat, tool cabinet
  - bathroom: tub, under sink, behind door, toilet
- If you enter the killer room, you lose immediately.
- Find the clue in each safe room to win.

Difficulty:
- easy: find 3 clues; default 4 rooms
- medium: find 5 clues; +1 extra room (random)
- hard: find 8 clues; +2 extra rooms (random)

Rules:
- One random killer room. Entering it is game over.
- Clues are hidden at random room-item pairs across the active rooms.

Commands:
- Choose difficulty by typing: `easy`, `medium`, or `hard`.
- Choose a room by typing its name (the list is shown).
- Then choose an item in that room, e.g. `under sink`.

## Files

- `index.html` — markup shell
- `style.css` — visual styles
- `script.js` — story engine and scenes
- `pyqt_main.py` — PyQt6 desktop app
- `requirements.txt` — Python deps for the desktop app
