# Meshtastic_Mass_Text

English documentation. German version: [README.de.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.de.md)

Small Python utility for Meshtastic that sends direct messages to known nodes and can also listen for incoming traffic, with filtering, ACK handling, logging, unattended mode, and separate local config files for send and listen workflows.

## Features

- Sends to all known nodes or only filtered targets
- Can prefilter and then manually select nodes from a numbered list
- Filters by node ID, short name, or long name
- Supports wildcard filters such as `FR*`
- Can auto-detect serial ports or let you choose one interactively
- Waits for ACK, implicit ACK, or NAK when requested
- Can retry after implicit ACKs or NAKs
- Can listen for incoming packets with sender/channel/scope/content filters
- Can write send and listen activity to a local JSONL log file
- Can send a real group/broadcast message on a selected channel
- Can run in dry-run mode without transmitting
- Can keep a local history/inbox and show recent entries later
- Stores runtime settings in separate send/listen `.cfg` files
- Supports unattended runs without prompts
- Can protect the config from changes or force config updates explicitly

## Requirements

- Windows
- Python 3.14+
- Python packages:
  - `meshtastic`
  - `pyserial`

## Installation

```powershell
python -m pip install meshtastic pyserial
```

## Files

- Script: [send_to_all_nodes.py](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.py)
- Send config: [send_to_all_nodes.send.cfg](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.send.cfg)
- Listen config: [send_to_all_nodes.listen.cfg](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.listen.cfg)
- History file: [send_to_all_nodes.history.jsonl](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.history.jsonl)
- German documentation: [README.de.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.de.md)

## First Run

If no matching config file exists yet, start the script once with parameters so it can create one.

Config selection rules:

- No parameters, or `--mode send`, `--mode broadcast`, `--mode history`
  - Use the send config: `send_to_all_nodes.send.cfg`
- `--listen` or `--mode listen`
  - Use the listen config: `send_to_all_nodes.listen.cfg`

Example:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --target-mode select --filter "FR*" --selection "1,3" --retry-implicit-ack 1 --retry-nak 1 --message "Test message" --unattended --forcecfg
```

After that, a plain run is usually enough:

```powershell
python .\send_to_all_nodes.py
```

## Config File Behavior

- No active config + parameters passed:
  - The active config can be created from those parameters.
- Existing active config + parameters passed:
  - Parameters are applied for the current run.
  - Whether the active config is updated depends on `--forcecfg` / `--protectcfg`.
- Existing active config + no parameters passed:
  - The script uses the values from the active config.
- No active config + no parameters passed:
  - The script shows an example command.

## Config Control

Use these switches to make config behavior explicit:

- `--forcecfg`
  - Always create or update the active config when parameters are passed.
- `--protectcfg`
  - Never update the active config for this run, even if parameters are passed.
- `--clear`
  - Delete the active config file and exit.

Examples:

- Clear send config:

```powershell
python .\send_to_all_nodes.py --clear
```

- Clear listen config:

```powershell
python .\send_to_all_nodes.py --listen --clear
```

Store send settings in the send config:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --message "Hello" --forcecfg
```

Store listen settings in the listen config:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-filter "FR*" --text-only --forcecfg
```

## Target Selection

The script can send:

- to all known nodes
- to filtered nodes only
- to manually selected nodes from a numbered list, optionally after prefiltering

Interactive mode:

```powershell
python .\send_to_all_nodes.py
```

You will be asked to choose:

- `1` for all known nodes
- `2` for filtered sending
- `3` for manual list selection

Direct parameter examples:

```powershell
python .\send_to_all_nodes.py --target-mode all
python .\send_to_all_nodes.py --target-mode filter --filter "FR*"
python .\send_to_all_nodes.py --target-mode filter --filter "!55d8c9dc"
python .\send_to_all_nodes.py --target-mode filter --filter "Rico"
python .\send_to_all_nodes.py --target-mode select --filter "FR*"
python .\send_to_all_nodes.py --target-mode select --filter "FR*" --selection "1,3-4" --unattended
```

Filter rules:

- With wildcards such as `FR*` or `*mobil*`, the filter is treated as a pattern.
- Without wildcards, partial matches are allowed.
- Matching is performed against node ID, short name, and long name.

## Message and Unattended Mode

You can store a default message in the config:

```powershell
python .\send_to_all_nodes.py --message "Hello everyone" --forcecfg
```

Run without prompts:

```powershell
python .\send_to_all_nodes.py --unattended
```

Typical unattended run:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --target-mode filter --filter "FR*" --message "Hello everyone" --unattended --forcecfg
```

