# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and uses project release tags where available.

## [Unreleased]

- Reserved for upcoming changes before the next tagged release.

## [0.6.1] - 2026-04-20

### Added

- Added a project-local changelog with release notes for tagged versions.
- Added direct links to the changelog from the English and German README files.

### Changed

- Moved visible version handling into a shared module used by CLI, GUI, cfg headers, and documentation.

## [0.6.0] - 2026-04-20

### Added

- Added a shared version module so the project version can be maintained in one place.
- Added visible version output to the CLI via `--version`.
- Added visible version markers to generated cfg files.
- Added visible version text to the GUI window title.
- Added version references to the English and German README files.

### Changed

- Improved autoresponder console output so sent reply text and target channel are shown before the ACK result.

## [0.5.1] - 2026-04-20

### Added

- Added a dedicated autoresponder cfg workflow.
- Added autoresponder support to the listen workflow.
- Added GUI support for send, listen, and autoresponder cfg generation.
- Added automatic loading of existing cfg files in the GUI.

### Changed

- Improved cfg separation between send and listen workflows.
- Improved cfg overwrite warnings for CLI and GUI usage.

### Fixed

- Fixed autoresponder loops caused by routing and ACK packets.
- Fixed listen and send mode handling so mode selection alone does not trigger cfg rewrites.
- Fixed cfg loading and saving so send and listen cfg files are handled independently.

## [0.5-beta] - 2026-04-20

### Added

- Added MIT licensing and copyright headers.
- Added send/listen/history workflows with cfg-based operation.
- Added filtered sending, retries, dry-run support, and local history logging.
- Added listen mode with filters and JSONL logging.

## [0.4.2] - 2026-04-20

### Changed

- Split default history files into separate send and listen history logs.

## [0.4.1] - 2026-04-20

### Fixed

- Fixed cfg separation bugs between send and listen handling.
- Fixed GUI save/load behavior so it applies to the active cfg family only.

## [0.4.0] - 2026-04-20

### Added

- Added platform-neutral documentation and examples.
- Added a GUI cfg generator.
- Added cleaner runtime parameter reporting.
