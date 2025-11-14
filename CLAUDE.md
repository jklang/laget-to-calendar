# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool that scrapes sports event registrations from laget.se and automatically syncs them to calendar applications. It converts Swedish sports team registrations into calendar events with automatic synchronization to macOS Calendar and/or Google Calendar.

## Core Architecture

### Main Components

1. **laget_scraper.py** - Main entry point with Typer CLI
   - `LagetSeScraper` class: Handles authentication, scraping, and data extraction from laget.se
   - Two commands: `scrape` (fetch and sync events) and `init-config` (create config file)
   - Credential management with 4-tier priority: CLI args → env vars → config file → interactive prompt

2. **calendar_integrations.py** - Calendar sync backends
   - `CalendarIntegration` (abstract base): Defines interface for calendar backends
   - `MacOSCalendarIntegration`: Uses PyObjC/EventKit to sync with macOS Calendar
   - `GoogleCalendarIntegration`: Uses Google Calendar API with OAuth 2.0
   - Smart sync logic: tracks events by UID, updates changed events, avoids duplicates

### Data Flow

```
laget.se login → fetch registrations → filter/parse → [.ics file + calendar sync]
                                                            ↓
                                            convert to standardized event format
                                                            ↓
                                    macOS Calendar ← sync → Google Calendar
                                        (via EventKit)        (via OAuth API)
```

### Configuration

- **Format**: YAML (migrated from TOML)
- **Location**: `~/.config/laget-scraper/config.yaml`
- **Structure**:
  ```yaml
  credentials:
    email: "..."
    password: "..."
  calendar:
    mode: "none|macos|google|both"
    calendar_name: null  # null = default/primary calendar
    google_credentials_file: "path/to/credentials.json"
  ```

### Event Tracking & Updates

- Events are identified by UID format: `laget-{pk}-{childId}@laget.se`
- For macOS: UID stored in event notes field (searched via date range query)
- For Google: UID stored in extended properties (queried via API)
- Event comparison checks: title, start, end, location, description
- Updates are applied to existing events rather than creating duplicates

## Development Commands

```bash
# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the scraper
python laget_scraper.py scrape [--calendar-mode macos|google|both]

# Create config file (interactive)
python laget_scraper.py init-config

# Run with specific calendar
python laget_scraper.py scrape --calendar-mode macos --calendar-name "Kids Sports"

# Test syntax
python -m py_compile laget_scraper.py calendar_integrations.py

# View help
python laget_scraper.py --help
python laget_scraper.py scrape --help
```

## Calendar Integration Details

### macOS Calendar (EventKit)

- Uses PyObjC to bridge Python → Objective-C → EventKit framework
- First run requests calendar permission via `requestAccessToEntityType_completion_`
- Default calendar: `eventStore.defaultCalendarForNewEvents`
- Custom calendar: searches by title, creates if not found
- Event lookup: searches within 1-year window (past/future) for UID marker in notes
- Platform check: Only loads EventKit on `sys.platform == 'darwin'`

### Google Calendar

- OAuth 2.0 flow using Desktop app credentials
- Token stored in `~/.config/laget-scraper/token.json` after first auth
- Uses extended properties: `{'private': {'lagetUid': 'laget-...'}}` for UID tracking
- Primary calendar: calendar ID = `"primary"`
- Custom calendar: lists all calendars, creates if name not found
- Timezone: Hard-coded to `Europe/Stockholm`

## Key Implementation Patterns

### Datetime Handling

- Swedish month names parsed via dictionary mapping
- Timezone: `pytz.timezone('Europe/Stockholm')`
- "Samling" time (gathering time) used as start time if available, otherwise uses event time
- Year inference: uses current year, assumes events are future/current year

### Web Scraping Strategy

- Session-based with CSRF token extraction from login page
- BeautifulSoup for HTML parsing
- Modal-based navigation: finds registration links via `/Common/Rsvp/ModalContent` pattern
- Extracts: title, team, child name, date, time, location, address, deadline, samling, description

### Error Handling Philosophy

- Calendar sync failures fall back gracefully (always creates .ics backup)
- Missing/invalid event data: events skipped with warnings, doesn't stop entire sync
- Permission denied: clear user guidance pointing to system settings

## Dependencies & Platform Notes

- **macOS only**: `pyobjc-framework-EventKit`, `pyobjc-framework-Cocoa` (conditional via `sys_platform == 'darwin'`)
- **Google Calendar**: Requires OAuth setup (see `docs/google-calendar-setup.md`)
- **Rich**: Used for styled console output (cyan/green/red/yellow styles, progress bars)
- **Typer**: CLI framework with automatic help generation

## Testing a Calendar Integration Change

When modifying calendar integration logic:

1. For macOS: May need to reset Calendar permissions in System Settings
2. For Google: Delete `~/.config/laget-scraper/token.json` to re-authenticate
3. Test with a single event first (limit registrations manually if needed)
4. Check both add and update scenarios
5. Verify UID tracking works (run twice, ensure no duplicates on second run)

## Important Behavioral Notes

- Practice events ("Träning") are excluded by default unless `--include-practice` specified
- Reminders are always added: -1 day and -2 hours relative to event start
- `.ics` file is always generated even when calendar sync is enabled (serves as backup)
- Config file permissions are set to 600 (owner read/write only) for security