In unattended mode:

- no message prompt
- no target selection prompt
- no send confirmation prompt
- required values must come from parameters or the config

## ACK Handling

With `--ack`, the script waits for a response per message.

Possible outcomes:

- `Received an ACK.`
  - Delivery was acknowledged.
- `Sent, but not confirmed (implicit ACK only).`
  - The packet was sent, but not explicitly confirmed.
- `Received a NAK, error reason: ...`
  - Delivery failed with a negative acknowledgment.
- `Error ... No ACK/NAK ...`
  - Timeout without a response.

Retry controls:

- `--retry-implicit-ack 1`
  - Retry once if a packet only receives an implicit ACK.
- `--retry-nak 1`
  - Retry once if a packet receives a NAK.

Example:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --retry-implicit-ack 1 --retry-nak 1
```

## Listen Mode

The script can also stay connected and print matching incoming packets live.

Examples:

```powershell
python .\send_to_all_nodes.py --mode listen
python .\send_to_all_nodes.py --listen --listen-filter "FR*"
python .\send_to_all_nodes.py --listen --listen-channel-index 1
python .\send_to_all_nodes.py --listen --dm-only
python .\send_to_all_nodes.py --listen --group-only --text-only
```

Listen filters:

- `--listen-filter`
  - Matches sender node ID, short name, or long name
- `--listen-channel-index`
  - Only show packets from one channel
- `--dm-only`
  - Only show direct messages
- `--group-only`
  - Only show group/broadcast traffic
- `--text-only`
  - Only show text packets

Stop listen mode with `Ctrl+C`.

## Logging

Use `--log-file` to append JSONL records for send attempts and received packets.

Examples:

```powershell
python .\send_to_all_nodes.py --mode send --log-file .\meshtastic_log.jsonl
python .\send_to_all_nodes.py --listen --log-file .\meshtastic_log.jsonl
```

## Broadcast Mode

Use broadcast mode to send one message to the selected channel instead of a direct-message loop.

Examples:

```powershell
python .\send_to_all_nodes.py --mode broadcast --port COM7 --channel-index 0 --message "Hello private group"
python .\send_to_all_nodes.py --broadcast --port COM7 --channel-index 1 --message "Hello LongFast"
```

Notes:

- Broadcast mode ignores `--ack`
- Broadcast mode sends once to the selected channel
- This is usually the right mode when you want the message to appear in the group/channel chat

## Dry Run

Use `--dry-run` to preview what would be sent without transmitting any packets.

Examples:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --target-mode select --filter "FR*" --selection "1,3" --message "Preview only" --dry-run
python .\send_to_all_nodes.py --mode broadcast --port COM7 --channel-index 1 --message "Preview group post" --dry-run
```

## History

The script stores a local history file for received packets and sent messages. You can review it later without connecting to the device.

Examples:

```powershell
python .\send_to_all_nodes.py --mode history
python .\send_to_all_nodes.py --history --history-limit 50
python .\send_to_all_nodes.py --history --history-filter "Naunhof"
python .\send_to_all_nodes.py --history --history-file .\logs\history.jsonl
```

## Example Workflows

### Quick Everyday Use

Use the script interactively and let it guide you:

```powershell
python .\send_to_all_nodes.py
```

Send a direct message to all known nodes on `COM7`:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --target-mode all --message "Hello all"
```

Listen on `COM7` and only show text traffic:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --text-only
```

Post once to the channel chat instead of sending DMs:

