from fastapi import WebSocket


connections: dict[str, set[WebSocket]] = {}


async def connect(session_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    connections.setdefault(session_id, set()).add(websocket)


def disconnect(session_id: str, websocket: WebSocket) -> None:
    if session_id in connections:
        connections[session_id].discard(websocket)

        if not connections[session_id]:
            del connections[session_id]


async def broadcast(session_id: str, message: dict) -> None:
    for websocket in list(connections.get(session_id, set())):
        try:
            await websocket.send_json(message)
        except Exception:
            disconnect(session_id, websocket)
