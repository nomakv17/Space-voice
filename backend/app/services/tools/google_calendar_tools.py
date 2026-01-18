"""Google Calendar integration tools for voice agents.

Provides tools for:
- Listing calendars
- Checking availability (free/busy)
- Creating calendar events (booking appointments)
- Listing upcoming events
- Canceling events
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
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

        if not self.refresh_token or not self.client_id or not self.client_secret:
            return False

        try:
            async with httpx.AsyncClient() as refresh_client:
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

                    logger.info("google_calendar_token_refreshed")
                    return True

        except Exception as e:
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
                    "description": "Check available time slots by querying free/busy information. Use this to find when the user is available for appointments.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (use 'primary' for main calendar)",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start of availability window (ISO 8601 format, e.g., 2024-01-15T09:00:00-05:00)",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End of availability window (ISO 8601 format)",
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
    ) -> dict[str, Any]:
        """Check free/busy information for a calendar.

        Returns busy periods within the specified time range.
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

            # Calculate available slots (gaps between busy periods)
            # For simplicity, return busy periods and let the AI figure out availability
            busy_times = []
            for period in busy_periods:
                busy_times.append(
                    {
                        "start": period["start"],
                        "end": period["end"],
                    }
                )

            return {
                "success": True,
                "calendar_id": calendar_id,
                "time_range": {"start": start_time, "end": end_time},
                "busy_periods": busy_times,
                "busy_count": len(busy_times),
                "message": f"Found {len(busy_times)} busy periods. Times NOT in busy periods are available.",
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
                params["timeMin"] = datetime.now(timezone.utc).isoformat()

            if time_max:
                params["timeMax"] = time_max
            else:
                # Default to 30 days ahead if not specified
                params["timeMax"] = (
                    datetime.now(timezone.utc) + timedelta(days=30)
                ).isoformat()

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
