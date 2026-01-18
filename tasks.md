# HVAC Triage Agent - Implementation Roadmap

Building the first SpaceVoice mirror prototype: an AI voice agent that triages HVAC service calls with emergency detection and instant dispatch.

---

## Phase 1: Retell Service Setup
**Goal:** Create the Retell SDK client for agent and call management.

- [ ] Create `backend/app/services/retell/__init__.py`
- [ ] Create `backend/app/services/retell/retell_service.py`
  - Agent CRUD (create, update, delete)
  - Phone number import (link Telnyx numbers)
  - Call registration for custom telephony
- [ ] Add config variables to `backend/app/core/config.py`
  - `RETELL_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `RETELL_LLM_WEBSOCKET_URL`

---

## Phase 2: Claude Adapter Implementation
**Goal:** Bridge Claude 4.5 Sonnet to Retell's Custom LLM protocol.

- [ ] Create `backend/app/services/retell/claude_adapter.py`
  - Message format conversion (Retell transcript → Claude messages)
  - Streaming response handling
  - Tool call detection and parsing
- [ ] Create `backend/app/services/retell/tool_converter.py`
  - OpenAI function format → Claude tool format
  - Tool result formatting

---

## Phase 3: Custom LLM WebSocket Server
**Goal:** Handle real-time voice conversation with Claude as the brain.

- [ ] Create `backend/app/services/retell/retell_llm_server.py`
  - WebSocket message handling (ping_pong, call_details, response_required)
  - Claude streaming integration
  - Tool execution routing
  - Response streaming to Retell
- [ ] Create `backend/app/api/retell_ws.py`
  - `/ws/retell/llm/{agent_id}` endpoint
  - Agent loading and configuration
  - Session management

---

## Phase 4: HVAC Triage Tools
**Goal:** Emergency classification and dispatch logic for HVAC calls.

- [ ] Create `backend/app/services/tools/hvac_triage_tools.py`
  - `classify_hvac_emergency` - Determine urgency based on issue, weather, occupants
  - `get_emergency_dispatch_info` - Return technician ETA and safety instructions
  - `schedule_routine_service` - Queue non-emergency appointments
- [ ] Update `backend/app/services/tools/registry.py`
  - Register HVAC tools in the tool registry
  - Add `hvac_triage` to enabled_tools options

### Emergency Classification Logic
```
EMERGENCY TRIGGERS:
├── Gas leak / CO detector alarm → CRITICAL (evacuate)
├── Electrical sparking / burning smell → CRITICAL
├── No heat + outdoor temp < 40°F → URGENT
├── No heat + vulnerable occupants → URGENT
├── No AC + indoor temp > 85°F + vulnerable → URGENT
└── All other issues → ROUTINE
```

---

## Phase 5: API Endpoints & Webhooks
**Goal:** Connect Retell events to our backend.

- [ ] Create `backend/app/api/retell_webhooks.py`
  - `/webhooks/retell/call-started` - Create call record
  - `/webhooks/retell/call-ended` - Save transcript, update metrics
  - `/webhooks/retell/inbound` - Route calls to correct agent
- [ ] Update `backend/app/main.py`
  - Include `retell_ws.router`
  - Include `retell_webhooks.router`

---

## Phase 6: Database Updates (Optional)
**Goal:** Support Retell as an alternative voice provider.

- [ ] Update `backend/app/models/agent.py`
  - Add `voice_provider` field (enum: openai_realtime, retell_claude)
  - Add `retell_agent_id` field
- [ ] Create Alembic migration
- [ ] Update agent creation API to support Retell agents

---

## Phase 7: Testing & Deployment
**Goal:** Validate the HVAC Triage Agent works end-to-end.

- [ ] Unit tests for HVAC triage tools
- [ ] Integration test for Custom LLM WebSocket
- [ ] Create test HVAC agent with system prompt
- [ ] Test scenarios:
  - Gas leak emergency (should dispatch immediately)
  - No heat with elderly occupant (should dispatch urgently)
  - AC maintenance request (should schedule routine)
  - Ambiguous issue (should ask clarifying questions)

---

## HVAC Triage Agent System Prompt

```
You are an HVAC service dispatcher for a home services company. Your job is to triage incoming calls and determine the appropriate response.

SAFETY FIRST - Always ask:
1. Do you smell gas or hear your CO detector?
2. Is there any sparking, smoke, or burning smell?
3. Are there elderly, infants, or anyone with medical conditions in the home?

GATHER INFORMATION:
- What equipment is affected? (furnace, AC, heat pump, water heater)
- What are the symptoms?
- What's the current temperature inside?
- Customer name and callback number

DECISION FLOW:
1. Use classify_hvac_emergency to determine urgency
2. If EMERGENCY: Use get_emergency_dispatch_info, assure customer help is coming
3. If ROUTINE: Use schedule_routine_service, confirm appointment details

VOICE RULES:
- Keep responses SHORT (1-2 sentences)
- Speak naturally, no lists or markdown
- Confirm understanding before acting
- Use filler words ("Let me check...", "One moment...")
```

---

## Success Criteria

1. **Response Latency**: < 200ms (Retell + Claude combined)
2. **Emergency Detection**: 100% accuracy on gas leak/CO scenarios
3. **Conversion Rate**: Track calls that result in booked appointments
4. **Zero-Detection**: Callers cannot tell they're talking to AI
