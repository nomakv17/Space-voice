"""Service for seeding realistic demo data with revenue calculations.

Note: Uses standard random for demo data generation (not cryptographic).
"""
# ruff: noqa: S311

import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_password_hash
from app.models.agent import Agent
from app.models.appointment import Appointment
from app.models.call_record import CallDirection, CallRecord, CallStatus
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber, PhoneNumberStatus, TelephonyProvider
from app.models.pricing_config import PricingConfig
from app.models.user import User
from app.models.workspace import AgentWorkspace, Workspace

logger = structlog.get_logger()

# Pricing tier distribution for seeded users (slightly randomized for realism)
# Will be randomized at runtime to avoid round numbers
TIER_DISTRIBUTION_BASE = [
    ("premium", 9, 12),        # 9-12 premium users
    ("premium-mini", 13, 17),  # 13-17 premium-mini users
    ("balanced", 14, 18),      # 14-18 balanced users
    ("budget", 8, 12),         # 8-12 budget users
]

# Call parameters for each tier (calls_per_user, avg_duration_min, demo_price_per_min)
# Demo prices set to generate ~$400K total across 6 months
TIER_CALL_PARAMS = {
    "premium": (200, 8, Decimal("3.00")),      # Enterprise: high volume, longer calls
    "premium-mini": (150, 6, Decimal("2.00")), # Business: medium-high volume
    "balanced": (120, 5, Decimal("1.50")),     # Standard: medium volume
    "budget": (80, 4, Decimal("1.00")),        # Starter: lower volume
}

# Phone number prefixes for realistic data
AREA_CODES = ["212", "310", "415", "305", "312", "702", "602", "206", "617", "404"]

# Realistic company/business names
BUSINESS_TYPES = [
    "HVAC Services", "Plumbing Co", "Electric Solutions", "Roofing Pros",
    "Landscaping", "Pest Control", "Cleaning Services", "Auto Repair",
    "Dental Office", "Law Firm", "Real Estate", "Insurance Agency",
    "Medical Clinic", "Veterinary", "Restaurant", "Salon & Spa",
]

# First names for contacts
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
]

# Last names for contacts
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
]

# Service types for appointments
SERVICE_TYPES = [
    "Initial Consultation", "Follow-up Visit", "Estimate Request", "Service Call",
    "Repair Appointment", "Maintenance Check", "Emergency Service", "Installation",
]


def generate_phone() -> str:
    """Generate a realistic phone number."""
    area = random.choice(AREA_CODES)
    return f"+1{area}{random.randint(1000000, 9999999)}"


def generate_email(first_name: str, last_name: str, company_domain: str | None = None) -> str:
    """Generate a realistic email address with optional company domain."""
    if company_domain:
        # Business email format
        return f"{first_name.lower()}.{last_name.lower()[0]}@{company_domain}"
    # Personal email with varied formats
    personal_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
    formats = [
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}",
        f"{first_name.lower()}{last_name.lower()[0]}{random.randint(10, 99)}",
        f"{first_name.lower()}_{last_name.lower()}",
        f"{first_name.lower()[0]}{last_name.lower()}{random.randint(1, 99)}",
    ]
    return f"{random.choice(formats)}@{random.choice(personal_domains)}"


# Company domain mapping for realistic business emails
BUSINESS_DOMAINS = {
    "HVAC Services": "hvacpro.com",
    "Plumbing Co": "plumbingco.com",
    "Electric Solutions": "electricsolutions.com",
    "Roofing Pros": "roofingpros.com",
    "Landscaping": "greenscapellc.com",
    "Pest Control": "bugbusters.com",
    "Cleaning Services": "sparkclean.com",
    "Auto Repair": "autofix.com",
    "Dental Office": "brightsmile.dental",
    "Law Firm": "legalpros.law",
    "Real Estate": "homefinders.realty",
    "Insurance Agency": "shieldins.com",
    "Medical Clinic": "carewellclinic.com",
    "Veterinary": "petcare.vet",
    "Restaurant": "tastybites.food",
    "Salon & Spa": "beautyspot.salon",
}


def generate_call_duration(avg_minutes: int) -> int:
    """Generate realistic call duration with variance."""
    min_dur = 30  # 30 seconds minimum
    max_dur = avg_minutes * 60 * 2.5  # Max ~2.5x average
    mode = avg_minutes * 60  # Peak at average
    return max(int(random.triangular(min_dur, max_dur, mode)), 30)


