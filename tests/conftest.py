import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mahjong.card import load_card  # noqa: E402


@pytest.fixture(scope="session")
def card():
    return load_card(os.path.join(ROOT, "cards", "practice_card.json"))


def tiles_of(binding):
    return [code for code, n in binding.groups for _ in range(n)]
