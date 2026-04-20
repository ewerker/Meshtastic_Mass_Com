import argparse
import configparser
import fnmatch
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from meshtastic.serial_interface import SerialInterface
from pubsub import pub
from serial.tools import list_ports

CONFIG_PATH = Path(__file__).with_suffix(".cfg")
CONFIG_SECTION = "settings"
DEFAULT_SETTINGS = {
    "mode": "send",
    "port": "",
    "channel_index": 0,
    "ack": False,
    "include_unmessageable": False,
    "delay": 0.5,
    "timeout": 30,
    "final_wait": 5.0,
    "target_mode": "all",
    "target_filter": "",
    "selection": "",
    "message": "",
    "unattended": False,
    "log_file": "",
    "listen_filter": "",
    "listen_channel_index": None,
    "listen_dm_only": False,
    "listen_group_only": False,
    "listen_text_only": False,
    "retry_implicit_ack": 0,
    "retry_nak": 0,
}

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def init_console_colors() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        if handle == 0:
            return False
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        enable_vt = 0x0004
        if mode.value & enable_vt:
            return True
        return kernel32.SetConsoleMode(handle, mode.value | enable_vt) != 0
    except Exception:
        return False


COLOR_ENABLED = init_console_colors()


def colorize(text: str, color: str | None = None, *, bold: bool = False) -> str:
    if not COLOR_ENABLED:
        return text
    parts = []
    if bold:
        parts.append(ANSI_BOLD)
    if color:
        parts.append(ANSI_COLORS[color])
    parts.append(text)
    parts.append(ANSI_RESET)
    return "".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send Meshtastic direct messages or listen for incoming traffic with filters and logging."
    )
    parser.add_argument(
        "--mode",
        choices=("send", "listen"),
        default=None,
        help="Run in send mode or listen mode.",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Shortcut for --mode listen.",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port of the Meshtastic device. If omitted, available ports are auto-detected.",
    )
    parser.add_argument(
        "--channel-index",
        type=int,
        default=None,
        help="Channel index to use for sending direct messages (default: 0).",
    )
    parser.add_argument(
        "--ack",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Request reliable delivery and wait for ACK/NAK for each message.",
    )
    parser.add_argument(
        "--include-unmessageable",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Also try nodes that are marked as unmessageable.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Delay in seconds between recipients or retries (default: 0.5).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Connection timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--final-wait",
        type=float,
        default=None,
        help="Seconds to keep the connection open after the last send when not waiting for ACKs (default: 5.0).",
    )
    parser.add_argument(
        "--retry-implicit-ack",
        type=int,
        default=None,
        help="How many times to retry a message after an implicit ACK.",
    )
    parser.add_argument(
        "--retry-nak",
        type=int,
        default=None,
        help="How many times to retry a message after a NAK.",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="Only show available serial ports and exit.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete the cfg file in the script directory and exit.",
    )
    cfg_group = parser.add_mutually_exclusive_group()
    cfg_group.add_argument(
        "--forcecfg",
        action="store_true",
        help="Always write/update the cfg when parameters are passed.",
    )
    cfg_group.add_argument(
        "--protectcfg",
        action="store_true",
        help="Never write/update the cfg for this run, even when parameters are passed.",
    )
    parser.add_argument(
        "--target-mode",
        choices=("all", "filter", "select"),
        default=None,
        help="Send to all known nodes, all filtered matches, or manually selected matches from a list.",
    )
    parser.add_argument(
        "--filter",
        dest="target_filter",
        default=None,
        help="Filter for node selection, e.g. !55d8c9dc, Rico, or FR*.",
    )
    parser.add_argument(
        "--selection",
        default=None,
        help="Comma-separated 1-based indexes or ranges from the displayed/prefiltered list, e.g. 1,3-5.",
    )
    parser.add_argument(
        "--message",
        default=None,
        help="Default message text to send. If omitted, the script asks interactively unless a message exists in the cfg.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional JSONL log file. Relative paths are stored next to the script.",
    )
    parser.add_argument(
        "--listen-filter",
        default=None,
        help="Only show received packets whose sender matches this filter.",
    )
    parser.add_argument(
        "--listen-channel-index",
        type=int,
        default=None,
        help="Only show received packets for the specified channel index.",
    )
    listen_scope_group = parser.add_mutually_exclusive_group()
    listen_scope_group.add_argument(
        "--dm-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Only show direct messages while listening.",
    )
    listen_scope_group.add_argument(
        "--group-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Only show group/broadcast traffic while listening.",
    )
    parser.add_argument(
        "--text-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Only show text packets while listening.",
    )
    parser.add_argument(
        "-u",
        "--unattended",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run without confirmation prompts. Missing required values must come from parameters or cfg.",
    )
    return parser


