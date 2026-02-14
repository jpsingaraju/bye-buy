def build_message_history(messages, new_buyer_messages: list[str] | None = None) -> list[dict]:
    """Convert DB messages into OpenAI chat message format.

    Args:
        messages: List of Message model instances, ordered by sent_at ASC.
            These are the FULL conversation history already in the DB.
        new_buyer_messages: List of new buyer message strings that haven't
            been responded to yet. These get appended as a single user
            message labeled "NEW MESSAGES" so the AI knows what to respond to.

    Returns:
        List of {"role": "user"|"assistant", "content": str} dicts.
    """
    history = []
    for msg in messages:
        role = "user" if msg.role == "buyer" else "assistant"
        history.append({"role": role, "content": msg.content})

    if new_buyer_messages:
        combined = "\n".join(new_buyer_messages)
        history.append({
            "role": "user",
            "content": f"[NEW MESSAGES - respond to these only]\n{combined}",
        })

    return history
