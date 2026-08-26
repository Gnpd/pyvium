'''Tests for thread-safe channel scoping (Pyvium.on_channel,
Pyvium.instance(n).channel(m)) and the channel helpers.

The DLL is replaced with an in-memory fake that mimics its global-selection
behaviour for both instance and channel, so no IviumSoft installation or
hardware is required.'''
# Pytest idioms default pylint flags: fixtures are injected as same-named
# arguments (redefined-outer-name) and may be requested only for their side
# effects (unused-argument); tests and the fake-DLL methods are self-describing
# (missing-function-docstring) and the fake mirrors the DLL's IV_* names
# (invalid-name).
# The fake mirrors the DLL's own state, hence its attribute count
# (too-many-instance-attributes).
# pylint: disable=missing-function-docstring,redefined-outer-name,unused-argument,invalid-name,too-many-instance-attributes
import threading
import time

import pytest

from pyvium import ChannelStatus, Pyvium
from pyvium.core import Core
from pyvium.core.core_base import CoreBase, ffi
from pyvium.errors import DeviceNotConnectedToIviumSoftError, DriverNotOpenError
from pyvium.pyvium import generic_functions
from pyvium.pyvium.instance import PyviumChannel


class FakeIviumLib:
    '''Mimics the DLL: one global selected instance and one global selected
        channel, a per-channel device map, and a log of every call with the
        (instance, channel) selected when it happened.

        Device status per channel: 1 if connected, 0 if a device is present but
        not connected, 3 if no device sits behind the channel. The serial number
        is only readable while connected, matching IviumSoft.'''

    def __init__(self, active_instances=(1, 2, 3), channel_serials=None,
                 connected_channels=(), channel_aliases=None):
        self.active_instances = set(active_instances)
        self.channel_serials = channel_serials or {}  # channel -> serial
        # channel -> IV_SelectSn dropdown token, when it differs from the serial
        # (multichannel hardware). IV_readSN still reports the serial.
        self.channel_aliases = channel_aliases or {}
        self.connected = {channel: True for channel in connected_channels}
        self.selected = 1
        self.channel = 1
        self.calls = []
        self.call_delay = 0.0
        # IV_connect is asynchronous: the status stays 0 for this many polls
        # after the call before it reports connected. 0 = lands immediately.
        self.connect_settle_polls = 0
        self._settling = 0
        # Serial the connect actually grabs, when it does not honour IV_SelectSn.
        self.misgrab_serial = None
        # Optional hook fired on each status poll while a connect is settling.
        self.on_status_poll = None

    def IV_open(self):
        # The driver resets its selected instance to 1 on open; channel tabs
        # likewise start at 1.
        self.selected = 1
        self.channel = 1
        self.calls.append(('IV_open', self.selected, self.channel))
        return 0

    def IV_close(self):
        self.calls.append(('IV_close', self.selected, self.channel))
        return 0

    def IV_selectdevice(self, instance_number_ptr):
        self.selected = instance_number_ptr[0]
        self.calls.append(('IV_selectdevice', self.selected, self.channel))

    def IV_SelectChannel(self, channel_ptr):
        self.channel = channel_ptr[0]
        self.calls.append(('IV_SelectChannel', self.selected, self.channel))
        return 0

    def IV_getdevicestatus(self):
        if self.call_delay:
            time.sleep(self.call_delay)
        self.calls.append(('IV_getdevicestatus', self.selected, self.channel))
        if self.selected not in self.active_instances:
            return -1
        if self.connected.get(self.channel):
            if self._settling > 0:  # connect issued but not landed yet
                self._settling -= 1
                if self.on_status_poll is not None:
                    self.on_status_poll()
                return 0
            return 1
        return 0 if self.channel in self.channel_serials else 3

    def IV_readSN(self, buffer):
        serial = self.channel_serials.get(self.channel, '')
        encoded = serial.encode('utf-8')
        buffer[0:len(encoded)] = encoded  # buffer is zero-filled by ffi.new
        return 0

    def IV_SelectSn(self, sn_ptr):
        token = ffi.string(sn_ptr).decode('utf-8')
        # A channel with an alias is selectable ONLY by that alias: its serial
        # is not a token IviumSoft lists in the dropdown.
        selectable = {self.channel_aliases.get(channel, serial)
                      for channel, serial in self.channel_serials.items()}
        return 0 if token in selectable else -1

    def IV_connect(self, connection_ptr):
        self.calls.append(('IV_connect', self.selected, self.channel))
        connecting = connection_ptr[0] == 1
        self.connected[self.channel] = connecting
        if not connecting:
            return 0
        if self.misgrab_serial is not None:
            # IV_connect took the first-available device rather than the one
            # IV_SelectSn steered it to.
            self.channel_serials[self.channel] = self.misgrab_serial
        self._settling = self.connect_settle_polls
        return 0


