# Laget.se to iCal Converter

Automatically converts your registrations from laget.se into iCal calendar entries that can be imported into any calendar application (Google Calendar, Apple Calendar, Outlook, etc.).

## Features

- Modern CLI interface with Typer
- Beautiful colored output with Rich
- Multiple credential input methods:
  - Environment variables
  - Config file
  - Command line arguments
  - Interactive prompts
- Logs into laget.se automatically
- Fetches all your registrations ("Mina anmälningar")
- Extracts event details including:
  - Event title and type (Träning, Match, etc.)
  - Date and time
  - Location and address
  - Team/group information
  - Child name
  - Additional notes and requirements
  - Google Maps link
- Creates an iCal (.ics) file that can be imported into any calendar app

## Installation

1. Make sure you have Python 3.7+ installed
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Quick Start (Recommended)

The easiest way is to create a config file with your credentials:

```bash
python laget_scraper.py init-config
```

Then run the scraper:

```bash
python laget_scraper.py scrape
```

### Using Environment Variables

```bash
export LAGET_EMAIL="your.email@example.com"
export LAGET_PASSWORD="your_password"
python laget_scraper.py scrape
```

### Using Command Line Arguments

```bash
python laget_scraper.py scrape --email "your.email@example.com" --password "your_password"
```

**Note:** For security, avoid using password on command line. Prefer environment variables or config file.

### Interactive Mode

Just run without credentials and you'll be prompted:

```bash
python laget_scraper.py scrape
```

### CLI Options

```bash
# Show help
python laget_scraper.py --help

# Scrape with custom output file
python laget_scraper.py scrape --output my-calendar.ics

# Use custom config file location
python laget_scraper.py scrape --config /path/to/config.toml

# Show all options for scrape command
python laget_scraper.py scrape --help
```

## Commands

### `scrape` - Main command

Scrape registrations and create iCal file.

**Options:**
- `--email, -e TEXT`: Laget.se email address
- `--password, -p TEXT`: Laget.se password
- `--output, -o TEXT`: Output filename (default: laget_registrations.ics)
- `--config, -c PATH`: Path to config file (default: ~/.config/laget-scraper/config.toml)
- `--include-practice/--exclude-practice`: Include practice events (Träning). Default is to exclude them.

**Examples:**

```bash
# Using config file
python laget_scraper.py scrape

# Using environment variables
LAGET_EMAIL="email@example.com" LAGET_PASSWORD="pass" python laget_scraper.py scrape

# Custom output file
python laget_scraper.py scrape --output events.ics

# Interactive mode (will prompt for credentials)
python laget_scraper.py scrape
```

### `init-config` - Create configuration file

Create a config file to store your credentials securely.

**Options:**
- `--config, -c PATH`: Path where config file should be created (default: ~/.config/laget-scraper/config.toml)

**Example:**

```bash
python laget_scraper.py init-config
```

The config file will be created with 600 permissions (owner read/write only) for security.

## Configuration File

The config file is a simple TOML file:

```toml
# Laget.se Scraper Configuration
email = "your.email@example.com"
password = "your_password"
```

Default location: `~/.config/laget-scraper/config.toml`

## Credential Priority

Credentials are searched in this order:

1. **Command line arguments** (`--email`, `--password`)
2. **Environment variables** (`LAGET_EMAIL`, `LAGET_PASSWORD`)
3. **Config file** (`~/.config/laget-scraper/config.toml`)
4. **Interactive prompt** (if nothing else is provided)

## Import to Calendar

**Google Calendar:**
1. Open Google Calendar
2. Click the "+" next to "Other calendars"
3. Select "Import"
4. Upload the `laget_registrations.ics` file

**Apple Calendar:**
1. Double-click the `laget_registrations.ics` file
2. It will automatically open in Calendar
3. Choose which calendar to add the events to

**Outlook:**
1. File → Import → iCalendar (.ics) file
2. Select the `laget_registrations.ics` file

## Example Output

```
Laget.se to iCal Converter
============================================================

Using credentials from config file: /Users/you/.config/laget-scraper/config.toml
Logging in to laget.se...
✓ Login successful

Fetching registration list...
Found 3 registrations

⠋ Fetching registration 1/3...
  ✓ Träning - 14 november
  ✓ Nacka Winter Kickoff - 16 november
  ✓ Träningsmatch Reymers IK F17 - 16 november

✓ Found 3 registrations

Creating iCal calendar with 3 events...
  ✓ Added: Träning - Gustav Klang
  ✓ Added: Nacka Winter Kickoff - Gustav Klang
  ✓ Added: Träningsmatch Reymers IK F17 - Emma Klang

✓ Calendar saved to: laget_registrations.ics

============================================================
Done! You can now import 'laget_registrations.ics' into your calendar app.
============================================================
```

## Security Best Practices

- **Config file**: Use `init-config` command which creates file with 600 permissions
- **Environment variables**: Set them in your shell profile or use a `.env` file (not committed to git)
- **Avoid command line passwords**: Command line history may expose passwords
- **Never commit credentials**: The `.gitignore` is configured to protect you

## Troubleshooting

**"Login failed"**
- Check your credentials are correct
- Make sure you can login manually on laget.se

**"No registrations found"**
- Make sure you have active registrations on laget.se
- Check that you're logged in to the correct account

**"Could not parse date/time"**
- Some events might have unusual date formats
- The script will skip these events and continue with others

**"Module not found"**
- Make sure you've activated the virtual environment: `source venv/bin/activate`
- Make sure you've installed dependencies: `pip install -r requirements.txt`

## How It Works

1. **Authentication:** Uses the laget.se login form with CSRF token protection
2. **Scraping:** Fetches registration data from the "Mina anmälningar" modal
3. **Parsing:** Extracts event details from HTML responses
4. **iCal Generation:** Creates RFC 5545 compliant iCalendar format
5. **File Output:** Saves to `.ics` file ready for import

## Data Extracted

For each registration, the following information is extracted:

- Event title (e.g., "Träning", "Match")
- Team/group name
- Child name (for which child the registration is for)
- Date and time (start and end)
- Location name
- Full address
- Event description and requirements
- Google Maps link
- Registration deadline

## Development

Run in development mode:

```bash
source venv/bin/activate
python laget_scraper.py scrape
```

## License

This is a personal tool. Use at your own risk.
