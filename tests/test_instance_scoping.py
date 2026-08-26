'''Tests for thread-safe instance scoping (Pyvium.on_instance, Pyvium.instance).

The DLL is replaced with an in-memory fake that mimics its global-selection
behaviour, so no IviumSoft installation or hardware is required.'''
# Pytest idioms default pylint flags: fixtures are injected as same-named
# arguments (redefined-outer-name) and may be requested only for their side
# effects (unused-argument); tests and the fake-DLL methods are self-describing
# (missing-function-docstring) and the fake mirrors the DLL's IV_* names
# (invalid-name).
# Tests also assert exact return shapes (e.g. == [] documents an empty list)
# rather than truthiness (use-implicit-booleaness-not-comparison).
# pylint: disable=missing-function-docstring,redefined-outer-name,unused-argument,invalid-name,use-implicit-booleaness-not-comparison
import threading
import time

import pytest

from pyvium import Pyvium
from pyvium.core import Core
from pyvium.core.core_base import CoreBase
from pyvium.errors import (DriverNotOpenError, IllegalCommandError,
                           IviumSoftNotRunningError)
from pyvium.pyvium.instance import PyviumInstance


class FakeIviumLib:
    '''Mimics the DLL: one global selected instance, and a log of every call
        with the instance that was selected when it happened.'''

    def __init__(self, active_instances=(1, 2, 3)):
        self.active_instances = set(active_instances)
        self.selected = 1
        self.calls = []
        self.call_delay = 0.0
        # Result code the fused IV_selectdevice_* setters return (0 = success).
        self.setter_result_code = 0

    def IV_open(self):
        # The driver resets its selected instance to 1 on open.
        self.selected = 1
        self.calls.append(('IV_open', self.selected))
        return 0

    def IV_close(self):
        self.calls.append(('IV_close', self.selected))
        return 0

    def IV_selectdevice(self, instance_number_ptr):
        self.selected = instance_number_ptr[0]
        self.calls.append(('IV_selectdevice', self.selected))

    def IV_getdevicestatus(self):
        if self.call_delay:
            time.sleep(self.call_delay)
        self.calls.append(('IV_getdevicestatus', self.selected))
        return 1 if self.selected in self.active_instances else -1

    # The fused IV_selectdevice_* setters are select+command in one call: they
    # park the global selection on the target instance and never restore it.
    def _fused_setter(self, name, instance_ptr):
        if self.call_delay:
            time.sleep(self.call_delay)
        self.selected = instance_ptr[0]
        self.calls.append((name, self.selected))
        return self.setter_result_code

    def IV_selectdevice_setcurrent(self, instance_ptr, value_ptr):
        return self._fused_setter('IV_selectdevice_setcurrent', instance_ptr)

    def IV_selectdevice_setpotential(self, instance_ptr, value_ptr):
        return self._fused_setter('IV_selectdevice_setpotential', instance_ptr)


@pytest.fixture
def fake_lib(monkeypatch):
    fake = FakeIviumLib()
    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: fake))
    CoreBase.set_driver_open(True)
    CoreBase.set_selected_instance(1)
    CoreBase.invalidate_active_instances_cache()
    yield fake
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)


@pytest.fixture
def cold_lib(monkeypatch):
    '''Driver closed, zero IviumSoft instances running, the cold-start case.'''
    fake = FakeIviumLib(active_instances=())
    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: fake))
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)
    yield fake
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)


def test_open_driver_raises_and_closes_when_no_iviumsoft(cold_lib):
    with pytest.raises(IviumSoftNotRunningError):
        Pyvium.open_driver()
    assert not Core.is_driver_open()


def test_open_driver_cold_start_skips_iviumsoft_check(cold_lib):
    Pyvium.open_driver(verify_iviumsoft=False)

    assert Core.is_driver_open()
    assert Pyvium.get_active_iviumsoft_instances() == []

    Pyvium.close_driver()
    assert not Core.is_driver_open()


def test_close_driver_resets_selected_instance_shadow(fake_lib):
    Pyvium.select_iviumsoft_instance(3)
    assert Core.get_selected_instance() == 3

    Pyvium.close_driver()

    assert Core.get_selected_instance() == 1


def test_open_driver_resets_selected_instance_shadow(fake_lib):
    Pyvium.select_iviumsoft_instance(3)

    Pyvium.close_driver()
    Pyvium.open_driver()

    # The driver is back on instance 1, so the shadow must say 1 too.
    assert Core.get_selected_instance() == 1
    assert fake_lib.selected == 1


def test_on_instance_after_reopen_restores_to_driver_default(fake_lib):
    """A stale shadow must not move the working instance after a reopen.

        Before the reset, the shadow still read 3 while the driver was on 1, so
        this block restored to 3 on exit and silently redirected every later
        unscoped call to the wrong instance."""
    Pyvium.select_iviumsoft_instance(3)
    Pyvium.close_driver()
    Pyvium.open_driver()

    with Pyvium.on_instance(2):
        assert fake_lib.selected == 2

    assert fake_lib.selected == 1
    assert Core.get_selected_instance() == 1


def test_on_instance_selects_then_restores(fake_lib):
    with Pyvium.on_instance(3):
        assert fake_lib.selected == 3
    assert fake_lib.selected == 1


