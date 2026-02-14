def build_message_history(messages) -> list[dict]:
    """Convert DB messages into OpenAI chat message format.

    Args:
        messages: List of Message model instances, ordered by sent_at ASC.

    Returns:
        List of {"role": "user"|"assistant", "content": str} dicts.
    """
    history = []
    for msg in messages:
        role = "user" if msg.role == "buyer" else "assistant"
        history.append({"role": role, "content": msg.content})
    return history
