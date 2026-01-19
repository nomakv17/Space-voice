"""Google Calendar integration tools for voice agents.

Provides tools for:
- Listing calendars
- Checking availability (free/busy)
- Creating calendar events (booking appointments)
- Listing upcoming events
- Canceling events
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class GoogleCalendarTools:
    """Google Calendar API integration tools.

    Uses Google Calendar API v3 for:
    - Calendar discovery
    - Free/busy queries
    - Event creation (booking)
    - Event listing
    - Event cancellation
    """

    BASE_URL = "https://www.googleapis.com/calendar/v3"

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Google Calendar tools.

        Args:
            access_token: Google OAuth 2.0 access token
            refresh_token: Optional refresh token for auto-renewal
            client_id: Optional client ID for token refresh
            client_secret: Optional client secret for token refresh
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _refresh_token_if_needed(self, response: httpx.Response) -> bool:
        """Attempt to refresh token if response is 401.

        Returns True if token was refreshed, False otherwise.
        """
        if response.status_code != HTTPStatus.UNAUTHORIZED:
            return False

        # Validate we have all required credentials for refresh
        if not self.refresh_token:
            print("[CALENDAR ERROR] Token expired but no refresh_token available", flush=True)  # noqa: T201
            logger.error("google_calendar_no_refresh_token")
            return False

        if not self.client_id or not self.client_secret:
            print("[CALENDAR ERROR] Token expired but missing client_id/client_secret", flush=True)  # noqa: T201
            logger.error("google_calendar_missing_oauth_credentials")
            return False

        print("[CALENDAR] Attempting to refresh Google Calendar token...", flush=True)  # noqa: T201

        try:
            async with httpx.AsyncClient(timeout=10.0) as refresh_client:
                refresh_response = await refresh_client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )

                if refresh_response.status_code == HTTPStatus.OK:
                    data = refresh_response.json()
                    self.access_token = data["access_token"]

                    # Recreate client with new token
                    if self._client:
                        await self._client.aclose()
                        self._client = None

                    print("[CALENDAR] Token refreshed successfully", flush=True)  # noqa: T201
                    logger.info("google_calendar_token_refreshed")
                    return True
                print(
                    f"[CALENDAR ERROR] Token refresh failed: {refresh_response.status_code} - {refresh_response.text}",
                    flush=True,
                )  # noqa: T201
                logger.error(
                    "google_calendar_token_refresh_http_error", status=refresh_response.status_code
                )

        except Exception as e:
            print(f"[CALENDAR ERROR] Token refresh exception: {type(e).__name__}: {e}", flush=True)  # noqa: T201
            logger.warning("google_calendar_token_refresh_failed", error=str(e))

        return False

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        """Get OpenAI function calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "google_calendar_list_calendars",
                    "description": "List all calendars the user has access to",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "google_calendar_check_availability",
                    "description": "Get AVAILABLE appointment slots. Returns a list of specific available times like 'Monday January 20th at 10 AM'. Use this to offer customers real times to choose from. Check the next 5-7 days.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (use 'primary' for main calendar)",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start of search window (ISO 8601, e.g., 2026-01-19T09:00:00-05:00). Use today or tomorrow.",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End of search window (ISO 8601). Search 5-7 days ahead.",
                            },
                        },
                        "required": ["start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "google_calendar_create_event",
                    "description": "Create a calendar event (book an appointment). Use this to schedule meetings or appointments.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Event title (e.g., 'HVAC Service Appointment')",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Event start time (ISO 8601 format)",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Event end time (ISO 8601 format)",
                            },
                            "description": {
                                "type": "string",
                                "description": "Event description with details",
                            },
                            "attendee_email": {
                                "type": "string",
                                "description": "Email of the attendee to invite",
                            },
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (use 'primary' for main calendar)",
                            },
                            "location": {
                                "type": "string",
                                "description": "Event location/address",
                            },
                        },
                        "required": ["summary", "start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "google_calendar_list_events",
                    "description": "List upcoming calendar events",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (use 'primary' for main calendar)",
                            },
                            "time_min": {
                                "type": "string",
                                "description": "Filter events starting after this time (ISO 8601)",
                            },
                            "time_max": {
                                "type": "string",
                                "description": "Filter events starting before this time (ISO 8601)",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of events to return (default 10, max 100)",
                            },
                            "query": {
                                "type": "string",
                                "description": "Free text search query",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "google_calendar_cancel_event",
                    "description": "Cancel/delete a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "type": "string",
                                "description": "The event ID to cancel",
                            },
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (use 'primary' for main calendar)",
                            },
                            "send_updates": {
                                "type": "string",
                                "enum": ["all", "externalOnly", "none"],
                                "description": "Whether to send cancellation emails",
                            },
                        },
                        "required": ["event_id"],
                    },
                },
            },
        ]

    async def list_calendars(self) -> dict[str, Any]:
        """List all calendars the user has access to."""
        try:
            response = await self.client.get("/users/me/calendarList")

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                if await self._refresh_token_if_needed(response):
                    response = await self.client.get("/users/me/calendarList")

            if response.status_code != HTTPStatus.OK:
                return {
                    "success": False,
                    "error": f"Failed to list calendars: {response.text}",
                }

            data = response.json()
            calendars = []
            for cal in data.get("items", []):
                calendars.append(
                    {
                        "id": cal["id"],
                        "summary": cal.get("summary"),
                        "description": cal.get("description"),
                        "primary": cal.get("primary", False),
                        "access_role": cal.get("accessRole"),
                        "time_zone": cal.get("timeZone"),
                    }
                )

            return {"success": True, "calendars": calendars}

        except Exception as e:
            logger.exception("google_calendar_list_calendars_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def check_availability(
        self,
        start_time: str,
        end_time: str,
        calendar_id: str = "primary",
        slot_duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Check availability and return AVAILABLE time slots.

        Returns a list of available appointment slots (not busy periods).
        This makes it easy for the AI to offer specific times to customers.
        """
        try:
            payload = {
                "timeMin": start_time,
                "timeMax": end_time,
                "items": [{"id": calendar_id}],
            }

            response = await self.client.post("/freeBusy", json=payload)

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                if await self._refresh_token_if_needed(response):
                    response = await self.client.post("/freeBusy", json=payload)

            if response.status_code != HTTPStatus.OK:
                return {
                    "success": False,
                    "error": f"Failed to check availability: {response.text}",
                }

            data = response.json()
            calendar_data = data.get("calendars", {}).get(calendar_id, {})
            busy_periods = calendar_data.get("busy", [])

            # Parse busy periods into datetime objects
            busy_ranges: list[tuple[datetime, datetime]] = []
            for period in busy_periods:
                busy_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
                busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
                busy_ranges.append((busy_start, busy_end))

            # Sort busy periods by start time
            busy_ranges.sort(key=lambda x: x[0])

            # Calculate available slots during business hours (9am-5pm)
            range_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            range_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

            available_slots: list[dict[str, str]] = []
            slot_duration = timedelta(minutes=slot_duration_minutes)

            # Iterate through each day in the range
            current_day = range_start.replace(hour=0, minute=0, second=0, microsecond=0)
            while current_day < range_end:
                # Skip weekends
                if current_day.weekday() < 5:  # Monday = 0, Friday = 4
                    # Business hours: 9am to 5pm
                    day_start = current_day.replace(hour=9, minute=0)
                    day_end = current_day.replace(hour=17, minute=0)

                    # Adjust if outside our search range
                    day_start = max(day_start, range_start)
                    day_end = min(day_end, range_end)

                    # Find available slots on this day
                    slot_start = day_start
                    while slot_start + slot_duration <= day_end:
                        slot_end = slot_start + slot_duration

                        # Check if this slot overlaps with any busy period
                        is_available = True
                        for busy_start, busy_end in busy_ranges:
                            if slot_start < busy_end and slot_end > busy_start:
                                is_available = False
                                # Skip to end of busy period
                                slot_start = busy_end
                                break

                        if is_available:
                            # Format nicely for voice: "Monday January 20th at 10am"
                            day_name = slot_start.strftime("%A")
                            month_day = slot_start.strftime("%B %d")
                            time_str = (
                                slot_start.strftime("%I:%M %p").lstrip("0").replace(":00", "")
                            )

                            available_slots.append(
                                {
                                    "start": slot_start.isoformat(),
                                    "end": slot_end.isoformat(),
                                    "display": f"{day_name} {month_day} at {time_str}",
                                }
                            )
                            slot_start = slot_end

                            # Limit to 10 slots max
                            if len(available_slots) >= 10:
                                break

                    if len(available_slots) >= 10:
                        break

                current_day += timedelta(days=1)

            # Format response for easy use by AI
            if available_slots:
                slot_displays = [s["display"] for s in available_slots[:5]]
                message = f"Available times: {', '.join(slot_displays)}"
            else:
                message = "No available slots found in the requested time range."

            return {
                "success": True,
                "available_slots": available_slots[:5],  # Top 5 for voice
                "slot_count": len(available_slots),
                "message": message,
            }

        except Exception as e:
            logger.exception("google_calendar_check_availability_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        attendee_email: str | None = None,
        calendar_id: str = "primary",
        location: str | None = None,
    ) -> dict[str, Any]:
        """Create a calendar event (book an appointment)."""
        try:
            event: dict[str, Any] = {
                "summary": summary,
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time},
            }

            if description:
                event["description"] = description

            if location:
                event["location"] = location

            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]

            response = await self.client.post(
                f"/calendars/{calendar_id}/events",
                json=event,
                params={"sendUpdates": "all"},
            )

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                if await self._refresh_token_if_needed(response):
                    response = await self.client.post(
                        f"/calendars/{calendar_id}/events",
                        json=event,
                        params={"sendUpdates": "all"},
                    )

            if response.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
                return {
                    "success": False,
                    "error": f"Failed to create event: {response.text}",
                }

            data = response.json()

            return {
                "success": True,
                "message": f"Event '{summary}' created successfully",
                "event": {
                    "id": data["id"],
                    "summary": data["summary"],
                    "start": data["start"].get("dateTime"),
                    "end": data["end"].get("dateTime"),
                    "html_link": data.get("htmlLink"),
                    "status": data.get("status"),
                },
            }

        except Exception as e:
            logger.exception("google_calendar_create_event_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 10,
        query: str | None = None,
    ) -> dict[str, Any]:
        """List upcoming calendar events."""
        try:
            params: dict[str, Any] = {
                "maxResults": min(max_results, 100),
                "singleEvents": True,
                "orderBy": "startTime",
            }

            # Default to events from now onwards
            if time_min:
                params["timeMin"] = time_min
            else:
                params["timeMin"] = datetime.now(UTC).isoformat()

            if time_max:
                params["timeMax"] = time_max
            else:
                # Default to 30 days ahead if not specified
                params["timeMax"] = (datetime.now(UTC) + timedelta(days=30)).isoformat()

            if query:
                params["q"] = query

            response = await self.client.get(f"/calendars/{calendar_id}/events", params=params)

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                if await self._refresh_token_if_needed(response):
                    response = await self.client.get(
                        f"/calendars/{calendar_id}/events", params=params
                    )

            if response.status_code != HTTPStatus.OK:
                return {
                    "success": False,
                    "error": f"Failed to list events: {response.text}",
                }

            data = response.json()
            events = []
            for event in data.get("items", []):
                events.append(
                    {
                        "id": event["id"],
                        "summary": event.get("summary", "(No title)"),
                        "start": event.get("start", {}).get("dateTime")
                        or event.get("start", {}).get("date"),
                        "end": event.get("end", {}).get("dateTime")
                        or event.get("end", {}).get("date"),
                        "status": event.get("status"),
                        "location": event.get("location"),
                        "description": event.get("description"),
                        "html_link": event.get("htmlLink"),
                        "attendees": [
                            {"email": a.get("email"), "status": a.get("responseStatus")}
                            for a in event.get("attendees", [])
                        ],
                    }
                )

            return {
                "success": True,
                "events": events,
                "total": len(events),
            }

        except Exception as e:
            logger.exception("google_calendar_list_events_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def cancel_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_updates: str = "all",
    ) -> dict[str, Any]:
        """Cancel/delete a calendar event."""
        try:
            response = await self.client.delete(
                f"/calendars/{calendar_id}/events/{event_id}",
                params={"sendUpdates": send_updates},
            )

            if response.status_code == HTTPStatus.UNAUTHORIZED:
                if await self._refresh_token_if_needed(response):
                    response = await self.client.delete(
                        f"/calendars/{calendar_id}/events/{event_id}",
                        params={"sendUpdates": send_updates},
                    )

            if response.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
                return {
                    "success": False,
                    "error": f"Failed to cancel event: {response.text}",
                }

            return {
                "success": True,
                "message": f"Event {event_id} has been canceled",
                "notifications_sent": send_updates != "none",
            }

        except Exception as e:
            logger.exception("google_calendar_cancel_event_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a Google Calendar tool by name."""
        tool_map: dict[str, ToolHandler] = {
            "google_calendar_list_calendars": self.list_calendars,
            "google_calendar_check_availability": self.check_availability,
            "google_calendar_create_event": self.create_event,
            "google_calendar_list_events": self.list_events,
            "google_calendar_cancel_event": self.cancel_event,
        }

        handler = tool_map.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        result: dict[str, Any] = await handler(**arguments)
        return result
