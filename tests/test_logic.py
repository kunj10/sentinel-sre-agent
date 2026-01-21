"""
Logic Tests
-----------
These tests verify that the brain makes smart decisions, not just any decision.

The key insight: an SRE bot that blindly restarts everything is worse than useless.
We need to test that it knows when NOT to restart - like when the real problem
is an external database that's down.
"""

import pytest
from modules.rca_brain import SREBrain


def test_smart_refusal():
    """
    Verify the brain escalates (not restarts) when the issue is external.

    Scenario: A container can't connect to a remote database.
    Expected: The brain should say "escalate" or "ignore" - restarting
    the local container won't fix a remote DB being down.

    This is the kind of nuance that separates a useful SRE bot from a
    dangerous one that just restarts everything.
    """
    brain = SREBrain()
    brain.load_production_weights("modules/brain_compiled.json")

    logs = "CRITICAL: Database Connection Refused to 192.168.1.50:5432"
    container = "chaos-monkey"

    prediction = brain(container_name=container, logs=logs)

    print(f"\nReasoning: {prediction.reasoning}")
    print(f"Action: {prediction.suggested_action}")

    # Pass if it recommends anything OTHER than restart
    is_smart_refusal = prediction.suggested_action in ["escalate", "ignore", "none"]

    assert is_smart_refusal, (
        f"FAILED: Brain tried to restart despite external dependency issue! "
        f"Action: {prediction.suggested_action}"
    )

    print("✅ PASSED: Brain correctly identified external dependency issue.")


if __name__ == "__main__":
    test_smart_refusal()
