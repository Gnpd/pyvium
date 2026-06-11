'''Tests for thread-safe instance scoping (Pyvium.on_instance, Pyvium.device).

The DLL is replaced with an in-memory fake that mimics its global-selection
behaviour, so no IviumSoft installation or hardware is required.'''
import threading
import time

import pytest

from pyvium import Pyvium
from pyvium.core import Core
from pyvium.core.core_base import CoreBase
from pyvium.errors import DriverNotOpenError
from pyvium.pyvium.device import PyviumDevice


class FakeIviumLib:
    '''Mimics the DLL: one global selected instance, and a log of every call
        with the instance that was selected when it happened.'''

    def __init__(self, active_instances=(1, 2, 3)):
        self.active_instances = set(active_instances)
        self.selected = 1
        self.calls = []
        self.call_delay = 0.0

    def IV_selectdevice(self, instance_number_ptr):
        self.selected = instance_number_ptr[0]
        self.calls.append(('IV_selectdevice', self.selected))

    def IV_getdevicestatus(self):
        if self.call_delay:
            time.sleep(self.call_delay)
        self.calls.append(('IV_getdevicestatus', self.selected))
        return 1 if self.selected in self.active_instances else -1


@pytest.fixture
def fake_lib(monkeypatch):
    fake = FakeIviumLib()
    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: fake))
    CoreBase.set_driver_open(True)
    CoreBase.set_selected_instance(1)
    yield fake
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)


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


def test_device_proxy_scopes_every_call(fake_lib):
    device = Pyvium.device(2)

    result_code, label = device.get_device_status()

    assert (result_code, label) == (1, 'available_idle')
    # get_device_status calls IV_getdevicestatus twice: once in the
    # iviumsoft-running verifier and once for the result itself.
    assert fake_lib.calls == [
        ('IV_selectdevice', 2),
        ('IV_getdevicestatus', 2),
        ('IV_getdevicestatus', 2),
        ('IV_selectdevice', 1),
    ]


def test_device_factory_and_attributes(fake_lib):
    device = Pyvium.device(7)
    assert isinstance(device, PyviumDevice)
    assert device.instance_number == 7
    with pytest.raises(AttributeError):
        device.not_a_pyvium_method  # pylint: disable=pointless-statement


def test_get_active_instances_restores_previous_selection(fake_lib):
    Core.IV_selectdevice(2)

    active = Pyvium.get_active_iviumsoft_instances()

    assert active == [1, 2, 3]
    assert fake_lib.selected == 2


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
