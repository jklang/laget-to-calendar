# Laget.se to iCal Converter

Converts your laget.se registrations into iCal calendar entries.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
# Create config file with your credentials
python laget_scraper.py init-config

# Run the scraper
python laget_scraper.py scrape
```

This creates `laget_registrations.ics` which you can import into any calendar app.

## Usage

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

**Include practice events:**
```bash
python laget_scraper.py scrape --include-practice
```

**Custom output file:**
```bash
python laget_scraper.py scrape --output events.ics
```

## Features

- Automatic login to laget.se
- Fetches all registrations ("Mina anmälningar")
- Extracts event details (title, date, time, location, team, child name)
- Uses "Samling" time as calendar start when available
- Excludes practice events by default
- Creates iCal files compatible with all calendar apps

## Import to Calendar

- **Google Calendar:** Settings → Import & export → Import
- **Apple Calendar:** Double-click the `.ics` file
- **Outlook:** File → Import → iCalendar file

## Configuration

Credentials are searched in this order:
1. Command line arguments
2. Environment variables (`LAGET_EMAIL`, `LAGET_PASSWORD`)
3. Config file (`~/.config/laget-scraper/config.toml`)
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
  -e, --email TEXT              Laget.se email address
  -p, --password TEXT           Laget.se password
  -o, --output TEXT             Output filename [default: laget_registrations.ics]
  -c, --config PATH             Config file path [default: ~/.config/laget-scraper/config.toml]
  --include-practice            Include practice events (Träning) [default: exclude]
  --exclude-practice
  --help                        Show this message and exit
```

## License

Personal tool. Use at your own risk.
