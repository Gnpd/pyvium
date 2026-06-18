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
physically-first channel. `select_serial_number` (`IV_SelectSn`) targets a
specific instrument by serial number and is the robust way to control which
hardware a connection lands on.

## Notes for PYVIUM development

- Prefer "instance" wherever the IviumSoft instance is meant; reserve "device"
  for the hardware connected inside a selected instance.
- When documenting channel APIs, qualify which sense is meant
  ("Multichannel-control tab", "WE32 channel", "multiplexer channel").
- Instance numbering follows launch order (DLL reference: opening instances in
  sequence makes `IV_selectdevice=1` the first, `=2` the second, ...), which is
  what `IviumsoftInstanceManager.launch` relies on. Stability of the numbering
  after an instance closes is not yet confirmed.
- `IV_SelectChannel`'s return value convention is not documented in the DLL
  reference, so `select_channel` does not route it through `verify_result_code`
  yet (the reference only documents setter codes 0 / -1 / 1 / 2).
