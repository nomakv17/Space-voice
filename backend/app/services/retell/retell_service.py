"""Retell AI service for agent and call management.

This service wraps the Retell SDK to provide:
- Agent CRUD operations (create, update, delete, list)
- Phone number management (import from Telnyx)
- Call registration for custom telephony integration
- LLM configuration for Custom LLM WebSocket
"""

from typing import Any

import structlog
from retell import AsyncRetell
from retell.types import AgentResponse, PhoneNumberResponse

logger = structlog.get_logger()


class RetellService:
    """Manages Retell AI agents, phone numbers, and calls.

    Retell AI handles voice orchestration (STT, TTS, barge-in, turn detection)
    while we provide the LLM backend via Custom LLM WebSocket.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize Retell client.

        Args:
            api_key: Retell API Key from dashboard.retellai.com
        """
        self.client = AsyncRetell(api_key=api_key)
        self.logger = logger.bind(component="retell_service")

    async def create_agent(
        self,
        agent_name: str,
        llm_websocket_url: str,
        voice_id: str = "11labs-Adrian",
        language: str = "en-US",
        responsiveness: float = 0.9,
        interruption_sensitivity: float = 0.8,
        enable_backchannel: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a Retell agent with Custom LLM backend.

        The agent uses our WebSocket endpoint for LLM responses, allowing
        Claude to power the conversation while Retell handles voice.

        Args:
            agent_name: Display name for the agent
            llm_websocket_url: Our Custom LLM WebSocket URL (e.g., wss://api.example.com/ws/retell/llm/{agent_id})
            voice_id: Retell voice ID (11labs-Adrian, 11labs-Rachel, etc.)
            language: Language code (en-US, es-ES, etc.)
            responsiveness: How quickly agent responds (0-1). Higher = faster. Default 0.9.
            interruption_sensitivity: How easily user can interrupt (0-1). Higher = easier. Default 0.8.
            enable_backchannel: Enable "uh-huh", "mm-hmm" responses. Default True.
            **kwargs: Additional agent configuration

        Returns:
            Dict with agent_id and configuration
        """
        self.logger.info(
            "creating_agent",
            name=agent_name,
            voice_id=voice_id,
            language=language,
            responsiveness=responsiveness,
            interruption_sensitivity=interruption_sensitivity,
        )

        agent: AgentResponse = await self.client.agent.create(
            response_engine={
                "type": "custom-llm",  # Retell SDK requires this literal
                "llm_websocket_url": llm_websocket_url,
            },
            voice_id=voice_id,
            agent_name=agent_name,
            language=language,  # type: ignore[arg-type]  # SDK has strict literal types
            responsiveness=responsiveness,
            interruption_sensitivity=interruption_sensitivity,
            enable_backchannel=enable_backchannel,
            **kwargs,
        )

        self.logger.info("agent_created", agent_id=agent.agent_id)

        return {
            "agent_id": agent.agent_id,
            "name": agent_name,
            "voice_id": voice_id,
            "language": language,
            "llm_websocket_url": llm_websocket_url,
            "responsiveness": responsiveness,
            "interruption_sensitivity": interruption_sensitivity,
            "enable_backchannel": enable_backchannel,
        }

    async def get_agent(self, agent_id: str) -> AgentResponse | None:
        """Get a Retell agent by ID.

        Args:
            agent_id: Retell agent ID

        Returns:
            AgentResponse or None if not found
        """
        try:
            return await self.client.agent.retrieve(agent_id)
        except Exception as e:
            self.logger.warning("agent_not_found", agent_id=agent_id, error=str(e))
            return None

    async def update_agent(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> AgentResponse:
        """Update a Retell agent configuration.

        Args:
            agent_id: Retell agent ID
            **kwargs: Fields to update (agent_name, voice_id, language, etc.)

        Returns:
            Updated AgentResponse
        """
        self.logger.info("updating_agent", agent_id=agent_id, updates=list(kwargs.keys()))

        agent = await self.client.agent.update(agent_id, **kwargs)

        self.logger.info("agent_updated", agent_id=agent_id)
        return agent

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete a Retell agent.

        Args:
            agent_id: Retell agent ID

        Returns:
            True if deleted successfully
        """
        self.logger.info("deleting_agent", agent_id=agent_id)

        try:
            await self.client.agent.delete(agent_id)
            self.logger.info("agent_deleted", agent_id=agent_id)
            return True
        except Exception as e:
            self.logger.exception("delete_failed", agent_id=agent_id, error=str(e))
            return False

    async def list_agents(self) -> list[AgentResponse]:
        """List all Retell agents.

        Returns:
            List of AgentResponse objects
        """
        self.logger.info("listing_agents")

        agents = await self.client.agent.list()
        agent_list = list(agents)

        self.logger.info("agents_listed", count=len(agent_list))
        return agent_list

    async def import_phone_number(
        self,
        phone_number: str,
        agent_id: str | None = None,
        termination_uri: str | None = None,
    ) -> PhoneNumberResponse:
        """Import a phone number from Telnyx/Twilio to Retell.

        This links an existing phone number to Retell for inbound call handling.
        The number must be configured in your telephony provider to forward
        SIP traffic to Retell's SIP endpoint.

        Args:
            phone_number: Phone number in E.164 format (+1234567890)
            agent_id: Retell agent ID to bind to this number
            termination_uri: SIP termination URI for outbound calls

        Returns:
            PhoneNumberResponse with import details
        """
        self.logger.info(
            "importing_phone_number",
            phone_number=phone_number,
            agent_id=agent_id,
        )

        # Build kwargs - only include termination_uri if provided
        import_kwargs: dict[str, Any] = {
            "phone_number": phone_number,
        }
        if agent_id:
            import_kwargs["inbound_agent_id"] = agent_id
        if termination_uri:
            import_kwargs["termination_uri"] = termination_uri

        phone = await self.client.phone_number.import_(**import_kwargs)

        self.logger.info("phone_number_imported", phone_number=phone_number)
        return phone

    async def update_phone_number(
        self,
        phone_number: str,
        agent_id: str | None = None,
    ) -> PhoneNumberResponse:
        """Update phone number configuration.

        Args:
            phone_number: Phone number in E.164 format
            agent_id: New agent ID to bind

        Returns:
            Updated PhoneNumberResponse
        """
        self.logger.info(
            "updating_phone_number",
            phone_number=phone_number,
            agent_id=agent_id,
        )

        phone = await self.client.phone_number.update(
            phone_number=phone_number,
            inbound_agent_id=agent_id,
        )

        self.logger.info("phone_number_updated", phone_number=phone_number)
        return phone

    async def register_call(
        self,
        agent_id: str,
        audio_encoding: str = "mulaw",
        sample_rate: int = 8000,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a call for custom telephony integration.

        Used when handling calls through your own telephony (Telnyx/Twilio)
        instead of Retell's built-in phone numbers.

        Args:
            agent_id: Retell agent ID to handle the call
            audio_encoding: Audio format (mulaw, linear16, opus)
            sample_rate: Sample rate in Hz (8000 for telephony)
            metadata: Optional call metadata (caller_phone, etc.)

        Returns:
            Dict with call_id and WebSocket URL for audio streaming
        """
        self.logger.info(
            "registering_call",
            agent_id=agent_id,
            audio_encoding=audio_encoding,
            sample_rate=sample_rate,
        )

        # Use register_phone_call for custom telephony integration
        # Note: audio_encoding and sample_rate are logged but SDK handles defaults
        call = await self.client.call.register_phone_call(
            agent_id=agent_id,
            metadata=metadata,
        )

        self.logger.info("call_registered", call_id=call.call_id)

        return {
            "call_id": call.call_id,
            "agent_id": agent_id,
            "access_token": getattr(call, "access_token", None),
        }

    async def create_web_call(
        self,
        agent_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a web call for browser-based voice interaction.

        Args:
            agent_id: Retell agent ID
            metadata: Optional call metadata

        Returns:
            Dict with call_id and access_token for WebRTC connection
        """
        self.logger.info("creating_web_call", agent_id=agent_id)

        call = await self.client.call.create_web_call(
            agent_id=agent_id,
            metadata=metadata,
        )

        self.logger.info("web_call_created", call_id=call.call_id)

        return {
            "call_id": call.call_id,
            "access_token": call.access_token,
            "agent_id": agent_id,
        }

    async def create_phone_call(
        self,
        agent_id: str,
        to_number: str,
        from_number: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an outbound phone call.

        Args:
            agent_id: Retell agent ID
            to_number: Destination phone number (E.164)
            from_number: Caller ID phone number (E.164)
            metadata: Optional call metadata

        Returns:
            Dict with call_id and call status
        """
        self.logger.info(
            "creating_phone_call",
            agent_id=agent_id,
            to=to_number,
            from_=from_number,
        )

        call = await self.client.call.create_phone_call(
            from_number=from_number,
            to_number=to_number,
            override_agent_id=agent_id,  # SDK uses override_agent_id, not agent_id
            metadata=metadata,
        )

        self.logger.info("phone_call_created", call_id=call.call_id)

        return {
            "call_id": call.call_id,
            "agent_id": agent_id,
            "to_number": to_number,
            "from_number": from_number,
            "status": getattr(call, "call_status", "initiated"),
        }

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        """Get call details.

        Args:
            call_id: Retell call ID

        Returns:
            Call details dict or None if not found
        """
        try:
            call = await self.client.call.retrieve(call_id)
            return {
                "call_id": call.call_id,
                "agent_id": call.agent_id,
                "status": call.call_status,
                "start_timestamp": getattr(call, "start_timestamp", None),
                "end_timestamp": getattr(call, "end_timestamp", None),
                "transcript": getattr(call, "transcript", None),
                "recording_url": getattr(call, "recording_url", None),
            }
        except Exception as e:
            self.logger.warning("call_not_found", call_id=call_id, error=str(e))
            return None

    async def list_calls(
        self,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List calls with optional filtering.

        Args:
            agent_id: Filter by agent ID
            limit: Maximum number of calls to return

        Returns:
            List of call detail dicts
        """
        self.logger.info("listing_calls", agent_id=agent_id, limit=limit)

        # Build filter criteria if agent_id provided
        filter_kwargs: dict[str, Any] = {"limit": limit}
        if agent_id:
            filter_kwargs["filter_criteria"] = {"agent_id": [agent_id]}

        calls = await self.client.call.list(**filter_kwargs)

        call_list = [
            {
                "call_id": call.call_id,
                "agent_id": call.agent_id,
                "status": call.call_status,
                "direction": getattr(call, "direction", None),
                "start_timestamp": getattr(call, "start_timestamp", None),
                "end_timestamp": getattr(call, "end_timestamp", None),
            }
            for call in calls
        ]

        self.logger.info("calls_listed", count=len(call_list))
        return call_list
