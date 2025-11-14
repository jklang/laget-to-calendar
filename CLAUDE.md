# Claude Code Project Documentation

This document provides information for AI assistants (like Claude) working on this project.

## Project Overview

**laget-to-calendar** is a Python-based web scraper that fetches event registrations from laget.se and syncs them to calendar applications. It supports automatic calendar synchronization to both macOS Calendar (via EventKit) and Google Calendar (via Google Calendar API).

## Key Features

- Web scraping of laget.se "Mina anmälningar" (My Registrations)
- Extraction of event details: title, date, time, location, team, child name, attendee list
- iCalendar (.ics) file generation
- Automatic calendar synchronization (macOS Calendar and/or Google Calendar)
- Smart event updates (detects and updates changed events)
- Event reminders (1 day and 2 hours before)
- Practice event filtering (excluded by default)

## Technology Stack

- **Python 3.x** with virtual environment
- **Web Scraping**: requests, BeautifulSoup4
- **Calendar**: icalendar, pytz
- **CLI**: typer, rich (for colored terminal output)
- **Configuration**: PyYAML
- **macOS Calendar**: PyObjC (EventKit, Cocoa frameworks)
- **Google Calendar**: google-api-python-client, google-auth
- **MCP Tools**: Chrome DevTools MCP (for inspecting JavaScript-loaded content)

## Project Structure

```
laget-to-calendar/
├── laget_scraper.py           # Main scraper and CLI entry point
├── calendar_integrations.py   # Calendar sync implementations (macOS, Google)
├── requirements.txt           # Python dependencies
├── README.md                  # User documentation
├── CLAUDE.md                  # This file - AI assistant documentation
├── docs/
│   └── google-calendar-setup.md  # Google Calendar API setup guide
├── test_attendees.py          # Debug script (not committed)
└── .gitignore
```

## Important Code Locations

### Main Scraper Class: `LagetSeScraper`

**File**: `laget_scraper.py`

Key methods:
- `login()` - Authenticates with laget.se
- `get_registrations()` - Fetches list of registrations
- `get_registration_details(pk, child_id, site)` - Extracts detailed event info including attendees
- `parse_datetime(date_str, time_str, samling_str)` - Parses Swedish date/time strings
- `create_ical_calendar(registrations, filename)` - Generates .ics file

### Calendar Integration

**File**: `calendar_integrations.py`

Classes:
- `MacOSCalendarIntegration` - EventKit-based macOS Calendar sync
- `GoogleCalendarIntegration` - Google Calendar API integration

Both implement:
- `authenticate()` - Authentication/authorization
- `sync_events(events)` - Sync event list to calendar
- `add_event(event_data)` - Add single event
- `update_event(uid, event_data)` - Update existing event

## Web Scraping Details

### Authentication
- URL: `https://www.laget.se/Common/Auth/Login`
- Session-based authentication with cookies
- Credentials stored in `~/.config/laget-scraper/config.yaml`

### Data Extraction

**Registration List**
- URL: `https://www.laget.se/` (requires authenticated session)
- Parsed from modal popup opened via JavaScript
- Each registration has: `pk` (primary key), `childId`, `site` parameters

**Registration Details**
- URL: `https://www.laget.se/Common/Rsvp/ModalContent`
- Query params: `pk`, `childId`, `site`
- **Important**: Content is JavaScript-loaded, returns empty HTML when accessed directly via HTTP
- Must be inspected using browser DevTools or rendered browser context

**Attendee List HTML Structure** (JavaScript-loaded):

```html
<ul class="attendingsList__list">
  <li class="attendingsList__row">
    <div class="attendingsList__cell">Attendee Name</div>
    <div class="attendingsList__cell--gray">...</div>
  </li>
  <!-- More attendees... -->
</ul>
```

CSS Selectors used:

- `ul.attendingsList__list` - Container
- `li.attendingsList__row` - Each attendee row
- `div.attendingsList__cell` - First cell contains the name

## MCP Configuration

### Chrome DevTools MCP

