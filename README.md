# Meshtastic_Mass_Text

English documentation. German version: [README.de.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.de.md)

Small Python utility for Meshtastic that sends direct messages to known nodes, with filtering, ACK handling, unattended mode, and a local config file.

## Features

- Sends to all known nodes or only filtered targets
- Filters by node ID, short name, or long name
- Supports wildcard filters such as `FR*`
- Can auto-detect serial ports or let you choose one interactively
- Waits for ACK, implicit ACK, or NAK when requested
- Stores runtime settings in a local `.cfg` file
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
- Local config: [send_to_all_nodes.cfg](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.cfg)
- German documentation: [README.de.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.de.md)

## First Run

If no config file exists yet, start the script once with parameters so it can create one.

Example:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --target-mode filter --filter "FR*" --message "Test message" --unattended --forcecfg
```

After that, a plain run is usually enough:

```powershell
python .\send_to_all_nodes.py
```

## Config File Behavior

- No config + parameters passed:
  - A config can be created from those parameters.
- Existing config + parameters passed:
  - Parameters are applied for the current run.
  - Whether the config is updated depends on `--forcecfg` / `--protectcfg`.
- Existing config + no parameters passed:
  - The script uses the config values.
- No config + no parameters passed:
  - The script shows an example command.

## Config Control

Use these switches to make config behavior explicit:

- `--forcecfg`
  - Always create or update the config when parameters are passed.
- `--protectcfg`
  - Never update the config for this run, even if parameters are passed.
- `--clear`
  - Delete the local config file and exit.

Examples:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --message "Hello" --forcecfg
```

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 0 --message "Private test" --protectcfg
```

```powershell
python .\send_to_all_nodes.py --clear
```

## Target Selection

The script can send:

- to all known nodes
- to filtered nodes only

Interactive mode:

```powershell
python .\send_to_all_nodes.py
```

You will be asked to choose:

- `1` for all known nodes
- `2` for filtered sending

Direct parameter examples:

```powershell
python .\send_to_all_nodes.py --target-mode all
python .\send_to_all_nodes.py --target-mode filter --filter "FR*"
python .\send_to_all_nodes.py --target-mode filter --filter "!55d8c9dc"
python .\send_to_all_nodes.py --target-mode filter --filter "Rico"
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

Example:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60
```

## Common Options

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
python .\send_to_all_nodes.py --unattended
python .\send_to_all_nodes.py --no-unattended
python .\send_to_all_nodes.py --forcecfg
python .\send_to_all_nodes.py --protectcfg
python .\send_to_all_nodes.py --clear
```

## Notes

- This tool is intended for controlled direct-message workflows.
- Please respect local radio regulations, duty-cycle limits, and other operators on the mesh.