async def ensure_pricing_tiers(db: AsyncSession) -> dict[str, PricingConfig]:
    """Ensure pricing tiers exist, create if missing."""
    result = await db.execute(select(PricingConfig))
    existing = {p.tier_id: p for p in result.scalars().all()}

    default_tiers = {
        "premium": {
            "tier_name": "Premium",
            "base_llm": Decimal("0.024"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
        "premium-mini": {
            "tier_name": "Premium Mini",
            "base_llm": Decimal("0.011"),
            "base_stt": Decimal("0.002"),
            "base_tts": Decimal("0.002"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("300"),
            "tel_markup": Decimal("25"),
        },
        "balanced": {
            "tier_name": "Balanced",
            "base_llm": Decimal("0.014"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
        "budget": {
            "tier_name": "Budget",
            "base_llm": Decimal("0.007"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
    }

    for tier_id, config in default_tiers.items():
        if tier_id not in existing:
            pricing = PricingConfig(
                tier_id=tier_id,
                tier_name=config["tier_name"],
                base_llm_cost_per_minute=config["base_llm"],
                base_stt_cost_per_minute=config["base_stt"],
                base_tts_cost_per_minute=config["base_tts"],
                base_telephony_cost_per_minute=config["base_tel"],
                ai_markup_percentage=config["ai_markup"],
                telephony_markup_percentage=config["tel_markup"],
                final_ai_price_per_minute=Decimal("0"),
                final_telephony_price_per_minute=Decimal("0"),
                final_total_price_per_minute=Decimal("0"),
            )
            pricing.recalculate_prices()
            db.add(pricing)
            existing[tier_id] = pricing

    await db.flush()
    return existing


async def seed_calls(db: AsyncSession) -> dict[str, int | Decimal]:
    """Seed realistic demo data with revenue across 6 months.

    Creates for each of 50 users:
    - 1 workspace
    - 1-2 agents
    - 5-15 contacts
    - 3-8 appointments
    - Multiple calls (scaled by tier and month)

    Revenue grows month-over-month: ~$37K (Aug) → ~$95K (Jan) = ~$400K total
    """
    # Check if already seeded
    result = await db.execute(
        select(func.count(User.id)).where(User.email.like("%@seeded.spacevoice.ai"))
    )
    existing_seeded = result.scalar() or 0

    if existing_seeded > 0:
        logger.info("Data already seeded", existing_users=existing_seeded)
        return {"seeded": False, "message": "Data already exists"}

    # Ensure pricing tiers exist
    pricing_tiers = await ensure_pricing_tiers(db)

    # Generate 6 months of dates
    now = datetime.now(UTC)
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from dateutil.relativedelta import relativedelta
    months = []
    for i in range(6):
        month_date = current_month - relativedelta(months=(5 - i))
        growth_multiplier = 0.4 + (i * 0.12)  # 0.4 → 1.0
        months.append((month_date, growth_multiplier))

    # Counters
    users_created = 0
    workspaces_created = 0
    agents_created = 0
    contacts_created = 0
    appointments_created = 0
    calls_created = 0
    phone_numbers_created = 0
    total_revenue = Decimal("0")
    total_cost = Decimal("0")

    user_index = 0

    # Randomize tier distribution for realistic counts (not round numbers)
    tier_distribution = [
        (tier_id, random.randint(min_users, max_users))
        for tier_id, min_users, max_users in TIER_DISTRIBUTION_BASE
    ]

    for tier_id, user_count in tier_distribution:
        pricing = pricing_tiers.get(tier_id)
        if not pricing:
            continue

        calls_per_user, avg_duration, demo_price = TIER_CALL_PARAMS.get(
            tier_id, (80, 4, Decimal("1.00"))
        )

        for _ in range(user_count):
            user_index += 1

            # User creation date spread across 6 months
            user_month_idx = user_index % 6
            user_created_date = months[user_month_idx][0].replace(
                day=random.randint(1, 28),
                hour=random.randint(9, 17),
                minute=random.randint(0, 59),
            )

            business_type = random.choice(BUSINESS_TYPES)

            # Create user
            user = User(
                email=f"user{user_index:03d}@seeded.spacevoice.ai",
                hashed_password=get_password_hash(secrets.token_urlsafe(16)),
                full_name=f"Seeded User {user_index}",
                company_name=f"{business_type} #{user_index}",
                is_active=True,
                is_superuser=False,
                onboarding_completed=True,
                created_at=user_created_date,
            )
            db.add(user)
            await db.flush()
            users_created += 1

            # Create workspace for this user
            workspace = Workspace(
                id=uuid.uuid4(),
                user_id=user.id,
                name=f"{business_type} Workspace",
                description=f"Main workspace for {business_type}",
                is_default=True,
                settings={
                    "timezone": random.choice([
                        "America/New_York", "America/Chicago",
                        "America/Denver", "America/Los_Angeles"
                    ]),
                    "business_hours": {
                        "monday": {"start": "09:00", "end": "17:00"},
                        "tuesday": {"start": "09:00", "end": "17:00"},
                        "wednesday": {"start": "09:00", "end": "17:00"},
                        "thursday": {"start": "09:00", "end": "17:00"},
                        "friday": {"start": "09:00", "end": "17:00"},
                    },
                },
            )
            workspace.created_at = user_created_date  # type: ignore[assignment]
            db.add(workspace)
            await db.flush()
            workspaces_created += 1

            # Create 1-2 agents for this user and link to workspace
            num_agents = random.randint(1, 2)
            user_agents = []
            agent_call_counts: dict[uuid.UUID, tuple[int, int]] = {}  # agent_id -> (calls, duration)

            for agent_num in range(num_agents):
                agent_name = f"{business_type} Assistant" if agent_num == 0 else f"{business_type} Support"
                agent = Agent(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    name=agent_name,
                    description=f"Voice agent for {business_type}",
                    pricing_tier=tier_id,
                    voice_provider="openai_realtime",
                    system_prompt=f"You are a helpful assistant for {business_type}. Help customers with inquiries, scheduling, and general questions.",
                    language="en-US",
                    voice=random.choice(["alloy", "shimmer", "echo", "nova"]),
                    is_active=True,
                    enable_recording=True,
                    enable_transcript=True,
                )
                agent.created_at = user_created_date + timedelta(days=random.randint(0, 7))  # type: ignore[assignment]
                db.add(agent)
                await db.flush()
                user_agents.append(agent)
                agent_call_counts[agent.id] = (0, 0)
                agents_created += 1

                # Link agent to workspace via AgentWorkspace junction table
                agent_workspace = AgentWorkspace(
                    id=uuid.uuid4(),
                    agent_id=agent.id,
                    workspace_id=workspace.id,
                    is_default=(agent_num == 0),  # First agent is default for this workspace
                )
                db.add(agent_workspace)
                await db.flush()

            # Create 1-2 phone numbers per user (some users may have none)
            if random.random() < 0.7:  # 70% of users have phone numbers
                num_phones = random.randint(1, 2)
                for phone_idx in range(num_phones):
                    phone_num = generate_phone()
                    provider = random.choice([TelephonyProvider.TELNYX.value, TelephonyProvider.TWILIO.value])

                    # Assign to first agent if available
                    assigned_agent = user_agents[0] if user_agents and phone_idx == 0 else None

                    phone = PhoneNumber(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        workspace_id=workspace.id,
                        phone_number=phone_num,
                        friendly_name=f"{business_type} Line {phone_idx + 1}",
                        provider=provider,
                        provider_id=f"{provider}_{secrets.token_hex(12)}",
                        can_receive_calls=True,
                        can_make_calls=True,
                        can_receive_sms=random.choice([True, False]),
                        can_send_sms=random.choice([True, False]),
                        status=PhoneNumberStatus.ACTIVE.value,
                        assigned_agent_id=assigned_agent.id if assigned_agent else None,
                        purchased_at=user_created_date + timedelta(days=random.randint(0, 14)),
                    )
                    phone.created_at = user_created_date + timedelta(days=random.randint(0, 7))  # type: ignore[assignment]
                    db.add(phone)
                    phone_numbers_created += 1

                await db.flush()

            # Create 5-15 contacts for this workspace with realistic emails
            num_contacts = random.randint(5, 15)
            user_contacts = []
            contact_statuses = ["new", "contacted", "qualified", "converted", "lost"]
            company_domain = BUSINESS_DOMAINS.get(business_type, "company.com")

            for _ in range(num_contacts):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)

                # Contact created sometime in the 6-month window
                contact_month_idx = random.randint(0, 5)
                contact_created = months[contact_month_idx][0].replace(
                    day=random.randint(1, 28),
                    hour=random.randint(9, 17),
                )

                # Use business email for ~30% of contacts, personal for the rest
                use_company_email = random.random() < 0.3
                email = generate_email(
                    first_name, last_name,
                    company_domain if use_company_email else None
                )

                # Realistic company names
                company_options = [
                    None,
                    f"{last_name} {random.choice(['Enterprises', 'LLC', 'Inc', 'Co'])}",
                    f"{first_name}'s {random.choice(['Shop', 'Business', 'Services'])}",
                    random.choice(["Martinez Restaurant", "Johnson Construction", "Smith & Associates",
                                   "Brown Consulting", "Davis Holdings", "Wilson Group"]),
                ]

                contact = Contact(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone_number=generate_phone(),
                    company_name=random.choice(company_options),
                    status=random.choice(contact_statuses),
                    tags=random.choice([None, "lead", "customer", "vip", "hvac", "emergency", "commercial,kitchen"]),
                )
                contact.created_at = contact_created  # type: ignore[assignment]
                db.add(contact)
                await db.flush()
                user_contacts.append(contact)
                contacts_created += 1

            # Create 3-8 appointments for some contacts
            # Past appointments should be completed/cancelled, future ones scheduled
            num_appointments = random.randint(3, 8)

            for _ in range(num_appointments):
                contact = random.choice(user_contacts)
                agent = random.choice(user_agents)

                # Appointment scheduled in the 6-month window
                appt_month_idx = random.randint(0, 5)
                appt_date = months[appt_month_idx][0].replace(
                    day=random.randint(1, 28),
                    hour=random.randint(9, 16),
                    minute=random.choice([0, 15, 30, 45]),
                )

                # Determine status based on whether appointment is in the past
                is_past = appt_date < now
                if is_past:
                    # Past appointments: mostly completed, some cancelled/no_show
                    status = random.choices(
                        ["completed", "cancelled", "no_show"],
                        weights=[70, 20, 10]
                    )[0]
                else:
                    # Future appointments: mostly scheduled, few cancelled
                    status = random.choices(
                        ["scheduled", "cancelled"],
                        weights=[85, 15]
                    )[0]

                appointment = Appointment(
                    contact_id=contact.id,
                    workspace_id=workspace.id,
                    agent_id=agent.id,
                    scheduled_at=appt_date,
                    duration_minutes=random.choice([15, 30, 45, 60, 90, 120, 240]),
                    status=status,
                    service_type=random.choice(SERVICE_TYPES),
                    created_by_agent=agent.name,
                )
                appointment.created_at = appt_date - timedelta(days=random.randint(1, 7))  # type: ignore[assignment]
                db.add(appointment)
                appointments_created += 1

            # Generate calls for this user across all 6 months
            for month_start, growth_mult in months:
                month_calls = int((calls_per_user + random.randint(-20, 20)) * growth_mult)
                is_current_month = month_start.month == now.month and month_start.year == now.year
                max_day = min(28, now.day) if is_current_month else 28

                for _ in range(month_calls):
                    call_time = month_start.replace(
                        day=random.randint(1, max_day),
                        hour=random.randint(8, 20),
                        minute=random.randint(0, 59),
                    )

                    duration_secs = generate_call_duration(avg_duration)
                    duration_mins = Decimal(str(duration_secs)) / 60

                    revenue = (duration_mins * demo_price).quantize(Decimal("0.0001"))
                    cost = (revenue * Decimal("0.40")).quantize(Decimal("0.0001"))

                    # Call status distribution
                    status_roll = random.random()
                    if status_roll < 0.85:
                        status = CallStatus.COMPLETED.value
                    elif status_roll < 0.92:
                        status = CallStatus.NO_ANSWER.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")
                    elif status_roll < 0.97:
                        status = CallStatus.BUSY.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")
                    else:
                        status = CallStatus.FAILED.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")

                    direction = (
                        CallDirection.INBOUND.value
                        if random.random() < 0.7
                        else CallDirection.OUTBOUND.value
                    )

                    # Link call to agent and optionally contact
                    agent = random.choice(user_agents)
                    contact = random.choice(user_contacts) if random.random() < 0.6 else None

                    # Track calls per agent for updating total_calls later
                    prev_calls, prev_dur = agent_call_counts.get(agent.id, (0, 0))
                    if status == CallStatus.COMPLETED.value:
                        agent_call_counts[agent.id] = (prev_calls + 1, prev_dur + duration_secs)
                    else:
                        agent_call_counts[agent.id] = (prev_calls + 1, prev_dur)

                    call = CallRecord(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        provider=random.choice(["telnyx", "twilio"]),
                        provider_call_id=f"call_{secrets.token_hex(16)}",
                        agent_id=agent.id,
                        contact_id=contact.id if contact else None,
                        workspace_id=workspace.id,
                        direction=direction,
                        status=status,
                        from_number=contact.phone_number if contact and direction == CallDirection.INBOUND.value else generate_phone(),
                        to_number=contact.phone_number if contact and direction == CallDirection.OUTBOUND.value else generate_phone(),
                        duration_seconds=duration_secs,
                        pricing_tier_id=tier_id,
                        price_per_minute=demo_price,
                        revenue_usd=revenue,
                        cost_usd=cost,
                        started_at=call_time,
                        answered_at=call_time if status == CallStatus.COMPLETED.value else None,
                        ended_at=(call_time + timedelta(seconds=duration_secs)) if status == CallStatus.COMPLETED.value else call_time,
                    )
                    db.add(call)
                    calls_created += 1
                    total_revenue += revenue
                    total_cost += cost

            # Update agent total_calls and total_duration_seconds
            for agent in user_agents:
                call_count, total_dur = agent_call_counts.get(agent.id, (0, 0))
                agent.total_calls = call_count
                agent.total_duration_seconds = total_dur
                if call_count > 0:
                    # Set last_call_at to a recent time
                    agent.last_call_at = now - timedelta(hours=random.randint(1, 48))

    await db.commit()

    logger.info(
        "seed_completed",
        users=users_created,
        workspaces=workspaces_created,
        agents=agents_created,
        contacts=contacts_created,
        appointments=appointments_created,
        phone_numbers=phone_numbers_created,
        calls=calls_created,
        revenue=float(total_revenue),
    )

    return {
        "seeded": True,
        "users_created": users_created,
        "workspaces_created": workspaces_created,
        "agents_created": agents_created,
        "contacts_created": contacts_created,
        "appointments_created": appointments_created,
        "phone_numbers_created": phone_numbers_created,
        "calls_created": calls_created,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
    }


async def reseed_calls(db: AsyncSession) -> dict[str, int | Decimal]:
    """Clear all seeded data and reseed fresh."""
    logger.info("Clearing existing seeded data...")

    # Get seeded user IDs
    seeded_user_ids = await db.execute(
        select(User.id).where(User.email.like("%@seeded.spacevoice.ai"))
    )
    user_ids = [row[0] for row in seeded_user_ids.fetchall()]

    if user_ids:
        # Get workspace IDs for these users
        workspace_ids_result = await db.execute(
            select(Workspace.id).where(Workspace.user_id.in_(user_ids))
        )
        workspace_ids = [row[0] for row in workspace_ids_result.fetchall()]

        # Get agent IDs for these users
        agent_ids_result = await db.execute(
            select(Agent.id).where(Agent.user_id.in_(user_ids))
        )
        agent_ids = [row[0] for row in agent_ids_result.fetchall()]

        # Delete in order (respecting foreign keys)
        if workspace_ids:
            await db.execute(
                delete(Appointment).where(Appointment.workspace_id.in_(workspace_ids))
            )
            await db.execute(
                delete(Contact).where(Contact.workspace_id.in_(workspace_ids))
            )

        await db.execute(
            delete(CallRecord).where(CallRecord.user_id.in_(user_ids))
        )

        # Delete phone numbers
        await db.execute(
            delete(PhoneNumber).where(PhoneNumber.user_id.in_(user_ids))
        )

        if agent_ids:
            # Delete agent-workspace links first
            await db.execute(
                delete(AgentWorkspace).where(AgentWorkspace.agent_id.in_(agent_ids))
            )
            await db.execute(
                delete(Agent).where(Agent.id.in_(agent_ids))
            )

        if workspace_ids:
            await db.execute(
                delete(Workspace).where(Workspace.id.in_(workspace_ids))
            )

        await db.execute(
            delete(User).where(User.id.in_(user_ids))
        )

        await db.commit()

    logger.info("Cleared seeded data", users_deleted=len(user_ids))

    # Reseed
    return await seed_calls(db)