This project benefits from Chrome DevTools MCP for inspecting JavaScript-loaded content on laget.se.

**When to use Chrome MCP:**
- Inspecting dynamic content that doesn't appear in HTTP responses
- Finding correct CSS selectors for newly added fields
- Debugging why scraping isn't working for specific elements

**Example usage from this project:**
The attendee list feature required Chrome DevTools MCP because:
1. Direct HTTP GET to `/Common/Rsvp/ModalContent` returned empty HTML
2. Content is loaded via JavaScript after page render
3. Used `take_snapshot()` to inspect the rendered DOM
4. Used `evaluate_script()` to extract attendee names and verify structure

**Relevant MCP tools used:**
- `navigate_page` - Navigate to laget.se pages
- `take_snapshot` - Get accessibility tree snapshot of rendered page
- `evaluate_script` - Execute JavaScript to inspect/extract data
- `click` - Interact with page elements

## Configuration Files

### User Config: `~/.config/laget-scraper/config.yaml`

```yaml
credentials:
  email: "user@example.com"
  password: "password"

calendar:
  mode: "macos"  # none, macos, google, both
  calendar_name: null  # or specify custom calendar name
  google_credentials_file: "~/.config/laget-scraper/credentials.json"
```

Created via: `python laget_scraper.py init-config`

### Google Calendar Setup

Requires OAuth 2.0 credentials from Google Cloud Console. See `docs/google-calendar-setup.md` for detailed setup instructions.

## Development Workflow

### Running the Scraper

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default config
python laget_scraper.py scrape

# Run with calendar sync
python laget_scraper.py scrape --calendar-mode macos

# Include practice events
python laget_scraper.py scrape --include-practice
```

### Testing Changes

1. Run scraper with `--include-practice` to get more test data
2. Check generated `.ics` file for correctness
3. Test calendar sync if applicable
4. Verify event descriptions contain expected information

### Common Issues

**Empty HTML responses**: Content is JavaScript-loaded. Use Chrome DevTools MCP to inspect the actual rendered DOM.

**Authentication failures**: Check that credentials in config are correct and that session is maintained.

**Calendar access denied**: macOS Calendar requires explicit permission grant in System Settings > Privacy & Security > Calendars.

## Git Workflow

- Main development branch: `calendar-integration`
- Main branch: Used for releases
- Commit messages: Descriptive, focus on what and why

## Code Style

- Python 3.x with type hints where beneficial
- Rich console output for user feedback
- Comprehensive error handling with user-friendly messages
- Swedish terminology in comments where referring to laget.se UI elements

## Recent Changes

### PR #2: Add attendee list to calendar events
- Extracts attendee names from registration details
- Displays in format: "Deltagare (count):" with bulleted names
- Required Chrome DevTools MCP to identify correct HTML structure
- Works with all calendar modes (.ics, macOS, Google, both)

### Previous Features
- Calendar integration (macOS via EventKit, Google via API)
- Smart event updates with UID tracking
- Automatic reminders (1 day and 2 hours before)
- Practice event filtering
- Configuration file support (YAML)

## Testing Approach

Manual testing workflow:
1. Run scraper to fetch current registrations
2. Inspect generated `.ics` file
3. Check event details (title, time, location, description, attendees)
4. Verify calendar sync works (if enabled)
5. Confirm events update correctly on subsequent runs

## Future Enhancement Ideas

- Add support for more event types
- Extract and include additional metadata (event costs, equipment lists, etc.)
- Support for multiple children/accounts
- Web UI for configuration
- Docker containerization for scheduled syncs

## Notes for AI Assistants

1. **Always use Chrome DevTools MCP** when inspecting laget.se for new fields, as much content is JavaScript-loaded
2. **Preserve existing functionality** - This is actively used by a real user
3. **Test thoroughly** - The scraper accesses a live website and real calendar data
4. **Document breaking changes** - Update README and this file with significant changes
5. **Swedish context** - The target website is Swedish, keep Swedish UI element names in comments for clarity
