"""Live Environment Validation + Kill Switch.

This module ensures the system CANNOT run live accidentally
or with missing / unsafe configuration.

This guard is NON-OPTIONAL for live trading.
It is a capital-protection mechanism.

ABSOLUTE REQUIREMENTS:
- Live mode must be explicitly enabled
- Missing credentials must HARD FAIL
- Failures default to NO TRADE
"""

import os
from typing import Any


ENV_LIVE_MODE = "LIVE_MODE"
ENV_REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"
ENV_TRADIER_TOKEN = "TRADIER_TOKEN"
ENV_TRADIER_BASE = "TRADIER_BASE"

REQUIRED_VALUE_TRUE = "true"


def validate_live_environment() -> dict[str, Any]:
    """Validate that the live environment is properly configured.

    Checks:
    1. LIVE_MODE must equal "true"
    2. REQUIRE_HUMAN_APPROVAL must equal "true"
    3. TRADIER_TOKEN must be non-empty
    4. TRADIER_BASE must be non-empty

    Returns:
        Dictionary with:
        - ok: bool - True if all checks pass
        - reason: str - Human-readable explanation
    """
    try:
        live_mode = os.environ.get(ENV_LIVE_MODE, "").lower().strip()
        if live_mode != REQUIRED_VALUE_TRUE:
            return {
                "ok": False,
                "reason": "LIVE_MODE disabled",
            }

        human_approval = os.environ.get(ENV_REQUIRE_HUMAN_APPROVAL, "").lower().strip()
        if human_approval != REQUIRED_VALUE_TRUE:
            return {
                "ok": False,
                "reason": "Human approval not enforced",
            }

        tradier_token = os.environ.get(ENV_TRADIER_TOKEN, "").strip()
        if not tradier_token:
            return {
                "ok": False,
                "reason": "TRADIER_TOKEN missing",
            }

        tradier_base = os.environ.get(ENV_TRADIER_BASE, "").strip()
        if not tradier_base:
            return {
                "ok": False,
                "reason": "TRADIER_BASE missing",
            }

        return {
            "ok": True,
            "reason": "Live environment validated",
        }

    except Exception:
        return {
            "ok": False,
            "reason": "Unexpected error during environment validation",
        }


if __name__ == "__main__":
    import json

    original_env = {
        ENV_LIVE_MODE: os.environ.get(ENV_LIVE_MODE),
        ENV_REQUIRE_HUMAN_APPROVAL: os.environ.get(ENV_REQUIRE_HUMAN_APPROVAL),
        ENV_TRADIER_TOKEN: os.environ.get(ENV_TRADIER_TOKEN),
        ENV_TRADIER_BASE: os.environ.get(ENV_TRADIER_BASE),
    }

    def restore_env() -> None:
        """Restore original environment."""
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def clear_env() -> None:
        """Clear all relevant env vars."""
        for key in original_env:
            os.environ.pop(key, None)

    print("=" * 60)
    print("ENV GUARD VALIDATION TESTS")
    print("=" * 60)

    print("\nTEST 1: Missing LIVE_MODE")
    print("-" * 60)
    clear_env()
    result = validate_live_environment()
    print(json.dumps(result, indent=2))

    print("\nTEST 2: LIVE_MODE=true but missing REQUIRE_HUMAN_APPROVAL")
    print("-" * 60)
    clear_env()
    os.environ[ENV_LIVE_MODE] = "true"
    result = validate_live_environment()
    print(json.dumps(result, indent=2))

    print("\nTEST 3: Missing TRADIER_TOKEN")
    print("-" * 60)
    clear_env()
    os.environ[ENV_LIVE_MODE] = "true"
    os.environ[ENV_REQUIRE_HUMAN_APPROVAL] = "true"
    result = validate_live_environment()
    print(json.dumps(result, indent=2))

    print("\nTEST 4: Missing TRADIER_BASE")
    print("-" * 60)
    clear_env()
    os.environ[ENV_LIVE_MODE] = "true"
    os.environ[ENV_REQUIRE_HUMAN_APPROVAL] = "true"
    os.environ[ENV_TRADIER_TOKEN] = "test_token_123"
    result = validate_live_environment()
    print(json.dumps(result, indent=2))

    print("\nTEST 5: All variables set correctly")
    print("-" * 60)
    clear_env()
    os.environ[ENV_LIVE_MODE] = "true"
    os.environ[ENV_REQUIRE_HUMAN_APPROVAL] = "true"
    os.environ[ENV_TRADIER_TOKEN] = "test_token_123"
    os.environ[ENV_TRADIER_BASE] = "https://api.tradier.com/v1/"
    result = validate_live_environment()
    print(json.dumps(result, indent=2))

    restore_env()
