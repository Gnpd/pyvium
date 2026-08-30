# Terminology: device, instance, channel

The words *device*, *instance*, and *channel* are overloaded in the Ivium
ecosystem, and the IviumSoft DLL reference itself warns about it. This page is
the canonical glossary for PYVIUM. It is grounded in the IviumSoft manual
(the help CHM that ships with IviumSoft), notably the *Software development
driver DLL* reference, *Multichannel control*, *MC Mode*, and *Ivium-n-Stat*
pages.

## The hierarchy

1. **Instrument** (hardware) — the physical box. Either a single-channel
   potentiostat/galvanostat, or a multichannel frame such as the Ivium-n-Stat
   or OctoStat that holds several modules.

2. **Channel** (hardware) — one potentiostat/galvanostat unit. For a
   single-channel instrument, instrument and channel are the same thing. A
   multichannel frame has many channels, **each with its own factory serial
   number** (an sModule has 1 channel, a dModule 2, a qModule 4). Channels can
   be given sequential numbers/descriptions via *Tools > Define channels*.

3. **IviumSoft instance** (software) — one running IviumSoft window/process.
   At most **32** instances run at once. Each instance is connected to **one**
   instrument/channel at a time (the "connected device").

## The trap: "device" usually means "instance"

The DLL reference states it directly:

> The command `IV_selectdevice` does not actually select a device but an
> IviumSoft instance. Multiple devices can only be operated with a separate
> IviumSoft instance. [...] The maximum of simultaneous operated IviumSoft
> instances is 32.

So in the raw DLL, the entire `device` vocabulary of `IV_selectdevice` is about
selecting an IviumSoft **instance**, not hardware. PYVIUM's high-level layer
names this correctly: `select_iviumsoft_instance`, `get_active_iviumsoft_instances`,
`on_instance`, `Pyvium.instance(n)` / `PyviumInstance`, and the parameter
`iviumsoft_instance_number`.

The DLL functions that genuinely act on the **hardware connected to the
selected instance** keep the `device` word, and there it is correct:
`connect_device`, `disconnect_device`, `get_device_status`,
`get_device_serial_number`. Read these as "the instrument connected inside the
currently selected instance".

`get_max_device_number` (`IV_MaxDevices`) returns the maximum number of
simultaneous IviumSoft instances (32 per the DLL reference), not a hardware
count; the `device` name there follows the DLL. Pending hardware confirmation.

## Three ways to address multiple channels

These are distinct mechanisms, not synonyms:

| Mechanism | DLL call | Count | PYVIUM API |
| --- | --- | --- | --- |
| One IviumSoft **instance** per channel | `IV_selectdevice(n)` | up to 32 instances | `select_iviumsoft_instance`, `on_instance`, `Pyvium.instance(n)`, `IviumsoftInstanceManager` |
| **Multichannel control** — tabs in one instance | `IV_SelectChannel(n)` | up to 32 tabs | `select_channel`, `on_channel`, `Pyvium.instance(n).channel(m)`, `get_channel_statuses`, `connect_device_to_channel` |
| **MC Mode** — one instance, one connected at a time | (UI) | up to 128 | not wrapped |

An Ivium-n-Stat physical channel can be driven **either** as its own IviumSoft
instance **or** as a tab under Multichannel control:

> Each channel can be connected to IviumSoft as a completely independent
> instrument. For each channel a new instance of IviumSoft can be opened.
> Alternatively, the channels can be operated using the Multichannel control.

In PYVIUM, `Pyvium.instance(n).channel(m)` is the Multichannel-control model:
channel tab `m` *within* instance `n`.

## "Channel" has at least five meanings

When you read "channel", check which one is meant:

1. **Multichannel-control tab** — `IV_SelectChannel` / `select_channel` /
   `PyviumChannel`. Software tab (1..32) inside one instance (Ivium-n-Soft).
   This is what `Pyvium.instance(n).channel(m)` selects.
2. **Physical hardware channel** — a potentiostat unit in an n-Stat/OctoStat,
   with its own factory serial number. The manual warns the tab number from (1)
   "is not necessarily the same as the actual physical channel".
3. **WE32 channel** — `IV_we32setchannel` / `set_we32_channel`. A
   working-electrode index (1..32) within a single MultiWE32 cell.
4. **Multiplexer channel** — `IV_setmuxchannel` / `set_mux_channel`. A
   multiplexer position.
5. **ADC channel** — `IV_getadc` external-port channel (0..7).

`PyviumChannel` and `select_channel` are always sense (1).

## Selection and connection ordering

The instrument list IviumSoft connects from is sorted **alphabetically by
serial number**. A bare `connect_device` / `IV_connect` grabs the first
available instrument in that list (the alphabetically-first serial), not the
physically-first channel. `select_serial_number` (`IV_SelectSn`) steers that
choice by putting a specific instrument at the top of the list, and is the
robust way to control which hardware a connection lands on.

`IV_connect` is also **asynchronous**: the status goes 0 -> 1 over a short
window after the call returns. A second connect issued before the first has
settled can land on a different instrument, so anything that needs to know
which device it got must wait for the connection to come up and read the serial
back (`IV_readSN`).

## "Serial" vs "alias": identity is not the selection token

Two different strings identify an instrument, and they coincide only on
single-channel hardware:

- **Serial** — the device *identity*, what `IV_readSN` /
  `get_device_serial_number` reports. Everything keys on this: status,
  ownership, the SQLite measurement files.
- **Alias** — the *selection token* `IV_SelectSn` takes, i.e. what IviumSoft
  lists in its device dropdown. On a multichannel frame (n-Stat, OctoStat) each
  channel has its own token, such as `Oc-0-3`, distinct from that channel's
  factory serial, and the serial will **not** select anything. On a
  single-channel device the two are equal.

`connect_device_to_channel(serial_number, channel, alias=...)` keeps them
apart: `alias` selects, `serial_number` is what the connection is verified
against. The serial -> alias mapping comes from the hardware configuration and
is **not** discoverable through the DLL, so resolving it is the caller's job.

"Alias" here is the selection token, never a human display name; keep any
friendly label as a separate field.

## Notes for PYVIUM development

- Prefer "instance" wherever the IviumSoft instance is meant; reserve "device"
  for the hardware connected inside a selected instance.
- When documenting channel APIs, qualify which sense is meant
  ("Multichannel-control tab", "WE32 channel", "multiplexer channel").
- Instance numbering follows launch order (DLL reference: opening instances in
  sequence makes `IV_selectdevice=1` the first, `=2` the second, ...), which is
  what `IviumsoftInstanceManager.launch` relies on. Stability of the numbering
  after an instance closes is not yet confirmed.
- `IV_SelectChannel`'s integer argument is the **number of tabs to open**, not a
  bounds-checked channel index, and the DLL does **not** validate it against the
  32-channel maximum: hardware-confirmed, `IV_SelectChannel(999)` makes IviumSoft
  open ~999 tabs. Recover by restarting IviumSoft or resetting the channel count
  in *Advanced parameters*. The high-level API (`select_channel`, `on_channel`,
  `get_channel_statuses`, `connect_device_to_channel`) guards against this with
  `_verify_channel_number`, raising `ValueError` outside 1..32 (`MAX_CHANNELS`).
- `IV_SelectChannel` is hardware-confirmed to **always return 0**, for valid and
  out-of-range arguments alike, so the return carries no success/failure status.
  `select_channel` therefore does not route it through `verify_result_code` (there
  is nothing to route); this is correct, not a pending item.
