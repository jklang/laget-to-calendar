#!/usr/bin/env python3
"""
Laget.se Scraper - Extracts registrations and creates iCal calendar entries
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event, Alarm
import pytz
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import tomli

app = typer.Typer(help="Scrape registrations from laget.se and create iCal calendar entries")
console = Console()


class LagetSeScraper:
    """Scraper for laget.se registrations"""

    def __init__(self, email: str, password: str):
        self.session = requests.Session()
        self.base_url = "https://www.laget.se"
        self.email = email
        self.password = password
        self.logged_in = False

    def login(self) -> bool:
        """Login to laget.se"""
        console.print("Logging in to laget.se...", style="cyan")

        # Get login page to extract CSRF token
        login_url = f"{self.base_url}/Common/Auth/Login"
        response = self.session.get(login_url)

        if response.status_code != 200:
            console.print(f"Failed to load login page: {response.status_code}", style="red")
            return False

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract CSRF token
        csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})
        if not csrf_token:
            console.print("Could not find CSRF token", style="red")
            return False

        csrf_value = csrf_token.get('value')

        # Extract referer value
        referer_input = soup.find('input', {'name': 'Referer', 'id': 'Referer'})
        referer_value = referer_input.get('value') if referer_input else ''

        # Prepare login data
        login_data = {
            '__RequestVerificationToken': csrf_value,
            'Referer': referer_value,
            'Email': self.email,
            'Password': self.password,
            'KeepAlive': 'true'
        }

        # Perform login
        response = self.session.post(login_url, data=login_data)

        # Check if login was successful (should redirect to home page)
        if response.status_code == 200 and 'laget.se' in response.url:
            self.logged_in = True
            console.print("✓ Login successful", style="green")
            return True
        else:
            console.print(f"✗ Login failed: {response.status_code}", style="red")
            return False

    def get_registration_links(self) -> List[Dict[str, str]]:
        """Get list of registration links from the page"""
        console.print("\nFetching registration list...", style="cyan")

        if not self.logged_in:
            console.print("Not logged in!", style="red")
            return []

        # Get the main page which has the modal data
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all registration links in the modal
        registration_links = []

        # Search for links with pattern /Common/Rsvp/ModalContent
        links = soup.find_all('a', href=re.compile(r'/Common/Rsvp/ModalContent'))

        for link in links:
            href = link.get('href')
            if href:
                # Extract parameters from URL
                match = re.search(r'pk=(\d+)&childId=(\d+)&site=([^&]+)', href)
                if match:
                    registration_links.append({
                        'pk': match.group(1),
                        'childId': match.group(2),
                        'site': match.group(3),
                        'url': f"{self.base_url}{href}" if href.startswith('/') else href
                    })

        console.print(f"Found {len(registration_links)} registrations", style="green")
        return registration_links

    def get_registration_details(self, pk: str, child_id: str, site: str) -> Optional[Dict]:
        """Get detailed information for a specific registration"""
        url = f"{self.base_url}/Common/Rsvp/ModalContent"
        params = {'pk': pk, 'childId': child_id, 'site': site}

        response = self.session.get(url, params=params)

        if response.status_code != 200:
            console.print(f"Failed to get registration details: {response.status_code}", style="red")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract event details
        details = {}

        # Title
        title_elem = soup.find('p', class_='invitation__title')
        details['title'] = title_elem.text.strip() if title_elem else 'Unknown Event'

        # Team/subtitle
        subtitle_elem = soup.find('p', class_='invitation__subTitle')
        details['team'] = subtitle_elem.text.strip() if subtitle_elem else ''

        # Child name (second subtitle)
        subtitles = soup.find_all('p', class_='invitation__subTitle')
        if len(subtitles) > 1:
            details['child_name'] = subtitles[1].text.strip().replace('Anmälning för ', '')
        else:
            details['child_name'] = ''

        # Date, Time, Location, Deadline, Samling (gathering time)
        labels = soup.find_all('span', class_='invitation__label--noWidth')
        for label in labels:
            label_text = label.text.strip().replace(':', '')
            value_elem = label.find_next_sibling()
            if value_elem:
                value = value_elem.text.strip() if hasattr(value_elem, 'text') else ''
            else:
                # Try to get text after the label in the same parent
                parent = label.parent
                value = parent.text.replace(label.text, '').strip()

            if 'Datum' in label_text:
                details['date'] = value
            elif 'Tid' in label_text:
                details['time'] = value
            elif 'Plats' in label_text:
                details['location'] = value
            elif 'Anmälningsstopp' in label_text:
                details['deadline'] = value
            elif 'Samling' in label_text:
                details['samling'] = value

        # Address
        address_elem = soup.find('span', class_='invitation__place__address')
        details['address'] = address_elem.text.strip() if address_elem else ''

        # Additional info/comments
        comment_elem = soup.find('div', class_='invitation__comment')
        if comment_elem:
            comment_p = comment_elem.find('p')
            details['description'] = comment_p.text.strip() if comment_p else ''
        else:
            details['description'] = ''

        # Google Maps link
        map_link = soup.find('a', href=re.compile(r'google.com/maps'))
        if map_link:
            details['map_url'] = map_link.get('href')
        else:
            details['map_url'] = ''

        return details

    def parse_datetime(self, date_str: str, time_str: str, samling_str: Optional[str] = None) -> tuple:
        """Parse Swedish date and time strings into datetime objects

        Args:
            date_str: Date string (e.g., "16 november")
            time_str: Event time string (e.g., "10:00-11:00")
            samling_str: Optional gathering time string (e.g., "16 nov, 09:45")
                        If provided, this will be used as the start time

        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        # Swedish months mapping
        months_sv = {
            'januari': 1, 'februari': 2, 'mars': 3, 'april': 4,
            'maj': 5, 'juni': 6, 'juli': 7, 'augusti': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
            'okt': 10, 'nov': 11, 'dec': 12
        }

        # Parse date (e.g., "14 november")
        date_match = re.search(r'(\d+)\s+(\w+)', date_str)
        if not date_match:
            return None, None

        day = int(date_match.group(1))
        month_str = date_match.group(2).lower()
        month = months_sv.get(month_str)

        if not month:
            return None, None

        # Use current year (or next year if date has passed)
        current_year = datetime.now().year
        tz = pytz.timezone('Europe/Stockholm')

        # Determine start time: use samling if available, otherwise use event time
        if samling_str:
            # Parse samling time (e.g., "16 nov, 09:45")
            samling_match = re.search(r'(\d+):(\d+)', samling_str)
            if samling_match:
                start_hour = int(samling_match.group(1))
                start_minute = int(samling_match.group(2))
                start_dt = tz.localize(datetime(current_year, month, day, start_hour, start_minute))
            else:
                # Fallback to event time if samling parsing fails
                time_match = re.search(r'(\d+):(\d+)', time_str)
                if not time_match:
                    return None, None
                start_hour = int(time_match.group(1))
                start_minute = int(time_match.group(2))
                start_dt = tz.localize(datetime(current_year, month, day, start_hour, start_minute))
        else:
            # No samling time, use event time
            time_match = re.search(r'(\d+):(\d+)', time_str)
            if not time_match:
                return None, None
            start_hour = int(time_match.group(1))
            start_minute = int(time_match.group(2))
            start_dt = tz.localize(datetime(current_year, month, day, start_hour, start_minute))

        # Parse end time from event time (e.g., "10:00-11:00")
        end_match = re.search(r'-(\d+):(\d+)', time_str)
        if end_match:
            end_hour = int(end_match.group(1))
            end_minute = int(end_match.group(2))
            end_dt = tz.localize(datetime(current_year, month, day, end_hour, end_minute))
        else:
            # Default to 1 hour duration from start
            end_dt = start_dt + timedelta(hours=1)

        return start_dt, end_dt

    def get_all_registrations(self) -> List[Dict]:
        """Get all registrations with details"""
        if not self.logged_in:
            if not self.login():
                return []

        # Get registration links
        links = self.get_registration_links()

        registrations = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Fetching details for {len(links)} registrations...",
                total=len(links)
            )

            for i, link in enumerate(links, 1):
                progress.update(task, description=f"[cyan]Fetching registration {i}/{len(links)}...")
                details = self.get_registration_details(link['pk'], link['childId'], link['site'])

                if details:
                    details['pk'] = link['pk']
                    details['childId'] = link['childId']
                    details['site'] = link['site']
                    registrations.append(details)
                    console.print(f"  ✓ {details.get('title', 'Unknown')} - {details.get('date', 'No date')}", style="green")
                else:
                    console.print(f"  ✗ Failed to get details", style="red")

                progress.advance(task)

        return registrations

    def create_ical_calendar(self, registrations: List[Dict], filename: str = 'laget_registrations.ics'):
        """Create iCal calendar file from registrations"""
        console.print(f"\nCreating iCal calendar with {len(registrations)} events...", style="cyan")

        cal = Calendar()
        cal.add('prodid', '-//Laget.se Registration Calendar//SE')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'Laget.se Anmälningar')
        cal.add('x-wr-caldesc', 'Registrations from laget.se')

        for reg in registrations:
            event = Event()

            # Event title
            title = reg.get('title', 'Event')
            child_name = reg.get('child_name', '')
            if child_name:
                title = f"{title} - {child_name}"

            event.add('summary', title)

            # Parse and add datetime
            date_str = reg.get('date', '')
            time_str = reg.get('time', '')
            samling_str = reg.get('samling')  # Optional gathering time

            if date_str and time_str:
                start_dt, end_dt = self.parse_datetime(date_str, time_str, samling_str)

                if start_dt and end_dt:
                    event.add('dtstart', start_dt)
                    event.add('dtend', end_dt)
                else:
                    console.print(f"  ⚠ Could not parse date/time for: {title}", style="yellow")
                    continue
            else:
                console.print(f"  ⚠ Missing date/time for: {title}", style="yellow")
                continue

            # Location
            location = reg.get('location', '')
            address = reg.get('address', '')
            if location and address:
                event.add('location', f"{location}, {address}")
            elif location:
                event.add('location', location)

            # Description
            description_parts = []

            team = reg.get('team', '')
            if team:
                description_parts.append(f"Lag: {team}")

            desc = reg.get('description', '')
            if desc:
                description_parts.append(f"\n{desc}")

            map_url = reg.get('map_url', '')
            if map_url:
                description_parts.append(f"\n\nKarta: {map_url}")

            if description_parts:
                event.add('description', '\n'.join(description_parts))

            # Add unique ID
            event.add('uid', f"laget-{reg.get('pk')}-{reg.get('childId')}@laget.se")

            # Add timestamp
            event.add('dtstamp', datetime.now(pytz.UTC))

            # Add reminders/alarms
            # 1 day before
            alarm_1day = Alarm()
            alarm_1day.add('action', 'DISPLAY')
            alarm_1day.add('description', f"Reminder: {title} tomorrow")
            alarm_1day.add('trigger', timedelta(days=-1))
            event.add_component(alarm_1day)

            # 2 hours before
            alarm_2hours = Alarm()
            alarm_2hours.add('action', 'DISPLAY')
            alarm_2hours.add('description', f"Reminder: {title} in 2 hours")
            alarm_2hours.add('trigger', timedelta(hours=-2))
            event.add_component(alarm_2hours)

            cal.add_component(event)
            console.print(f"  ✓ Added: {title}", style="green")

        # Write to file
        with open(filename, 'wb') as f:
            f.write(cal.to_ical())

        console.print(f"\n✓ Calendar saved to: {filename}", style="green bold")
        return filename