def example_command() -> str:
    python_exe = Path(sys.executable)
    script_path = Path(__file__)
    return (
        f'"{python_exe}" "{script_path}" --mode send --port COM7 --channel-index 1 --ack '
        '--delay 1.5 --timeout 60 --target-mode select --filter "FR*" --selection "1,3" '
        '--retry-implicit-ack 1 --retry-nak 1 --message "Test message" --unattended'
    )


def load_config() -> dict:
    settings = DEFAULT_SETTINGS.copy()
    if not CONFIG_PATH.exists():
        return settings

    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    if not parser.has_section(CONFIG_SECTION):
        return settings

    section = parser[CONFIG_SECTION]
    settings["mode"] = section.get("mode", fallback=settings["mode"])
    settings["port"] = section.get("port", fallback=settings["port"])
    settings["channel_index"] = section.getint("channel_index", fallback=settings["channel_index"])
    settings["ack"] = section.getboolean("ack", fallback=settings["ack"])
    settings["include_unmessageable"] = section.getboolean(
        "include_unmessageable", fallback=settings["include_unmessageable"]
    )
    settings["delay"] = section.getfloat("delay", fallback=settings["delay"])
    settings["timeout"] = section.getint("timeout", fallback=settings["timeout"])
    settings["final_wait"] = section.getfloat("final_wait", fallback=settings["final_wait"])
    settings["target_mode"] = section.get("target_mode", fallback=settings["target_mode"])
    settings["target_filter"] = section.get("target_filter", fallback=settings["target_filter"])
    settings["selection"] = section.get("selection", fallback=settings["selection"])
    settings["message"] = section.get("message", fallback=settings["message"])
    settings["unattended"] = section.getboolean("unattended", fallback=settings["unattended"])
    settings["log_file"] = section.get("log_file", fallback=settings["log_file"])
    settings["listen_filter"] = section.get("listen_filter", fallback=settings["listen_filter"])
    listen_channel_raw = section.get("listen_channel_index", fallback="")
    settings["listen_channel_index"] = int(listen_channel_raw) if listen_channel_raw else None
    settings["listen_dm_only"] = section.getboolean("listen_dm_only", fallback=settings["listen_dm_only"])
    settings["listen_group_only"] = section.getboolean(
        "listen_group_only", fallback=settings["listen_group_only"]
    )
    settings["listen_text_only"] = section.getboolean("listen_text_only", fallback=settings["listen_text_only"])
    settings["retry_implicit_ack"] = section.getint(
        "retry_implicit_ack", fallback=settings["retry_implicit_ack"]
    )
    settings["retry_nak"] = section.getint("retry_nak", fallback=settings["retry_nak"])
    return settings


def save_config(settings: dict) -> None:
    parser = configparser.ConfigParser()
    parser[CONFIG_SECTION] = {
        "mode": settings["mode"] or "send",
        "port": settings["port"] or "",
        "channel_index": str(settings["channel_index"]),
        "ack": str(settings["ack"]).lower(),
        "include_unmessageable": str(settings["include_unmessageable"]).lower(),
        "delay": str(settings["delay"]),
        "timeout": str(settings["timeout"]),
        "final_wait": str(settings["final_wait"]),
        "target_mode": settings["target_mode"] or "all",
        "target_filter": settings["target_filter"] or "",
        "selection": settings["selection"] or "",
        "message": settings["message"] or "",
        "unattended": str(settings["unattended"]).lower(),
        "log_file": settings["log_file"] or "",
        "listen_filter": settings["listen_filter"] or "",
        "listen_channel_index": "" if settings["listen_channel_index"] is None else str(settings["listen_channel_index"]),
        "listen_dm_only": str(settings["listen_dm_only"]).lower(),
        "listen_group_only": str(settings["listen_group_only"]).lower(),
        "listen_text_only": str(settings["listen_text_only"]).lower(),
        "retry_implicit_ack": str(settings["retry_implicit_ack"]),
        "retry_nak": str(settings["retry_nak"]),
    }
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        parser.write(config_file)


