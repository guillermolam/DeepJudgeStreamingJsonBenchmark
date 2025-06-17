# parser_loader.py

import importlib
import pkgutil
import traceback
from typing import Dict, Type

LOADED_PARSERS: Dict[str, Type] = {}
FAILED_PARSERS: Dict[str, str] = {}


def discover_parsers(base_package: str = "src.serializers") -> None:
    """Discovers and loads all parsers from the specified base package."""
    global LOADED_PARSERS, FAILED_PARSERS
    LOADED_PARSERS.clear()
    FAILED_PARSERS.clear()

    for finder, name, ispkg in pkgutil.walk_packages(
        [base_package.replace(".", "/")], base_package + "."
    ):
        try:
            module = importlib.import_module(name)
            parser_cls = getattr(module, "StreamingJsonParser", None)
            if parser_cls:
                LOADED_PARSERS[name] = parser_cls
                print(f"✓ Loaded parser: {name}")
        except Exception as e:
            FAILED_PARSERS[name] = str(e)
            print(f"❌ Failed to load parser: {name} - {e}")
            traceback.print_exc()


# Discover parsers at import time
discover_parsers()
