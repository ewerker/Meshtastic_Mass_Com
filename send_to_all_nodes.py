import argparse
import sys
import time

from meshtastic.serial_interface import SerialInterface
from serial.tools import list_ports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a direct Meshtastic message to all known message-capable nodes."
    )
    parser.add_argument(
        "--port",
        help="Serial port of the Meshtastic device. If omitted, available ports are auto-detected.",
    )
    parser.add_argument(
        "--channel-index",
        type=int,
        default=0,
        help="Channel index to use for sending (default: 0).",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Wait for an ACK for each message.",
    )
    parser.add_argument(
        "--include-unmessageable",
        action="store_true",
        help="Also try nodes that are marked as unmessageable.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between messages (default: 0.5).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Connection timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="Only show available serial ports and exit.",
    )
    return parser


def prompt_message() -> str:
    message = input("Text, der an alle bekannten Nodes gesendet werden soll: ").strip()
    if not message:
        raise ValueError("Leere Nachricht wird nicht gesendet.")
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
        print("Keine seriellen Ports gefunden.")
        return

    print("Verfuegbare serielle Ports:")
    for index, port in enumerate(ports, start=1):
        description = port.description or "ohne Beschreibung"
        hwid = port.hwid or "ohne HWID"
        print(f"  {index}. {port.device} - {description} [{hwid}]")


def choose_port_interactively(ports: list) -> str:
    while True:
        choice = input("Welchen Port moechtest du verwenden? Nummer eingeben: ").strip()
        if not choice.isdigit():
            print("Bitte eine gueltige Nummer eingeben.")
            continue

        selected_index = int(choice)
        if 1 <= selected_index <= len(ports):
            return ports[selected_index - 1].device

        print("Die Nummer liegt ausserhalb der Liste.")


def resolve_port(cli_port: str | None) -> str:
    if cli_port:
        return cli_port

    ports = get_available_ports()
    if not ports:
        raise RuntimeError("Keine seriellen Ports gefunden. Bitte Geraet anschliessen oder --port angeben.")

    if len(ports) == 1:
        selected = ports[0].device
        print(f"Ein serieller Port gefunden, verwende automatisch: {selected}")
        return selected

    print_available_ports(ports)
    return choose_port_interactively(ports)


def collect_recipients(interface: SerialInterface, include_unmessageable: bool) -> list[tuple[str, str]]:
    recipients: list[tuple[str, str]] = []
    local_num = get_local_node_num(interface)

    for node_id, node in sorted(interface.nodes.items()):
        user = node.get("user", {})
        if not user:
            continue
        if node.get("num") == local_num:
            continue
        if user.get("isUnmessagable") and not include_unmessageable:
            continue

        label = user.get("longName") or user.get("shortName") or node_id
        recipients.append((node_id, label))

    return recipients


def confirm_send(message: str, recipients: list[tuple[str, str]]) -> bool:
    print()
    print(f'Nachricht: "{message}"')
    print(f"Empfaenger: {len(recipients)}")
    for node_id, label in recipients:
        print(f"  - {label} ({node_id})")
    print()
    answer = input("Jetzt senden? [j/N]: ").strip().lower()
    return answer in {"j", "ja", "y", "yes"}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_ports:
        print_available_ports(get_available_ports())
        return 0

    try:
        message = prompt_message()
    except ValueError as exc:
        print(exc)
        return 1

    interface = None
    try:
        port = resolve_port(args.port)
        print(f"Verbinde ueber {port} ...")
        interface = SerialInterface(devPath=port, timeout=args.timeout)
        recipients = collect_recipients(interface, args.include_unmessageable)

        if not recipients:
            print("Keine passenden bekannten Nodes gefunden.")
            return 1

        if not confirm_send(message, recipients):
            print("Abgebrochen.")
            return 0

        sent = 0
        failed = 0

        for node_id, label in recipients:
            try:
                interface.sendText(
                    message,
                    destinationId=node_id,
                    wantAck=args.ack,
                    channelIndex=args.channel_index,
                )
                sent += 1
                print(f"Gesendet an {label} ({node_id})")
            except Exception as exc:
                failed += 1
                print(f"Fehler bei {label} ({node_id}): {exc}")

            time.sleep(args.delay)

        print()
        print(f"Fertig. Erfolgreich: {sent}, Fehler: {failed}")
        return 0 if sent else 1
    except Exception as exc:
        print(f"Verbindung oder Senden fehlgeschlagen: {exc}")
        return 1
    finally:
        if interface is not None:
            try:
                interface.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
