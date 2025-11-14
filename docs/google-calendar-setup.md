# Google Calendar API Setup Guide

This guide will help you set up Google Calendar API access for automatic event synchronization.

## Prerequisites

- Google account with Google Calendar enabled
- Python environment with the laget-scraper dependencies installed

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top, then click "New Project"
3. Give your project a name (e.g., "Laget Calendar Sync")
4. Click "Create"

### 2. Enable Google Calendar API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click on "Google Calendar API" in the results
4. Click "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields:
     - App name: "Laget Calendar Sync" (or your choice)
     - User support email: your email
     - Developer contact: your email
   - Click "Save and Continue"
   - Skip scopes (click "Save and Continue")
   - **Add your email as a test user** (click "Add Users")
     - **Important:** You MUST add your email here to access the app
     - Without this, you'll get "Error 403: access_denied"
   - Click "Save and Continue"
4. Go to Clients > Create Client
   - Application type: "Desktop app"
   - Name: "Laget Scraper" (or your choice)
   - Click "Create"
5. Download the credentials:
   - Click "Download JSON" in the popup
   - Save the file as `credentials.json`

### 4. Place Credentials File

Move the downloaded `credentials.json` to:
```
~/.config/laget-scraper/credentials.json
```

Or another location of your choice (specify with `--google-credentials-file` or in config).

```bash
# Create directory
mkdir -p ~/.config/laget-scraper

# Move credentials file
mv ~/Downloads/credentials.json ~/.config/laget-scraper/credentials.json
```

### 5. First-Time Authentication

The first time you run the scraper with Google Calendar integration, it will:

1. Open your web browser automatically
2. Ask you to log in to your Google account
3. Show a warning that the app isn't verified (this is normal for personal projects)
   - Click "Advanced" > "Go to [your app name] (unsafe)"
4. Review and grant calendar permissions
5. Save an authentication token for future use

After this initial setup, the scraper will automatically use the saved token.

## Usage Examples

### Command Line

```bash
# Use Google Calendar integration
python laget_scraper.py scrape --calendar-mode google

# Use specific credentials file
python laget_scraper.py scrape \
  --calendar-mode google \
  --google-credentials-file ~/path/to/credentials.json

# Use custom calendar name
python laget_scraper.py scrape \
  --calendar-mode google \
  --calendar-name "Laget.se Events"
```

### Configuration File

Add to `~/.config/laget-scraper/config.yaml`:

```yaml
credentials:
  email: "your.email@example.com"
  password: "your_password"

calendar:
  mode: "google"  # or "both" for Google + macOS
  calendar_name: null  # null = primary calendar, or specify a name
  google_credentials_file: "~/.config/laget-scraper/credentials.json"
```

Then simply run:
```bash
python laget_scraper.py scrape
```

## Troubleshooting

### "Credentials file not found"

Make sure you've placed `credentials.json` in the correct location and specified the path correctly.

### "Access denied" or authentication fails

1. Make sure you've added your email as a test user in the OAuth consent screen
2. Try deleting the token file and re-authenticating:
   ```bash
   rm ~/.config/laget-scraper/token.json
   python laget_scraper.py scrape --calendar-mode google
   ```

### "API quota exceeded"

Google Calendar API has generous quotas for personal use. If you hit limits:
- Wait a few minutes before trying again
- Check your quota usage in Google Cloud Console

### Events not updating

The script identifies events by UID. If you manually delete events from Google Calendar, they will be re-added on the next sync. This is by design to ensure your calendar stays in sync with laget.se.

## Security Notes

- The `credentials.json` file contains your OAuth client ID and secret
- The `token.json` file (created after first auth) contains your access token
- Both files should be kept secure and not shared
- The script sets restrictive file permissions (600) automatically

## Alternative: Service Account

For automated/server deployments, consider using a Service Account instead of OAuth. However, Service Accounts require Google Workspace and additional setup. The OAuth flow described here is recommended for personal use.

## Further Resources

- [Google Calendar API Documentation](https://developers.google.com/calendar)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Python Quickstart for Calendar API](https://developers.google.com/calendar/api/quickstart/python)
