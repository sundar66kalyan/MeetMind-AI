from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"


class AnswerResponse(BaseModel):
    question: str
    answer: str
    session_id: str
