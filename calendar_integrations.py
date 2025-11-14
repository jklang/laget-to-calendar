"""
Calendar integration backends for automatic event synchronization
"""

import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json

from rich.console import Console

console = Console()


class CalendarIntegration(ABC):
    """Abstract base class for calendar integrations"""

    def __init__(self, calendar_name: Optional[str] = None):
        """
        Initialize calendar integration

        Args:
            calendar_name: Name of calendar to use. If None, uses default/primary calendar.
        """
        self.calendar_name = calendar_name

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate and establish connection to calendar service

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def add_event(self, event_data: Dict) -> bool:
        """
        Add a new event to the calendar

        Args:
            event_data: Dictionary containing event details (title, start, end, location, etc.)

        Returns:
            True if event added successfully, False otherwise
        """
        pass

    @abstractmethod
    def update_event(self, uid: str, event_data: Dict) -> bool:
        """
        Update an existing event

        Args:
            uid: Unique identifier for the event
            event_data: Dictionary containing updated event details

        Returns:
            True if event updated successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_event_by_uid(self, uid: str) -> Optional[Dict]:
        """
        Retrieve an event by its UID

        Args:
            uid: Unique identifier for the event

        Returns:
            Event data dictionary if found, None otherwise
        """
        pass

    def sync_events(self, events: List[Dict]) -> Tuple[int, int, int]:
        """
        Synchronize a list of events with the calendar

        Args:
            events: List of event dictionaries to sync

        Returns:
            Tuple of (added_count, updated_count, error_count)
        """
        added = 0
        updated = 0
        errors = 0

        for event in events:
            uid = event.get('uid')
            if not uid:
                console.print(f"  ⚠ Skipping event without UID: {event.get('title', 'Unknown')}", style="yellow")
                errors += 1
                continue

            # Check if event already exists
            existing_event = self.get_event_by_uid(uid)

            if existing_event:
                # Check if event needs updating
                if self._event_needs_update(existing_event, event):
                    if self.update_event(uid, event):
                        console.print(f"  ↻ Updated: {event.get('title', 'Unknown')}", style="cyan")
                        updated += 1
                    else:
                        console.print(f"  ✗ Failed to update: {event.get('title', 'Unknown')}", style="red")
                        errors += 1
                else:
                    # Event unchanged, skip
                    pass
            else:
                # Add new event
                if self.add_event(event):
                    console.print(f"  ✓ Added: {event.get('title', 'Unknown')}", style="green")
                    added += 1
                else:
                    console.print(f"  ✗ Failed to add: {event.get('title', 'Unknown')}", style="red")
                    errors += 1

        return added, updated, errors

    def _event_needs_update(self, existing: Dict, new: Dict) -> bool:
        """
        Check if an event needs to be updated

        Args:
            existing: Existing event data
            new: New event data

        Returns:
            True if event should be updated, False otherwise
        """
        # Compare key fields
        fields_to_compare = ['title', 'start', 'end', 'location', 'description']

        for field in fields_to_compare:
            if existing.get(field) != new.get(field):
                return True

        return False


class MacOSCalendarIntegration(CalendarIntegration):
    """macOS Calendar integration using EventKit"""

    def __init__(self, calendar_name: Optional[str] = None):
        super().__init__(calendar_name)
        self.event_store = None
        self.calendar = None

    def authenticate(self) -> bool:
        """Request calendar access and initialize EventKit"""
        if sys.platform != 'darwin':
            console.print("macOS Calendar integration is only available on macOS", style="red")
            return False

        try:
            # Import EventKit (macOS only)
            import EventKit
            from Foundation import NSDate
            import objc

            self.EventKit = EventKit
            self.NSDate = NSDate
            self.objc = objc

            # Create event store
            self.event_store = EventKit.EKEventStore.alloc().init()

            # Request access (macOS 10.9+)
            console.print("Requesting calendar access...", style="cyan")

            # Use semaphore to wait for async permission request
            import threading
            semaphore = threading.Semaphore(0)
            granted = [False]

            def completion_handler(granted_val, error):
                granted[0] = granted_val
                if error:
                    console.print(f"Error requesting access: {error}", style="red")
                semaphore.release()

            self.event_store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent,
                completion_handler
            )

            # Wait for permission response (with timeout)
            if not semaphore.acquire(timeout=30):
                console.print("Calendar access request timed out", style="red")
                return False

            if not granted[0]:
                console.print("Calendar access denied. Please grant permission in System Settings > Privacy & Security > Calendars", style="red")
                return False

            console.print("✓ Calendar access granted", style="green")

            # Get or create calendar
            if self.calendar_name:
                self.calendar = self._find_or_create_calendar(self.calendar_name)
            else:
                self.calendar = self.event_store.defaultCalendarForNewEvents()
                console.print(f"Using default calendar: {self.calendar.title()}", style="dim")

            return self.calendar is not None

        except ImportError:
            console.print("EventKit not available. Install with: pip install pyobjc-framework-EventKit pyobjc-framework-Cocoa", style="red")
            return False
        except Exception as e:
            console.print(f"Failed to initialize macOS Calendar: {e}", style="red")
            return False

    def _find_or_create_calendar(self, name: str):
        """Find or create a calendar by name"""
        # Search for existing calendar
        calendars = self.event_store.calendarsForEntityType_(self.EventKit.EKEntityTypeEvent)

        for cal in calendars:
            if cal.title() == name:
                console.print(f"Using existing calendar: {name}", style="dim")
                return cal

        # Create new calendar
        console.print(f"Creating new calendar: {name}", style="cyan")
        new_calendar = self.EventKit.EKCalendar.calendarForEntityType_eventStore_(
            self.EventKit.EKEntityTypeEvent,
            self.event_store
        )
        new_calendar.setTitle_(name)

        # Use iCloud source if available, otherwise local
        sources = self.event_store.sources()
        icloud_source = None
        local_source = None

        for source in sources:
            if source.sourceType() == self.EventKit.EKSourceTypeCalDAV:
                icloud_source = source
                break
            elif source.sourceType() == self.EventKit.EKSourceTypeLocal:
                local_source = source

        new_calendar.setSource_(icloud_source or local_source)

        success, error = self.event_store.saveCalendar_commit_error_(new_calendar, True, None)
        if not success:
            error_msg = str(error) if error else "Unknown error"
            console.print(f"Error creating calendar: {error_msg}", style="red")
            return None

        console.print(f"✓ Created calendar: {name}", style="green")
        return new_calendar

    def add_event(self, event_data: Dict) -> bool:
        """Add event to macOS Calendar"""
        try:
            event = self.EventKit.EKEvent.eventWithEventStore_(self.event_store)
            event.setTitle_(event_data.get('title', 'Untitled Event'))
            event.setStartDate_(self._python_datetime_to_nsdate(event_data['start']))
            event.setEndDate_(self._python_datetime_to_nsdate(event_data['end']))

            if event_data.get('location'):
                event.setLocation_(event_data['location'])

            if event_data.get('description'):
                event.setNotes_(event_data['description'])

            event.setCalendar_(self.calendar)

            # Add alarms if specified
            if event_data.get('alarms'):
                for alarm_offset in event_data['alarms']:
                    alarm = self.EventKit.EKAlarm.alarmWithRelativeOffset_(alarm_offset)
                    event.addAlarm_(alarm)

            # Save with UID for later retrieval
            success, error = self.event_store.saveEvent_span_commit_error_(
                event,
                self.EventKit.EKSpanThisEvent,
                True,
                None
            )

            if not success:
                error_msg = str(error) if error else "Unknown error"
                console.print(f"Error saving event: {error_msg}", style="red")
                return False

            # Store mapping of our UID to EventKit's identifier
            # (We'll use notes field to store our UID)
            notes = event_data.get('description', '')
            uid_marker = f"\n\n[UID: {event_data['uid']}]"
            if uid_marker not in notes:
                event.setNotes_(notes + uid_marker)
                self.event_store.saveEvent_span_commit_error_(
                    event,
                    self.EventKit.EKSpanThisEvent,
                    True,
                    None
                )

            return True

        except Exception as e:
            console.print(f"Error adding event: {e}", style="red")
            return False

    def update_event(self, uid: str, event_data: Dict) -> bool:
        """Update existing event in macOS Calendar"""
        try:
            # Find event by UID marker in notes
            event = self._find_event_by_uid(uid)
            if not event:
                console.print(f"Event not found for update: {uid}", style="yellow")
                return False

            # Update event details
            event.setTitle_(event_data.get('title', 'Untitled Event'))
            event.setStartDate_(self._python_datetime_to_nsdate(event_data['start']))
            event.setEndDate_(self._python_datetime_to_nsdate(event_data['end']))

            if event_data.get('location'):
                event.setLocation_(event_data['location'])

            if event_data.get('description'):
                notes = event_data['description']
                uid_marker = f"\n\n[UID: {uid}]"
                if uid_marker not in notes:
                    notes += uid_marker
                event.setNotes_(notes)

            # Save changes
            success, error = self.event_store.saveEvent_span_commit_error_(
                event,
                self.EventKit.EKSpanThisEvent,
                True,
                None
            )

            if not success:
                error_msg = str(error) if error else "Unknown error"
                console.print(f"Error updating event: {error_msg}", style="red")
                return False

            return True

        except Exception as e:
            console.print(f"Error updating event: {e}", style="red")
            return False

    def get_event_by_uid(self, uid: str) -> Optional[Dict]:
        """Get event by UID"""
        event = self._find_event_by_uid(uid)
        if not event:
            return None

        return {
            'title': event.title(),
            'start': self._nsdate_to_python_datetime(event.startDate()),
            'end': self._nsdate_to_python_datetime(event.endDate()),
            'location': event.location() or '',
            'description': event.notes() or '',
            'uid': uid
        }

    def _find_event_by_uid(self, uid: str):
        """Find an event by searching for UID marker in notes"""
        # Search events in the calendar
        # Create date range (search 1 year back and forward)
        from datetime import timedelta
        now = datetime.now()
        start_date = self._python_datetime_to_nsdate(now - timedelta(days=365))
        end_date = self._python_datetime_to_nsdate(now + timedelta(days=365))

        predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
            start_date,
            end_date,
            [self.calendar]
        )

        events = self.event_store.eventsMatchingPredicate_(predicate)

        uid_marker = f"[UID: {uid}]"
        for event in events:
            notes = event.notes() or ''
            if uid_marker in notes:
                return event

        return None

    def _python_datetime_to_nsdate(self, dt: datetime):
        """Convert Python datetime to NSDate"""
        return self.NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())

    def _nsdate_to_python_datetime(self, nsdate) -> datetime:
        """Convert NSDate to Python datetime"""
        timestamp = nsdate.timeIntervalSince1970()
        return datetime.fromtimestamp(timestamp)


class GoogleCalendarIntegration(CalendarIntegration):
    """Google Calendar integration using Google Calendar API"""

    def __init__(self, calendar_name: Optional[str] = None, credentials_file: Optional[str] = None):
        super().__init__(calendar_name)
        self.credentials_file = credentials_file or str(Path.home() / ".config" / "laget-scraper" / "credentials.json")
        self.token_file = str(Path.home() / ".config" / "laget-scraper" / "token.json")
        self.service = None
        self.calendar_id = None

    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ['https://www.googleapis.com/auth/calendar']

            creds = None
            token_path = Path(self.token_file)

            # Load existing token if available
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    console.print("Refreshing Google Calendar access token...", style="cyan")
                    creds.refresh(Request())
                else:
                    # Check if credentials file exists
                    if not Path(self.credentials_file).exists():
                        console.print(f"Google Calendar credentials file not found: {self.credentials_file}", style="red")
                        console.print("See docs/google-calendar-setup.md for setup instructions", style="yellow")
                        return False

                    console.print("Opening browser for Google Calendar authentication...", style="cyan")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save token for future use
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                console.print(f"✓ Saved authentication token to {self.token_file}", style="green")

            # Build service
            self.service = build('calendar', 'v3', credentials=creds)
            console.print("✓ Connected to Google Calendar", style="green")

            # Get or create calendar
            if self.calendar_name:
                self.calendar_id = self._find_or_create_calendar(self.calendar_name)
            else:
                self.calendar_id = 'primary'
                console.print("Using primary Google Calendar", style="dim")

            return self.calendar_id is not None

        except ImportError:
            console.print("Google Calendar libraries not available. Install with: pip install google-auth google-auth-oauthlib google-api-python-client", style="red")
            return False
        except Exception as e:
            console.print(f"Failed to authenticate with Google Calendar: {e}", style="red")
            return False

    def _find_or_create_calendar(self, name: str) -> Optional[str]:
        """Find or create a calendar by name"""
        try:
            # List calendars
            calendar_list = self.service.calendarList().list().execute()

            # Search for existing calendar
            for calendar in calendar_list.get('items', []):
                if calendar.get('summary') == name:
                    console.print(f"Using existing Google Calendar: {name}", style="dim")
                    return calendar['id']

            # Create new calendar
            console.print(f"Creating new Google Calendar: {name}", style="cyan")
            calendar = {
                'summary': name,
                'timeZone': 'Europe/Stockholm'
            }
            created_calendar = self.service.calendars().insert(body=calendar).execute()
            console.print(f"✓ Created Google Calendar: {name}", style="green")
            return created_calendar['id']

        except Exception as e:
            console.print(f"Error finding/creating calendar: {e}", style="red")
            return None

    def add_event(self, event_data: Dict) -> bool:
        """Add event to Google Calendar"""
        try:
            # Build event object
            event = {
                'summary': event_data.get('title', 'Untitled Event'),
                'location': event_data.get('location', ''),
                'description': event_data.get('description', ''),
                'start': {
                    'dateTime': event_data['start'].isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'end': {
                    'dateTime': event_data['end'].isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'extendedProperties': {
                    'private': {
                        'lagetUid': event_data['uid']
                    }
                }
            }

            # Add reminders/alarms if specified
            if event_data.get('alarms'):
                reminders = []
                for alarm_offset_seconds in event_data['alarms']:
                    minutes = int(abs(alarm_offset_seconds) / 60)
                    reminders.append({'method': 'popup', 'minutes': minutes})
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': reminders
                }

            # Insert event
            self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return True

        except Exception as e:
            console.print(f"Error adding Google Calendar event: {e}", style="red")
            return False

    def update_event(self, uid: str, event_data: Dict) -> bool:
        """Update existing event in Google Calendar"""
        try:
            # Find event by extended property
            event_id = self._find_event_id_by_uid(uid)
            if not event_id:
                console.print(f"Google Calendar event not found for update: {uid}", style="yellow")
                return False

            # Build updated event object
            event = {
                'summary': event_data.get('title', 'Untitled Event'),
                'location': event_data.get('location', ''),
                'description': event_data.get('description', ''),
                'start': {
                    'dateTime': event_data['start'].isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'end': {
                    'dateTime': event_data['end'].isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'extendedProperties': {
                    'private': {
                        'lagetUid': uid
                    }
                }
            }

            # Update event
            self.service.events().patch(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            return True

        except Exception as e:
            console.print(f"Error updating Google Calendar event: {e}", style="red")
            return False

    def get_event_by_uid(self, uid: str) -> Optional[Dict]:
        """Get event by UID from Google Calendar"""
        try:
            event_id = self._find_event_id_by_uid(uid)
            if not event_id:
                return None

            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            # Parse datetime
            from dateutil import parser as date_parser

            return {
                'title': event.get('summary', ''),
                'start': date_parser.parse(event['start'].get('dateTime', event['start'].get('date'))),
                'end': date_parser.parse(event['end'].get('dateTime', event['end'].get('date'))),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'uid': uid
            }

        except Exception as e:
            console.print(f"Error getting Google Calendar event: {e}", style="red")
            return None

    def _find_event_id_by_uid(self, uid: str) -> Optional[str]:
        """Find Google Calendar event ID by laget UID"""
        try:
            # Search for events with matching extended property
            # Note: Google Calendar API doesn't support filtering by extended properties directly
            # So we need to fetch events and filter client-side

            from datetime import timedelta
            now = datetime.now()
            time_min = (now - timedelta(days=365)).isoformat() + 'Z'
            time_max = (now + timedelta(days=365)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                privateExtendedProperty=f'lagetUid={uid}'
            ).execute()

            events = events_result.get('items', [])

            if events:
                return events[0]['id']

            return None

        except Exception as e:
            console.print(f"Error searching for Google Calendar event: {e}", style="red")
            return None
