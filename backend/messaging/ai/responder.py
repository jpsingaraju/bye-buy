import json
import logging
from dataclasses import dataclass
from typing import Optional

from .client import get_openai_client
from .prompts import build_system_prompt
from .context import build_message_history
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Structured response from the AI."""
    message: str
    deal_status: str = "none"
    agreed_price: Optional[float] = None
    delivery_address: Optional[str] = None
    buyer_offer: Optional[float] = None


async def generate_response(
    listing,
    messages: list,
    conversation_status: str = "active",
    new_buyer_messages: list[str] | None = None,
    agreed_price: float | None = None,
    competing_offer: float | None = None,
    delivery_address: str | None = None,
) -> AIResponse | None:
    """Generate an AI response for a conversation.

    Args:
        listing: The Listing model instance (or None if unmatched).
        messages: List of Message model instances (full conversation history).
        conversation_status: Current conversation status (e.g. "pending_address").
        new_buyer_messages: New buyer messages not yet responded to.
        agreed_price: The agreed-upon price if deal is in pending_address state.
        delivery_address: Saved delivery address for confirmation step.

    Returns:
        AIResponse with message text and deal status, or None on failure.
    """
    client = get_openai_client()
    system_prompt = build_system_prompt(
        listing, conversation_status, agreed_price, competing_offer, delivery_address
    )
    chat_history = build_message_history(messages, new_buyer_messages)

    try:
        response = await client.chat.completions.create(
            model=settings.gpt_model,
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history,
            ],
            temperature=0.7,
            max_completion_tokens=256,
        )

        raw = response.choices[0].message.content.strip()
        return _parse_response(raw)

    except Exception as e:
        logger.error(f"AI response error: {e}")
        return None


def _parse_response(raw: str) -> AIResponse:
    """Parse the JSON response from GPT."""
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)
        return AIResponse(
            message=data.get("message", raw),
            deal_status=data.get("deal_status", "none"),
            agreed_price=data.get("agreed_price"),
            delivery_address=data.get("delivery_address"),
            buyer_offer=data.get("buyer_offer"),
        )
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Failed to parse AI JSON, using raw: {raw[:100]}")
        return AIResponse(message=raw)
