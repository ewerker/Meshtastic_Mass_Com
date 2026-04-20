# Meshtastic_Mass_Text

Deutsche Dokumentation. English version: [README.md](C:\Users\richt\Documents\Codex\2026-04-19-installiere-mir-phyton\README.md)

Kleines Python-Werkzeug fuer Meshtastic, das Direktnachrichten an bekannte Nodes sendet und zusaetzlich eingehenden Verkehr mitlesen kann, inklusive Filterung, ACK-Auswertung, Logging, unattended-Modus und lokaler Konfigurationsdatei.

## Funktionen

- Sendet an alle bekannten Nodes oder nur an gefilterte Ziele
- Kann eine vorgefilterte Liste anzeigen und daraus gezielt einzelne Nodes auswaehlen
- Filtert ueber Node-ID, Kurzname oder Langname
- Unterstuetzt Wildcards wie `FR*`
- Erkennt serielle Ports automatisch oder laesst dich interaktiv waehlen
- Wartet optional auf ACK, implizites ACK oder NAK
- Kann bei implizitem ACK oder NAK automatisch erneut senden
- Kann eingehende Pakete live mit Filtern anzeigen
- Kann Sende- und Empfangsdaten in eine lokale JSONL-Datei schreiben
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
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --target-mode select --filter "FR*" --selection "1,3" --retry-implicit-ack 1 --retry-nak 1 --message "Testnachricht" --unattended --forcecfg
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
- aus einer nummerierten Liste einzelne Nodes auswaehlen, auf Wunsch nach Vorfilterung

Interaktiv:

```powershell
python .\send_to_all_nodes.py
```

Dann fragt das Skript:

- `1` fuer alle bekannten Nodes
- `2` fuer gefiltertes Senden
- `3` fuer manuelle Listenauswahl

Direkte Beispiele per Parameter:

```powershell
python .\send_to_all_nodes.py --target-mode all
python .\send_to_all_nodes.py --target-mode filter --filter "FR*"
python .\send_to_all_nodes.py --target-mode filter --filter "!55d8c9dc"
python .\send_to_all_nodes.py --target-mode filter --filter "Rico"
python .\send_to_all_nodes.py --target-mode select --filter "FR*"
python .\send_to_all_nodes.py --target-mode select --filter "FR*" --selection "1,3-4" --unattended
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

Retry-Steuerung:

- `--retry-implicit-ack 1`
  - Sendet nach einem impliziten ACK einmal erneut.
- `--retry-nak 1`
  - Sendet nach einem NAK einmal erneut.

Beispiel:

```powershell
python .\send_to_all_nodes.py --port COM7 --channel-index 1 --ack --delay 1.5 --timeout 60 --retry-implicit-ack 1 --retry-nak 1
```

## Listen-Modus

Das Skript kann auch verbunden bleiben und passende eingehende Pakete live anzeigen.

Beispiele:

```powershell
python .\send_to_all_nodes.py --mode listen
python .\send_to_all_nodes.py --listen --listen-filter "FR*"
python .\send_to_all_nodes.py --listen --listen-channel-index 1
python .\send_to_all_nodes.py --listen --dm-only
python .\send_to_all_nodes.py --listen --group-only --text-only
```

Filter im Listen-Modus:

- `--listen-filter`
  - Filtert ueber Absender-Node-ID, Kurzname oder Langname
- `--listen-channel-index`
  - Zeigt nur Pakete eines bestimmten Kanals
- `--dm-only`
  - Zeigt nur Direktnachrichten
- `--group-only`
  - Zeigt nur Gruppen-/Broadcast-Verkehr
- `--text-only`
  - Zeigt nur Textpakete

Beenden mit `Ctrl+C`.

## Logging

Mit `--log-file` schreibt das Skript JSONL-Eintraege fuer Sendeversuche und empfangene Pakete.

Beispiele:

```powershell
python .\send_to_all_nodes.py --mode send --log-file .\meshtastic_log.jsonl
python .\send_to_all_nodes.py --listen --log-file .\meshtastic_log.jsonl
```

## Beispiel-Workflows

### Schnelle Alltagsnutzung

Skript interaktiv starten und sich durchfuehren lassen:

```powershell
python .\send_to_all_nodes.py
```

Direktnachricht an alle bekannten Nodes auf `COM7`:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --target-mode all --message "Hallo an alle"
```

