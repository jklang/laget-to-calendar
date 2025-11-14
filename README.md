# Laget.se to iCal Converter

Converts your laget.se registrations into iCal calendar entries with automatic calendar synchronization.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
# Create config file with your credentials and calendar settings
python laget_scraper.py init-config

# Run the scraper (syncs to calendar if configured)
python laget_scraper.py scrape
```

The script can automatically sync events to your calendar or create an `.ics` file for manual import.

## Usage

### Basic Usage

**With config file (recommended):**
```bash
python laget_scraper.py scrape
```

**With environment variables:**
```bash
export LAGET_EMAIL="your.email@example.com"
export LAGET_PASSWORD="your_password"
python laget_scraper.py scrape
```

### Calendar Integration

**Sync to macOS Calendar:**
```bash
python laget_scraper.py scrape --calendar-mode macos
```

**Sync to Google Calendar:**
```bash
python laget_scraper.py scrape --calendar-mode google
```

**Sync to both:**
```bash
python laget_scraper.py scrape --calendar-mode both
```

**Use a custom calendar:**
```bash
python laget_scraper.py scrape --calendar-mode macos --calendar-name "Kids Sports"
```

### Other Options

**Include practice events:**
```bash
python laget_scraper.py scrape --include-practice
```

**Custom output file:**
```bash
python laget_scraper.py scrape --output events.ics
```

## Features

- **Automatic calendar sync** to macOS Calendar and/or Google Calendar
- **Smart event updates** - detects and updates changed events
- Automatic login to laget.se
- Fetches all registrations ("Mina anmälningar")
- Extracts event details (title, date, time, location, team, child name)
- Uses "Samling" time as calendar start when available
- Excludes practice events by default
- Automatic reminders: 1 day before and 2 hours before each event
- Creates iCal files compatible with all calendar apps (as backup)

## Calendar Integration Setup

### macOS Calendar

No setup required! Just use `--calendar-mode macos` and the script will:
1. Request calendar access (first time only)
2. Sync events to your default calendar (or custom calendar if specified)
3. Update events automatically on subsequent runs

### Google Calendar

Requires one-time setup:
1. Create Google Cloud project and enable Calendar API
2. Download OAuth credentials
3. Place credentials file in `~/.config/laget-scraper/credentials.json`

See [docs/google-calendar-setup.md](docs/google-calendar-setup.md) for detailed instructions.

### Manual Import (No Auto-Sync)

If you prefer manual import, the script always creates a `.ics` file:
- **Google Calendar:** Settings → Import & export → Import
- **Apple Calendar:** Double-click the `.ics` file
- **Outlook:** File → Import → iCalendar file

## Configuration

### Config File Format

Create `~/.config/laget-scraper/config.yaml`:

```yaml
credentials:
  email: "your.email@example.com"
  password: "your_password"

calendar:
  mode: "macos"  # Options: none, macos, google, both
  calendar_name: null  # null = default/primary calendar, or specify name
  google_credentials_file: "~/.config/laget-scraper/credentials.json"
```

### Credential Priority

Credentials are searched in this order:
1. Command line arguments (`--email`, `--password`)
2. Environment variables (`LAGET_EMAIL`, `LAGET_PASSWORD`)
3. Config file (`~/.config/laget-scraper/config.yaml`)
4. Interactive prompt

## Command Reference

```
$ python laget_scraper.py --help

Usage: laget_scraper.py [OPTIONS] COMMAND [ARGS]...

Commands:
  scrape        Scrape registrations and create iCal calendar file
  init-config   Create a configuration file with your credentials

$ python laget_scraper.py scrape --help

Options:
  -e, --email TEXT                    Laget.se email address
  -p, --password TEXT                 Laget.se password
  -o, --output TEXT                   Output filename [default: laget_registrations.ics]
  -c, --config PATH                   Config file path [default: ~/.config/laget-scraper/config.yaml]
  --include-practice                  Include practice events (Träning) [default: exclude]
  --exclude-practice
  --calendar-mode TEXT                Calendar integration: none, macos, google, both
  --calendar-name TEXT                Custom calendar name (default: use default/primary)
  --google-credentials-file TEXT      Path to Google OAuth credentials JSON
  --help                              Show this message and exit
```

## How It Works

1. **Scrapes laget.se** - Logs in and fetches all your registrations
2. **Filters events** - Excludes practice events by default (configurable)
3. **Generates .ics file** - Always creates a backup iCal file
4. **Syncs to calendar** - If calendar mode is enabled:
   - Adds new events to your calendar
   - Updates existing events if details changed
   - Uses unique IDs to track events across syncs

## Scheduling Automatic Syncs

You can schedule the scraper to run automatically using cron (macOS/Linux):

```bash
# Edit crontab
crontab -e

# Add line to run daily at 8 AM
0 8 * * * cd /path/to/laget-to-calendar && /path/to/venv/bin/python laget_scraper.py scrape
```

## License

Personal tool. Use at your own risk.