```powershell
python .\send_to_all_nodes.py --mode broadcast --port COM7 --channel-index 1 --message "Hello group"
```

### Filtered Send Workflows

Send only to nodes matching a callsign pattern:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Net check" --ack
```

Send only to one exact node ID:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "!55d8c9dc" --message "Private test" --ack
```

Prefilter the list, then manually choose recipients:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*"
```

Run the same selection unattended with saved indexes:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*" --selection "1,3-5" --message "Scheduled ping" --unattended
```

### Reliable Delivery Workflows

Request ACKs and retry once on implicit ACK or NAK:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Please confirm" --ack --retry-implicit-ack 1 --retry-nak 1 --delay 1.5 --timeout 60
```

Use channel `0` for a small private group, but do not overwrite the saved cfg:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 0 --target-mode select --selection "1-3" --message "Private check-in" --ack --protectcfg
```

### Listen Workflows

Listen only to LongFast traffic on channel `1`:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-channel-index 1
```

Listen only to direct messages from nodes matching `FR*`:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-filter "FR*" --dm-only --text-only
```

Listen only to group traffic and keep non-text packets visible:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --group-only
```

### Logging Workflows

Send with ACK handling and write all attempts to a JSONL log:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Logged test" --ack --retry-implicit-ack 1 --retry-nak 1 --log-file .\logs\send_log.jsonl
```

Listen continuously and append all matching packets to a shared log:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --text-only --log-file .\logs\listen_log.jsonl
```

Keep a separate local history file while listening:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --text-only --history-file .\logs\history.jsonl
```

### Config-Centered Workflows

Create or refresh a reusable unattended profile:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*" --selection "1,2" --message "Routine message" --ack --retry-implicit-ack 1 --retry-nak 1 --log-file .\logs\routine.jsonl --unattended --forcecfg
```

Run later with only the saved config:

```powershell
python .\send_to_all_nodes.py
```

Listen with temporary settings but keep the saved config untouched:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-filter "FR*" --dm-only --text-only --protectcfg
```

Preview a broadcast without changing the config or transmitting:

```powershell
python .\send_to_all_nodes.py --mode broadcast --port COM7 --channel-index 0 --message "Test group" --dry-run --protectcfg
```

## Common Options Reference

```powershell
python .\send_to_all_nodes.py --help
python .\send_to_all_nodes.py --list-ports
python .\send_to_all_nodes.py --port COM7
python .\send_to_all_nodes.py --channel-index 1
python .\send_to_all_nodes.py --ack
python .\send_to_all_nodes.py --no-ack
python .\send_to_all_nodes.py --include-unmessageable
python .\send_to_all_nodes.py --no-include-unmessageable
python .\send_to_all_nodes.py --message "Hello"
python .\send_to_all_nodes.py --selection "1,3-5"
python .\send_to_all_nodes.py --retry-implicit-ack 1
python .\send_to_all_nodes.py --retry-nak 1
python .\send_to_all_nodes.py --listen
python .\send_to_all_nodes.py --broadcast
python .\send_to_all_nodes.py --history
python .\send_to_all_nodes.py --listen-filter "FR*"
python .\send_to_all_nodes.py --listen-channel-index 1
python .\send_to_all_nodes.py --dm-only
python .\send_to_all_nodes.py --group-only
python .\send_to_all_nodes.py --text-only
python .\send_to_all_nodes.py --log-file .\meshtastic_log.jsonl
python .\send_to_all_nodes.py --history-file .\meshtastic_history.jsonl
python .\send_to_all_nodes.py --history-filter "Naunhof"
python .\send_to_all_nodes.py --history-limit 50
python .\send_to_all_nodes.py --dry-run
python .\send_to_all_nodes.py --unattended
python .\send_to_all_nodes.py --no-unattended
python .\send_to_all_nodes.py --forcecfg
python .\send_to_all_nodes.py --protectcfg
python .\send_to_all_nodes.py --clear
```

## Notes

- This tool is intended for controlled direct-message workflows.
- Please respect local radio regulations, duty-cycle limits, and other operators on the mesh.