def collect_cli_overrides(args: argparse.Namespace) -> dict:
    overrides = {}
    for key in (
        "mode",
        "port",
        "channel_index",
        "ack",
        "include_unmessageable",
        "delay",
        "timeout",
        "final_wait",
        "target_mode",
        "target_filter",
        "selection",
        "message",
        "unattended",
        "log_file",
        "listen_filter",
        "listen_channel_index",
        "listen_dm_only",
        "listen_group_only",
        "listen_text_only",
        "retry_implicit_ack",
        "retry_nak",
    ):
        value = getattr(args, key, None)
        if value is not None:
            overrides[key] = value

    if args.listen:
        overrides["mode"] = "listen"
    if "selection" in overrides and "target_mode" not in overrides:
        overrides["target_mode"] = "select"
    elif "target_filter" in overrides and "target_mode" not in overrides:
        overrides["target_mode"] = "filter"

    return overrides


def resolve_settings(args: argparse.Namespace) -> dict | None:
    cli_overrides = collect_cli_overrides(args)
    config_exists = CONFIG_PATH.exists()
    should_write_cfg = bool(cli_overrides) and not args.protectcfg

    if not config_exists and not cli_overrides:
        print(f"No configuration file found: {CONFIG_PATH}")
        print("Run the script with parameters the first time, for example:")
        print(example_command())
        return None

    settings = load_config()

    if cli_overrides:
        settings.update(cli_overrides)
        if should_write_cfg:
            save_config(settings)
            if config_exists:
                print(colorize(f"Configuration updated: {CONFIG_PATH}", "green"))
            else:
                print(colorize(f"Configuration created: {CONFIG_PATH}", "green"))
        elif args.protectcfg:
            print(colorize("CFG protection is active, configuration changes will not be saved for this run.", "yellow"))
    elif config_exists:
        print(colorize(f"Using configuration from: {CONFIG_PATH}", "cyan"))

    return settings


def clear_config() -> int:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
        print(colorize(f"Configuration deleted: {CONFIG_PATH}", "green"))
    else:
        print(colorize(f"No configuration file present: {CONFIG_PATH}", "yellow"))
    return 0


def prompt_message(default_message: str | None = None, unattended: bool = False) -> str:
    if unattended:
        message = (default_message or "").strip()
        if not message:
            raise ValueError("No message is set. Please provide --message or store one in the cfg.")
        return message

    prompt = "Message text to send"
    if default_message:
        prompt += f' [{default_message}]'
    prompt += ": "
    message = input(prompt).strip()
    if not message and default_message:
        message = default_message.strip()
    if not message:
        raise ValueError("Empty messages are not sent.")
    return message


def get_local_node_num(interface: SerialInterface):
    my_info = getattr(interface, "myInfo", None)
    if my_info is None:
        return None

    for attr in ("myNodeNum", "my_node_num"):
        if hasattr(my_info, attr):
            return getattr(my_info, attr)
    return None


def get_available_ports() -> list:
    return list(list_ports.comports())


def print_available_ports(ports: list) -> None:
    if not ports:
        print(colorize("No serial ports found.", "red"))
        return

    print("Available serial ports:")
    for index, port in enumerate(ports, start=1):
        description = port.description or "no description"
        hwid = port.hwid or "no HWID"
        print(f"  {index}. {port.device} - {description} [{hwid}]")


def choose_port_interactively(ports: list) -> str:
    while True:
        choice = input("Which port do you want to use? Enter the number: ").strip()
        if not choice.isdigit():
            print("Please enter a valid number.")
            continue

        selected_index = int(choice)
        if 1 <= selected_index <= len(ports):
            return ports[selected_index - 1].device

        print("That number is outside the list.")


def resolve_port(cli_port: str | None, unattended: bool = False) -> str:
    if cli_port:
        return cli_port

    ports = get_available_ports()
    if not ports:
        raise RuntimeError("No serial ports found. Please connect a device or provide --port.")

    if len(ports) == 1:
        selected = ports[0].device
        print(f"One serial port found, selecting it automatically: {selected}")
        return selected

    if unattended:
        raise RuntimeError(
            "Multiple serial ports found. Please provide --port or save a port in the cfg."
        )

    print_available_ports(ports)
    return choose_port_interactively(ports)


def collect_recipients(interface: SerialInterface, include_unmessageable: bool) -> list[dict]:
    recipients: list[dict] = []
    local_num = get_local_node_num(interface)

    for node_id, node in sorted(interface.nodes.items()):
        user = node.get("user", {})
        if not user:
            continue
        if node.get("num") == local_num:
            continue
        if user.get("isUnmessagable") and not include_unmessageable:
            continue

        recipients.append(
            {
                "node_id": node_id,
                "label": user.get("longName") or user.get("shortName") or node_id,
                "long_name": user.get("longName", ""),
                "short_name": user.get("shortName", ""),
            }
        )

    return recipients


