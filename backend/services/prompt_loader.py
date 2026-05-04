"""Load channel and audience definitions from YAML config files.

Provides the same data as the old hardcoded CHANNEL_CONSTRAINTS and AUDIENCE_TONE
dicts, but from editable YAML files in backend/prompts/.
"""

import logging
from pathlib import Path
from functools import lru_cache
import yaml

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=1)
def load_channels() -> dict[str, dict]:
    """Load channel definitions from channels.yaml."""
    path = _PROMPTS_DIR / "channels.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("Loaded %d channel definitions from %s", len(data), path.name)
    return data


@lru_cache(maxsize=1)
def load_audiences() -> dict[str, dict]:
    """Load audience definitions from audiences.yaml."""
    path = _PROMPTS_DIR / "audiences.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("Loaded %d audience definitions from %s", len(data), path.name)
    return data


def get_channel_constraints(channel_value: str) -> dict:
    """Get constraints dict for a channel by its enum value."""
    channels = load_channels()
    return channels.get(channel_value, {})


def get_audience_tone(audience_value: str) -> str:
    """Get tone guidance string for an audience by its enum value."""
    audiences = load_audiences()
    aud = audiences.get(audience_value, {})
    return aud.get("tone_guidance", "")
