"""Channel Adaptation Engine — adapts content with change log."""

import logging
from backend.services.llm import chat_json, render_template
from backend.services.guidelines import get_rules_as_text
from backend.services.prompt_loader import get_channel_constraints, get_audience_tone
from backend.models.schemas import (
    AdaptationResult,
    ChangeLogEntry,
    Channel,
    Audience,
)

logger = logging.getLogger(__name__)


def run_adaptation(
    content: str,
    guideline_id: str,
    channel: str,
    audience: str,
) -> AdaptationResult:
    """Adapt content for a target channel and audience with a traced change log."""
    rules_text = get_rules_as_text(guideline_id)

    import json
    user_message = render_template(
        "adapt_user.j2",
        channel=channel,
        channel_constraints=json.dumps(get_channel_constraints(channel)),
        audience=audience,
        audience_tone=get_audience_tone(audience),
        rules_text=rules_text,
        content=content,
    )

    result = chat_json("adapt_system.txt", user_message, max_completion_tokens=4096)

    change_log = []
    for entry in result.get("change_log", []):
        try:
            change_log.append(ChangeLogEntry(
                original_text=entry["original_text"],
                changed_text=entry["changed_text"],
                change_type=entry.get("change_type", "terminology"),
                rule_reference=entry.get("rule_reference", ""),
                rationale=entry.get("rationale", ""),
            ))
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed change log entry: %s", e)

    adapted_content = result.get("adapted_content", "")
    word_count = len(adapted_content.split())

    adaptation = AdaptationResult(
        adapted_content=adapted_content,
        word_count=word_count,
        channel=channel,
        audience=audience,
        change_log=change_log,
    )

    logger.info(
        "Adaptation complete: %d words, %d changes logged",
        word_count, len(change_log),
    )
    return adaptation