def recipient_matches_filter(recipient: dict, target_filter: str) -> bool:
    pattern = target_filter.casefold()
    candidates = [
        recipient["node_id"],
        recipient["label"],
        recipient["short_name"],
        recipient["long_name"],
    ]
    normalized = [candidate.casefold() for candidate in candidates if candidate]

    has_wildcards = any(char in target_filter for char in "*?[]")
    if has_wildcards:
        return any(fnmatch.fnmatch(value, pattern) for value in normalized)

    return any(pattern in value for value in normalized)


def prompt_target_mode(
    cli_target_mode: str | None,
    cli_target_filter: str | None,
    selection: str | None,
    unattended: bool = False,
) -> tuple[str, str | None, str | None]:
    resolved_filter = (cli_target_filter or "").strip() or None
    resolved_selection = (selection or "").strip() or None
    if cli_target_mode == "all":
        return "all", None, resolved_selection
    if cli_target_mode == "filter":
        if resolved_filter:
            return "filter", resolved_filter, resolved_selection
        if unattended:
            raise ValueError("Target mode 'filter' requires --filter or a saved cfg value.")
    if cli_target_mode == "select":
        return "select", resolved_filter, resolved_selection

    if unattended:
        return "all", resolved_filter, resolved_selection

    while True:
        print()
        print("Target selection:")
        print("  1. Send to all known nodes")
        print("  2. Send to all filtered matches")
        print("  3. Select nodes from a list")
        choice = input("Choice [1/2/3]: ").strip().lower()
        if choice in {"1", "all"}:
            return "all", None, None
        if choice in {"2", "filter"}:
            target_filter = input("Enter a filter (for example !55d8c9dc, Rico, or FR*): ").strip()
            if target_filter:
                return "filter", target_filter, None
            print("Please enter a non-empty filter.")
            continue
        if choice in {"3", "select"}:
            target_filter = input(
                "Optional prefilter for the list (for example !55d8c9dc, Rico, or FR*), or press Enter for all: "
            ).strip()
            return "select", target_filter or None, None
        print("Please enter 1, 2, or 3.")


def filter_recipients(recipients: list[dict], target_filter: str | None) -> list[dict]:
    if not target_filter:
        return list(recipients)
    return [recipient for recipient in recipients if recipient_matches_filter(recipient, target_filter)]


def print_recipient_list(recipients: list[dict]) -> None:
    for index, recipient in enumerate(recipients, start=1):
        print(f"  {index:>2}. {recipient['label']} ({recipient['node_id']})")


def parse_selection_spec(selection: str, max_index: int) -> list[int]:
    selected: set[int] = set()
    for part in selection.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            if not start_text.strip().isdigit() or not end_text.strip().isdigit():
                raise ValueError(f"Invalid range: {token}")
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError(f"Invalid range: {token}")
            for index in range(start, end + 1):
                if not 1 <= index <= max_index:
                    raise ValueError(f"Selection index out of range: {index}")
                selected.add(index)
            continue

        if not token.isdigit():
            raise ValueError(f"Invalid selection entry: {token}")

        index = int(token)
        if not 1 <= index <= max_index:
            raise ValueError(f"Selection index out of range: {index}")
        selected.add(index)

    if not selected:
        raise ValueError("No valid selection entries were provided.")

    return sorted(selected)


def choose_recipients_from_list(
    recipients: list[dict], selection: str | None, unattended: bool = False
) -> tuple[list[dict], str]:
    if not recipients:
        return [], "manual selection"

    print()
    print("Selectable nodes:")
    print_recipient_list(recipients)

    if unattended:
        if not selection:
            raise ValueError("Selection is required in unattended mode when target mode is 'select'.")
        indices = parse_selection_spec(selection, len(recipients))
    else:
        selection_prompt = (
            "Enter selection indexes or ranges (for example 1,3-5)"
            if not selection
            else f"Enter selection indexes or ranges [{selection}]"
        )
        while True:
            raw = input(f"{selection_prompt}: ").strip()
            if not raw and selection:
                raw = selection
            try:
                indices = parse_selection_spec(raw, len(recipients))
                break
            except ValueError as exc:
                print(exc)

    selected = [recipients[index - 1] for index in indices]
    description = f"manual selection [{','.join(str(index) for index in indices)}]"
    return selected, description