@pytest.fixture
def fake_lib(monkeypatch):
    fake = FakeIviumLib(
        channel_serials={1: 'SN001', 2: 'SN002'},  # channel 3 has no device
        connected_channels=(1, 2),
    )
    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: fake))
    CoreBase.set_driver_open(True)
    CoreBase.set_selected_instance(1)
    CoreBase.set_selected_channel(1)
    yield fake
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)
    CoreBase.set_selected_channel(1)


def test_open_driver_resets_selected_channel_shadow(fake_lib):
    """A stale channel shadow must not survive a driver reopen.

        IV_SelectChannel treats its argument as a tab count, so restoring a
        stale channel 3 against a freshly restarted IviumSoft would open three
        tabs instead of switching to one."""
    Core.IV_SelectChannel(3)
    assert Core.get_selected_channel() == 3

    Pyvium.close_driver()
    Pyvium.open_driver()

    assert Core.get_selected_channel() == 1

    with Pyvium.on_channel(2):
        assert fake_lib.channel == 2

    assert fake_lib.channel == 1


def test_on_channel_selects_then_restores(fake_lib):
    with Pyvium.on_channel(3):
        assert fake_lib.channel == 3
    assert fake_lib.channel == 1


def test_on_channel_restores_on_exception(fake_lib):
    with pytest.raises(RuntimeError):
        with Pyvium.on_channel(3):
            raise RuntimeError('boom')
    assert fake_lib.channel == 1


def test_on_channel_nests_inside_on_instance(fake_lib):
    with Pyvium.on_instance(2):
        with Pyvium.on_channel(3):
            assert (fake_lib.selected, fake_lib.channel) == (2, 3)
        assert (fake_lib.selected, fake_lib.channel) == (2, 1)
    assert (fake_lib.selected, fake_lib.channel) == (1, 1)


def test_on_channel_requires_open_driver(fake_lib):
    CoreBase.set_driver_open(False)
    with pytest.raises(DriverNotOpenError):
        with Pyvium.on_channel(2):
            pass


def test_channel_handle_scopes_instance_and_channel(fake_lib):
    channel = Pyvium.instance(2).channel(3)

    result_code, label = channel.get_device_status()

    assert (result_code, label) == (3, 'no device available')
    # The handle selects instance and channel, runs the call (get_device_status
    # hits IV_getdevicestatus in the verifier and once for the result), then
    # restores channel and instance in reverse order.
    assert fake_lib.calls == [
        ('IV_selectdevice', 2, 1),
        ('IV_SelectChannel', 2, 3),
        ('IV_getdevicestatus', 2, 3),
        ('IV_getdevicestatus', 2, 3),
        ('IV_SelectChannel', 2, 1),
        ('IV_selectdevice', 1, 1),
    ]


def test_channel_handle_factory_and_attributes(fake_lib):
    channel = Pyvium.instance(7).channel(4)
    assert isinstance(channel, PyviumChannel)
    assert channel.instance_number == 7
    assert channel.channel_number == 4
    with pytest.raises(AttributeError):
        channel.not_a_pyvium_method  # pylint: disable=pointless-statement


def test_get_channel_statuses_scans_and_restores(fake_lib):
    Core.IV_SelectChannel(2)

    statuses = Pyvium.get_channel_statuses(3)

    assert statuses == [
        ChannelStatus(1, 'SN001', 1, 'available_idle'),
        ChannelStatus(2, 'SN002', 1, 'available_idle'),
        ChannelStatus(3, '', 3, 'no device available'),
    ]
    # The scan restores the channel selected before it ran.
    assert fake_lib.channel == 2


def test_connect_device_to_channel_targets_and_leaves_channel_active(fake_lib):
    fake_lib.connected[2] = False  # start disconnected

    Pyvium.connect_device_to_channel('SN002', 2)

    assert fake_lib.channel == 2
    assert fake_lib.connected.get(2) is True


def test_connect_device_to_channel_unknown_serial_raises(fake_lib):
    with pytest.raises(DeviceNotConnectedToIviumSoftError):
        Pyvium.connect_device_to_channel('NOPE', 2)


@pytest.fixture
def octostat_lib(monkeypatch):
    '''Multichannel hardware: each channel is selected by a dropdown token
        ("Oc-0-N") that differs from the serial IV_readSN reports.'''
    fake = FakeIviumLib(
        channel_serials={1: 'R31593', 2: 'R31594'},
        channel_aliases={1: 'Oc-0-1', 2: 'Oc-0-2'},
    )
    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: fake))
    CoreBase.set_driver_open(True)
    CoreBase.set_selected_instance(1)
    CoreBase.set_selected_channel(1)
    yield fake
    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)
    CoreBase.set_selected_channel(1)


