"""HVAC Triage tools for emergency classification and service scheduling.

This module implements the "Emergency Triage Logic" pattern from the SpaceVoice
agency specification, inspired by medical triage systems (MedVoice/Assort).

The triage system classifies HVAC service calls into:
- CRITICAL: Immediate safety hazards (gas leak, CO, electrical fire)
- URGENT: Time-sensitive issues (no heat in cold, no AC with vulnerable occupants)
- ROUTINE: Standard maintenance and non-emergency repairs

This enables the voice agent to:
1. Prioritize emergency dispatches
2. Provide appropriate safety instructions
3. Capture high-intent data for job value estimation
"""

from typing import Any, ClassVar

import structlog

logger = structlog.get_logger()

# Temperature thresholds (Fahrenheit)
TEMP_COLD_OUTSIDE = 40  # Below this is considered cold
TEMP_COLD_INSIDE = 55  # Below this is uncomfortably cold
TEMP_FREEZING = 32  # Pipe burst risk
TEMP_CRITICAL_COLD = 50  # Critically low indoor temp
TEMP_HOT_OUTSIDE = 95  # Above this is considered hot
TEMP_HOT_INSIDE = 85  # Above this is uncomfortably hot
TEMP_DANGEROUS_HEAT = 90  # Dangerously high indoor temp

# Equipment age thresholds (years)
EQUIPMENT_AGE_MAINTENANCE = 5  # Suggest maintenance after this age
EQUIPMENT_AGE_CONSIDER_REPLACEMENT = 10  # Consider replacement
EQUIPMENT_AGE_RECOMMEND_REPLACEMENT = 15  # Strongly recommend replacement