def select_recipients(
    recipients: list[dict],
    cli_target_mode: str | None,
    cli_target_filter: str | None,
    selection: str | None,
    unattended: bool = False,
) -> tuple[list[dict], str]:
    target_mode, target_filter, resolved_selection = prompt_target_mode(
        cli_target_mode, cli_target_filter, selection, unattended
    )
    if target_mode == "all":
        return recipients, "all known nodes"

    filtered = filter_recipients(recipients, target_filter)
    if target_mode == "filter":
        return filtered, f'filter "{target_filter}"'

    selected, selection_description = choose_recipients_from_list(filtered, resolved_selection, unattended)
    if target_filter:
        return selected, f'{selection_description} from filter "{target_filter}"'
    return selected, selection_description


def confirm_send(message: str, recipients: list[dict], target_description: str, unattended: bool = False) -> bool:
    print()
    print(f'Message: "{message}"')
    print(f"Target mode: {target_description}")
    print(f"Recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"  - {recipient['label']} ({recipient['node_id']})")
    print()
    if unattended:
        print("Unattended mode is active, sending without confirmation.")
        return True
    answer = input("Send now? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def wait_for_ack(interface: SerialInterface, message: str, node_id: str, channel_index: int, timeout: int):
    ack_event = threading.Event()
    ack_result = {"packet": None}

    def onAckNak(packet):
        ack_result["packet"] = packet
        ack_event.set()

    interface._acknowledgment.reset()
    packet = interface.sendText(
        message,
        destinationId=node_id,
        wantAck=True,
        onResponse=onAckNak,
        channelIndex=channel_index,
    )

    if not ack_event.wait(timeout):
        raise TimeoutError(f"No ACK/NAK received within {timeout}s for packet ID {packet.id}")

    return packet, ack_result["packet"]


def classify_ack(interface: SerialInterface, ack_packet: dict | None) -> tuple[str, str]:
    if not ack_packet:
        return "timeout", "No ACK/NAK packet received."

    routing = ack_packet.get("decoded", {}).get("routing", {})
    error_reason = routing.get("errorReason", "NONE")
    if error_reason != "NONE":
        return "nak", f"Received a NAK, error reason: {error_reason}"

    if int(ack_packet.get("from", -1)) == interface.localNode.nodeNum:
        return "implicit_ack", "Sent, but not confirmed (implicit ACK only)."

    return "ack", "Received an ACK."


def now_string() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_log_path(log_file: str | None) -> Path | None:
    if not log_file:
        return None
    path = Path(log_file)
    if not path.is_absolute():
        path = CONFIG_PATH.parent / path
    return path


def sanitize_for_json(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key == "raw":
                continue
            sanitized[key] = sanitize_for_json(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return value


def append_jsonl(log_path: Path | None, event_type: str, payload: dict) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_string(),
        "event": event_type,
        **payload,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")


def get_recipient_label(interface: SerialInterface, node_id: str | None) -> str:
    if not node_id:
        return "unknown"
    node = interface.nodes.get(node_id, {})
    user = node.get("user", {})
    return user.get("longName") or user.get("shortName") or node_id


def extract_text(packet: dict) -> str | None:
    decoded = packet.get("decoded", {})
    text = decoded.get("text")
    if text:
        return text
    payload = decoded.get("payload")
    if isinstance(payload, (bytes, bytearray)):
        try:
            return bytes(payload).decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def local_channel_infos(interface: SerialInterface) -> list[dict]:
    try:
        return interface.localNode.get_channels_with_hash()
    except Exception:
        return []


def channel_from_hash(interface: SerialInterface, raw_channel: int) -> dict | None:
    for info in local_channel_infos(interface):
        if info.get("hash") == raw_channel:
            return info
    return None


def packet_channel(interface: SerialInterface, packet: dict) -> int | None:
    value = packet.get("channel")
    if value is None:
        value = packet.get("channelIndex")
    if value is None:
        return 0
    try:
        channel_index = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= channel_index <= 7:
        return channel_index
    hashed_channel = channel_from_hash(interface, channel_index)
    if hashed_channel is not None:
        return hashed_channel.get("index")
    return None


def packet_raw_channel(packet: dict):
    value = packet.get("channel")
    if value is None:
        value = packet.get("channelIndex")
    return value


def channel_name(interface: SerialInterface, channel_index: int | None) -> str | None:
    if channel_index is None:
        return None
    for info in local_channel_infos(interface):
        if info.get("index") == channel_index:
            if info.get("name"):
                return str(info["name"])
            role = info.get("role")
            if role == "PRIMARY":
                return "Primary"
            if role == "SECONDARY":
                return f"Channel {channel_index}"
            return None
    try:
        channel = interface.localNode.getChannelByChannelIndex(channel_index)
    except Exception:
        channel = None
    if channel is None:
        return None
    settings = getattr(channel, "settings", None)
    if settings is None:
        return None
    name = getattr(settings, "name", None)
    if name:
        return str(name)
    return None


def is_direct_message(packet: dict) -> bool:
    to_id = packet.get("toId")
    return bool(to_id and to_id != "^all")


def build_sender_candidate(interface: SerialInterface, packet: dict) -> dict:
    node_id = packet.get("fromId") or str(packet.get("from", "unknown"))
    node = interface.nodes.get(node_id, {})
    user = node.get("user", {})
    label = user.get("longName") or user.get("shortName") or node_id
    return {
        "node_id": node_id,
        "label": label,
        "short_name": user.get("shortName", ""),
        "long_name": user.get("longName", ""),
    }


def packet_matches_listen_filters(interface: SerialInterface, packet: dict, settings: dict) -> bool:
    if settings["listen_filter"]:
        sender = build_sender_candidate(interface, packet)
        if not recipient_matches_filter(sender, settings["listen_filter"]):
            return False

    if settings["listen_channel_index"] is not None:
        if packet_channel(interface, packet) != settings["listen_channel_index"]:
            return False

    if settings["listen_dm_only"] and not is_direct_message(packet):
        return False

    if settings["listen_group_only"] and is_direct_message(packet):
        return False

    if settings["listen_text_only"] and not extract_text(packet):
        return False

    return True


def build_receive_record(interface: SerialInterface, packet: dict) -> dict:
    sender_id = packet.get("fromId") or str(packet.get("from", "unknown"))
    sender_label = get_recipient_label(interface, sender_id)
    receiver_id = packet.get("toId") or str(packet.get("to", "unknown"))
    text = extract_text(packet)
    channel = packet_channel(interface, packet)
    raw_channel = packet_raw_channel(packet)
    hashed_channel = None
    if raw_channel is not None and channel is not None:
        try:
            raw_value = int(raw_channel)
        except (TypeError, ValueError):
            raw_value = None
        if raw_value is not None and not 0 <= raw_value <= 7:
            hashed_channel = channel_from_hash(interface, raw_value)
    portnum = packet.get("decoded", {}).get("portnum", "UNKNOWN")
    dm = is_direct_message(packet)
    return {
        "from_id": sender_id,
        "from_label": sender_label,
        "to_id": receiver_id,
        "channel_index": channel,
        "channel_name": channel_name(interface, channel),
        "raw_channel": raw_channel,
        "channel_hash_match": hashed_channel,
        "scope": "dm" if dm else "group",
        "portnum": portnum,
        "text": text,
        "packet": sanitize_for_json(packet),
    }


def format_port_label(portnum) -> str:
    value = str(portnum or "UNKNOWN")
    labels = {
        "TEXT_MESSAGE_APP": "text",
        "TEXT_MESSAGE_COMPRESSED_APP": "text-compressed",
        "NODEINFO_APP": "nodeinfo",
        "POSITION_APP": "position",
        "TELEMETRY_APP": "telemetry",
        "ROUTING_APP": "routing",
        "ADMIN_APP": "admin",
        "NEIGHBORINFO_APP": "neighborinfo",
        "TRACEROUTE_APP": "traceroute",
        "WAYPOINT_APP": "waypoint",
        "RANGE_TEST_APP": "rangetest",
        "STORE_FORWARD_APP": "storeforward",
        "PRIVATE_APP": "private",
        "ATAK_PLUGIN": "atak",
        "MAP_REPORT_APP": "map-report",
        "ALERT_APP": "alert",
        "REPLY_APP": "reply",
    }
    return labels.get(value, value.lower().replace("_app", "").replace("_", "-"))


def format_receive_line(record: dict) -> str:
    scope_text = record["scope"].upper()
    scope = colorize(scope_text, "green" if scope_text == "DM" else "cyan", bold=True)
    if record["channel_index"] is None:
        if record.get("raw_channel") is None:
            channel = "unknown"
        else:
            channel = f"unknown(raw={record['raw_channel']})"
    elif record.get("channel_hash_match"):
        channel = (
            f"{record['channel_index']}:{record.get('channel_name') or 'unknown'}"
            f"(hash={record['raw_channel']})"
        )
    elif record.get("channel_name"):
        channel = f"{record['channel_index']}:{record['channel_name']}"
    else:
        channel = str(record["channel_index"])
    port_label = format_port_label(record["portnum"])
    channel = colorize(f"ch={channel}", "magenta")
    port_label = colorize(f"port={port_label}", "blue")
    sender = colorize(f"{record['from_label']} ({record['from_id']})", "white", bold=True)
    target = colorize(record["to_id"], "white")
    text = record["text"]
    if text:
        return (
            f"[{now_string()}] {scope} {channel} {port_label} "
            f"{sender} -> {target}: {text}"
        )
    return (
        f"[{now_string()}] {scope} {channel} {port_label} "
        f"{sender} -> {target} "
        f"[{record['portnum']}]"
    )


def run_listen_mode(interface: SerialInterface, settings: dict) -> int:
    log_path = resolve_log_path(settings["log_file"])
    received_count = 0

    print("Listen mode started. Press Ctrl+C to stop.")
    if settings["listen_filter"]:
        print(f"Sender filter: {settings['listen_filter']}")
    if settings["listen_channel_index"] is not None:
        print(f"Channel filter: {settings['listen_channel_index']}")
    if settings["listen_dm_only"]:
        print("Scope filter: direct messages only")
    if settings["listen_group_only"]:
        print("Scope filter: group traffic only")
    if settings["listen_text_only"]:
        print("Content filter: text packets only")
    if log_path:
        print(colorize(f"Logging to: {log_path}", "cyan"))

    def on_receive(packet, interface):
        nonlocal received_count
        if not packet_matches_listen_filters(interface, packet, settings):
            return
        received_count += 1
        record = build_receive_record(interface, packet)
        print(format_receive_line(record))
        append_jsonl(log_path, "receive", record)

    pub.subscribe(on_receive, "meshtastic.receive")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        print(colorize(f"Stopped listening. Matching packets shown: {received_count}", "green"))
        return 0
    finally:
        try:
            pub.unsubscribe(on_receive, "meshtastic.receive")
        except Exception:
            pass


def send_with_ack_retry(
    interface: SerialInterface,
    recipient: dict,
    message: str,
    settings: dict,
    log_path: Path | None,
) -> tuple[str, str, int, int]:
    node_id = recipient["node_id"]
    label = recipient["label"]
    attempt = 0
    implicit_retries_used = 0
    nak_retries_used = 0

    while True:
        attempt += 1
        packet, ack_packet = wait_for_ack(
            interface,
            message,
            node_id,
            settings["channel_index"],
            settings["timeout"],
        )
        packet_id = getattr(packet, "id", "unknown")
        ack_kind, ack_message = classify_ack(interface, ack_packet)
        append_jsonl(
            log_path,
            "send_attempt",
            {
                "recipient_id": node_id,
                "recipient_label": label,
                "attempt": attempt,
                "packet_id": packet_id,
                "result": ack_kind,
                "message": message,
                "channel_index": settings["channel_index"],
                "ack_packet": sanitize_for_json(ack_packet),
            },
        )

        if ack_kind == "implicit_ack" and implicit_retries_used < settings["retry_implicit_ack"]:
            implicit_retries_used += 1
            print(
                colorize(
                    f"{ack_message} {label} ({node_id}), packet ID {packet_id}. "
                    f"Retrying implicit ACK ({implicit_retries_used}/{settings['retry_implicit_ack']}) ...",
                    "yellow",
                )
            )
            time.sleep(settings["delay"])
            continue

        if ack_kind == "nak" and nak_retries_used < settings["retry_nak"]:
            nak_retries_used += 1
            print(
                colorize(
                    f"{ack_message} {label} ({node_id}), packet ID {packet_id}. "
                    f"Retrying NAK ({nak_retries_used}/{settings['retry_nak']}) ...",
                    "yellow",
                )
            )
            time.sleep(settings["delay"])
            continue

        return ack_kind, ack_message, packet_id, attempt


def run_send_mode(interface: SerialInterface, settings: dict) -> int:
    try:
        message = prompt_message(settings["message"], settings["unattended"])
    except ValueError as exc:
        print(colorize(str(exc), "red"))
        return 1

    log_path = resolve_log_path(settings["log_file"])
    recipients = collect_recipients(interface, settings["include_unmessageable"])

    if not recipients:
        print(colorize("No matching known nodes found.", "red"))
        return 1

    try:
        recipients, target_description = select_recipients(
            recipients,
            settings["target_mode"],
            settings["target_filter"],
            settings["selection"],
            settings["unattended"],
        )
    except ValueError as exc:
        print(colorize(str(exc), "red"))
        return 1

    if not recipients:
        print(colorize("No nodes match the selected filter or selection.", "red"))
        return 1

    if not confirm_send(message, recipients, target_description, settings["unattended"]):
        print(colorize("Cancelled.", "yellow"))
        return 0

    if log_path:
        print(colorize(f"Logging to: {log_path}", "cyan"))

    sent = 0
    failed = 0
    acked = 0
    implicit_acks = 0
    total_attempts = 0

    for recipient in recipients:
        node_id = recipient["node_id"]
        label = recipient["label"]
        try:
            if settings["ack"]:
                ack_kind, ack_message, packet_id, attempts_used = send_with_ack_retry(
                    interface,
                    recipient,
                    message,
                    settings,
                    log_path,
                )
                total_attempts += attempts_used
                if ack_kind == "ack":
                    acked += 1
                    print(colorize(f"{ack_message} {label} ({node_id}), packet ID {packet_id}", "green"))
                elif ack_kind == "implicit_ack":
                    implicit_acks += 1
                    print(colorize(f"{ack_message} {label} ({node_id}), packet ID {packet_id}", "yellow"))
                else:
                    failed += 1
                    print(colorize(f"{ack_message} {label} ({node_id}), packet ID {packet_id}", "red"))
            else:
                packet = interface.sendText(
                    message,
                    destinationId=node_id,
                    wantAck=False,
                    channelIndex=settings["channel_index"],
                )
                packet_id = getattr(packet, "id", "unknown")
                total_attempts += 1
                print(colorize(f"Sent to {label} ({node_id}), packet ID {packet_id}", "cyan"))
                append_jsonl(
                    log_path,
                    "send_attempt",
                    {
                        "recipient_id": node_id,
                        "recipient_label": label,
                        "attempt": 1,
                        "packet_id": packet_id,
                        "result": "sent_without_ack",
                        "message": message,
                        "channel_index": settings["channel_index"],
                    },
                )

            sent += 1
        except TimeoutError as exc:
            failed += 1
            total_attempts += 1
            print(colorize(f"Timeout for {label} ({node_id}): {exc}", "red"))
            append_jsonl(
                log_path,
                "send_attempt",
                {
                    "recipient_id": node_id,
                    "recipient_label": label,
                    "attempt": 1,
                    "result": "timeout",
                    "message": message,
                    "channel_index": settings["channel_index"],
                    "error": str(exc),
                },
            )
        except Exception as exc:
            failed += 1
            total_attempts += 1
            print(colorize(f"Error for {label} ({node_id}): {exc}", "red"))
            append_jsonl(
                log_path,
                "send_attempt",
                {
                    "recipient_id": node_id,
                    "recipient_label": label,
                    "attempt": 1,
                    "result": "error",
                    "message": message,
                    "channel_index": settings["channel_index"],
                    "error": str(exc),
                },
            )

        time.sleep(settings["delay"])

    if not settings["ack"] and settings["final_wait"] > 0:
        print()
        print(colorize(
            f"Waiting another {settings['final_wait']:.1f}s so the device can finish sending outgoing packets ...",
            "yellow",
        ))
        time.sleep(settings["final_wait"])

    print()
    if settings["ack"]:
        summary_color = "green" if failed == 0 and implicit_acks == 0 else "yellow" if failed == 0 else "red"
        print(colorize(
            f"Done. Recipients processed: {sent}, attempts: {total_attempts}, "
            f"ACKs: {acked}, implicit ACKs: {implicit_acks}, errors/timeouts: {failed}",
            summary_color,
            bold=True,
        ))
    else:
        summary_color = "green" if failed == 0 else "red"
        print(colorize(
            f"Done. Recipients processed: {sent}, attempts: {total_attempts}, errors: {failed}",
            summary_color,
            bold=True,
        ))
    return 0 if sent else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.clear:
        return clear_config()

    if args.list_ports:
        print_available_ports(get_available_ports())
        return 0

    settings = resolve_settings(args)
    if settings is None:
        return 1

    interface = None
    try:
        port = resolve_port(settings["port"] or None, settings["unattended"])
        print(colorize(f"Connecting via {port} ...", "cyan"))
        interface = SerialInterface(devPath=port, timeout=settings["timeout"])

        if settings["mode"] == "listen":
            return run_listen_mode(interface, settings)
        return run_send_mode(interface, settings)
    except Exception as exc:
        print(colorize(f"Connection or send failed: {exc}", "red", bold=True))
        return 1
    finally:
        if interface is not None:
            try:
                interface.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
