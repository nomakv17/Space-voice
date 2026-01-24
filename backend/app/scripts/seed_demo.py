"""Seed demo workspace with sample HVAC data.

This script creates a demo workspace with sample contacts, appointments,
and links existing agents for demonstration purposes.

It also creates a demo user account (demo@spacevoice.ai) for customer demos.
This user is NOT a superuser, so admin-only pages (Pricing, Clients) are hidden.

Usage:
    cd backend
    uv run python -m app.scripts.seed_demo
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.user import User
from app.models.workspace import AgentWorkspace, Workspace

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo user credentials
DEMO_USER_EMAIL = "demo@spacevoice.ai"
DEMO_USER_PASSWORD = "demo2024!"  # Change this in production
DEMO_USER_NAME = "Demo User"

# Sample HVAC contacts data
SAMPLE_CONTACTS: list[dict[str, Any]] = [
    {
        "first_name": "John",
        "last_name": "Mitchell",
        "phone_number": "+15551234001",
        "email": "john.mitchell@example.com",
        "company_name": None,
        "status": "qualified",
        "tags": "hvac,furnace,priority",
        "notes": "Furnace making loud noise. Prefers morning appointments.",
    },
    {
        "first_name": "Sarah",
        "last_name": "Johnson",
        "phone_number": "+15551234002",
        "email": "sarah.j@example.com",
        "company_name": None,
        "status": "new",
        "tags": "hvac,ac,summer",
        "notes": "AC not cooling. New customer from Google Ads.",
    },
    {
        "first_name": "Robert",
        "last_name": "Williams",
        "phone_number": "+15551234003",
        "email": "rwilliams@example.com",
        "company_name": "Williams Property Management",
        "status": "contacted",
        "tags": "hvac,commercial,maintenance",
        "notes": "Manages 12 units. Interested in maintenance contract.",
    },
    {
        "first_name": "Emily",
        "last_name": "Davis",
        "phone_number": "+15551234004",
        "email": "emily.davis@example.com",
        "company_name": None,
        "status": "converted",
        "tags": "hvac,installation,referral",
        "notes": "New system installed. Happy customer - referred by neighbor.",
    },
    {
        "first_name": "Michael",
        "last_name": "Brown",
        "phone_number": "+15551234005",
        "email": "mbrown@example.com",
        "company_name": None,
        "status": "new",
        "tags": "hvac,emergency,gas",
        "notes": "Called about gas smell. URGENT - dispatched immediately.",
    },
    {
        "first_name": "Jennifer",
        "last_name": "Garcia",
        "phone_number": "+15551234006",
        "email": "jen.garcia@example.com",
        "company_name": None,
        "status": "qualified",
        "tags": "hvac,heat-pump,upgrade",
        "notes": "Interested in upgrading to heat pump. Got quote.",
    },
    {
        "first_name": "David",
        "last_name": "Martinez",
        "phone_number": "+15551234007",
        "email": "david.m@example.com",
        "company_name": "Martinez Restaurant",
        "status": "contacted",
        "tags": "hvac,commercial,kitchen",
        "notes": "Restaurant HVAC. Needs hood ventilation service.",
    },
    {
        "first_name": "Lisa",
        "last_name": "Anderson",
        "phone_number": "+15551234008",
        "email": "lisa.anderson@example.com",
        "company_name": None,
        "status": "new",
        "tags": "hvac,filter,maintenance",
        "notes": "Wants to schedule regular filter changes.",
    },
]

# Sample appointments (scheduled for next few days)
SAMPLE_APPOINTMENTS: list[dict[str, Any]] = [
    {
        "contact_index": 0,  # John Mitchell
        "days_from_now": 1,
        "hour": 9,
        "duration_minutes": 60,
        "service_type": "Furnace Repair",
        "status": "scheduled",
        "notes": "Furnace making loud noise - inspect blower motor",
    },
    {
        "contact_index": 3,  # Emily Davis
        "days_from_now": 0,
        "hour": 14,
        "duration_minutes": 30,
        "service_type": "Follow-up Check",
        "status": "scheduled",
        "notes": "30-day follow-up after new system installation",
    },
    {
        "contact_index": 5,  # Jennifer Garcia
        "days_from_now": 2,
        "hour": 10,
        "duration_minutes": 90,
        "service_type": "Heat Pump Consultation",
        "status": "scheduled",
        "notes": "On-site assessment for heat pump upgrade",
    },
    {
        "contact_index": 2,  # Robert Williams
        "days_from_now": 3,
        "hour": 8,
        "duration_minutes": 240,
        "service_type": "Commercial Maintenance",
        "status": "scheduled",
        "notes": "Quarterly maintenance - 12 units",
    },
    {
        "contact_index": 1,  # Sarah Johnson
        "days_from_now": -1,
        "hour": 11,
        "duration_minutes": 60,
        "service_type": "AC Repair",
        "status": "completed",
        "notes": "Replaced capacitor. AC working.",
    },
]


async def create_demo_user() -> User | None:
    """Create or get the demo user account.

    Returns:
        The demo user, or None if creation failed.
    """
    async with AsyncSessionLocal() as db:
        # Check if demo user already exists
        result = await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Demo user already exists: {existing_user.email} (ID: {existing_user.id})")
            return existing_user

        # Create demo user (NOT a superuser - can't see admin pages)
        demo_user = User(
            email=DEMO_USER_EMAIL,
            hashed_password=pwd_context.hash(DEMO_USER_PASSWORD),
            full_name=DEMO_USER_NAME,
            is_superuser=False,  # Important: NOT admin - hides Pricing & Clients pages
            is_active=True,
            onboarding_completed=True,
            onboarding_step=5,
            company_name="Demo HVAC Company",
            industry="HVAC",
        )
        db.add(demo_user)
        await db.commit()
        await db.refresh(demo_user)

        print(f"Created demo user: {demo_user.email} (ID: {demo_user.id})")
        print(f"  Password: {DEMO_USER_PASSWORD}")
        print(f"  is_superuser: {demo_user.is_superuser} (admin pages hidden)")

        return demo_user


async def seed_demo_workspace(user_id: int | None = None) -> dict[str, Any]:
    """Seed demo workspace with sample data.

    Args:
        user_id: Optional user ID to create demo for. If None, creates/uses demo user.

    Returns:
        Dict with created workspace and counts
    """
    async with AsyncSessionLocal() as db:
        # Get user - prefer demo user if no specific ID given
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        else:
            # Try to get or create demo user
            result = await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
            user = result.scalar_one_or_none()

            if not user:
                # Create demo user first
                demo_user = await create_demo_user()
                if demo_user:
                    # Re-fetch in current session
                    result = await db.execute(
                        select(User).where(User.email == DEMO_USER_EMAIL)
                    )
                    user = result.scalar_one_or_none()

        if not user:
            return {"error": "No users found. Please create a user first."}

        print(f"Creating demo workspace for user: {user.email} (ID: {user.id})")

        # Check if demo workspace already exists
        result = await db.execute(
            select(Workspace).where(
                Workspace.user_id == user.id, Workspace.name == "Demo HVAC Business"
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Demo workspace already exists: {existing.id}")
            return {
                "workspace_id": str(existing.id),
                "message": "Demo workspace already exists",
                "existing": True,
            }

        # Create demo workspace
        workspace = Workspace(
            id=uuid.uuid4(),
            user_id=user.id,
            name="Demo HVAC Business",
            description="Sample HVAC service company for demonstration. "
            "Includes sample contacts, appointments, and call scenarios.",
            is_default=False,
            settings={
                "timezone": "America/New_York",
                "business_hours": {
                    "monday": {"start": "08:00", "end": "18:00"},
                    "tuesday": {"start": "08:00", "end": "18:00"},
                    "wednesday": {"start": "08:00", "end": "18:00"},
                    "thursday": {"start": "08:00", "end": "18:00"},
                    "friday": {"start": "08:00", "end": "17:00"},
                    "saturday": {"start": "09:00", "end": "14:00"},
                    "sunday": None,
                },
                "booking_buffer_minutes": 30,
                "max_advance_booking_days": 30,
                "default_appointment_duration": 60,
                "allow_same_day_booking": True,
            },
        )
        db.add(workspace)
        await db.flush()
        print(f"Created workspace: {workspace.id}")

        # Create contacts
        contacts: list[Contact] = []
        for contact_data in SAMPLE_CONTACTS:
            contact = Contact(
                user_id=user.id,
                workspace_id=workspace.id,
                **contact_data,
            )
            db.add(contact)
            contacts.append(contact)
        await db.flush()
        print(f"Created {len(contacts)} contacts")

        # Create appointments
        appointments_created = 0
        now = datetime.now(UTC)
        for appt_data in SAMPLE_APPOINTMENTS:
            contact_index = int(appt_data["contact_index"])
            hour = int(appt_data["hour"])
            days_from_now = int(appt_data["days_from_now"])
            contact = contacts[contact_index]
            scheduled_at = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            scheduled_at += timedelta(days=days_from_now)

            appointment = Appointment(
                contact_id=contact.id,
                workspace_id=workspace.id,
                scheduled_at=scheduled_at,
                duration_minutes=appt_data["duration_minutes"],
                service_type=appt_data["service_type"],
                status=appt_data["status"],
                notes=appt_data["notes"],
                created_by_agent="Demo Seeder",
            )
            db.add(appointment)
            appointments_created += 1
        await db.flush()
        print(f"Created {appointments_created} appointments")

        # Link existing agents to demo workspace
        result = await db.execute(select(Agent).where(Agent.user_id == user.id))
        agents = result.scalars().all()

        agents_linked = 0
        for agent in agents:
            # Check if already linked
            result = await db.execute(
                select(AgentWorkspace).where(
                    AgentWorkspace.agent_id == agent.id,
                    AgentWorkspace.workspace_id == workspace.id,
                )
            )
            if not result.scalar_one_or_none():
                agent_workspace = AgentWorkspace(
                    agent_id=agent.id,
                    workspace_id=workspace.id,
                    is_default=False,
                )
                db.add(agent_workspace)
                agents_linked += 1

        await db.commit()
        print(f"Linked {agents_linked} agents to demo workspace")

        return {
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "contacts_created": len(contacts),
            "appointments_created": appointments_created,
            "agents_linked": agents_linked,
            "user_email": user.email,
        }


async def main() -> None:
    """Run the demo seeder."""
    print("=" * 50)
    print("SpaceVoice Demo Workspace Seeder")
    print("=" * 50)
    print()

    # Create or get demo user first
    _ = await create_demo_user()

    # Seed demo workspace
    result = await seed_demo_workspace()

    print()
    print("=" * 50)
    print("Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print()
    print("-" * 50)
    print("DEMO CREDENTIALS (for customer demos):")
    print("  URL:      https://dashboard.spacevoice.ai/login")
    print(f"  Email:    {DEMO_USER_EMAIL}")
    print(f"  Password: {DEMO_USER_PASSWORD}")
    print()
    print("NOTE: This account CANNOT see admin pages (Pricing, Clients)")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
