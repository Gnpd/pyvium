'''Public device-status label API. Pure constants/helpers, no DLL or hardware.'''
from pyvium import DEVICE_STATUS_LABELS, device_status_label


def test_labels_cover_the_documented_codes():
    assert DEVICE_STATUS_LABELS[-1] == "no IviumSoft"
    assert DEVICE_STATUS_LABELS[1] == "available_idle"
    assert set(DEVICE_STATUS_LABELS) == {-1, 0, 1, 2, 3}


def test_mapping_is_read_only():
    import pytest
    with pytest.raises(TypeError):
        DEVICE_STATUS_LABELS[1] = "changed"


def test_helper_matches_map_and_falls_back():
    for code, label in DEVICE_STATUS_LABELS.items():
        assert device_status_label(code) == label
    assert device_status_label(99) == "unknown (99)"
