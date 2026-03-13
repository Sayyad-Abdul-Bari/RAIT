"""Red-team dataset loader."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List


@dataclass
class AttackPrompt:
    id: str
    category: str
    prompt: str
    attack_intent: str
    expected_behavior: str


def load_attack_prompts(path: str) -> List[AttackPrompt]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [
        AttackPrompt(
            id=item["id"],
            category=item["category"],
            prompt=item["prompt"],
            attack_intent=item["attack_intent"],
            expected_behavior=item["expected_behavior"],
        )
        for item in raw
    ]
