'''Tests for the DLL result-code check every high-level setter routes through.

verify_result_code is a pure function over an int, so this needs no DLL, no fake
and no hardware.'''
# pylint: disable=missing-function-docstring
import pytest

from pyvium.errors import (IllegalCommandError, InvalidStateError,
                           NoDeviceDetectedError, UnexpectedResultCodeError)
from pyvium.pyvium_verifiers import PyviumVerifiers


def test_success_code_raises_nothing():
    assert PyviumVerifiers.verify_result_code(0, "set_potential") is None


@pytest.mark.parametrize("result_code, expected_error", [
    (-1, NoDeviceDetectedError),
    (1, IllegalCommandError),
    (2, ValueError),
    (3, InvalidStateError),
])
def test_known_codes_map_to_their_typed_errors(result_code, expected_error):
    with pytest.raises(expected_error):
        PyviumVerifiers.verify_result_code(result_code, "set_potential")


@pytest.mark.parametrize("result_code", [4, 5, -2, 99])
def test_unmodelled_codes_raise_rather_than_pass(result_code):
    """A non-zero code the wrapper does not model is not success.

        The DLL convention is 0 for success, so reporting one of these as a
        successful command tells the caller a setpoint was applied when the
        firmware may have rejected it."""
    with pytest.raises(UnexpectedResultCodeError):
        PyviumVerifiers.verify_result_code(result_code, "set_potential")


def test_the_error_carries_the_code_and_context():
    with pytest.raises(UnexpectedResultCodeError) as raised:
        PyviumVerifiers.verify_result_code(4, "set_potential")

    assert raised.value.result_code == 4
    assert "4" in str(raised.value)
    assert "set_potential" in str(raised.value)
