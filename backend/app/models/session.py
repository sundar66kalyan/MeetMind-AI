from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatSession(BaseModel):
    session_id: str
    messages: list[ChatMessage] = []
