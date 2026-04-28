from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    name: str
    display_name: str
    method: str
    args: list
    kwargs: dict


COMMAND_MAP: list[dict] = [
    {
        "name": "stretch",
        "display": "Stretch",
        "method": "stretch",
        "triggers": ["stretch", "reach", "reach out"],
    },
    {
        "name": "sit",
        "display": "Sit Down",
        "method": "sit",
        "triggers": ["sit down", "sit", "take a seat"],
    },
    {
        "name": "stand_up",
        "display": "Stand Up",
        "method": "stand_up",
        "triggers": ["stand up", "get up", "rise", "stand"],
    },
    {
        "name": "rise_sit",
        "display": "Rise from Sit",
        "method": "rise_sit",
        "triggers": ["rise from sit", "get up from sit"],
    },
    {
        "name": "hello",
        "display": "Hello / Greet",
        "method": "hello",
        "triggers": ["hello", "greet", "wave", "say hi", "say hello", "hi"],
    },
    {
        "name": "heart",
        "display": "Heart / Love",
        "method": "heart",
        "triggers": ["love", "heart", "i love you", "send love"],
    },
    {
        "name": "dance1",
        "display": "Dance 1",
        "method": "dance1",
        "triggers": ["dance", "dance one", "first dance", "do a dance"],
    },
    {
        "name": "dance2",
        "display": "Dance 2",
        "method": "dance2",
        "triggers": ["dance two", "second dance"],
    },
    {
        "name": "front_flip",
        "display": "Front Flip",
        "method": "front_flip",
        "triggers": ["front flip", "flip", "do a flip"],
    },
    {
        "name": "back_flip",
        "display": "Back Flip",
        "method": "back_flip",
        "triggers": ["back flip", "backflip"],
    },
    {
        "name": "left_flip",
        "display": "Left Flip",
        "method": "left_flip",
        "triggers": ["left flip", "left flip"],
    },
    {
        "name": "front_jump",
        "display": "Jump",
        "method": "front_jump",
        "triggers": ["jump", "front jump", "leap"],
    },
    {
        "name": "front_pounce",
        "display": "Pounce",
        "method": "front_pounce",
        "triggers": ["pounce", "front pounce"],
    },
    {
        "name": "handstand",
        "display": "Handstand",
        "method": "hand_stand",
        "triggers": ["hand stand", "handstand", "stand on hands"],
    },
    {
        "name": "scrape",
        "display": "Scrape",
        "method": "scrape",
        "triggers": ["scrape", "scratch"],
    },
    {
        "name": "content",
        "display": "Happy / Content",
        "method": "content",
        "triggers": ["happy", "content", "be happy", "feel good"],
    },
    {
        "name": "stand_down",
        "display": "Lie Down",
        "method": "stand_down",
        "triggers": ["lie down", "lay down", "lay", "rest"],
    },
    {
        "name": "balance_stand",
        "display": "Balance Stand",
        "method": "balance_stand",
        "triggers": ["balance", "balance stand"],
    },
    {
        "name": "recovery_stand",
        "display": "Recovery Stand",
        "method": "recovery_stand",
        "triggers": ["recovery", "recover", "recovery stand"],
    },
    {
        "name": "stop",
        "display": "Stop",
        "method": "stop_move",
        "triggers": ["stop", "halt", "freeze", "whoa"],
    },
    {
        "name": "damp",
        "display": "Emergency Stop",
        "method": "damp",
        "triggers": ["emergency", "emergency stop", "kill", "shutdown motors"],
    },
    {
        "name": "move_forward",
        "display": "Move Forward",
        "method": "move",
        "triggers": ["go forward", "forward", "move forward", "walk forward"],
        "args": [0.3, 0.0, 0.0],
    },
    {
        "name": "move_backward",
        "display": "Move Backward",
        "method": "move",
        "triggers": ["go back", "backward", "back", "move back", "walk back"],
        "args": [-0.3, 0.0, 0.0],
    },
    {
        "name": "turn_left",
        "display": "Turn Left",
        "method": "move",
        "triggers": ["turn left", "left", "rotate left"],
        "args": [0.0, 0.0, 0.5],
    },
    {
        "name": "turn_right",
        "display": "Turn Right",
        "method": "move",
        "triggers": ["turn right", "right", "rotate right"],
        "args": [0.0, 0.0, -0.5],
    },
    {
        "name": "strafe_left",
        "display": "Strafe Left",
        "method": "move",
        "triggers": ["strafe left", "side step left", "step left"],
        "args": [0.0, 0.3, 0.0],
    },
    {
        "name": "strafe_right",
        "display": "Strafe Right",
        "method": "move",
        "triggers": ["strafe right", "side step right", "step right"],
        "args": [0.0, -0.3, 0.0],
    },
    {
        "name": "free_walk",
        "display": "Free Walk",
        "method": "free_walk",
        "triggers": ["free walk", "roam"],
    },
    {
        "name": "trot_run",
        "display": "Trot Run",
        "method": "trot_run",
        "triggers": ["trot", "run", "trot run", "jog"],
    },
    {
        "name": "static_walk",
        "display": "Static Walk",
        "method": "static_walk",
        "triggers": ["static walk", "walk carefully"],
    },
    {
        "name": "cross_step",
        "display": "Cross Step",
        "method": "cross_step",
        "triggers": ["cross step", "cross"],
    },
]

_MOVE_COMMAND_NAMES = {
    "move_forward",
    "move_backward",
    "turn_left",
    "turn_right",
    "strafe_left",
    "strafe_right",
}


def parse_command(text: str) -> ParsedCommand | None:
    normalized = text.lower().strip()
    if not normalized:
        return None

    for cmd in COMMAND_MAP:
        for trigger in cmd["triggers"]:
            if trigger in normalized:
                args = cmd.get("args", [])
                kwargs = cmd.get("kwargs", {})
                logger.info(
                    "Matched command '%s' via trigger '%s'", cmd["display"], trigger
                )
                return ParsedCommand(
                    name=cmd["name"],
                    display_name=cmd["display"],
                    method=cmd["method"],
                    args=args,
                    kwargs=kwargs,
                )

    logger.info("No command matched for: '%s'", normalized)
    return None


def get_all_commands() -> list[dict]:
    return [
        {
            "name": c["name"],
            "display": c["display"],
            "triggers": c["triggers"],
            "is_movement": c["name"] in _MOVE_COMMAND_NAMES,
        }
        for c in COMMAND_MAP
    ]