class HVACTriageTools:
    """HVAC-specific triage tools for voice agents.

    Provides emergency classification and routing logic for HVAC calls,
    following the agency mirroring patterns from the SpaceVoice spec.
    """

    # Emergency keywords that indicate immediate danger
    CRITICAL_KEYWORDS: ClassVar[set[str]] = {
        "gas leak", "smell gas", "gas smell", "natural gas",
        "carbon monoxide", "co detector", "co alarm", "monoxide alarm",
        "smoke", "fire", "burning", "sparking", "electrical fire",
        "flames", "on fire",
    }

    # Keywords indicating heating/cooling failure
    NO_HEAT_KEYWORDS: ClassVar[set[str]] = {
        "no heat", "not heating", "won't heat", "furnace not working",
        "heater broken", "no warm air", "cold air only", "freezing",
        "furnace won't start", "boiler not working", "heat pump not heating",
    }

    NO_AC_KEYWORDS: ClassVar[set[str]] = {
        "no ac", "no air conditioning", "ac not working", "not cooling",
        "won't cool", "ac broken", "hot air only", "air conditioner broken",
        "ac won't start", "heat pump not cooling",
    }

    # Vulnerable occupant indicators
    VULNERABLE_KEYWORDS: ClassVar[set[str]] = {
        "elderly", "senior", "old", "baby", "infant", "newborn", "child",
        "medical condition", "oxygen", "on oxygen", "heart condition",
        "diabetes", "immunocompromised", "sick", "ill", "disabled",
        "wheelchair", "bedridden",
    }

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        """Get OpenAI function calling tool definitions for HVAC triage.

        Returns:
            List of tool definitions compatible with ToolRegistry
        """
        return [
            {
                "type": "function",
                "name": "classify_hvac_emergency",
                "description": (
                    "Classify an HVAC service request as CRITICAL, URGENT, or ROUTINE. "
                    "Use this IMMEDIATELY when a caller reports an HVAC issue to determine "
                    "the appropriate response. Always ask about gas smells and CO detectors first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issue_description": {
                            "type": "string",
                            "description": "Detailed description of the HVAC issue from the caller",
                        },
                        "equipment_type": {
                            "type": "string",
                            "enum": ["furnace", "ac", "heat_pump", "boiler", "water_heater", "thermostat", "ductwork", "unknown"],
                            "description": "Type of HVAC equipment affected",
                        },
                        "has_vulnerable_occupants": {
                            "type": "boolean",
                            "description": "Whether elderly, infants, or medically vulnerable people are present",
                        },
                        "current_indoor_temp": {
                            "type": "number",
                            "description": "Current indoor temperature in Fahrenheit, if known",
                        },
                        "outdoor_temp": {
                            "type": "number",
                            "description": "Current outdoor temperature in Fahrenheit, if known",
                        },
                        "safety_concerns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Any safety concerns mentioned: gas_smell, co_detector, smoke, sparking, etc.",
                        },
                    },
                    "required": ["issue_description", "equipment_type"],
                },
            },
            {
                "type": "function",
                "name": "get_emergency_dispatch_info",
                "description": (
                    "Get emergency dispatch information and safety instructions. "
                    "Use this AFTER classifying a call as CRITICAL or URGENT to get "
                    "technician ETA and caller safety instructions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "emergency_type": {
                            "type": "string",
                            "enum": ["gas_leak", "carbon_monoxide", "electrical", "no_heat_critical", "no_ac_critical", "other_urgent"],
                            "description": "Type of emergency from classification",
                        },
                        "address": {
                            "type": "string",
                            "description": "Service address for dispatch",
                        },
                        "callback_number": {
                            "type": "string",
                            "description": "Phone number to reach the customer",
                        },
                    },
                    "required": ["emergency_type"],
                },
            },
            {
                "type": "function",
                "name": "estimate_job_value",
                "description": (
                    "Estimate the potential value of an HVAC service job. "
                    "Use this for non-emergency calls to capture high-intent data "
                    "and suggest appropriate service options."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_type": {
                            "type": "string",
                            "enum": ["repair", "maintenance", "installation", "replacement", "inspection", "estimate"],
                            "description": "Type of service needed",
                        },
                        "equipment_type": {
                            "type": "string",
                            "description": "Type of equipment requiring service",
                        },
                        "equipment_age_years": {
                            "type": "number",
                            "description": "Age of the equipment in years, if known",
                        },
                        "issue_severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "major"],
                            "description": "Severity of the issue",
                        },
                        "customer_budget_mentioned": {
                            "type": "string",
                            "description": "Any budget or price sensitivity mentioned by customer",
                        },
                    },
                    "required": ["service_type", "equipment_type"],
                },
            },
            {
                "type": "function",
                "name": "schedule_hvac_service",
                "description": (
                    "Schedule a routine HVAC service appointment. "
                    "Use for non-emergency maintenance, repairs, or installations. "
                    "Collects preferred scheduling and service details."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_type": {
                            "type": "string",
                            "enum": ["maintenance", "repair", "installation", "inspection", "estimate", "tune_up"],
                            "description": "Type of service needed",
                        },
                        "equipment_type": {
                            "type": "string",
                            "description": "Type of equipment requiring service",
                        },
                        "preferred_date": {
                            "type": "string",
                            "description": "Preferred appointment date (YYYY-MM-DD format)",
                        },
                        "preferred_time": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening", "anytime"],
                            "description": "Preferred time of day",
                        },
                        "issue_description": {
                            "type": "string",
                            "description": "Description of the issue or service needed",
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["flexible", "this_week", "next_few_days", "asap"],
                            "description": "How urgently the customer needs service",
                        },
                    },
                    "required": ["service_type", "equipment_type"],
                },
            },
        ]

    @classmethod
    def _detect_emergency_type(
        cls,
        issue_description: str,
        safety_concerns: list[str] | None = None,
    ) -> tuple[str | None, str]:
        """Detect if the issue description indicates an emergency.

        Args:
            issue_description: Description of the issue
            safety_concerns: Explicit safety concerns mentioned

        Returns:
            Tuple of (emergency_type, reason) or (None, "") if not emergency
        """
        issue_lower = issue_description.lower()
        concerns = set(safety_concerns or [])

        # Check for gas leak / CO (ALWAYS CRITICAL)
        if any(kw in issue_lower for kw in cls.CRITICAL_KEYWORDS) or "gas_smell" in concerns or "co_detector" in concerns:
            if "gas" in issue_lower or "gas_smell" in concerns:
                return "gas_leak", "Potential gas leak detected - evacuate immediately"
            if "carbon monoxide" in issue_lower or "co" in issue_lower or "co_detector" in concerns:
                return "carbon_monoxide", "Carbon monoxide alert - evacuate immediately"
            if any(kw in issue_lower for kw in ["spark", "fire", "smoke", "burning"]) or "sparking" in concerns:
                return "electrical", "Electrical hazard detected - disconnect power if safe"

        return None, ""

    @classmethod
    def _is_heating_emergency(
        cls,
        issue_description: str,
        has_vulnerable: bool,
        indoor_temp: float | None,
        outdoor_temp: float | None,
    ) -> tuple[bool, str]:
        """Check if a heating issue is an emergency.

        Args:
            issue_description: Description of the issue
            has_vulnerable: Whether vulnerable occupants are present
            indoor_temp: Current indoor temperature (F)
            outdoor_temp: Current outdoor temperature (F)

        Returns:
            Tuple of (is_emergency, reason)
        """
        issue_lower = issue_description.lower()

        # Check if it's a no-heat situation
        if not any(kw in issue_lower for kw in cls.NO_HEAT_KEYWORDS):
            return False, ""

        # Emergency conditions for no heat
        is_cold_outside = outdoor_temp is not None and outdoor_temp < TEMP_COLD_OUTSIDE
        is_cold_inside = indoor_temp is not None and indoor_temp < TEMP_COLD_INSIDE
        is_freezing_risk = outdoor_temp is not None and outdoor_temp < TEMP_FREEZING

        if is_freezing_risk:
            return True, "No heat with freezing temperatures - pipe burst risk"
        if has_vulnerable and (is_cold_outside or is_cold_inside):
            return True, "No heat with vulnerable occupants in cold conditions"
        if is_cold_inside and indoor_temp is not None and indoor_temp < TEMP_CRITICAL_COLD:
            return True, "Indoor temperature critically low"

        return False, ""

    @classmethod
    def _is_cooling_emergency(
        cls,
        issue_description: str,
        has_vulnerable: bool,
        indoor_temp: float | None,
        outdoor_temp: float | None,
    ) -> tuple[bool, str]:
        """Check if a cooling issue is an emergency.

        Args:
            issue_description: Description of the issue
            has_vulnerable: Whether vulnerable occupants are present
            indoor_temp: Current indoor temperature (F)
            outdoor_temp: Current outdoor temperature (F)

        Returns:
            Tuple of (is_emergency, reason)
        """
        issue_lower = issue_description.lower()

        # Check if it's a no-AC situation
        if not any(kw in issue_lower for kw in cls.NO_AC_KEYWORDS):
            return False, ""

        # Emergency conditions for no AC
        is_hot_outside = outdoor_temp is not None and outdoor_temp > TEMP_HOT_OUTSIDE
        is_hot_inside = indoor_temp is not None and indoor_temp > TEMP_HOT_INSIDE
        is_dangerous_heat = indoor_temp is not None and indoor_temp > TEMP_DANGEROUS_HEAT

        if has_vulnerable and (is_hot_outside or is_hot_inside):
            return True, "No AC with vulnerable occupants in hot conditions"
        if is_dangerous_heat:
            return True, "Indoor temperature dangerously high"

        return False, ""

    @classmethod
    async def execute_tool(cls, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute an HVAC triage tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        log = logger.bind(component="hvac_triage", tool=tool_name)

        if tool_name == "classify_hvac_emergency":
            return await cls._classify_emergency(arguments, log)

        if tool_name == "get_emergency_dispatch_info":
            return await cls._get_dispatch_info(arguments, log)

        if tool_name == "estimate_job_value":
            return await cls._estimate_job_value(arguments, log)

        if tool_name == "schedule_hvac_service":
            return await cls._schedule_service(arguments, log)

        log.warning("unknown_hvac_tool", tool_name=tool_name)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    @classmethod
    async def _classify_emergency(
        cls,
        args: dict[str, Any],
        log: Any,
    ) -> dict[str, Any]:
        """Classify an HVAC issue as CRITICAL, URGENT, or ROUTINE.

        Args:
            args: Tool arguments
            log: Logger instance

        Returns:
            Classification result with recommended action
        """
        issue = args.get("issue_description", "")
        equipment = args.get("equipment_type", "unknown")
        has_vulnerable = args.get("has_vulnerable_occupants", False)
        indoor_temp = args.get("current_indoor_temp")
        outdoor_temp = args.get("outdoor_temp")
        safety_concerns = args.get("safety_concerns", [])

        log.info(
            "classifying_hvac_issue",
            equipment=equipment,
            has_vulnerable=has_vulnerable,
            indoor_temp=indoor_temp,
            outdoor_temp=outdoor_temp,
        )

        # Check for critical emergencies first
        emergency_type, reason = cls._detect_emergency_type(issue, safety_concerns)
        if emergency_type:
            log.info("critical_emergency_detected", type=emergency_type)
            return {
                "success": True,
                "classification": "CRITICAL",
                "emergency_type": emergency_type,
                "reason": reason,
                "recommended_action": "DISPATCH_IMMEDIATELY",
                "safety_instructions": cls._get_safety_instructions(emergency_type),
                "estimated_response_time": "15-30 minutes",
            }

        # Check for urgent heating issues
        is_heat_emergency, heat_reason = cls._is_heating_emergency(
            issue, has_vulnerable, indoor_temp, outdoor_temp
        )
        if is_heat_emergency:
            log.info("urgent_heating_emergency", reason=heat_reason)
            return {
                "success": True,
                "classification": "URGENT",
                "emergency_type": "no_heat_critical",
                "reason": heat_reason,
                "recommended_action": "DISPATCH_PRIORITY",
                "safety_instructions": cls._get_safety_instructions("no_heat_critical"),
                "estimated_response_time": "1-2 hours",
            }

        # Check for urgent cooling issues
        is_cool_emergency, cool_reason = cls._is_cooling_emergency(
            issue, has_vulnerable, indoor_temp, outdoor_temp
        )
        if is_cool_emergency:
            log.info("urgent_cooling_emergency", reason=cool_reason)
            return {
                "success": True,
                "classification": "URGENT",
                "emergency_type": "no_ac_critical",
                "reason": cool_reason,
                "recommended_action": "DISPATCH_PRIORITY",
                "safety_instructions": cls._get_safety_instructions("no_ac_critical"),
                "estimated_response_time": "1-2 hours",
            }

        # Routine service
        log.info("routine_service_request")
        return {
            "success": True,
            "classification": "ROUTINE",
            "emergency_type": None,
            "reason": "Standard service request - no emergency conditions detected",
            "recommended_action": "SCHEDULE_APPOINTMENT",
            "safety_instructions": None,
            "estimated_response_time": "Next available appointment",
        }

    @classmethod
    async def _get_dispatch_info(
        cls,
        args: dict[str, Any],
        log: Any,
    ) -> dict[str, Any]:
        """Get emergency dispatch information.

        Args:
            args: Tool arguments
            log: Logger instance

        Returns:
            Dispatch information with ETA and safety instructions
        """
        emergency_type = args.get("emergency_type", "other_urgent")
        address = args.get("address")
        callback_number = args.get("callback_number")

        log.info(
            "generating_dispatch_info",
            emergency_type=emergency_type,
            has_address=bool(address),
        )

        # Determine response time based on emergency type
        if emergency_type in ["gas_leak", "carbon_monoxide", "electrical"]:
            eta = "15-30 minutes"
            priority = "CRITICAL"
        else:
            eta = "1-2 hours"
            priority = "URGENT"

        return {
            "success": True,
            "dispatch_status": "technician_dispatched",
            "priority": priority,
            "estimated_arrival": eta,
            "safety_instructions": cls._get_safety_instructions(emergency_type),
            "technician_info": "Next available emergency technician",
            "confirmation": f"Emergency dispatch initiated. A technician will arrive within {eta}.",
            "callback_confirmed": bool(callback_number),
            "address_confirmed": bool(address),
        }

    @classmethod
    async def _estimate_job_value(
        cls,
        args: dict[str, Any],
        log: Any,
    ) -> dict[str, Any]:
        """Estimate the potential value of an HVAC job.

        This implements the "VIP Intake" pattern from the SpaceVoice spec,
        capturing high-intent data to suggest curated solutions.

        Args:
            args: Tool arguments
            log: Logger instance

        Returns:
            Job value estimate with service recommendations
        """
        service_type = args.get("service_type", "repair")
        equipment_type = args.get("equipment_type", "unknown")
        equipment_age = args.get("equipment_age_years")
        severity = args.get("issue_severity", "moderate")
        budget_mentioned = args.get("customer_budget_mentioned")

        log.info(
            "estimating_job_value",
            service_type=service_type,
            equipment_type=equipment_type,
            age=equipment_age,
        )

        # Base value ranges by service type
        value_ranges = {
            "repair": {"low": 150, "mid": 400, "high": 1200},
            "maintenance": {"low": 100, "mid": 200, "high": 400},
            "installation": {"low": 3000, "mid": 7000, "high": 15000},
            "replacement": {"low": 4000, "mid": 8000, "high": 20000},
            "inspection": {"low": 75, "mid": 150, "high": 300},
            "estimate": {"low": 0, "mid": 0, "high": 100},
        }

        base = value_ranges.get(service_type, value_ranges["repair"])

        # Adjust based on severity
        if severity == "major":
            estimated_range = f"${base['mid']}-${base['high']}"
            upsell_opportunity = "high"
        elif severity == "minor":
            estimated_range = f"${base['low']}-${base['mid']}"
            upsell_opportunity = "low"
        else:
            estimated_range = f"${base['low']}-${base['high']}"
            upsell_opportunity = "medium"

        # Check for replacement recommendation
        recommend_replacement = False
        replacement_reason = None
        if equipment_age and equipment_age > EQUIPMENT_AGE_RECOMMEND_REPLACEMENT:
            recommend_replacement = True
            replacement_reason = f"Equipment is {equipment_age} years old - replacement may be more cost-effective"
        elif equipment_age and equipment_age > EQUIPMENT_AGE_CONSIDER_REPLACEMENT and severity == "major":
            recommend_replacement = True
            replacement_reason = "Significant repair on aging equipment - consider replacement options"

        return {
            "success": True,
            "service_type": service_type,
            "equipment_type": equipment_type,
            "estimated_value_range": estimated_range,
            "upsell_opportunity": upsell_opportunity,
            "recommend_replacement": recommend_replacement,
            "replacement_reason": replacement_reason,
            "suggested_services": cls._get_suggested_services(service_type, equipment_age),
            "budget_sensitivity": "mentioned" if budget_mentioned else "not_mentioned",
        }

    @classmethod
    async def _schedule_service(
        cls,
        args: dict[str, Any],
        log: Any,
    ) -> dict[str, Any]:
        """Schedule a routine HVAC service appointment.

        Args:
            args: Tool arguments
            log: Logger instance

        Returns:
            Scheduling information (to be integrated with booking system)
        """
        service_type = args.get("service_type", "repair")
        equipment_type = args.get("equipment_type", "unknown")
        preferred_date = args.get("preferred_date")
        preferred_time = args.get("preferred_time", "anytime")
        issue_description = args.get("issue_description", "")
        urgency = args.get("urgency", "flexible")

        log.info(
            "scheduling_hvac_service",
            service_type=service_type,
            preferred_date=preferred_date,
            urgency=urgency,
        )

        # This would integrate with the CRM booking system
        # For now, return scheduling confirmation
        return {
            "success": True,
            "status": "ready_to_book",
            "service_type": service_type,
            "equipment_type": equipment_type,
            "preferred_date": preferred_date,
            "preferred_time": preferred_time,
            "urgency": urgency,
            "issue_summary": issue_description[:200] if issue_description else None,
            "next_step": "Use book_appointment to finalize with customer contact info",
            "message": f"I can schedule a {service_type} appointment for your {equipment_type}. "
                      f"Let me get your contact information to confirm the booking.",
        }

    @staticmethod
    def _get_safety_instructions(emergency_type: str) -> str:
        """Get safety instructions for an emergency type.

        Args:
            emergency_type: Type of emergency

        Returns:
            Safety instructions string
        """
        instructions = {
            "gas_leak": (
                "IMPORTANT: Leave the building immediately. Do not use any electrical switches, "
                "phones, or anything that could create a spark. Do not start your car in the garage. "
                "Call from outside or a neighbor's house. Wait for the technician outside."
            ),
            "carbon_monoxide": (
                "IMPORTANT: Open all windows and doors immediately. Leave the building and get fresh air. "
                "If anyone feels dizzy, nauseous, or has a headache, seek medical attention. "
                "Do not return inside until cleared by a technician."
            ),
            "electrical": (
                "IMPORTANT: If safe to do so, turn off the main electrical breaker. "
                "Do not touch any equipment that is sparking or smoking. Keep everyone away from the area. "
                "If there is active fire or smoke, call 911 first."
            ),
            "no_heat_critical": (
                "While waiting for the technician: Use space heaters safely, keeping them away from "
                "flammable materials. Close off unused rooms to conserve heat. Layer clothing and use blankets. "
                "If pipes are at risk of freezing, let faucets drip slightly."
            ),
            "no_ac_critical": (
                "While waiting for the technician: Stay hydrated and drink plenty of water. "
                "Move to the coolest area of your home. Use fans if available. Close blinds to block sunlight. "
                "If anyone shows signs of heat exhaustion, seek medical attention."
            ),
            "other_urgent": (
                "A technician will arrive as soon as possible. Please ensure someone is available "
                "to provide access to the equipment when they arrive."
            ),
        }
        return instructions.get(emergency_type, instructions["other_urgent"])

    @staticmethod
    def _get_suggested_services(service_type: str, equipment_age: float | None) -> list[str]:
        """Get suggested additional services.

        Args:
            service_type: Primary service type
            equipment_age: Age of equipment in years

        Returns:
            List of suggested services
        """
        suggestions = []

        if service_type == "repair":
            suggestions.append("Diagnostic inspection")
            if equipment_age and equipment_age > EQUIPMENT_AGE_MAINTENANCE:
                suggestions.append("Preventive maintenance tune-up")

        if service_type == "maintenance":
            suggestions.append("Air filter replacement")
            suggestions.append("Duct inspection")

        if equipment_age and equipment_age > EQUIPMENT_AGE_CONSIDER_REPLACEMENT:
            suggestions.append("Energy efficiency evaluation")
            suggestions.append("Replacement cost estimate")

        return suggestions
