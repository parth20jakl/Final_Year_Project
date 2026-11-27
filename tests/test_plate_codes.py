"""Sanity checks for configs/plate_codes.json."""
import json
import re
from pathlib import Path

import pytest

DATA = json.loads((Path(__file__).resolve().parents[1] / "configs" / "plate_codes.json").read_text(encoding="utf-8"))


def test_every_state_has_an_rto_table() -> None:
    assert set(DATA["rto"]) == set(DATA["states"])
    assert all(DATA["rto"].values())


def test_keys_and_names_are_well_formed() -> None:
    for state, offices in DATA["rto"].items():
        for code, name in offices.items():
            assert re.fullmatch(r"\d{2,3}", code), f"{state}{code}"
            assert name.strip() == name and name, f"{state}{code}"
            assert not re.search(r"[\[\]{}|<>�]", name), f"{state}{code}: {name!r}"


def test_aliases_point_to_known_states() -> None:
    for old, new in DATA["rto_aliases"].items():
        assert old in DATA["old_state_codes_still_on_road"]
        assert new in DATA["rto"]


@pytest.mark.parametrize(
    "code, expected",
    [("MH12", "Pune"), ("MH14", "Pimpri"), ("MH04", "Thane"), ("KA01", "Bengaluru"), ("TN01", "Chennai"),
     ("KL07", "Ernakulam"), ("UP14", "Ghaziabad"), ("UP16", "Noida"), ("HR26", "Gurugram"), ("GJ01", "Ahmedabad"),
     ("RJ27", "Udaipur"), ("MP09", "Indore"), ("AN01", "Port Blair")],
)
def test_known_offices(code: str, expected: str) -> None:
    assert expected in DATA["rto"][code[:2]][code[2:]]
