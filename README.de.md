# Meshtastic_Mass_Text

Deutsche Dokumentation. English version: [README.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.md)

Kleines Python-Werkzeug fuer Meshtastic, das Direktnachrichten an bekannte Nodes sendet, inklusive Filterung, ACK-Auswertung, unattended-Modus und lokaler Konfigurationsdatei.

## Funktionen

- Sendet an alle bekannten Nodes oder nur an gefilterte Ziele
- Filtert ueber Node-ID, Kurzname oder Langname
- Unterstuetzt Wildcards wie `FR*`
- Erkennt serielle Ports automatisch oder laesst dich interaktiv waehlen
- Wartet optional auf ACK, implizites ACK oder NAK
- Speichert Laufzeitwerte in einer lokalen `.cfg`-Datei
- Unterstuetzt unbeaufsichtigte Laeufe ohne Rueckfragen
- Kann die Konfigurationsdatei gezielt schuetzen oder bewusst aktualisieren

## Voraussetzungen

- Windows
- Python 3.14+
- Python-Pakete:
  - `meshtastic`
  - `pyserial`

## Installation

```powershell
python -m pip install meshtastic pyserial
```

## Dateien

- Skript: [send_to_all_nodes.py](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.py)
- Lokale Konfiguration: [send_to_all_nodes.cfg](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\send_to_all_nodes.cfg)
- Englische Dokumentation: [README.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.md)

## Erster Start

Wenn noch keine Konfigurationsdatei existiert, sollte das Skript einmal mit Parametern gestartet werden, damit eine CFG erzeugt werden kann.

Beispiel:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --target-mode filter --filter "FR*" --message "Testnachricht" --unattended --forcecfg
```

Danach reicht oft:

```powershell
python .\send_to_all_nodes.py
```

## Verhalten der Konfigurationsdatei

- Keine CFG + Parameter uebergeben:
  - Aus den Parametern kann eine CFG erzeugt werden.
- Vorhandene CFG + Parameter uebergeben:
  - Die Parameter gelten fuer diesen Lauf.
  - Ob die CFG aktualisiert wird, haengt von `--forcecfg` / `--protectcfg` ab.
- Vorhandene CFG + keine Parameter:
  - Das Skript verwendet die Werte aus der CFG.
- Keine CFG + keine Parameter:
  - Das Skript zeigt ein Beispiel fuer einen gueltigen Erstaufruf.

## Steuerung der CFG

Diese Schalter machen das Verhalten eindeutig:

- `--forcecfg`
  - Erzeugt oder aktualisiert die CFG immer, wenn Parameter uebergeben werden.
- `--protectcfg`
  - Veraendert die CFG in diesem Lauf niemals, auch wenn Parameter uebergeben werden.
- `--clear`
  - Loescht die lokale CFG und beendet sich danach.

Beispiele:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --message "Hallo" --forcecfg
```

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 0 --message "Privater Test" --protectcfg
```

```powershell
python .\send_to_all_nodes.py --clear
```

## Zielauswahl

Das Skript kann:

- an alle bekannten Nodes senden
- nur an gefilterte Nodes senden

Interaktiv:

```powershell
python .\send_to_all_nodes.py
```

Dann fragt das Skript:

- `1` fuer alle bekannten Nodes
- `2` fuer gefiltertes Senden

Direkte Beispiele per Parameter:

```powershell
python .\send_to_all_nodes.py --target-mode all
python .\send_to_all_nodes.py --target-mode filter --filter "FR*"
python .\send_to_all_nodes.py --target-mode filter --filter "!55d8c9dc"
python .\send_to_all_nodes.py --target-mode filter --filter "Rico"
```

Filterregeln:

- Mit Wildcards wie `FR*` oder `*mobil*` wird als Muster gesucht.
- Ohne Wildcards sind Teiltreffer erlaubt.
- Geprueft werden Node-ID, Kurzname und Langname.

## Nachricht und Unattended-Modus

Du kannst eine Standardnachricht in der CFG speichern:

```powershell
python .\send_to_all_nodes.py --message "Hallo zusammen" --forcecfg
```

Start ohne Rueckfragen:

```powershell
python .\send_to_all_nodes.py --unattended
```

Typischer unattended-Aufruf:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --target-mode filter --filter "FR*" --message "Hallo zusammen" --unattended --forcecfg
```

Im unattended-Modus gilt:

- keine Rueckfrage nach der Nachricht
- keine Rueckfrage zur Zielauswahl
- keine Rueckfrage vor dem Versand
- benoetigte Werte muessen aus Parametern oder der CFG kommen

## ACK-Auswertung

Mit `--ack` wartet das Skript pro Nachricht auf eine Rueckmeldung.

Moegliche Ergebnisse:

- `Received an ACK.`
  - Die Zustellung wurde bestaetigt.
- `Sent, but not confirmed (implicit ACK only).`
  - Das Paket wurde gesendet, aber nicht explizit bestaetigt.
- `Received a NAK, error reason: ...`
  - Die Zustellung wurde negativ beantwortet.
- `Error ... No ACK/NAK ...`
  - Timeout ohne Rueckmeldung.

Beispiel:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60
```

## Wichtige Optionen

```powershell
python .\send_to_all_nodes.py --help
python .\send_to_all_nodes.py --list-ports
python .\send_to_all_nodes.py --port COM7
python .\send_to_all_nodes.py --channel-index 1
python .\send_to_all_nodes.py --ack
python .\send_to_all_nodes.py --no-ack
python .\send_to_all_nodes.py --include-unmessageable
python .\send_to_all_nodes.py --no-include-unmessageable
python .\send_to_all_nodes.py --message "Hallo"
python .\send_to_all_nodes.py --unattended
python .\send_to_all_nodes.py --no-unattended
python .\send_to_all_nodes.py --forcecfg
python .\send_to_all_nodes.py --protectcfg
python .\send_to_all_nodes.py --clear
```

## Hinweise

- Dieses Werkzeug ist fuer kontrollierte Direktnachrichten gedacht.
- Bitte beachte lokale Funkregeln, Duty-Cycle-Grenzen und andere Teilnehmer im Mesh.
