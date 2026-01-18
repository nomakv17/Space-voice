"""Jobber CRM integration tools for HVAC voice agents.

Jobber is a popular field service management software used by HVAC,
plumbing, electrical, and other home service businesses.

Provides tools for:
- Searching and managing clients
- Creating and managing jobs (work orders)
- Creating quotes/estimates
- Scheduling service visits
"""

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class JobberTools:
    """Jobber API integration tools for HVAC field service management.

    Uses Jobber's GraphQL API for:
    - Client management
    - Job/work order creation
    - Quote generation
    - Service scheduling
    """

    BASE_URL = "https://api.getjobber.com/api/graphql"

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Initialize Jobber tools.

        Args:
            access_token: Jobber OAuth 2.0 access token
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
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-JOBBER-GRAPHQL-VERSION": "2024-06-21",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _execute_graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL query against Jobber API."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.client.post(self.BASE_URL, json=payload)

        if response.status_code != HTTPStatus.OK:
            return {
                "success": False,
                "error": f"Jobber API error ({response.status_code}): {response.text}",
            }

        data = response.json()

        if "errors" in data:
            error_messages = [e.get("message", "Unknown error") for e in data["errors"]]
            return {
                "success": False,
                "error": f"GraphQL errors: {'; '.join(error_messages)}",
            }

        return {"success": True, "data": data.get("data", {})}

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        """Get OpenAI function calling tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "jobber_search_clients",
                    "description": "Search for clients/customers in Jobber by name, phone, or email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Search term (name, phone, or email)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default 10)",
                            },
                        },
                        "required": ["search_term"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_create_client",
                    "description": "Create a new client/customer in Jobber",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "first_name": {
                                "type": "string",
                                "description": "Client's first name",
                            },
                            "last_name": {
                                "type": "string",
                                "description": "Client's last name",
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number",
                            },
                            "email": {
                                "type": "string",
                                "description": "Email address",
                            },
                            "street_address": {
                                "type": "string",
                                "description": "Street address",
                            },
                            "city": {
                                "type": "string",
                                "description": "City",
                            },
                            "state": {
                                "type": "string",
                                "description": "State/Province",
                            },
                            "postal_code": {
                                "type": "string",
                                "description": "ZIP/Postal code",
                            },
                            "company_name": {
                                "type": "string",
                                "description": "Company name (for commercial clients)",
                            },
                        },
                        "required": ["first_name", "last_name", "phone"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_get_client",
                    "description": "Get detailed information about a specific client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "The Jobber client ID",
                            },
                        },
                        "required": ["client_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_create_job",
                    "description": "Create a new job/work order for a client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "The Jobber client ID",
                            },
                            "title": {
                                "type": "string",
                                "description": "Job title (e.g., 'HVAC Repair - No Heat')",
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed job description",
                            },
                            "job_type": {
                                "type": "string",
                                "enum": ["service", "maintenance", "installation", "inspection"],
                                "description": "Type of job",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                                "description": "Job priority level",
                            },
                        },
                        "required": ["client_id", "title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_list_jobs",
                    "description": "List jobs for a client or all recent jobs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "Filter by client ID (optional)",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["active", "completed", "cancelled", "all"],
                                "description": "Filter by job status",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default 10)",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_create_quote",
                    "description": "Create a quote/estimate for a client",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "The Jobber client ID",
                            },
                            "title": {
                                "type": "string",
                                "description": "Quote title",
                            },
                            "line_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "description": {"type": "string"},
                                        "quantity": {"type": "number"},
                                        "unit_price": {"type": "number"},
                                    },
                                },
                                "description": "Line items for the quote",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes for the quote",
                            },
                        },
                        "required": ["client_id", "title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "jobber_schedule_visit",
                    "description": "Schedule a service visit for a job",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "The Jobber job ID",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Visit start time (ISO 8601 format)",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Visit end time (ISO 8601 format)",
                            },
                            "assigned_to": {
                                "type": "string",
                                "description": "Team member/technician to assign (optional)",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Visit notes",
                            },
                        },
                        "required": ["job_id", "start_time", "end_time"],
                    },
                },
            },
        ]

    async def search_clients(
        self, search_term: str, limit: int = 10
    ) -> dict[str, Any]:
        """Search for clients by name, phone, or email."""
        query = """
        query SearchClients($searchTerm: String!, $first: Int) {
            clients(searchTerm: $searchTerm, first: $first) {
                nodes {
                    id
                    firstName
                    lastName
                    companyName
                    emails {
                        address
                        primary
                    }
                    phones {
                        number
                        primary
                    }
                    defaultAddress {
                        street
                        city
                        province
                        postalCode
                    }
                }
            }
        }
        """

        try:
            result = await self._execute_graphql(
                query, {"searchTerm": search_term, "first": min(limit, 50)}
            )

            if not result["success"]:
                return result

            clients_data = result["data"].get("clients", {}).get("nodes", [])
            clients = []
            for c in clients_data:
                primary_email = next(
                    (e["address"] for e in c.get("emails", []) if e.get("primary")),
                    c.get("emails", [{}])[0].get("address") if c.get("emails") else None,
                )
                primary_phone = next(
                    (p["number"] for p in c.get("phones", []) if p.get("primary")),
                    c.get("phones", [{}])[0].get("number") if c.get("phones") else None,
                )
                address = c.get("defaultAddress", {})

                clients.append(
                    {
                        "id": c["id"],
                        "first_name": c.get("firstName"),
                        "last_name": c.get("lastName"),
                        "company_name": c.get("companyName"),
                        "email": primary_email,
                        "phone": primary_phone,
                        "address": {
                            "street": address.get("street"),
                            "city": address.get("city"),
                            "state": address.get("province"),
                            "postal_code": address.get("postalCode"),
                        }
                        if address
                        else None,
                    }
                )

            return {
                "success": True,
                "clients": clients,
                "total": len(clients),
            }

        except Exception as e:
            logger.exception("jobber_search_clients_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def create_client(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str | None = None,
        street_address: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new client in Jobber."""
        mutation = """
        mutation CreateClient($input: ClientCreateInput!) {
            clientCreate(input: $input) {
                client {
                    id
                    firstName
                    lastName
                    companyName
                }
                userErrors {
                    message
                    path
                }
            }
        }
        """

        client_input: dict[str, Any] = {
            "firstName": first_name,
            "lastName": last_name,
            "phones": [{"number": phone, "primary": True}],
        }

        if email:
            client_input["emails"] = [{"address": email, "primary": True}]

        if company_name:
            client_input["companyName"] = company_name

        if street_address or city or state or postal_code:
            client_input["billingAddress"] = {
                "street": street_address or "",
                "city": city or "",
                "province": state or "",
                "postalCode": postal_code or "",
            }

        try:
            result = await self._execute_graphql(mutation, {"input": client_input})

            if not result["success"]:
                return result

            create_result = result["data"].get("clientCreate", {})
            user_errors = create_result.get("userErrors", [])

            if user_errors:
                error_messages = [e.get("message", "Unknown error") for e in user_errors]
                return {"success": False, "error": "; ".join(error_messages)}

            client = create_result.get("client", {})
            return {
                "success": True,
                "message": f"Client {first_name} {last_name} created successfully",
                "client": {
                    "id": client.get("id"),
                    "first_name": client.get("firstName"),
                    "last_name": client.get("lastName"),
                    "company_name": client.get("companyName"),
                },
            }

        except Exception as e:
            logger.exception("jobber_create_client_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def get_client(self, client_id: str) -> dict[str, Any]:
        """Get detailed information about a client."""
        query = """
        query GetClient($id: EncodedId!) {
            client(id: $id) {
                id
                firstName
                lastName
                companyName
                emails {
                    address
                    primary
                }
                phones {
                    number
                    primary
                }
                defaultAddress {
                    street
                    city
                    province
                    postalCode
                }
                balance
                tags {
                    label
                }
                createdAt
            }
        }
        """

        try:
            result = await self._execute_graphql(query, {"id": client_id})

            if not result["success"]:
                return result

            client = result["data"].get("client")
            if not client:
                return {"success": False, "error": "Client not found"}

            primary_email = next(
                (e["address"] for e in client.get("emails", []) if e.get("primary")),
                client.get("emails", [{}])[0].get("address") if client.get("emails") else None,
            )
            primary_phone = next(
                (p["number"] for p in client.get("phones", []) if p.get("primary")),
                client.get("phones", [{}])[0].get("number") if client.get("phones") else None,
            )
            address = client.get("defaultAddress", {})

            return {
                "success": True,
                "client": {
                    "id": client["id"],
                    "first_name": client.get("firstName"),
                    "last_name": client.get("lastName"),
                    "company_name": client.get("companyName"),
                    "email": primary_email,
                    "phone": primary_phone,
                    "address": {
                        "street": address.get("street"),
                        "city": address.get("city"),
                        "state": address.get("province"),
                        "postal_code": address.get("postalCode"),
                    }
                    if address
                    else None,
                    "balance": client.get("balance"),
                    "tags": [t.get("label") for t in client.get("tags", [])],
                    "created_at": client.get("createdAt"),
                },
            }

        except Exception as e:
            logger.exception("jobber_get_client_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def create_job(
        self,
        client_id: str,
        title: str,
        description: str | None = None,
        job_type: str = "service",
        priority: str = "medium",
    ) -> dict[str, Any]:
        """Create a new job/work order."""
        mutation = """
        mutation CreateJob($input: JobCreateInput!) {
            jobCreate(input: $input) {
                job {
                    id
                    title
                    jobNumber
                    jobStatus
                }
                userErrors {
                    message
                    path
                }
            }
        }
        """

        job_input: dict[str, Any] = {
            "clientId": client_id,
            "title": title,
        }

        if description:
            job_input["instructions"] = description

        try:
            result = await self._execute_graphql(mutation, {"input": job_input})

            if not result["success"]:
                return result

            create_result = result["data"].get("jobCreate", {})
            user_errors = create_result.get("userErrors", [])

            if user_errors:
                error_messages = [e.get("message", "Unknown error") for e in user_errors]
                return {"success": False, "error": "; ".join(error_messages)}

            job = create_result.get("job", {})
            return {
                "success": True,
                "message": f"Job '{title}' created successfully",
                "job": {
                    "id": job.get("id"),
                    "title": job.get("title"),
                    "job_number": job.get("jobNumber"),
                    "status": job.get("jobStatus"),
                },
            }

        except Exception as e:
            logger.exception("jobber_create_job_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def list_jobs(
        self,
        client_id: str | None = None,
        status: str = "all",
        limit: int = 10,
    ) -> dict[str, Any]:
        """List jobs, optionally filtered by client or status."""
        query = """
        query ListJobs($first: Int, $filter: JobFilterAttributes) {
            jobs(first: $first, filter: $filter) {
                nodes {
                    id
                    title
                    jobNumber
                    jobStatus
                    createdAt
                    client {
                        id
                        firstName
                        lastName
                    }
                    visits {
                        nodes {
                            id
                            startAt
                            endAt
                            status
                        }
                    }
                }
            }
        }
        """

        variables: dict[str, Any] = {"first": min(limit, 50)}

        filter_input: dict[str, Any] = {}
        if client_id:
            filter_input["clientId"] = client_id
        if status and status != "all":
            # Map status to Jobber's job status enum
            status_map = {
                "active": "ACTIVE",
                "completed": "COMPLETED",
                "cancelled": "CANCELLED",
            }
            if status in status_map:
                filter_input["jobStatus"] = status_map[status]

        if filter_input:
            variables["filter"] = filter_input

        try:
            result = await self._execute_graphql(query, variables)

            if not result["success"]:
                return result

            jobs_data = result["data"].get("jobs", {}).get("nodes", [])
            jobs = []
            for j in jobs_data:
                client = j.get("client", {})
                visits = j.get("visits", {}).get("nodes", [])
                next_visit = visits[0] if visits else None

                jobs.append(
                    {
                        "id": j["id"],
                        "title": j.get("title"),
                        "job_number": j.get("jobNumber"),
                        "status": j.get("jobStatus"),
                        "created_at": j.get("createdAt"),
                        "client": {
                            "id": client.get("id"),
                            "name": f"{client.get('firstName', '')} {client.get('lastName', '')}".strip(),
                        }
                        if client
                        else None,
                        "next_visit": {
                            "start": next_visit.get("startAt"),
                            "end": next_visit.get("endAt"),
                            "status": next_visit.get("status"),
                        }
                        if next_visit
                        else None,
                    }
                )

            return {
                "success": True,
                "jobs": jobs,
                "total": len(jobs),
            }

        except Exception as e:
            logger.exception("jobber_list_jobs_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def create_quote(
        self,
        client_id: str,
        title: str,
        line_items: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a quote/estimate for a client."""
        mutation = """
        mutation CreateQuote($input: QuoteCreateInput!) {
            quoteCreate(input: $input) {
                quote {
                    id
                    quoteNumber
                    quoteStatus
                    total
                }
                userErrors {
                    message
                    path
                }
            }
        }
        """

        quote_input: dict[str, Any] = {
            "clientId": client_id,
            "title": title,
        }

        if line_items:
            quote_input["lineItems"] = [
                {
                    "name": item.get("description", "Service"),
                    "quantity": item.get("quantity", 1),
                    "unitPrice": item.get("unit_price", 0),
                }
                for item in line_items
            ]

        if notes:
            quote_input["internalNotes"] = notes

        try:
            result = await self._execute_graphql(mutation, {"input": quote_input})

            if not result["success"]:
                return result

            create_result = result["data"].get("quoteCreate", {})
            user_errors = create_result.get("userErrors", [])

            if user_errors:
                error_messages = [e.get("message", "Unknown error") for e in user_errors]
                return {"success": False, "error": "; ".join(error_messages)}

            quote = create_result.get("quote", {})
            return {
                "success": True,
                "message": f"Quote '{title}' created successfully",
                "quote": {
                    "id": quote.get("id"),
                    "quote_number": quote.get("quoteNumber"),
                    "status": quote.get("quoteStatus"),
                    "total": quote.get("total"),
                },
            }

        except Exception as e:
            logger.exception("jobber_create_quote_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def schedule_visit(
        self,
        job_id: str,
        start_time: str,
        end_time: str,
        assigned_to: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Schedule a service visit for a job."""
        mutation = """
        mutation CreateVisit($input: VisitCreateInput!) {
            visitCreate(input: $input) {
                visit {
                    id
                    startAt
                    endAt
                    status
                }
                userErrors {
                    message
                    path
                }
            }
        }
        """

        visit_input: dict[str, Any] = {
            "jobId": job_id,
            "startAt": start_time,
            "endAt": end_time,
        }

        if assigned_to:
            visit_input["assignedUserIds"] = [assigned_to]

        if notes:
            visit_input["instructions"] = notes

        try:
            result = await self._execute_graphql(mutation, {"input": visit_input})

            if not result["success"]:
                return result

            create_result = result["data"].get("visitCreate", {})
            user_errors = create_result.get("userErrors", [])

            if user_errors:
                error_messages = [e.get("message", "Unknown error") for e in user_errors]
                return {"success": False, "error": "; ".join(error_messages)}

            visit = create_result.get("visit", {})
            return {
                "success": True,
                "message": "Visit scheduled successfully",
                "visit": {
                    "id": visit.get("id"),
                    "start_time": visit.get("startAt"),
                    "end_time": visit.get("endAt"),
                    "status": visit.get("status"),
                },
            }

        except Exception as e:
            logger.exception("jobber_schedule_visit_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a Jobber tool by name."""
        tool_map: dict[str, ToolHandler] = {
            "jobber_search_clients": self.search_clients,
            "jobber_create_client": self.create_client,
            "jobber_get_client": self.get_client,
            "jobber_create_job": self.create_job,
            "jobber_list_jobs": self.list_jobs,
            "jobber_create_quote": self.create_quote,
            "jobber_schedule_visit": self.schedule_visit,
        }

        handler = tool_map.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        result: dict[str, Any] = await handler(**arguments)
        return result
