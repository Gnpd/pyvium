'''Guards that every function declared in the bundled IviumSoft header has a
matching Core binding. Pure static check: it reads the .h and inspects Core
attributes, so it needs no IviumSoft or hardware (the DLL is still dlopen'd
when Core is imported, which the CI machine allows).'''
import re
from pathlib import Path

import pytest

from pyvium import Core

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "pyvium"
HEADERS = ["Ivium_remdriver64.h", "IVIUM_remdriver.h"]

# Matches the function name after IVIUM_API or __stdcall in the header, e.g.
# "IVIUM_API   IV_open();" and "void __stdcall IV_selectdevice(long *devnr);".
_DECL = re.compile(r"(?:IVIUM_API|__stdcall)\s+(IV_\w+)")


def _header_functions(header_name: str) -> set[str]:
    text = (PACKAGE_DIR / header_name).read_text(encoding="utf-8", errors="ignore")
    return set(_DECL.findall(text))


def test_both_headers_declare_the_same_functions():
    names_64, names_32 = (_header_functions(header) for header in HEADERS)
    assert names_64 == names_32, (
        "32- and 64-bit headers disagree: "
        f"{names_64.symmetric_difference(names_32)}")


@pytest.mark.parametrize("function_name", sorted(_header_functions(HEADERS[0])))
def test_core_binds_every_header_function(function_name):
    assert hasattr(Core, function_name), (
        f"{function_name} is declared in the IviumSoft header but not bound on Core")