def load_config(config_file: Path) -> Dict:
    """Load configuration from TOML file"""
    if not config_file.exists():
        return {}

    with open(config_file, 'rb') as f:
        return tomli.load(f)


def get_credentials(
    email: Optional[str],
    password: Optional[str],
    config_file: Path
) -> tuple[str, str]:
    """Get credentials from various sources in order of precedence:
    1. Command line arguments
    2. Environment variables
    3. Config file
    4. Interactive prompt
    """

    # Try command line args first
    if email and password:
        return email, password

    # Try environment variables
    env_email = os.environ.get('LAGET_EMAIL')
    env_password = os.environ.get('LAGET_PASSWORD')

    if env_email and env_password:
        console.print("Using credentials from environment variables", style="dim")
        return env_email, env_password

    # Try config file
    config = load_config(config_file)
    if 'email' in config and 'password' in config:
        console.print(f"Using credentials from config file: {config_file}", style="dim")
        return config['email'], config['password']

    # Fall back to interactive prompt
    console.print("\n[yellow]No credentials found. Please enter them now:[/yellow]")

    if not email:
        email = typer.prompt("Email")

    if not password:
        password = typer.prompt("Password", hide_input=True)

    return email, password


@app.command()
def scrape(
    email: Optional[str] = typer.Option(
        None,
        "--email",
        "-e",
        help="Laget.se email address"
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Laget.se password (use environment variable for security)"
    ),
    output: str = typer.Option(
        "laget_registrations.ics",
        "--output",
        "-o",
        help="Output filename for the iCal file"
    ),
    config_file: Path = typer.Option(
        Path.home() / ".config" / "laget-scraper" / "config.toml",
        "--config",
        "-c",
        help="Path to config file"
    ),
    include_practice: bool = typer.Option(
        False,
        "--include-practice/--exclude-practice",
        help="Include practice events (Träning). Default is to exclude them."
    ),
):
    """
    Scrape registrations from laget.se and create an iCal calendar file.

    By default, practice events (Träning) are excluded. Use --include-practice to include them.

    Credentials can be provided via:
    - Command line arguments (--email, --password)
    - Environment variables (LAGET_EMAIL, LAGET_PASSWORD)
    - Config file (default: ~/.config/laget-scraper/config.toml)
    - Interactive prompt
    """

    console.print("\n[bold cyan]Laget.se to iCal Converter[/bold cyan]")
    console.print("=" * 60 + "\n")

    # Get credentials
    try:
        email, password = get_credentials(email, password, config_file)
    except typer.Abort:
        console.print("\n[red]Aborted by user[/red]")
        raise typer.Exit(1)

    # Create scraper
    scraper = LagetSeScraper(email, password)

    # Get all registrations
    registrations = scraper.get_all_registrations()

    if not registrations:
        console.print("\n[red]✗ No registrations found or failed to fetch data[/red]")
        raise typer.Exit(1)

    # Filter out practice events if not included
    if not include_practice:
        original_count = len(registrations)
        registrations = [r for r in registrations if r.get('title', '').lower() != 'träning']
        excluded_count = original_count - len(registrations)
        if excluded_count > 0:
            console.print(f"[dim]Excluded {excluded_count} practice event(s)[/dim]")

    if not registrations:
        console.print("\n[yellow]⚠ No registrations to export after filtering (all were practice events)[/yellow]")
        console.print("[dim]Use --include-practice to include practice events[/dim]")
        raise typer.Exit(0)

    console.print(f"\n[green]✓ Found {len(registrations)} registrations to export[/green]")

    # Create iCal file
    filename = scraper.create_ical_calendar(registrations, output)

    console.print("\n" + "=" * 60)
    console.print(f"[bold green]Done! You can now import '{filename}' into your calendar app.[/bold green]")
    console.print("=" * 60 + "\n")


@app.command()
def init_config(
    config_file: Path = typer.Option(
        Path.home() / ".config" / "laget-scraper" / "config.toml",
        "--config",
        "-c",
        help="Path to config file to create"
    ),
):
    """
    Create a configuration file with your credentials.
    """

    if config_file.exists():
        overwrite = typer.confirm(f"Config file already exists at {config_file}. Overwrite?")
        if not overwrite:
            console.print("[yellow]Aborted[/yellow]")
            raise typer.Exit(0)

    console.print("\n[bold cyan]Creating configuration file[/bold cyan]")
    console.print(f"Location: {config_file}\n")

    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)

    # Create directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write config file
    with open(config_file, 'w') as f:
        f.write(f'# Laget.se Scraper Configuration\n')
        f.write(f'email = "{email}"\n')
        f.write(f'password = "{password}"\n')

    # Set restrictive permissions
    config_file.chmod(0o600)

    console.print(f"\n[green]✓ Config file created at: {config_file}[/green]")
    console.print(f"[dim]File permissions set to 600 (owner read/write only)[/dim]\n")


if __name__ == "__main__":
    app()
