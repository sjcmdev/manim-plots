import json

import manim
import pytest

from poc4.evidence import SYMBOLS, contract
from poc4.model import ROOT

EXPECTED = json.loads((ROOT / "manim_contract.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("symbol", SYMBOLS, ids=lambda symbol: symbol.__qualname__)
def test_k1_cited_manim_symbol(symbol):
    assert manim.__version__ == "0.21.0"
    assert contract()[symbol.__qualname__] == EXPECTED[symbol.__qualname__]
