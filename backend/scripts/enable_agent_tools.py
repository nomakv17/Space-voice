#!/usr/bin/env python3
"""Quick script to enable tools on an agent.

Usage:
    # With DATABASE_URL set:
    DATABASE_URL="postgres://..." python scripts/enable_agent_tools.py

    # Or via Railway:
    railway run python scripts/enable_agent_tools.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> None:
    """Enable tools on the HVAC agent."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    agent_id = "98e6b0e1-59da-4e56-b75c-eae6c84c0684"

    async with async_session() as session:
        # First, check current state
        result = await session.execute(
            text("SELECT id, name, enabled_tools, enabled_tool_ids FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id},
        )
        row = result.fetchone()

        if not row:
            print(f"ERROR: Agent {agent_id} not found")
            sys.exit(1)

        print(f"Agent: {row[1]} ({row[0]})")
        print(f"Current enabled_tools: {row[2]}")
        print(f"Current enabled_tool_ids: {row[3]}")
        print()

        # Check integrations
        result = await session.execute(
            text("""
                SELECT integration_id, is_active, credentials IS NOT NULL as has_credentials
                FROM user_integrations
                WHERE user_id = (SELECT user_id FROM agents WHERE id = :agent_id)
                  AND is_active = true
            """),
            {"agent_id": agent_id},
        )
        integrations = result.fetchall()
        print("Active integrations:")
        for integration in integrations:
            print(f"  - {integration[0]}: active={integration[1]}, has_credentials={integration[2]}")
        print()

        # Update the agent
        enabled_tools = ["google-calendar", "telnyx-sms"]
        enabled_tool_ids = {
            "google-calendar": ["google_calendar_create_event", "google_calendar_check_availability"],
            "telnyx-sms": ["telnyx_send_sms"],
        }

        import json

        await session.execute(
            text("""
                UPDATE agents
                SET enabled_tools = :enabled_tools::jsonb,
                    enabled_tool_ids = :enabled_tool_ids::jsonb
                WHERE id = :agent_id
            """),
            {
                "agent_id": agent_id,
                "enabled_tools": json.dumps(enabled_tools),
                "enabled_tool_ids": json.dumps(enabled_tool_ids),
            },
        )
        await session.commit()

        # Verify update
        result = await session.execute(
            text("SELECT enabled_tools, enabled_tool_ids FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id},
        )
        row = result.fetchone()
        print("✅ Agent updated!")
        print(f"New enabled_tools: {row[0]}")
        print(f"New enabled_tool_ids: {row[1]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
