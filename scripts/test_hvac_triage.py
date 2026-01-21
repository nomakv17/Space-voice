#!/usr/bin/env python3
"""
SpaceVoice HVAC Triage Logic Stress Test
Tests the emergency classification logic for various HVAC scenarios.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.tools.hvac_triage_tools import HVACTriageTools


class TriageTestResult:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.results = []

    def add_result(self, name: str, passed: bool, expected: str, actual: str, details: dict = None):
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append({
            "name": name,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "details": details or {},
        })


# Test scenarios based on SpaceVoice HVAC Triage spec
TEST_SCENARIOS = [
    # CRITICAL - Gas/CO emergencies (should ALWAYS be CRITICAL)
    {
        "name": "Gas Leak Emergency",
        "input": {
            "issue_description": "Help, my furnace is making a loud banging noise and I smell gas!",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": False,
            "safety_concerns": ["gas_smell"],
        },
        "expected_classification": "CRITICAL",
        "expected_type": "gas_leak",
    },
    {
        "name": "Carbon Monoxide Alert",
        "input": {
            "issue_description": "Our carbon monoxide detector keeps going off near the furnace",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": False,
            "safety_concerns": ["co_detector"],
        },
        "expected_classification": "CRITICAL",
        "expected_type": "carbon_monoxide",
    },
    {
        "name": "Electrical Fire Risk",
        "input": {
            "issue_description": "I see sparking coming from my HVAC unit and there's a burning smell",
            "equipment_type": "ac",
            "has_vulnerable_occupants": False,
            "safety_concerns": ["sparking"],
        },
        "expected_classification": "CRITICAL",
        "expected_type": "electrical",
    },

    # URGENT - No heat in cold conditions
    {
        "name": "No Heat - Freezing Temperatures",
        "input": {
            "issue_description": "Furnace not working, no heat at all",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": False,
            "current_indoor_temp": 48,
            "outdoor_temp": 25,  # Below freezing
        },
        "expected_classification": "URGENT",
        "expected_type": "no_heat_critical",
    },
    {
        "name": "No Heat - Elderly Occupant",
        "input": {
            "issue_description": "Heater broken, won't heat at all",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": True,
            "current_indoor_temp": 58,
            "outdoor_temp": 35,
        },
        "expected_classification": "URGENT",
        "expected_type": "no_heat_critical",
    },
    {
        "name": "No AC - Vulnerable Occupant in Heat",
        "input": {
            "issue_description": "AC not working, not cooling",
            "equipment_type": "ac",
            "has_vulnerable_occupants": True,
            "current_indoor_temp": 88,
            "outdoor_temp": 98,
        },
        "expected_classification": "URGENT",
        "expected_type": "no_ac_critical",
    },

    # ROUTINE - Non-emergency scenarios
    {
        "name": "Quote Request - Low Priority",
        "input": {
            "issue_description": "Just calling for a quote on a new AC unit for next summer",
            "equipment_type": "ac",
            "has_vulnerable_occupants": False,
        },
        "expected_classification": "ROUTINE",
        "expected_type": None,
    },
    {
        "name": "Maintenance Request",
        "input": {
            "issue_description": "I'd like to schedule my annual furnace tune-up",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": False,
        },
        "expected_classification": "ROUTINE",
        "expected_type": None,
    },
    {
        "name": "Thermostat Issue - Non-Emergency",
        "input": {
            "issue_description": "My thermostat display is flickering",
            "equipment_type": "thermostat",
            "has_vulnerable_occupants": False,
            "current_indoor_temp": 72,
            "outdoor_temp": 65,
        },
        "expected_classification": "ROUTINE",
        "expected_type": None,
    },
    {
        "name": "Minor Noise Complaint",
        "input": {
            "issue_description": "My AC makes a slight rattling sound",
            "equipment_type": "ac",
            "has_vulnerable_occupants": False,
        },
        "expected_classification": "ROUTINE",
        "expected_type": None,
    },

    # Edge cases
    {
        "name": "No Heat - Mild Weather (Should be Routine)",
        "input": {
            "issue_description": "Furnace not working, no heat",
            "equipment_type": "furnace",
            "has_vulnerable_occupants": False,
            "current_indoor_temp": 68,
            "outdoor_temp": 55,
        },
        "expected_classification": "ROUTINE",  # Mild weather, no emergency
        "expected_type": None,
    },
    {
        "name": "AC Not Cooling - Moderate Temp (Should be Routine)",
        "input": {
            "issue_description": "AC not cooling well",
            "equipment_type": "ac",
            "has_vulnerable_occupants": False,
            "current_indoor_temp": 78,
            "outdoor_temp": 85,
        },
        "expected_classification": "ROUTINE",  # Not dangerously hot
        "expected_type": None,
    },
]


async def run_triage_tests() -> TriageTestResult:
    """Run all HVAC triage test scenarios."""
    result = TriageTestResult()

    print("\n" + "-" * 60)
    print("Running HVAC Triage Tests...")
    print("-" * 60)

    for scenario in TEST_SCENARIOS:
        try:
            # Call the classification tool
            classification_result = await HVACTriageTools.execute_tool(
                "classify_hvac_emergency",
                scenario["input"]
            )

            actual_classification = classification_result.get("classification")
            actual_type = classification_result.get("emergency_type")

            # Check if classification matches expected
            classification_match = actual_classification == scenario["expected_classification"]
            type_match = actual_type == scenario["expected_type"]

            passed = classification_match and type_match

            result.add_result(
                name=scenario["name"],
                passed=passed,
                expected=f"{scenario['expected_classification']} ({scenario['expected_type']})",
                actual=f"{actual_classification} ({actual_type})",
                details={
                    "reason": classification_result.get("reason"),
                    "recommended_action": classification_result.get("recommended_action"),
                    "safety_instructions": classification_result.get("safety_instructions"),
                }
            )

            status = "[PASS]" if passed else "[FAIL]"
            print(f"\n{status} {scenario['name']}")
            print(f"    Expected: {scenario['expected_classification']} ({scenario['expected_type']})")
            print(f"    Actual:   {actual_classification} ({actual_type})")
            if not passed:
                print(f"    Reason:   {classification_result.get('reason')}")

        except Exception as e:
            result.add_result(
                name=scenario["name"],
                passed=False,
                expected=scenario["expected_classification"],
                actual=f"ERROR: {str(e)}",
            )
            print(f"\n[ERROR] {scenario['name']}: {str(e)}")

    return result


async def test_safety_instructions():
    """Test that safety instructions are provided for emergencies."""
    print("\n" + "-" * 60)
    print("Testing Safety Instructions...")
    print("-" * 60)

    gas_result = await HVACTriageTools.execute_tool(
        "classify_hvac_emergency",
        {
            "issue_description": "I smell gas",
            "equipment_type": "furnace",
            "safety_concerns": ["gas_smell"],
        }
    )

    if gas_result.get("safety_instructions"):
        print("\n[PASS] Gas leak provides safety instructions")
        print(f"    Instructions: {gas_result['safety_instructions'][:100]}...")
        return True
    else:
        print("\n[FAIL] Gas leak missing safety instructions")
        return False


async def test_dispatch_info():
    """Test emergency dispatch info generation."""
    print("\n" + "-" * 60)
    print("Testing Dispatch Info Generation...")
    print("-" * 60)

    dispatch_result = await HVACTriageTools.execute_tool(
        "get_emergency_dispatch_info",
        {
            "emergency_type": "gas_leak",
            "address": "123 Main St",
            "callback_number": "+15551234567",
        }
    )

    if dispatch_result.get("dispatch_status") == "technician_dispatched":
        print("\n[PASS] Dispatch info generated correctly")
        print(f"    ETA: {dispatch_result.get('estimated_arrival')}")
        print(f"    Priority: {dispatch_result.get('priority')}")
        return True
    else:
        print("\n[FAIL] Dispatch info generation failed")
        return False


async def main():
    """Run all HVAC triage tests."""
    print("=" * 60)
    print("SpaceVoice HVAC Triage Logic Stress Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Run main triage tests
    result = await run_triage_tests()

    # Run additional tests
    safety_ok = await test_safety_instructions()
    dispatch_ok = await test_dispatch_info()

    # Summary
    print("\n" + "=" * 60)
    print("TRIAGE TEST SUMMARY")
    print("=" * 60)
    print(f"Total Scenarios: {result.total}")
    print(f"Passed: {result.passed}")
    print(f"Failed: {result.failed}")
    print(f"Safety Instructions: {'PASS' if safety_ok else 'FAIL'}")
    print(f"Dispatch Generation: {'PASS' if dispatch_ok else 'FAIL'}")

    # Calculate score
    base_score = (result.passed / result.total * 10) if result.total > 0 else 0
    bonus = 0.5 if safety_ok else 0
    bonus += 0.5 if dispatch_ok else 0
    final_score = min(10, base_score + bonus)

    print(f"\nSAFETY TRIAGE SCORE: {final_score:.1f}/10")

    # List failures
    failures = [r for r in result.results if not r["passed"]]
    if failures:
        print("\nFailed Scenarios:")
        for f in failures:
            print(f"  - {f['name']}: expected {f['expected']}, got {f['actual']}")

    return {
        "score": final_score,
        "total": result.total,
        "passed": result.passed,
        "failed": result.failed,
        "safety_instructions": safety_ok,
        "dispatch_generation": dispatch_ok,
        "failures": [f["name"] for f in failures],
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    # Exit with error if score is too low
    sys.exit(0 if result["score"] >= 7 else 1)