def test_connect_device_to_channel_selects_by_alias_and_verifies_by_serial(octostat_lib):
    # The alias selects; the serial is what the read-back must match.
    Pyvium.connect_device_to_channel('R31594', 2, alias='Oc-0-2')

    assert octostat_lib.connected.get(2) is True
    assert octostat_lib.channel == 2


def test_connect_device_to_channel_without_an_alias_cannot_select_on_multichannel(
        octostat_lib):
    # Documents why the alias parameter exists: the serial is not a dropdown
    # token on multichannel hardware, so the selection itself fails.
    with pytest.raises(DeviceNotConnectedToIviumSoftError) as raised:
        Pyvium.connect_device_to_channel('R31594', 2)

    assert 'not found in the available device list' in str(raised.value)


def test_connect_device_to_channel_alias_still_catches_a_misgrab(octostat_lib, fast_settle):
    octostat_lib.misgrab_serial = 'R31593'  # a different channel's device landed

    with pytest.raises(DeviceNotConnectedToIviumSoftError) as raised:
        Pyvium.connect_device_to_channel('R31594', 2, alias='Oc-0-2')

    assert "grabbed 'R31593'" in str(raised.value)
    assert octostat_lib.connected.get(2) is False


@pytest.fixture
def fast_settle(monkeypatch):
    '''Shrinks the connect settle poll so the timeout paths run in milliseconds.'''
    monkeypatch.setattr(generic_functions, '_CONNECT_SETTLE_TIMEOUT_S', 0.05)
    monkeypatch.setattr(generic_functions, '_CONNECT_POLL_INTERVAL_S', 0.005)


def test_connect_device_to_channel_waits_for_the_async_connect(fake_lib, fast_settle):
    fake_lib.connected[2] = False
    fake_lib.connect_settle_polls = 3  # status reports 0 three times, then 1

    Pyvium.connect_device_to_channel('SN002', 2)

    assert fake_lib.connected.get(2) is True


def test_connect_device_to_channel_rejects_a_misgrab(fake_lib, fast_settle):
    fake_lib.connected[2] = False
    fake_lib.misgrab_serial = 'SN001'  # connect takes SN001 instead of SN002

    with pytest.raises(DeviceNotConnectedToIviumSoftError) as raised:
        Pyvium.connect_device_to_channel('SN002', 2)

    assert "grabbed 'SN001'" in str(raised.value)
    # The wrongly grabbed device is freed rather than left connected.
    assert fake_lib.connected.get(2) is False


def test_connect_device_to_channel_raises_when_connect_never_lands(fake_lib, fast_settle):
    fake_lib.connected[2] = False
    fake_lib.connect_settle_polls = 10_000  # never comes up within the timeout

    with pytest.raises(DeviceNotConnectedToIviumSoftError) as raised:
        Pyvium.connect_device_to_channel('SN002', 2)

    assert 'did not complete' in str(raised.value)


def test_connect_device_to_channel_holds_the_lock_while_the_connect_settles(
        fake_lib, fast_settle):
    '''The read-back is only meaningful if no other thread can retarget the
        driver while the connect is still in flight, which is exactly the
        second-connect-within-the-cooldown case that causes a mis-grab.'''
    fake_lib.connected[2] = False
    fake_lib.connect_settle_polls = 3
    acquired_from_another_thread = []

    def probe():
        # The lock is re-entrant, so it has to be probed off the connecting
        # thread to mean anything.
        acquired = Core.get_lock().acquire(blocking=False)
        acquired_from_another_thread.append(acquired)
        if acquired:
            Core.get_lock().release()

    def on_status_poll():
        prober = threading.Thread(target=probe)
        prober.start()
        prober.join()

    fake_lib.on_status_poll = on_status_poll

    Pyvium.connect_device_to_channel('SN002', 2)

    assert acquired_from_another_thread  # the settle loop really ran
    assert not any(acquired_from_another_thread)
    assert fake_lib.connected.get(2) is True


def test_scoped_channel_calls_from_threads_do_not_interleave(fake_lib):
    fake_lib.call_delay = 0.001  # widen the race window
    errors = []

    def worker(channel_number):
        for _ in range(20):
            try:
                with Pyvium.on_channel(channel_number):
                    assert fake_lib.channel == channel_number
                    Core.IV_getdevicestatus()
                    assert fake_lib.channel == channel_number
            except AssertionError as error:  # pragma: no cover
                errors.append(error)

    threads = [threading.Thread(target=worker, args=(number,))
               for number in (2, 3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
