from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

import os
import pathlib
import PyQt6
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


def normalize(text: str) -> str:
    return str(text).strip().lower()


@dataclass
class Scene:
    text: List[str]
    parse: Optional[Callable[[str], Union[str, Dict[str, Union[str, bool]]]]] = None
    danger: bool = False


def _ensure_qt_plugin_paths() -> None:
    # Help Qt find the bundled platform plugins (e.g., 'cocoa') on macOS
    pkg_dir = pathlib.Path(PyQt6.__file__).parent
    plugins_dir = pkg_dir / "Qt6" / "plugins"
    platforms_dir = plugins_dir / "platforms"
    # Environment fallbacks
    os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_dir))
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platforms_dir))
    # Qt runtime search path
    QCoreApplication.addLibraryPath(str(plugins_dir))


class TextAdventureWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Homicide Detective")
        self.resize(700, 520)

        central = QWidget(self)
        self.setCentralWidget(central)

        # Dark theme styles for readability and mood
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #0f1220; color: #e6e8f2; }
            QLabel { color: #e6e8f2; font-size: 18px; font-weight: 600; }
            QTextBrowser {
                background-color: #171a2b; color: #e6e8f2;
                border: 1px solid #2a2f45; border-radius: 10px;
                padding: 8px; font-size: 15px;
            }
            QLineEdit {
                background-color: #171a2b; color: #e6e8f2;
                border: 1px solid #2a2f45; border-radius: 10px;
                padding: 10px; font-size: 15px;
            }
            QPushButton {
                background-color: #6c8cff; color: #ffffff;
                border: none; border-radius: 10px; padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:pressed { background-color: #5b78db; }
            QMenuBar { background-color: #0f1220; color: #e6e8f2; }
            QMenuBar::item:selected { background: #171a2b; }
            QScrollBar:vertical { background: #0f1220; width: 10px; }
            QScrollBar::handle:vertical { background: #2a2f45; border-radius: 5px; }
            QScrollBar::add-line, QScrollBar::sub-line { background: transparent; }
            """
        )

        self.output = QTextBrowser(self)
        self.output.setOpenExternalLinks(False)
        self.output.setPlaceholderText("")

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Type your response and press Enter…")

        self.submit = QPushButton("Send", self)
        self.submit.setDefault(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Homicide Detective", self))
        layout.addWidget(self.output)
        layout.addWidget(self.input)
        layout.addWidget(self.submit)
        central.setLayout(layout)

        # Menu: Restart / About
        restart_action = QAction("Restart", self)
        restart_action.setShortcut("Ctrl+R")
        restart_action.triggered.connect(self.restart)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        self.menuBar().addAction(restart_action)
        self.menuBar().addAction(about_action)

        self.submit.clicked.connect(self.on_submit)
        self.input.returnPressed.connect(self.on_submit)

        self.current_scene_key: str = "start"
        self.scenes: Dict[str, Scene] = self._build_scenes()
        # Hunt mode state
        self.rooms: Dict[str, List[str]] = {
            "kitchen": ["oven", "under sink", "pantry", "stove"],
            "bedroom": ["closet", "under bed", "behind curtains", "behind door"],
            "garage": ["under car", "trunk", "backseat", "tool cabinet"],
            "bathroom": ["tub", "under sink", "behind door", "toilet"],
            "livingroom": ["sofa", "under rug", "tv cabinet", "bookshelf"],
            "basement": ["workbench", "fuse box", "storage shelf", "laundry basket"],
            "attic": ["old trunk", "rafters", "dusty boxes", "behind insulation"],
            "office": ["desk drawer", "filing cabinet", "behind monitor", "under chair"],
            "laundry": ["washer", "dryer", "detergent shelf", "laundry hamper"],
            "study": ["globe", "secret panel", "under carpet", "curio cabinet"],
        }
        self.hunt_active: bool = False
        self.killer_room: Optional[str] = None  # legacy
        self.killer_rooms: List[str] = []
        self.active_rooms: List[str] = []
        self.required_clues: int = 0
        self.clue_pairs: set[str] = set()
        self.found_pairs: set[str] = set()
        self.hunt_mode: str = "choose-difficulty"  # then 'choose-room'/'choose-item'
        self.current_room: Optional[str] = None
        self.difficulty: Optional[str] = None
        self.lives: int = 0
        # Show backstory (without changing current scene), then initial prompt
        prologue = None
        try:
            prologue = self._build_scenes()["prologue"].text
        except Exception:
            prologue = [
                "You are a homicide detective, called to a chilling case.",
                "They call the suspect the 'House Hunter'—a predator who stalks homes after dark.",
                "Find the clues, avoid the killer, and end the spree.",
            ]
        for line in prologue:
            self._append_line(line, "system")
        self._render_scene("start")

    def _append_line(self, text: str, kind: str = "game") -> None:
        # Simple styling via HTML spans
        color = {
            "game": "#e6e8f2",
            "player": "#6c8cff",
            "system": "#9aa0b6",
            "danger": "#ff6c6c",
        }.get(kind, "#e6e8f2")
        self.output.append(f'<span style="color:{color}">{text}</span>')
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)

    def _render_scene(self, key: str) -> None:
        scene = self.scenes.get(key)
        if not scene:
            return
        for line in scene.text:
            self._append_line(line, "danger" if scene.danger else "game")
        self.current_scene_key = key

    def on_submit(self) -> None:
        value = self.input.text().strip()
        if not value:
            return
        self.input.clear()
        self._append_line(f"> {value}", "player")

        if normalize(value) == "restart":
            self.restart()
            return

        scene = self.scenes.get(self.current_scene_key)
        if not scene or scene.parse is None:
            self._append_line('The story has ended. Type "restart" to begin again.', "system")
            return

        result = scene.parse(value)
        if isinstance(result, str):
            self._render_scene(result)
            return
        if isinstance(result, dict) and result.get("stay"):
            feedback = result.get("feedback")
            if feedback:
                self._append_line(str(feedback), "system")
            return

    def restart(self) -> None:
        self.output.clear()
        self.current_scene_key = "start"
        self.hunt_active = False
        self.killer_room = None
        self.killer_rooms = []
        self.active_rooms = []
        self.required_clues = 0
        self.clue_pairs = set()
        self.found_pairs = set()
        self.hunt_mode = "choose-difficulty"
        self.current_room = None
        self.difficulty = None
        self.lives = 0
        self._render_scene(self.current_scene_key)

    def show_about(self) -> None:
        self._append_line("Homicide Detective — House Hunter case", "system")
        self._append_line("A text-based investigation: find clues, avoid killer rooms, solve the case.", "system")
        self._append_line("Web and desktop versions included. Type 'restart' anytime to begin again.", "system")

    def _build_scenes(self) -> Dict[str, Scene]:
        def start_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            t = normalize(inp)
            if t in ["y", "yes", "yeah", "yep", "ok", "okay", "sure"]:
                return "investigate"
            if t in ["n", "no", "nope", "nah"]:
                return "avoid"
            return {"feedback": 'Please answer with "yes" or "no".', "stay": True}

        def initialize_hunt(diff: str) -> None:
            import random
            DIFF = {
                "easy": {"requiredClues": 3, "extraRooms": 0, "killers": 1, "lives": 0},
                "medium": {"requiredClues": 5, "extraRooms": 1, "killers": 1, "lives": 0},
                "hard": {"requiredClues": 8, "extraRooms": 2, "killers": 2, "lives": 1},
            }
            base_rooms = ["kitchen", "bedroom", "garage", "bathroom"]
            extras_pool = [
                "livingroom",
                "basement",
                "attic",
                "office",
                "laundry",
                "study",
            ]
            extra_n = DIFF[diff]["extraRooms"]
            extras = random.sample(extras_pool, k=min(extra_n, len(extras_pool)))
            self.active_rooms = base_rooms + extras
            self.required_clues = DIFF[diff]["requiredClues"]
            killers_n = DIFF[diff]["killers"]
            self.killer_rooms = random.sample(self.active_rooms, k=min(killers_n, len(self.active_rooms)))
            self.lives = DIFF[diff]["lives"]
            # Build all pairs excluding killer room
            all_pairs: List[str] = []
            for room in self.active_rooms:
                for item in self.rooms[room]:
                    all_pairs.append(f"{room}|{item}")
            candidates = [
                p for p in all_pairs
                if not any(p.startswith(kr + "|") for kr in self.killer_rooms)
            ]
            k = min(self.required_clues, len(candidates))
            self.clue_pairs = set(random.sample(candidates, k=k))
            self.found_pairs = set()
            self.hunt_mode = "choose-room"
            self.current_room = None
            self.hunt_active = True
            self.difficulty = diff

        def prompt_rooms():
            rooms_text = ", ".join(self.active_rooms)
            # Status line
            diff = f" • Difficulty: {self.difficulty}" if self.difficulty else ""
            self._append_line(
                f"Status — Clues: {len(self.found_pairs)}/{self.required_clues}"
                + (f" • Lives: {self.lives}" if self.lives else "")
                + diff,
                "system",
            )
            self._append_line(f"Rooms: {rooms_text}", "system")
            self._append_line("Choose a room to search. Type the room name.", "system")

        def prompt_items(room: str):
            items = self.rooms[room]
            self._append_line(
                f"You're in the {room}. Look where? ({' / '.join(items)})",
                "system",
            )

        def investigate_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            self.hunt_active = True
            self.hunt_mode = "choose-difficulty"
            self._append_line(
                "Choose a difficulty: easy (3 clues), medium (5, +1 room), hard (8, +2 rooms).",
                "system",
            )
            self._append_line("Type: easy, medium, or hard.", "system")
            return "hunt"
        def hunt_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            t = normalize(inp)
            if not self.hunt_active:
                self.hunt_active = True
                self.hunt_mode = "choose-difficulty"
                self._append_line("Type: easy, medium, or hard.", "system")
                return {"stay": True}
            if self.hunt_mode == "choose-difficulty":
                if t not in ("easy", "medium", "hard"):
                    return {"feedback": "Type: easy, medium, or hard.", "stay": True}
                initialize_hunt(t)
                self._append_line(
                    f"Find {self.required_clues} clues without entering the killer's room.",
                    "system",
                )
                prompt_rooms()
                return {"stay": True}
            if self.hunt_mode == "choose-room":
                room = next((r for r in self.active_rooms if t == r), None)
                if room is None:
                    return {"feedback": f"Type a room: {', '.join(self.active_rooms)}.", "stay": True}
                if room in self.killer_rooms:
                    if self.lives > 0:
                        self.lives -= 1
                        self._append_line("The killer attacks! You barely escape this time. Be careful.", "danger")
                        self._append_line(f"You can survive {self.lives} more encounter(s).", "system")
                        prompt_rooms()
                        return {"stay": True}
                    return "ending_caught_by_killer"
                self.current_room = room
                self.hunt_mode = "choose-item"
                prompt_items(room)
                return {"stay": True}
            if self.hunt_mode == "choose-item":
                room = self.current_room or ""
                items = self.rooms.get(room, [])
                item_match = next((i for i in items if t == i or i in t), None)
                if item_match is None:
                    return {"feedback": f"In the {room}, type one of: {' / '.join(items)}", "stay": True}
                key = f"{room}|{item_match}"
                if key in self.clue_pairs and key not in self.found_pairs:
                    self.found_pairs.add(key)
                    self._append_line(
                        f"You found a clue in the {room} ({item_match}). ({len(self.found_pairs)}/{self.required_clues})",
                        "system",
                    )
                elif key not in self.clue_pairs:
                    self._append_line("Nothing here. Keep looking.", "system")
                else:
                    self._append_line("You already found this clue.", "system")
                if len(self.found_pairs) >= self.required_clues:
                    return "ending_all_clues"
                self.hunt_mode = "choose-room"
                self.current_room = None
                prompt_rooms()
                return {"stay": True}
            return {"stay": True}

        def avoid_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            t = normalize(inp)
            if t in ["y", "yes"]:
                return "investigate"
            if t in ["n", "no"]:
                return "ending_avoid"
            return {"feedback": 'Answer "yes" or "no".', "stay": True}

        def call_police_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            t = normalize(inp)
            if "wait" in t:
                return "ending_police_wait"
            if any(k in t for k in ["go", "warehouse", "head", "move"]):
                return "warehouse"
            return {"feedback": 'Type "wait" or "go".', "stay": True}

        def warehouse_parse(inp: str) -> Union[str, Dict[str, Union[str, bool]]]:
            t = normalize(inp)
            if "pipe" in t:
                return "ending_confront"
            if "call" in t:
                return "ending_betrayed"
            return {"feedback": 'Type "pipe" or "call".', "stay": True}

        return {
            "prologue": Scene(
                text=[
                    "You are a homicide detective, called to a chilling case.",
                    "They call the suspect the 'House Hunter'—a predator who stalks homes after dark.",
                    "Find the clues, avoid the killer, and end the spree.",
                ]
            ),
            "start": Scene(
                text=[
                    "There is a killer on the loose. Should we try to stop them? (yes/no)",
                ],
                parse=start_parse,
            ),
            "investigate": Scene(
                text=[
                    "You choose to intervene. We need clues before the killer finds us.",
                    "Choose a difficulty: easy (3 clues), medium (5 clues, +1 room), hard (8 clues, +2 rooms).",
                ],
                parse=investigate_parse,
            ),
            "hunt": Scene(
                text=[],
                parse=hunt_parse,
            ),
            "avoid": Scene(
                text=[
                    "You decide to stay out of it and lock your doors.",
                    "Hours pass. Sirens wail in the distance. Guilt gnaws at you.",
                    "Do you change your mind and get involved? (yes/no)",
                ],
                parse=avoid_parse,
            ),
            "callPolice": Scene(
                text=[
                    "You call the police and report the last known location.",
                    "They advise you to keep your distance. Do you wait or head to the warehouse anyway? (wait/go)",
                ],
                parse=call_police_parse,
            ),
            "warehouse": Scene(
                text=[
                    "The warehouse is dark. You hear footsteps above. There is a loose pipe nearby.",
                    "Do you arm yourself with the pipe or quietly call out? (pipe/call)",
                ],
                parse=warehouse_parse,
            ),
            # Endings
            "ending_caught_by_killer": Scene(
                text=[
                    "You step into the room and the door slams behind you.",
                    "Breath at your neck. Wrong room. THE END.",
                ],
                danger=True,
            ),
            "ending_all_clues": Scene(
                text=[
                    "Piece by piece, the truth emerges from the clues you gathered.",
                    "You alert the authorities with precise details. The killer is caught without another victim. THE END.",
                ],
            ),
            "ending_avoid": Scene(
                text=[
                    "Days later, the news reports an arrest made after another close call.",
                    "You are safe, but the what-ifs linger. THE END.",
                ]
            ),
            "ending_police_wait": Scene(
                text=[
                    "You wait. Police storm the warehouse and apprehend the suspect.",
                    "Your caution may have saved you—and someone else. THE END.",
                ]
            ),
            "ending_confront": Scene(
                text=[
                    "With the pipe in hand, you creak up the stairs. A shadow lunges.",
                    "You parry, shouting for help. Sirens swell outside—backup arrives just in time. THE END.",
                ]
            ),
            "ending_betrayed": Scene(
                text=[
                    '"Hello?" you whisper. The footsteps stop. A voice behind you: "Found you."',
                    "Trust can be deadly in the dark. THE END.",
                ],
                danger=True,
            ),
        }


def main() -> int:
    _ensure_qt_plugin_paths()
    app = QApplication(sys.argv)
    win = TextAdventureWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