Auf `COM7` lauschen und nur Textverkehr anzeigen:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --text-only
```

### Gefilterte Sende-Workflows

Nur an Nodes senden, deren Rufname auf ein Muster passt:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Netztest" --ack
```

Nur an eine exakte Node-ID senden:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "!55d8c9dc" --message "Privater Test" --ack
```

Liste vorfiltern und dann einzelne Empfaenger manuell auswaehlen:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*"
```

Dieselbe Auswahl unattended mit gespeicherten Indexen ausfuehren:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*" --selection "1,3-5" --message "Geplanter Ping" --unattended
```

### Zuverlaessige Zustellung

ACK anfordern und bei implizitem ACK oder NAK jeweils einmal erneut senden:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Bitte bestaetigen" --ack --retry-implicit-ack 1 --retry-nak 1 --delay 1.5 --timeout 60
```

Kanal `0` fuer eine kleine private Gruppe nutzen, ohne die gespeicherte CFG zu veraendern:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 0 --target-mode select --selection "1-3" --message "Privater Check-in" --ack --protectcfg
```

### Listen-Workflows

Nur LongFast-Verkehr auf Kanal `1` anzeigen:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-channel-index 1
```

Nur Direktnachrichten von Nodes passend auf `FR*` anzeigen:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-filter "FR*" --dm-only --text-only
```

Nur Gruppenverkehr anzeigen und Nicht-Text-Pakete sichtbar lassen:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --group-only
```

### Logging-Workflows

Versand mit ACK-Auswertung und JSONL-Logdatei:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode filter --filter "FR*" --message "Mit Log" --ack --retry-implicit-ack 1 --retry-nak 1 --log-file .\logs\send_log.jsonl
```

Dauerhaft lauschen und passende Pakete in ein gemeinsames Log schreiben:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --text-only --log-file .\logs\listen_log.jsonl
```

### CFG-zentrierte Workflows

Ein wiederverwendbares unattended-Profil erzeugen oder aktualisieren:

```powershell
python .\send_to_all_nodes.py --mode send --port COM7 --channel-index 1 --target-mode select --filter "FR*" --selection "1,2" --message "Routine-Nachricht" --ack --retry-implicit-ack 1 --retry-nak 1 --log-file .\logs\routine.jsonl --unattended --forcecfg
```

Spaeter nur noch mit der gespeicherten CFG starten:

```powershell
python .\send_to_all_nodes.py
```

Temporar im Listen-Modus mit anderen Werten arbeiten, ohne die CFG zu veraendern:

```powershell
python .\send_to_all_nodes.py --listen --port COM7 --listen-filter "FR*" --dm-only --text-only --protectcfg
```

## Wichtige Optionen Referenz

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
python .\send_to_all_nodes.py --selection "1,3-5"
python .\send_to_all_nodes.py --retry-implicit-ack 1
python .\send_to_all_nodes.py --retry-nak 1
python .\send_to_all_nodes.py --listen
python .\send_to_all_nodes.py --listen-filter "FR*"
python .\send_to_all_nodes.py --listen-channel-index 1
python .\send_to_all_nodes.py --dm-only
python .\send_to_all_nodes.py --group-only
python .\send_to_all_nodes.py --text-only
python .\send_to_all_nodes.py --log-file .\meshtastic_log.jsonl
python .\send_to_all_nodes.py --unattended
python .\send_to_all_nodes.py --no-unattended
python .\send_to_all_nodes.py --forcecfg
python .\send_to_all_nodes.py --protectcfg
python .\send_to_all_nodes.py --clear
```

## Hinweise

- Dieses Werkzeug ist fuer kontrollierte Direktnachrichten gedacht.
- Bitte beachte lokale Funkregeln, Duty-Cycle-Grenzen und andere Teilnehmer im Mesh.
