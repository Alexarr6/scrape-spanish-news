from __future__ import annotations

from src.adapters.abc import ABCAdapter
from src.adapters.elmundo import ElMundoAdapter
from src.adapters.elpais import ElPaisAdapter
from src.adapters.lavanguardia import LaVanguardiaAdapter
from src.adapters.minutos20 import Minutos20Adapter


ADAPTERS = {
    "elpais": ElPaisAdapter,
    "elmundo": ElMundoAdapter,
    "abc": ABCAdapter,
    "lavanguardia": LaVanguardiaAdapter,
    "20minutos": Minutos20Adapter,
}


def build_adapter(source: str):
    key = source.strip().lower()
    if key not in ADAPTERS:
        raise ValueError(f"Unknown source '{source}'. Valid: {', '.join(sorted(ADAPTERS.keys()))}")
    return ADAPTERS[key]()