def test_on_instance_restores_selection_on_exception(fake_lib):
    with pytest.raises(RuntimeError):
        with Pyvium.on_instance(3):
            raise RuntimeError('boom')
    assert fake_lib.selected == 1


def test_on_instance_nests(fake_lib):
    with Pyvium.on_instance(2):
        with Pyvium.on_instance(3):
            assert fake_lib.selected == 3
        assert fake_lib.selected == 2
    assert fake_lib.selected == 1


def test_on_instance_requires_open_driver(fake_lib):
    CoreBase.set_driver_open(False)
    with pytest.raises(DriverNotOpenError):
        with Pyvium.on_instance(2):
            pass


def test_instance_proxy_scopes_every_call(fake_lib):
    instance = Pyvium.instance(2)

    result_code, label = instance.get_device_status()

    assert (result_code, label) == (1, 'available_idle')
    # get_device_status calls IV_getdevicestatus twice: once in the
    # iviumsoft-running verifier and once for the result itself.
    assert fake_lib.calls == [
        ('IV_selectdevice', 2),
        ('IV_getdevicestatus', 2),
        ('IV_getdevicestatus', 2),
        ('IV_selectdevice', 1),
    ]


def test_instance_factory_and_attributes(fake_lib):
    instance = Pyvium.instance(7)
    assert isinstance(instance, PyviumInstance)
    assert instance.instance_number == 7
    with pytest.raises(AttributeError):
        instance.not_a_pyvium_method  # pylint: disable=pointless-statement


def test_get_active_instances_restores_previous_selection(fake_lib):
    Core.IV_selectdevice(2)

    active = Pyvium.get_active_iviumsoft_instances()

    assert active == [1, 2, 3]
    assert fake_lib.selected == 2


def test_get_active_populates_cache_and_use_cache_skips_dll(fake_lib):
    assert Pyvium.get_active_iviumsoft_instances() == [1, 2, 3]
    calls_after_scan = len(fake_lib.calls)

    cached = Pyvium.get_active_iviumsoft_instances(use_cache=True)

    assert cached == [1, 2, 3]
    assert len(fake_lib.calls) == calls_after_scan  # cache hit: no DLL calls


def test_use_cache_falls_back_to_full_scan_when_empty(fake_lib):
    CoreBase.invalidate_active_instances_cache()

    active = Pyvium.get_active_iviumsoft_instances(use_cache=True)

    assert active == [1, 2, 3]
    assert ('IV_getdevicestatus', 1) in fake_lib.calls  # a real scan happened


def test_invalidating_cache_forces_a_rescan(fake_lib):
    Pyvium.get_active_iviumsoft_instances()        # populate
    fake_lib.active_instances.add(4)               # topology changes underneath

    # stale cache cannot see instance 4
    assert Pyvium.get_active_iviumsoft_instances(use_cache=True) == [1, 2, 3]

    CoreBase.invalidate_active_instances_cache()

    # a rescan picks it up
    assert Pyvium.get_active_iviumsoft_instances(use_cache=True) == [1, 2, 3, 4]


def test_set_device_potential_restores_previous_selection(fake_lib):
    Core.IV_selectdevice(2)

    Pyvium.set_device_potential(3, 0.5)

    # The fused call parks the DLL on instance 3; the caller's selection and the
    # shadow that on_instance restores from must both come back to 2.
    assert fake_lib.selected == 2
    assert Core.get_selected_instance() == 2


def test_set_device_current_restores_selection_on_failure(fake_lib):
    Core.IV_selectdevice(2)
    fake_lib.setter_result_code = 1  # illegal command

    with pytest.raises(IllegalCommandError):
        Pyvium.set_device_current(3, 0.001)

    assert fake_lib.selected == 2
    assert Core.get_selected_instance() == 2


def test_set_device_potential_does_not_escape_an_on_instance_block(fake_lib):
    '''The regression test for the lock bypass: a setpoint issued from another
        thread must not move the selection out from under an on_instance block.'''
    fake_lib.call_delay = 0.001  # widen the race window
    errors = []
    stop = threading.Event()

    def scoped_worker():
        for _ in range(20):
            try:
                with Pyvium.on_instance(2):
                    assert fake_lib.selected == 2
                    Core.IV_getdevicestatus()
                    assert fake_lib.selected == 2
            except AssertionError as error:  # pragma: no cover
                errors.append(error)
        stop.set()

    def setpoint_worker():
        while not stop.is_set():
            Pyvium.set_device_potential(5, 0.1)

    threads = [threading.Thread(target=scoped_worker),
               threading.Thread(target=setpoint_worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors


def test_scoped_calls_from_threads_do_not_interleave(fake_lib):
    fake_lib.call_delay = 0.001  # widen the race window
    errors = []

    def worker(instance_number):
        for _ in range(20):
            try:
                with Pyvium.on_instance(instance_number):
                    assert fake_lib.selected == instance_number
                    Core.IV_getdevicestatus()
                    assert fake_lib.selected == instance_number
            except AssertionError as error:  # pragma: no cover
                errors.append(error)

    threads = [threading.Thread(target=worker, args=(number,))
               for number in (2, 3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
