from backend.app.models.session import ChatMessage


_sessions: dict[str, list[ChatMessage]] = {}


def get_messages(session_id: str) -> list[ChatMessage]:
    return _sessions.get(session_id, [])


def add_message(session_id: str, role: str, content: str) -> None:

    if session_id not in _sessions:
        _sessions[session_id] = []

    _sessions[session_id].append(
        ChatMessage(
            role=role,
            content=content
        )
    )


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
