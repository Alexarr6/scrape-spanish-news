from __future__ import annotations

import pytest

from src.analysis.taxonomy import validate_tag_codes


def test_validate_tag_codes_accepts_known_codes_once():
    assert validate_tag_codes(["politics_national", "justice", "justice"]) == [
        "politics_national",
        "justice",
    ]


def test_validate_tag_codes_rejects_unknown_codes():
    with pytest.raises(ValueError):
        validate_tag_codes(["made_up_tag"])
